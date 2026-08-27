import type { Ref } from 'react';

import { EmptyState } from '@/components/EmptyState';
import { Chip } from '@/components/ui/Chip';

import { MessageFeedback } from './MessageFeedback';
import { RichText } from './RichText';
import { EXAMPLE_QUESTIONS, type UiMessage } from './types';

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
    <div className="flex-1 space-y-4 overflow-auto px-4 py-4">
      {messages.length === 0 && (
        <div className="flex h-full min-h-[220px] flex-col items-center justify-center">
          <EmptyState title="选择知识库后开始提问" description="回答会附带可核验的证据引用" />
          <div className="mt-4 flex max-w-lg flex-wrap justify-center gap-2">
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
          <div key={m.id} className={['flex', isUser ? 'justify-end' : 'justify-start'].join(' ')}>
            <div
              className={[
                'max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed shadow-panel',
                isUser
                  ? 'whitespace-pre-wrap bg-accent text-white'
                  : 'border border-line bg-surface text-ink',
              ].join(' ')}
            >
              {m.role === 'assistant' ? (
                m.content ? (
                  <RichText
                    content={m.content}
                    activeCitation={activeCitation}
                    onCitationClick={onCitationClick}
                  />
                ) : (
                  <span className="text-ink-faint">…</span>
                )
              ) : (
                m.content
              )}
              {m.role === 'assistant' && m.status === 'streaming' && (
                <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-accent align-middle" />
              )}
              {m.role === 'assistant' && m.status === 'failed' && (
                <p className="mt-2 text-xs text-danger">生成失败，可重新生成</p>
              )}
              {m.role === 'assistant' && (m.status === 'completed' || lastAssistant) && (
                <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-line/60 pt-2">
                  {m.status === 'completed' && (
                    <MessageFeedback messageId={m.id} initial={m.feedback} disabled={streaming} />
                  )}
                  {lastAssistant && (
                    <button
                      type="button"
                      disabled={streaming}
                      onClick={() => void onRegenerate()}
                      className="rounded-md px-1.5 py-0.5 text-xs text-ink-muted hover:bg-elevated hover:text-ink disabled:opacity-50"
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
  );
}
