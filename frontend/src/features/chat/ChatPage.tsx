import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { useKnowledgeBases } from '@/features/knowledge/hooks';

import * as chatApi from './api';
import type { Citation, ChatMessage } from './api';
import { ChatRightPanel } from './ChatRightPanel';
import { MessageFeedback } from './MessageFeedback';
import { useConversations, useDeleteConversation, useMessages } from './hooks';

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
  const [rightMode, setRightMode] = useState<'list' | 'pdf'>('list');
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
    setError(null);
  }

  function selectConversation(id: string) {
    abortRef.current?.abort();
    setLiveMessages([]);
    setActiveCitation(null);
    setRightMode('list');
    setError(null);
    setConversationId(id);
  }

  function openCitation(n: number) {
    setActiveCitation(n);
    setRightMode('pdf');
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
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
      for await (const ev of chatApi.streamChatCompletions(
        {
          conversation_id: conversationId,
          ...(conversationId ? {} : { kb_ids: selectedKbIds }),
          message: text,
        },
        ac.signal,
      )) {
        const data = ev.data as Record<string, unknown>;
        if (ev.event === 'message_created') {
          const cid = String(data.conversation_id);
          const mid = String(data.message_id);
          setConversationId(cid);
          setLiveMessages((prev) =>
            prev.map((m, i) => (i === prev.length - 1 ? { ...m, id: mid } : m)),
          );
        } else if (ev.event === 'citations') {
          const citations = (data.citations as Citation[]) ?? [];
          setLiveMessages((prev) =>
            prev.map((m, i) => (i === prev.length - 1 ? { ...m, citations } : m)),
          );
        } else if (ev.event === 'delta') {
          const chunk = asString(data.text);
          setLiveMessages((prev) =>
            prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, content: m.content + chunk } : m,
            ),
          );
        } else if (ev.event === 'no_answer') {
          const reason = asString(data.reason) || 'no_relevant_evidence';
          setLiveMessages((prev) =>
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
          setError(`拒答：${reason}`);
        } else if (ev.event === 'done') {
          const used = Array.isArray(data.used_citations)
            ? (data.used_citations as number[])
            : [];
          setLiveMessages((prev) =>
            prev.map((m, i) =>
              i === prev.length - 1
                ? { ...m, status: 'completed', used_citations: used }
                : m,
            ),
          );
        } else if (ev.event === 'error') {
          setError(asString(data.message) || '流式问答失败');
          setLiveMessages((prev) =>
            prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, status: 'failed' } : m,
            ),
          );
        }
      }
      void refetchConversations();
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError(err instanceof Error ? err.message : '问答失败');
        setLiveMessages((prev) =>
          prev.map((m, i) =>
            i === prev.length - 1 ? { ...m, status: 'failed' } : m,
          ),
        );
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-5.5rem)] max-w-6xl gap-4">
      <aside className="flex w-56 shrink-0 flex-col overflow-hidden panel">
        <div className="flex items-center justify-between border-b border-line px-3 py-2">
          <span className="text-sm font-medium text-ink">会话</span>
          <button
            type="button"
            className="text-xs text-brand-700 hover:underline"
            onClick={startNewChat}
          >
            新对话
          </button>
        </div>
        <ul className="flex-1 space-y-1 overflow-auto p-2">
          {conversations.map((c) => (
            <li key={c.id} className="group flex items-center gap-1">
              <button
                type="button"
                onClick={() => selectConversation(c.id)}
                className={[
                  'min-w-0 flex-1 truncate rounded-md px-2 py-1.5 text-left text-sm',
                  conversationId === c.id
                    ? 'bg-brand-50 font-medium text-brand-700'
                    : 'text-ink hover:bg-canvas',
                ].join(' ')}
              >
                {c.title || '未命名'}
              </button>
              <button
                type="button"
                className="hidden shrink-0 px-1 text-xs text-ink-faint group-hover:inline hover:text-danger"
                onClick={() => {
                  void deleteConv.mutateAsync(c.id).then(() => {
                    if (conversationId === c.id) startNewChat();
                  });
                }}
              >
                删
              </button>
            </li>
          ))}
          {conversations.length === 0 && (
            <li className="px-2 py-4 text-center text-xs text-ink-faint">暂无历史会话</li>
          )}
        </ul>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden panel">
        <div className="border-b border-line px-4 py-3">
          <h1 className="text-sm font-semibold text-ink">问答</h1>
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
                    'rounded border px-2.5 py-0.5 text-xs transition-colors duration-150',
                    on
                      ? 'border-brand-500 bg-brand-50 text-brand-700'
                      : 'border-line text-ink-muted',
                    conversationId ? 'opacity-60' : '',
                  ].join(' ')}
                  title={conversationId ? '会话已绑定知识库' : undefined}
                >
                  {kb.name}
                  {kb.doc_count > 0 ? ` · ${kb.doc_count}` : ''}
                </button>
              );
            })}
            {!kbLoading && bases.length === 0 && (
              <span className="text-xs text-warn">请先在知识库页创建并上传文档</span>
            )}
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-auto px-4 py-4">
          {displayMessages.length === 0 && (
            <p className="py-12 text-center text-sm text-ink-faint">
              选择知识库后提问，例如：「HYD-2201 保养周期是多久？」
            </p>
          )}
          {displayMessages.map((m) => (
            <div
              key={m.id}
              className={['flex', m.role === 'user' ? 'justify-end' : 'justify-start'].join(' ')}
            >
              <div
                className={[
                  'max-w-[85%] rounded px-3.5 py-2.5 text-sm leading-relaxed',
                  m.role === 'user' ? 'bg-brand-600 text-white' : 'border border-line bg-surface text-ink',
                ].join(' ')}
              >
                <MessageBody
                  content={m.content}
                  isAssistant={m.role === 'assistant'}
                  activeCitation={activeCitation}
                  onCitationClick={openCitation}
                />
                {m.role === 'assistant' && m.status === 'streaming' && (
                  <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-ink-faint align-middle" />
                )}
                {m.role === 'assistant' && m.status === 'completed' && (
                  <MessageFeedback
                    messageId={m.id}
                    initial={m.feedback}
                    disabled={streaming}
                  />
                )}
              </div>
            </div>
          ))}
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
          <button
            type="submit"
            className="btn-primary shrink-0"
            disabled={streaming || !input.trim()}
          >
            {streaming ? '生成中…' : '发送'}
          </button>
        </form>
        {error && <p className="px-3 pb-3 text-sm text-danger">{error}</p>}
      </section>

      <div className="hidden w-80 shrink-0 lg:block">
        <ChatRightPanel
          citations={panelCitations}
          activeIndex={activeCitation}
          usedCitations={panelUsed}
          mode={rightMode}
          onSelectCitation={openCitation}
          onBackToList={() => setRightMode('list')}
        />
      </div>
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

function MessageBody({
  content,
  isAssistant,
  activeCitation,
  onCitationClick,
}: {
  content: string;
  isAssistant: boolean;
  activeCitation: number | null;
  onCitationClick: (n: number) => void;
}) {
  if (!isAssistant || !content) {
    return <>{content || (isAssistant ? '…' : '')}</>;
  }

  const parts = content.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const m = /^\[(\d+)\]$/.exec(part);
        if (!m) return <span key={i}>{part}</span>;
        const n = Number(m[1]);
        const active = activeCitation === n;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onCitationClick(n)}
            className={[
              'mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded px-1 text-xs font-medium',
              active
                ? 'bg-brand-600 text-white'
                : 'bg-surface/80 text-brand-700 ring-1 ring-brand-200',
            ].join(' ')}
          >
            {n}
          </button>
        );
      })}
    </>
  );
}
