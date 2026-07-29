import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { PdfHighlightViewer } from '@/components/PdfHighlightViewer';
import type { PdfBBox } from '@/components/PdfHighlightViewer';

import * as kbApi from '@/features/knowledge/api';

import type { Citation } from './api';
import { EvidencePanel } from './EvidencePanel';

type Props = {
  citations: Citation[];
  activeIndex: number | null;
  usedCitations?: number[] | null | undefined;
  mode: 'list' | 'pdf';
  onSelectCitation: (indexNo: number) => void;
  onBackToList: () => void;
};

export function ChatRightPanel({
  citations,
  activeIndex,
  usedCitations,
  mode,
  onSelectCitation,
  onBackToList,
}: Props) {
  const active = citations.find((c) => c.index_no === activeIndex) ?? null;

  const { data: preview, isLoading, error } = useQuery({
    queryKey: ['preview-url', active?.document_id],
    queryFn: () => kbApi.getPreviewUrl(active!.document_id),
    enabled: mode === 'pdf' && Boolean(active?.document_id),
    staleTime: 10 * 60 * 1000,
  });

  if (mode !== 'pdf' || !active) {
    return (
      <EvidencePanel
        citations={citations}
        activeIndex={activeIndex}
        usedCitations={usedCitations}
        onSelect={onSelectCitation}
      />
    );
  }

  const bboxes: PdfBBox[] = (active.bboxes || [])
    .map((b) => {
      const page = Number((b as { page?: unknown }).page);
      const bbox = (b as { bbox?: unknown }).bbox;
      if (!Array.isArray(bbox)) return null;
      return { page, bbox: bbox as number[] };
    })
    .filter((x): x is PdfBBox => x !== null);

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <button
          type="button"
          className="text-xs text-brand-700 hover:underline"
          onClick={onBackToList}
        >
          ← 返回证据
        </button>
        <div className="min-w-0 flex-1 truncate text-right text-xs text-slate-500">
          [{active.index_no}] {active.document_title || '文档'} · p.{active.page_start}
        </div>
      </div>
      <div className="border-b border-slate-50 px-3 py-1.5 text-right">
        <Link
          className="text-xs text-slate-500 hover:text-brand-700"
          to={`/documents/${active.document_id}?page=${active.page_start}${
            active.chunk_id ? `&chunk=${active.chunk_id}` : ''
          }`}
        >
          打开文档详情
        </Link>
      </div>
      <div className="min-h-0 flex-1">
        {isLoading && <p className="p-4 text-sm text-slate-500">加载预览…</p>}
        {error && <p className="p-4 text-sm text-red-600">预览失败</p>}
        {preview?.url && (
          <PdfHighlightViewer
            url={preview.url}
            page={active.page_start || 1}
            bboxes={bboxes}
          />
        )}
      </div>
    </aside>
  );
}
