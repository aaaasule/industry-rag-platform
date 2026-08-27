import { ChatsCircle, FileMagnifyingGlass, Plus } from '@phosphor-icons/react';
import { Link } from 'react-router-dom';

import { Chip } from '@/components/ui/Chip';
import type { KnowledgeBase } from '@/features/knowledge/api';

type Props = {
  bases: KnowledgeBase[];
  kbLoading: boolean;
  selectedKbIds: string[];
  conversationId: string | null;
  streaming: boolean;
  conversationsCount: number;
  citationsCount: number;
  onToggleKb: (id: string) => void;
  onOpenSessions: () => void;
  onOpenEvidence: () => void;
  onNewChat: () => void;
};

export function ChatToolbar({
  bases,
  kbLoading,
  selectedKbIds,
  conversationId,
  streaming,
  conversationsCount,
  citationsCount,
  onToggleKb,
  onOpenSessions,
  onOpenEvidence,
  onNewChat,
}: Props) {
  const locked = Boolean(conversationId) || streaming;

  return (
    <div className="border-b border-line bg-elevated/60 px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-sm font-semibold text-ink">问答</h1>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="chip-idle inline-flex items-center gap-1 sm:hidden"
            onClick={onOpenSessions}
          >
            <ChatsCircle size={16} weight="duotone" />
            会话{conversationsCount > 0 ? ` · ${conversationsCount}` : ''}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline sm:hidden"
            onClick={onNewChat}
          >
            <Plus size={14} weight="bold" />
            新对话
          </button>
          <button
            type="button"
            className="chip-soft inline-flex items-center gap-1 lg:hidden"
            onClick={onOpenEvidence}
          >
            <FileMagnifyingGlass size={16} weight="duotone" />
            证据{citationsCount > 0 ? ` · ${citationsCount}` : ''}
          </button>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {kbLoading && <span className="text-xs text-ink-faint">加载知识库…</span>}
        {bases.map((kb) => {
          const on = selectedKbIds.includes(kb.id);
          return (
            <Chip
              key={kb.id}
              active={on}
              disabled={locked}
              onClick={() => onToggleKb(kb.id)}
              title={conversationId ? '会话已绑定知识库' : undefined}
              className={locked ? 'opacity-60' : ''}
            >
              {kb.name}
              {kb.doc_count > 0 ? ` · ${kb.doc_count}` : ''}
            </Chip>
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
  );
}
