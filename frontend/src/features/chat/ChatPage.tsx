import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { useKnowledgeBases } from '@/features/knowledge/hooks';

import * as chatApi from './api';
import type { Citation, ChatMessage } from './api';
import { EvidencePanel } from './EvidencePanel';
import { useConversations, useDeleteConversation, useMessages } from './hooks';

type UiMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: string;
  citations?: Citation[];
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
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const { data: history = [] } = useMessages(conversationId);

  // 默认勾选全部知识库（有文档的优先）
  useEffect(() => {
    if (bases.length === 0 || selectedKbIds.length > 0) return;
    const withDocs = bases.filter((b) => b.doc_count > 0).map((b) => b.id);
    setSelectedKbIds(withDocs.length > 0 ? withDocs : bases.map((b) => b.id));
  }, [bases, selectedKbIds.length]);

  const displayMessages: UiMessage[] = useMemo(() => {
    if (liveMessages.length > 0) return liveMessages;
    return history.map((m: ChatMessage) => ({
      id: m.id,
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.content,
      status: m.status,
      citations: m.citations,
    }));
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
    setError(null);
  }

  function selectConversation(id: string) {
    abortRef.current?.abort();
    setLiveMessages([]);
    setActiveCitation(null);
    setError(null);
    setConversationId(id);
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
          setLiveMessages((prev) =>
            prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, status: 'completed' } : m,
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
      <aside className="flex w-56 shrink-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
          <span className="text-sm font-medium text-slate-900">会话</span>
          <button type="button" className="text-xs text-brand-700 hover:underline" onClick={startNewChat}>
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
                    ? 'bg-brand-50 font-medium text-brand-800'
                    : 'text-slate-700 hover:bg-slate-50',
                ].join(' ')}
              >
                {c.title || '未命名'}
              </button>
              <button
                type="button"
                className="hidden shrink-0 px-1 text-xs text-slate-400 group-hover:inline hover:text-red-600"
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
            <li className="px-2 py-4 text-center text-xs text-slate-400">暂无历史会话</li>
          )}
        </ul>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-3">
          <h1 className="text-sm font-semibold text-slate-900">问答</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            {kbLoading && <span className="text-xs text-slate-400">加载知识库…</span>}
            {bases.map((kb) => {
              const on = selectedKbIds.includes(kb.id);
              return (
                <button
                  key={kb.id}
                  type="button"
                  disabled={Boolean(conversationId) || streaming}
                  onClick={() => toggleKb(kb.id)}
                  className={[
                    'rounded-full border px-2.5 py-0.5 text-xs transition',
                    on
                      ? 'border-brand-300 bg-brand-50 text-brand-800'
                      : 'border-slate-200 text-slate-500',
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
              <span className="text-xs text-amber-600">请先在知识库页创建并上传文档</span>
            )}
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-auto px-4 py-4">
          {displayMessages.length === 0 && (
            <p className="py-12 text-center text-sm text-slate-400">
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
                  'max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                  m.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-100 text-slate-800',
                ].join(' ')}
              >
                <MessageBody
                  content={m.content}
                  isAssistant={m.role === 'assistant'}
                  activeCitation={activeCitation}
                  onCitationClick={setActiveCitation}
                />
                {m.role === 'assistant' && m.status === 'streaming' && (
                  <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-slate-400 align-middle" />
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={(e) => void onSubmit(e)}
          className="flex items-end gap-2 border-t border-slate-100 p-3"
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
        {error && <p className="px-3 pb-3 text-sm text-red-600">{error}</p>}
      </section>

      <div className="hidden w-72 shrink-0 lg:block">
        <EvidencePanel
          citations={panelCitations}
          activeIndex={activeCitation}
          onSelect={setActiveCitation}
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
              active ? 'bg-brand-600 text-white' : 'bg-white/80 text-brand-700 ring-1 ring-brand-200',
            ].join(' ')}
          >
            {n}
          </button>
        );
      })}
    </>
  );
}
