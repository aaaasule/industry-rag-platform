import type { Ref } from 'react';
import { RefreshCw } from 'lucide-react';

import { EmptyState } from '@/components/EmptyState';
import { Chip } from '@/components/ui/Chip';
import { cn } from '@/components/ui/cn';

import { MessageFeedback } from './MessageFeedback';
import { RichText } from './RichText';
import {
  EXAMPLE_QUESTIONS,
  formatTokenUsage,
  formatTookMs,
  type UiMessage,
} from './types';

type Props = {
  messages: UiMessage[];
  streaming: boolean;
  activeCitation: number | null;
  bottomRef: Ref<HTMLDivElement>;
  hasKnowledgeBases: boolean;
  onCitationClick: (n: number) => void;
  onExampleClick: (question: string) => void;
  onRegenerate: () => void;
};

export function MessageList({
  messages,
  streaming,
  activeCitation,
  bottomRef,
  hasKnowledgeBases,
  onCitationClick,
  onExampleClick,
  onRegenerate,
}: Props) {
  return (
    <div className="flex-1 space-y-5 overflow-auto bg-[#F9FAFB] px-4 py-5 sm:px-6">
      {messages.length === 0 && (
        <div className="flex h-full min-h-[240px] flex-col items-center justify-center">
          <EmptyState
            title="选择或新建会话开始提问"
            description="回答会附带可核验的证据引用"
          />
          <div className="mt-5 flex max-w-lg flex-wrap justify-center gap-2">
            {EXAMPLE_QUESTIONS.map((q) => (
              <Chip
                key={q}
                disabled={streaming || !hasKnowledgeBases}
                onClick={() => void onExampleClick(q)}
                className="max-w-full disabled:cursor-not-allowed disabled:opacity-50"
              >
                {q}
              </Chip>
            ))}
          </div>
        </div>
      )}
      {messages.map((m, idx) => {
        const lastAssistant =
          m.role === 'assistant' &&
          idx === messages.length - 1 &&
          !m.id.startsWith('local-') &&
          (m.status === 'completed' || m.status === 'failed');
        const isUser = m.role === 'user';
        return (
          <div
            key={m.id}
            className={cn('flex', isUser ? 'justify-end' : 'justify-start')}
          >
            <div
              className={cn(
                'max-w-[min(88%,42rem)] px-4 py-3 text-sm leading-relaxed transition-all duration-200',
                isUser
                  ? 'whitespace-pre-wrap rounded-2xl rounded-br-md bg-indigo-50 text-slate-800 ring-1 ring-indigo-100'
                  : 'rounded-2xl rounded-bl-md border border-slate-200/80 bg-white text-slate-800 shadow-sm',
              )}
            >
              {m.role === 'assistant' ? (
                m.content ? (
                  <RichText
                    content={m.content}
                    activeCitation={activeCitation}
                    onCitationClick={onCitationClick}
                  />
                ) : (
                  <span className="inline-flex items-center gap-1 text-slate-400">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:300ms]" />
                  </span>
                )
              ) : (
                m.content
              )}
              {m.role === 'assistant' && m.status === 'streaming' && m.content ? (
                <span className="ml-1 inline-block h-3.5 w-1 animate-pulse rounded-full bg-indigo-500 align-middle" />
              ) : null}
              {m.role === 'assistant' && m.status === 'failed' && (
                <p className="mt-2 text-xs text-danger">生成失败，可重新生成</p>
              )}
              {m.role === 'assistant' && (m.status === 'completed' || lastAssistant) && (
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2.5">
                  {m.status === 'completed' && (
                    <MessageMeta
                      tookMs={m.took_ms ?? null}
                      tokenUsage={m.token_usage ?? null}
                    />
                  )}
                  {m.status === 'completed' && (
                    <MessageFeedback messageId={m.id} initial={m.feedback} disabled={streaming} />
                  )}
                  {lastAssistant && (
                    <button
                      type="button"
                      disabled={streaming}
                      onClick={() => void onRegenerate()}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500 transition-all duration-200 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600 disabled:opacity-50"
                    >
                      <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.5} />
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
  );
}

function MessageMeta({
  tookMs,
  tokenUsage,
}: {
  tookMs?: number | null;
  tokenUsage?: UiMessage['token_usage'];
}) {
  const took =
    typeof tookMs === 'number' && Number.isFinite(tookMs) && tookMs >= 0
      ? formatTookMs(tookMs)
      : null;
  const tokens = formatTokenUsage(tokenUsage);
  if (!took && !tokens) return null;
  return (
    <p className="mr-auto text-[11px] tabular-nums text-slate-400">
      {[took ? `耗时 ${took}` : null, tokens].filter(Boolean).join(' · ')}
    </p>
  );
}
