import { EmptyState } from '@/components/EmptyState';

import type { Citation } from './api';

interface Props {
  citations: Citation[];
  activeIndex: number | null;
  usedCitations?: number[] | null | undefined;
  onSelect: (indexNo: number) => void;
}

export function EvidencePanel({
  citations,
  activeIndex,
  usedCitations,
  onSelect,
}: Props) {
  if (citations.length === 0) {
    return (
      <aside className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-line/70 px-4 py-3.5">
          <h2 className="text-sm font-semibold text-ink">证据</h2>
        </div>
        <EmptyState
          className="flex-1"
          title="暂无引用片段"
          description="回答生成后，可核验的证据会显示在这里"
        />
      </aside>
    );
  }

  const usedSet =
    usedCitations && usedCitations.length > 0 ? new Set(usedCitations) : null;

  return (
    <aside className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-line/70 bg-gradient-to-b from-elevated/70 to-transparent px-4 py-3.5">
        <h2 className="text-sm font-semibold text-ink">证据（{citations.length}）</h2>
      </div>
      <ul className="flex-1 space-y-2.5 overflow-auto p-3">
        {citations.map((c) => {
          const active = activeIndex === c.index_no;
          const unused = usedSet !== null && !usedSet.has(c.index_no);
          return (
            <li key={`${c.document_id}-${c.index_no}`}>
              <button
                type="button"
                onClick={() => onSelect(c.index_no)}
                className={[
                  'w-full rounded-xl border px-3.5 py-3 text-left shadow-sm transition-all duration-200',
                  active
                    ? 'border-accent/40 bg-accent-soft shadow-md ring-1 ring-accent/15'
                    : 'border-line/80 bg-surface hover:-translate-y-0.5 hover:border-accent/30 hover:shadow-md',
                  unused ? 'opacity-45' : '',
                ].join(' ')}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={[
                      'inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1.5 text-xs font-semibold',
                      active
                        ? 'bg-gradient-to-br from-indigo-500 to-violet-600 text-white'
                        : 'bg-elevated text-ink-muted',
                    ].join(' ')}
                  >
                    {c.index_no}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs font-semibold text-ink">
                    {c.document_title || '文档'}
                  </span>
                  <span className="shrink-0 rounded-full bg-elevated px-2 py-0.5 text-[10px] font-medium text-ink-faint">
                    p.{c.page_start}
                  </span>
                  {unused && (
                    <span className="shrink-0 rounded-full bg-elevated px-2 py-0.5 text-[10px] text-ink-faint">
                      未引用
                    </span>
                  )}
                </div>
                <p className="mt-2 line-clamp-4 text-sm leading-relaxed text-ink-muted">
                  {c.quote}
                </p>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
