import type { Citation } from './api';

interface Props {
  citations: Citation[];
  activeIndex: number | null;
  onSelect: (indexNo: number) => void;
}

export function EvidencePanel({ citations, activeIndex, onSelect }: Props) {
  if (citations.length === 0) {
    return (
      <aside className="flex h-full flex-col rounded-xl border border-dashed border-slate-300 bg-white p-4">
        <h2 className="text-sm font-medium text-slate-900">证据</h2>
        <p className="mt-3 text-sm text-slate-500">回答生成后，引用片段会显示在这里。</p>
      </aside>
    );
  }

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-medium text-slate-900">证据（{citations.length}）</h2>
      </div>
      <ul className="flex-1 space-y-2 overflow-auto p-3">
        {citations.map((c) => {
          const active = activeIndex === c.index_no;
          return (
            <li key={`${c.document_id}-${c.index_no}`}>
              <button
                type="button"
                onClick={() => onSelect(c.index_no)}
                className={[
                  'w-full rounded-lg border px-3 py-2 text-left transition',
                  active
                    ? 'border-brand-300 bg-brand-50'
                    : 'border-slate-200 bg-white hover:border-slate-300',
                ].join(' ')}
              >
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span
                    className={[
                      'inline-flex h-5 min-w-5 items-center justify-center rounded px-1 font-medium',
                      active ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-700',
                    ].join(' ')}
                  >
                    {c.index_no}
                  </span>
                  <span className="truncate">
                    {c.document_title || '文档'} · p.{c.page_start}
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-4 text-sm text-slate-700">{c.quote}</p>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
