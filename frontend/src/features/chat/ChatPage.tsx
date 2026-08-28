import { useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import { SideSheet } from '@/components/SideSheet';
import { useToast } from '@/components/toast/useToast';
import { useKnowledgeBases } from '@/features/knowledge/hooks';

import * as chatApi from './api';
import type { Citation, ChatMessage } from './api';
import { ChatComposer } from './ChatComposer';
import { ChatRightPanel } from './ChatRightPanel';
import { ChatToolbar } from './ChatToolbar';
import { ConversationList } from './ConversationList';
import { MessageList } from './MessageList';
import { useConversations, useDeleteConversation, useMessages } from './hooks';
import type { UiMessage } from './types';

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
              took_ms: null,
              token_usage: null,
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

  return (
    <div className="page-fill gap-3 xl:gap-4">
      <aside className="panel hidden h-full min-h-0 w-52 shrink-0 overflow-hidden sm:block xl:w-60">
        <ConversationList
          conversations={conversations}
          activeId={conversationId}
          onSelect={selectConversation}
          onDelete={deleteConversation}
          onNew={startNewChat}
          showHeader
        />
      </aside>

      <section className="panel flex min-w-0 flex-1 flex-col overflow-hidden">
        <ChatToolbar
          bases={bases}
          kbLoading={kbLoading}
          selectedKbIds={selectedKbIds}
          conversationId={conversationId}
          streaming={streaming}
          conversationsCount={conversations.length}
          citationsCount={panelCitations.length}
          onToggleKb={toggleKb}
          onOpenSessions={() => {
            setEvidenceOpen(false);
            setSessionsOpen(true);
          }}
          onOpenEvidence={() => {
            setSessionsOpen(false);
            setRightMode('list');
            setEvidenceOpen(true);
          }}
          onNewChat={startNewChat}
        />

        <MessageList
          messages={displayMessages}
          streaming={streaming}
          activeCitation={activeCitation}
          bottomRef={bottomRef}
          hasKnowledgeBases={bases.length > 0}
          onCitationClick={openCitation}
          onExampleClick={(q) => {
            void onExampleClick(q);
          }}
          onRegenerate={() => {
            void regenerateLast();
          }}
        />

        <ChatComposer
          input={input}
          streaming={streaming}
          error={error}
          onInputChange={setInput}
          onSubmit={(e) => void onSubmit(e)}
          onStop={stopStreaming}
        />
      </section>

      <div className="panel hidden h-full min-h-0 w-72 shrink-0 overflow-hidden lg:block xl:w-80">
        {evidencePanel}
      </div>

      <SideSheet
        open={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        title="会话"
        side="left"
        className="sm:hidden"
      >
        <ConversationList
          conversations={conversations}
          activeId={conversationId}
          onSelect={selectConversation}
          onDelete={deleteConversation}
          onNew={startNewChat}
          showHeader={false}
        />
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

function toUi(m: ChatMessage): UiMessage {
  return {
    id: m.id,
    role: m.role === 'user' ? 'user' : 'assistant',
    content: m.content,
    status: m.status,
    citations: m.citations,
    used_citations: m.used_citations,
    feedback: m.feedback,
    token_usage: m.token_usage ?? null,
    took_ms: m.took_ms ?? null,
  };
}

function parseTokenUsage(raw: unknown): UiMessage['token_usage'] {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  const prompt = Number(obj.prompt_tokens ?? 0);
  const completion = Number(obj.completion_tokens ?? 0);
  if (!Number.isFinite(prompt) && !Number.isFinite(completion)) return null;
  return {
    prompt_tokens: Number.isFinite(prompt) ? prompt : 0,
    completion_tokens: Number.isFinite(completion) ? completion : 0,
  };
}

function parseTookMs(raw: unknown): number | null {
  if (typeof raw === 'number' && Number.isFinite(raw)) return Math.max(0, Math.round(raw));
  if (typeof raw === 'string' && raw.trim() !== '' && Number.isFinite(Number(raw))) {
    return Math.max(0, Math.round(Number(raw)));
  }
  return null;
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
      const tookMs = parseTookMs(data.took_ms);
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1
            ? {
                ...m,
                content: '未找到足够相关的资料，请换一种问法或补充上传文档。',
                status: 'completed',
                took_ms: tookMs,
                token_usage: null,
              }
            : m,
        ),
      );
      ctx.setError(`拒答：${reason}`);
    } else if (ev.event === 'done') {
      const used = Array.isArray(data.used_citations)
        ? (data.used_citations as number[])
        : [];
      const tookMs = parseTookMs(data.took_ms);
      const tokenUsage = parseTokenUsage(data.usage);
      ctx.setLiveMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1
            ? {
                ...m,
                status: 'completed',
                used_citations: used,
                took_ms: tookMs,
                token_usage: tokenUsage ?? null,
              }
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

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
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
