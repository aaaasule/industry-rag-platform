import { useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { SideSheet } from '@/components/SideSheet';
import { useToast } from '@/components/toast/useToast';
import { useKnowledgeBases } from '@/features/knowledge/hooks';

import * as chatApi from './api';
import type { Citation, ChatMessage, Conversation } from './api';
import { ChatRightPanel } from './ChatRightPanel';
import { MessageFeedback } from './MessageFeedback';
import { RichText } from './RichText';
import { useConversations, useDeleteConversation, useMessages } from './hooks';

const EXAMPLE_QUESTIONS = [
  'HYD-2201 保养周期是多久？',
  '设备检修作业有哪些安全规范？',
  'Agent 的组成部分是什么？',
];

type UiMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: string;
  citations?: Citation[];
  used_citations?: number[] | undefined;
  feedback?: ChatMessage['feedback'];
};

export function ChatPage() {
  const toast = useToast();
  const { data: bases = [], isLoading: kbLoading } = useKnowledgeBases();
  const { data: conversations = [], refetch: refetchConversations } = useConversations();
  const deleteConv = useDeleteConversation();

  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveMessages, setLiveMessages] = useState<UiMessage[]>([]);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [rightMode, setRightMode] = useState<'list' | 'preview'>('list');
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const { data: history = [] } = useMessages(conversationId);

  useEffect(() => {
    if (bases.length === 0 || selectedKbIds.length > 0) return;
    const withDocs = bases.filter((b) => b.doc_count > 0).map((b) => b.id);
    setSelectedKbIds(withDocs.length > 0 ? withDocs : bases.map((b) => b.id));
  }, [bases, selectedKbIds.length]);

  const displayMessages: UiMessage[] = useMemo(() => {
    if (liveMessages.length > 0) return liveMessages;
    return history.map(toUi);
  }, [history, liveMessages]);

  const panelCitations = useMemo(() => {
    for (let i = displayMessages.length - 1; i >= 0; i -= 1) {
      const m = displayMessages[i];
      if (
        m !== undefined &&
        m.role === 'assistant' &&
        m.citations &&
        m.citations.length > 0
      ) {
        return m.citations;
      }
    }
    return [];
  }, [displayMessages]);

  const panelUsed = useMemo(() => {
    for (let i = displayMessages.length - 1; i >= 0; i -= 1) {
      const m = displayMessages[i];
      if (m !== undefined && m.role === 'assistant' && m.citations && m.citations.length > 0) {
        return m.used_citations ?? null;
      }
    }
    return null;
  }, [displayMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, streaming]);

  function toggleKb(id: string) {
    setSelectedKbIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function startNewChat() {
    abortRef.current?.abort();
    setConversationId(null);
    setLiveMessages([]);
    setActiveCitation(null);
    setRightMode('list');
    setEvidenceOpen(false);
    setSessionsOpen(false);
    setError(null);
  }

  function selectConversation(id: string) {
    abortRef.current?.abort();
    setLiveMessages([]);
    setActiveCitation(null);
    setRightMode('list');
    setEvidenceOpen(false);
    setSessionsOpen(false);
    setError(null);
    setConversationId(id);
  }

  function deleteConversation(id: string) {
    void deleteConv.mutateAsync(id).then(() => {
      if (conversationId === id) startNewChat();
      toast.success('已删除会话');
    });
  }

  function openCitation(n: number) {
    setActiveCitation(n);
    setRightMode('preview');
    setEvidenceOpen(true);
  }

  function stopStreaming() {
    abortRef.current?.abort();
  }

  async function submitText(text: string) {
    if (!text || streaming) return;
    if (!conversationId && selectedKbIds.length === 0) {
      setError('请至少选择一个知识库');
      return;
    }

    setError(null);
    setInput('');
    setStreaming(true);
    setActiveCitation(null);
    setRightMode('list');

    const userMsg: UiMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: text,
    };
    const asstMsg: UiMessage = {
      id: `local-asst-${Date.now()}`,
      role: 'assistant',
      content: '',
      status: 'streaming',
      citations: [],
      used_citations: [],
    };
    setLiveMessages((prev) => {
      const base = prev.length > 0 ? prev : history.map(toUi);
      return [...base, userMsg, asstMsg];
    });

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      await consumeAssistantStream(
        chatApi.streamChatCompletions(
          {
            conversation_id: conversationId,
            ...(conversationId ? {} : { kb_ids: selectedKbIds }),
            message: text,
          },
          ac.signal,
        ),
        {
          setConversationId,
          setLiveMessages,
          setError,
        },
      );
      void refetchConversations();
    } catch (err) {
      handleStreamError(err, setLiveMessages, setError, toast);
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await submitText(input.trim());
  }

  async function onExampleClick(question: string) {
    if (streaming) return;
    if (!conversationId && selectedKbIds.length === 0) {
      setError('请至少选择一个知识库');
      return;
    }
    await submitText(question);
  }

  async function regenerateLast() {
    if (streaming) return;
    const base = liveMessages.length > 0 ? liveMessages : history.map(toUi);
    const last = base[base.length - 1];
    if (!last || last.role !== 'assistant' || last.id.startsWith('local-')) return;
    if (last.status !== 'completed' && last.status !== 'failed') return;

    setError(null);
    setStreaming(true);
    setActiveCitation(null);
    setRightMode('list');
    setLiveMessages(
      base.map((m, i) =>
        i === base.length - 1
          ? {
              ...m,
              content: '',
              status: 'streaming',
              citations: [],
              used_citations: [],
              feedback: undefined,
            }
          : m,
      ),
    );

    const ac = new AbortController();
    abortRef.current = ac;
    try {
      await consumeAssistantStream(chatApi.streamRegenerate(last.id, ac.signal), {
        setConversationId,
        setLiveMessages,
        setError,
      });
      void refetchConversations();
    } catch (err) {
      handleStreamError(err, setLiveMessages, setError, toast);
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  const evidencePanel = (
    <ChatRightPanel
      citations={panelCitations}
      activeIndex={activeCitation}
      usedCitations={panelUsed}
      mode={rightMode}
      onSelectCitation={openCitation}
      onBackToList={() => setRightMode('list')}
    />
  );

  const sessionList = (
    <ConversationList
      conversations={conversations}
      activeId={conversationId}
      onSelect={selectConversation}
      onDelete={deleteConversation}
      onNew={startNewChat}
      showHeader
    />
  );

  return (
    <div className="page-fill gap-3 xl:gap-4">
      <aside className="hidden h-full min-h-0 w-52 shrink-0 overflow-hidden panel sm:block xl:w-60">
        {sessionList}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden panel">
        <div className="border-b border-line px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <h1 className="text-sm font-semibold text-ink">问答</h1>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="chip-idle sm:hidden"
                onClick={() => {
                  setEvidenceOpen(false);
                  setSessionsOpen(true);
                }}
              >
                会话{conversations.length > 0 ? ` · ${conversations.length}` : ''}
              </button>
              <button
                type="button"
                className="text-xs font-medium text-brand-700 hover:underline sm:hidden"
                onClick={startNewChat}
              >
                新对话
              </button>
              <button
                type="button"
                className="chip-soft lg:hidden"
                onClick={() => {
                  setSessionsOpen(false);
                  setRightMode('list');
                  setEvidenceOpen(true);
                }}
              >
                证据{panelCitations.length > 0 ? ` · ${panelCitations.length}` : ''}
              </button>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {kbLoading && <span className="text-xs text-ink-faint">加载知识库…</span>}
            {bases.map((kb) => {
              const on = selectedKbIds.includes(kb.id);
              return (
                <button
                  key={kb.id}
                  type="button"
                  disabled={Boolean(conversationId) || streaming}
                  onClick={() => toggleKb(kb.id)}
                  className={[
                    on ? 'chip-active' : 'chip-idle',
                    conversationId || streaming ? 'opacity-60' : '',
                  ].join(' ')}
                  title={conversationId ? '会话已绑定知识库' : undefined}
                >
                  {kb.name}
                  {kb.doc_count > 0 ? ` · ${kb.doc_count}` : ''}
                </button>
              );
            })}
            {!kbLoading && bases.length === 0 && (
              <span className="text-xs text-warn">
                请先在{' '}
                <Link to="/knowledge" className="underline hover:text-ink">
                  知识库
                </Link>{' '}
                页创建并上传文档
              </span>
            )}
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-auto px-4 py-4">
          {displayMessages.length === 0 && (
            <div className="flex h-full min-h-[220px] flex-col items-center justify-center">
              <EmptyState
                title="选择知识库后开始提问"
                description="回答会附带可核验的证据引用"
              />
              <div className="mt-4 flex max-w-md flex-wrap justify-center gap-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    disabled={streaming || bases.length === 0}
                    onClick={() => void onExampleClick(q)}
                    className="chip-idle max-w-full truncate disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {displayMessages.map((m, idx) => {
            const lastAssistant =
              m.role === 'assistant' &&
              idx === displayMessages.length - 1 &&
              !m.id.startsWith('local-') &&
              (m.status === 'completed' || m.status === 'failed');
            return (
            <div
              key={m.id}
              className={['flex', m.role === 'user' ? 'justify-end' : 'justify-start'].join(' ')}
            >
              <div
                className={[
                  'max-w-[85%] rounded px-3.5 py-2.5 text-sm leading-relaxed',
                  m.role === 'user'
                    ? 'whitespace-pre-wrap bg-brand-600 text-white'
                    : 'border border-line bg-surface text-ink',
                ].join(' ')}
              >
                {m.role === 'assistant' ? (
                  m.content ? (
                    <RichText
                      content={m.content}
                      activeCitation={activeCitation}
                      onCitationClick={openCitation}
                    />
                  ) : (
                    <span className="text-ink-faint">…</span>
                  )
                ) : (
                  m.content
                )}
                {m.role === 'assistant' && m.status === 'streaming' && (
                  <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-ink-faint align-middle" />
                )}
                {m.role === 'assistant' && m.status === 'failed' && (
                  <p className="mt-2 text-xs text-danger">生成失败，可重新生成</p>
                )}
                {m.role === 'assistant' && (m.status === 'completed' || lastAssistant) && (
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    {m.status === 'completed' && (
                      <MessageFeedback
                        messageId={m.id}
                        initial={m.feedback}
                        disabled={streaming}
                      />
                    )}
                    {lastAssistant && (
                      <button
                        type="button"
                        disabled={streaming}
                        onClick={() => void regenerateLast()}
                        className="rounded px-1.5 py-0.5 text-xs text-ink-muted hover:bg-canvas hover:text-ink disabled:opacity-50"
                      >
                        重新生成
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={(e) => void onSubmit(e)}
          className="flex items-end gap-2 border-t border-line p-3"
        >
          <textarea
            className="field-input min-h-[44px] flex-1 resize-none"
            rows={2}
            value={input}
            disabled={streaming}
            placeholder="输入问题…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
          />
          {streaming ? (
            <button
              type="button"
              className="shrink-0 rounded-md border border-danger/40 bg-surface px-4 py-2 text-sm font-semibold text-danger transition-colors hover:bg-danger/5"
              onClick={stopStreaming}
            >
              停止
            </button>
          ) : (
            <button type="submit" className="btn-primary shrink-0" disabled={!input.trim()}>
              发送
            </button>
          )}
        </form>
        {error && <p className="px-3 pb-3 text-sm text-danger">{error}</p>}
      </section>

      <div className="hidden h-full min-h-0 w-72 shrink-0 lg:block xl:w-80">{evidencePanel}</div>

      <SideSheet
        open={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        title="会话"
        side="left"
        className="sm:hidden"
      >
        <div className="flex h-full flex-col overflow-hidden panel">
          <ConversationList
            conversations={conversations}
            activeId={conversationId}
            onSelect={selectConversation}
            onDelete={deleteConversation}
            onNew={startNewChat}
            showHeader={false}
          />
        </div>
      </SideSheet>

      <SideSheet
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        title="证据"
        side="right"
        className="lg:hidden"
      >
        {evidencePanel}
      </SideSheet>
    </div>
  );
}

function ConversationList({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNew,
  showHeader,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  showHeader: boolean;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      {showHeader ? (
        <div className="flex items-center justify-between border-b border-line px-3 py-2">
          <span className="text-sm font-medium text-ink">会话</span>
          <button
            type="button"
            className="text-xs font-medium text-brand-700 hover:underline"
            onClick={onNew}
          >
            新对话
          </button>
        </div>
      ) : (
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            className="text-xs font-medium text-brand-700 hover:underline"
            onClick={onNew}
          >
            新对话
          </button>
        </div>
      )}
      <ul className="flex-1 space-y-1 overflow-auto p-2">
        {conversations.map((c) => (
          <li key={c.id} className="group flex items-center gap-1">
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              className={[
                'relative min-w-0 flex-1 truncate rounded-md px-2 py-1.5 pl-2.5 text-left text-sm transition-colors',
                activeId === c.id
                  ? 'bg-brand-50 font-medium text-brand-700 before:absolute before:inset-y-1 before:left-0 before:w-0.5 before:rounded-full before:bg-brand-600'
                  : 'text-ink hover:bg-canvas',
              ].join(' ')}
            >
              {c.title || '未命名'}
            </button>
            <button
              type="button"
              className="shrink-0 px-1 text-xs text-ink-faint hover:text-danger sm:invisible sm:group-hover:visible"
              onClick={() => onDelete(c.id)}
            >
              删
            </button>
          </li>
        ))}
        {conversations.length === 0 && (
          <li>
            <EmptyState compact title="暂无历史会话" description="发送问题后会出现在这里" />
          </li>
        )}
      </ul>
    </div>
  );
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function toUi(m: ChatMessage): UiMessage {
  return {
    id: m.id,
    role: m.role === 'user' ? 'user' : 'assistant',
    content: m.content,
    status: m.status,
    citations: m.citations,
    used_citations: m.used_citations,
    feedback: m.feedback,
  };
}

async function consumeAssistantStream(
  stream: AsyncIterable<{ event: string; data: unknown }>,
  ctx: {
    setConversationId: (id: string) => void;
    setLiveMessages: Dispatch<SetStateAction<UiMessage[]>>;
    setError: (msg: string | null) => void;
  },
) {
  for await (const ev of stream) {
    const data = ev.data as Record<string, unknown>;
    if (ev.event === 'message_created') {
      const cid = String(data.conversation_id);
      const mid = String(data.message_id);
      ctx.setConversationId(cid);
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) => (i === prev.length - 1 ? { ...m, id: mid } : m)),
      );
    } else if (ev.event === 'citations') {
      const citations = (data.citations as Citation[]) ?? [];
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) => (i === prev.length - 1 ? { ...m, citations } : m)),
      );
    } else if (ev.event === 'delta') {
      const chunk = asString(data.text);
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1 ? { ...m, content: m.content + chunk } : m,
        ),
      );
    } else if (ev.event === 'no_answer') {
      const reason = asString(data.reason) || 'no_relevant_evidence';
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1
            ? {
                ...m,
                content: '未找到足够相关的资料，请换一种问法或补充上传文档。',
                status: 'completed',
              }
            : m,
        ),
      );
      ctx.setError(`拒答：${reason}`);
    } else if (ev.event === 'done') {
      const used = Array.isArray(data.used_citations)
        ? (data.used_citations as number[])
        : [];
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1
            ? { ...m, status: 'completed', used_citations: used }
            : m,
        ),
      );
    } else if (ev.event === 'error') {
      ctx.setError(asString(data.message) || '流式问答失败');
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) => (i === prev.length - 1 ? { ...m, status: 'failed' } : m)),
      );
    }
  }
}

function handleStreamError(
  err: unknown,
  setLiveMessages: Dispatch<SetStateAction<UiMessage[]>>,
  setError: (msg: string | null) => void,
  toast: { info: (msg: string) => void },
) {
  if ((err as Error).name === 'AbortError') {
    setLiveMessages((prev) =>
      prev.map((m, i) =>
        i === prev.length - 1 && m.role === 'assistant'
          ? {
              ...m,
              status: 'completed',
              content: m.content.trim() ? m.content : '（已停止生成）',
            }
          : m,
      ),
    );
    toast.info('已停止生成');
    return;
  }
  setError(err instanceof Error ? err.message : '问答失败');
  setLiveMessages((prev) =>
    prev.map((m, i) => (i === prev.length - 1 ? { ...m, status: 'failed' } : m)),
  );
}
