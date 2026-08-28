import { FileSearch, MessagesSquare, PanelRight, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Chip } from '@/components/ui/Chip';
import { cn } from '@/components/ui/cn';
import type { KnowledgeBase } from '@/features/knowledge/api';

type Props = {
  bases: KnowledgeBase[];
  kbLoading: boolean;
  selectedKbIds: string[];
  conversationId: string | null;
  conversationTitle?: string | null;
  streaming: boolean;
  conversationsCount: number;
  citationsCount: number;
  evidenceCollapsed: boolean;
  onToggleKb: (id: string) => void;
  onOpenSessions: () => void;
  onOpenEvidence: () => void;
  onToggleEvidencePanel: () => void;
  onNewChat: () => void;
};

export function ChatToolbar({
  bases,
  kbLoading,
  selectedKbIds,
  conversationId,
  conversationTitle,
  streaming,
  conversationsCount,
  citationsCount,
  evidenceCollapsed,
  onToggleKb,
  onOpenSessions,
  onOpenEvidence,
  onToggleEvidencePanel,
  onNewChat,
}: Props) {
  const locked = Boolean(conversationId) || streaming;
  const title = conversationId
    ? conversationTitle || '当前会话'
    : '新会话';

  return (
    <div className="border-b border-slate-200/60 bg-white px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold tracking-tight text-slate-900">
            {title}
          </h1>
          <p className="mt-0.5 text-[11px] text-slate-400">
            {conversationId ? '已绑定知识库' : '选择知识库后开始提问'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600 transition-all duration-200 hover:bg-slate-50 sm:hidden"
            onClick={onOpenSessions}
          >
            <MessagesSquare className="h-4 w-4" strokeWidth={1.5} />
            会话{conversationsCount > 0 ? ` · ${conversationsCount}` : ''}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-600 transition-all duration-200 hover:bg-indigo-100 sm:hidden"
            onClick={onNewChat}
          >
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            新建
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg border border-indigo-100 bg-indigo-50/80 px-2.5 py-1.5 text-xs font-medium text-indigo-600 transition-all duration-200 hover:bg-indigo-100 lg:hidden"
            onClick={onOpenEvidence}
          >
            <FileSearch className="h-4 w-4" strokeWidth={1.5} />
            证据{citationsCount > 0 ? ` · ${citationsCount}` : ''}
          </button>
          <button
            type="button"
            className="hidden items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600 transition-all duration-200 hover:bg-slate-50 lg:inline-flex"
            onClick={onToggleEvidencePanel}
            title={evidenceCollapsed ? '展开证据面板' : '收起证据面板'}
          >
            <PanelRight className="h-4 w-4" strokeWidth={1.5} />
            {evidenceCollapsed ? '证据' : '收起证据'}
            {citationsCount > 0 ? ` · ${citationsCount}` : ''}
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {kbLoading && <span className="text-xs text-slate-400">加载知识库…</span>}
        {bases.map((kb) => {
          const on = selectedKbIds.includes(kb.id);
          return (
            <Chip
              key={kb.id}
              active={on}
              disabled={locked}
              onClick={() => onToggleKb(kb.id)}
              title={conversationId ? '会话已绑定知识库' : undefined}
              className={cn(locked && 'opacity-60')}
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
