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
      <aside className="flex h-full flex-col panel border-dashed p-4">
        <h2 className="text-sm font-medium text-ink">证据</h2>
        <p className="mt-3 text-sm text-ink-muted">回答生成后，引用片段会显示在这里。</p>
      </aside>
    );
  }

  const usedSet =
    usedCitations && usedCitations.length > 0 ? new Set(usedCitations) : null;

  return (
    <aside className="flex h-full flex-col overflow-hidden panel">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-sm font-medium text-ink">证据（{citations.length}）</h2>
      </div>
      <ul className="flex-1 space-y-2 overflow-auto p-3">
        {citations.map((c) => {
          const active = activeIndex === c.index_no;
          const unused = usedSet !== null && !usedSet.has(c.index_no);
          return (
            <li key={`${c.document_id}-${c.index_no}`}>
              <button
                type="button"
                onClick={() => onSelect(c.index_no)}
                className={[
                  'w-full rounded-lg border px-3 py-2 text-left transition',
                  active
                    ? 'border-brand-300 bg-brand-50'
                    : 'border-line bg-surface hover:border-line',
                  unused ? 'opacity-45' : '',
                ].join(' ')}
              >
                <div className="flex items-center gap-2 text-xs text-ink-muted">
                  <span
                    className={[
                      'inline-flex h-5 min-w-5 items-center justify-center rounded px-1 font-medium',
                      active ? 'bg-brand-600 text-white' : 'bg-canvas text-ink',
                    ].join(' ')}
                  >
                    {c.index_no}
                  </span>
                  <span className="truncate">
                    {c.document_title || '文档'} · p.{c.page_start}
                  </span>
                  {unused && <span className="shrink-0 text-[10px] text-ink-faint">未引用</span>}
                </div>
                <p className="mt-1.5 line-clamp-4 text-sm text-ink">{c.quote}</p>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
