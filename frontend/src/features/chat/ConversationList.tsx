import { useEffect, useMemo, useState } from 'react';
import { MessageSquare, Plus, Search, Trash2, X } from 'lucide-react';

import { EmptyState } from '@/components/EmptyState';
import { cn } from '@/components/ui/cn';

import type { Conversation } from './api';
import { groupConversations } from './conversationGroups';

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
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQuery(query), 300);
    return () => window.clearTimeout(t);
  }, [query]);

  const groups = useMemo(
    () => groupConversations(conversations, debouncedQuery),
    [conversations, debouncedQuery],
  );

  const hasQuery = debouncedQuery.trim().length > 0;
  const emptyTitle = hasQuery ? '未找到相关会话' : '暂无历史会话';
  const emptyDesc = hasQuery ? '试试其他关键词' : '发送问题后会出现在这里';

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#F9FAFB]">
      <div className={cn('shrink-0 space-y-2 p-3', showHeader && 'border-b border-slate-200/60')}>
        {showHeader && (
          <div className="flex items-center gap-2 px-0.5">
            <MessageSquare className="h-4 w-4 text-indigo-600" strokeWidth={1.5} aria-hidden />
            <span className="text-sm font-semibold text-slate-800">会话</span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onNew}
            title="新建会话"
            className={cn(
              'inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-lg px-3',
              'bg-indigo-50 text-sm font-medium text-indigo-600',
              'transition-all duration-200 ease-in-out',
              'hover:bg-indigo-100 active:scale-[0.98]',
            )}
          >
            <Plus className="h-4 w-4" strokeWidth={1.5} aria-hidden />
            新建
          </button>
          <div className="relative min-w-0 flex-1">
            <Search
              className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              strokeWidth={1.5}
              aria-hidden
            />
            <input
              type="search"
              value={query}
              placeholder="搜索会话..."
              aria-label="搜索会话"
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setQuery('');
              }}
              className={cn(
                'w-full rounded-lg bg-slate-100 py-1.5 pl-8 pr-8 text-sm text-slate-700',
                'border-0 outline-none placeholder:text-slate-400',
                'transition-all duration-200',
                'focus:bg-white focus:ring-2 focus:ring-indigo-300',
              )}
            />
            {query ? (
              <button
                type="button"
                aria-label="清空搜索"
                onClick={() => setQuery('')}
                className="absolute right-1.5 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-slate-200/80 hover:text-slate-600"
              >
                <X className="h-3.5 w-3.5" strokeWidth={1.5} />
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-2 pb-3">
        {groups.length === 0 ? (
          <div className="px-1 pt-4">
            <EmptyState compact title={emptyTitle} description={emptyDesc} />
          </div>
        ) : (
          groups.map((group) => (
            <section key={group.key} className="mt-1 first:mt-0">
              <h3 className="px-2 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                {group.label}
              </h3>
              <ul className="flex flex-col gap-0.5">
                {group.items.map((c) => {
                  const active = activeId === c.id;
                  return (
                    <li key={c.id} className="group relative">
                      <button
                        type="button"
                        onClick={() => onSelect(c.id)}
                        className={cn(
                          'relative flex w-full items-center rounded-md px-3 py-2.5 pr-9 text-left text-sm transition-all duration-200',
                          active
                            ? 'bg-indigo-50 font-medium text-indigo-600'
                            : 'text-slate-700 hover:bg-slate-50',
                        )}
                      >
                        {active && (
                          <span
                            className="absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-indigo-600"
                            aria-hidden
                          />
                        )}
                        <span className="truncate">{c.title || '未命名'}</span>
                      </button>
                      <button
                        type="button"
                        aria-label="删除会话"
                        className={cn(
                          'absolute right-1 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md',
                          'text-slate-400 opacity-0 transition-all duration-200',
                          'hover:bg-red-50 hover:text-red-600 group-hover:opacity-100',
                          active && 'opacity-70',
                        )}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(c.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))
        )}
      </div>
    </div>
  );
}
