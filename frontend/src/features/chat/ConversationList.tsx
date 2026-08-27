import { EmptyState } from '@/components/EmptyState';

import type { Conversation } from './api';

type Props = {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  showHeader: boolean;
};

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNew,
  showHeader,
}: Props) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      {showHeader ? (
        <div className="flex items-center justify-between border-b border-line px-3 py-2.5">
          <span className="text-sm font-medium text-ink">会话</span>
          <button
            type="button"
            className="text-xs font-medium text-accent hover:underline"
            onClick={onNew}
          >
            新对话
          </button>
        </div>
      ) : (
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            className="text-xs font-medium text-accent hover:underline"
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
                'relative min-w-0 flex-1 truncate rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
                activeId === c.id
                  ? 'bg-accent-soft font-medium text-accent before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-accent'
                  : 'text-ink-muted hover:bg-elevated hover:text-ink',
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
