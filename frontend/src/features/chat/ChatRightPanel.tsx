import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { PdfHighlightViewer } from '@/components/PdfHighlightViewer';
import type { PdfBBox } from '@/components/PdfHighlightViewer';
import { TextPreview } from '@/components/TextPreview';

import * as kbApi from '@/features/knowledge/api';

import type { Citation } from './api';
import { EvidencePanel } from './EvidencePanel';

type Props = {
  citations: Citation[];
  activeIndex: number | null;
  usedCitations?: number[] | null | undefined;
  mode: 'list' | 'preview';
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
  const docId = active?.document_id;

  const { data: doc, isLoading: docLoading, error: docError } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => kbApi.getDocument(docId!),
    enabled: mode === 'preview' && Boolean(docId),
  });

  const isPdf = kbApi.isPdfMime(doc?.mime_type);

  const { data: preview, isLoading: previewLoading, error: previewError } = useQuery({
    queryKey: ['preview-url', docId],
    queryFn: () => kbApi.getPreviewUrl(docId!),
    enabled: mode === 'preview' && Boolean(docId) && isPdf,
    staleTime: 10 * 60 * 1000,
  });

  const { data: pages = [], isLoading: pagesLoading, error: pagesError } = useQuery({
    queryKey: ['document-pages', docId],
    queryFn: () => kbApi.listPages(docId!),
    enabled: mode === 'preview' && Boolean(docId) && Boolean(doc) && !isPdf,
  });

  if (mode !== 'preview' || !active) {
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

  const loading = docLoading || (isPdf ? previewLoading : pagesLoading);
  const error = docError || previewError || pagesError;

  return (
    <aside className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-line/70 px-3 py-2.5">
        <button
          type="button"
          className="rounded-full px-2 py-1 text-xs font-medium text-accent transition-all duration-200 hover:bg-accent-soft"
          onClick={onBackToList}
        >
          ← 返回证据
        </button>
        <div className="min-w-0 flex-1 truncate text-right text-xs text-ink-muted">
          [{active.index_no}] {active.document_title || '文档'} · p.{active.page_start}
        </div>
      </div>
      <div className="border-b border-line/70 px-3 py-1.5 text-right">
        <Link
          className="rounded-full px-2 py-1 text-xs text-ink-muted transition-colors duration-200 hover:bg-accent-soft hover:text-accent"
          to={`/documents/${active.document_id}?page=${active.page_start}${
            active.chunk_id ? `&chunk=${active.chunk_id}` : ''
          }`}
        >
          打开文档详情
        </Link>
      </div>
      <div className="min-h-0 flex-1">
        {loading && <p className="p-4 text-sm text-ink-muted">加载预览…</p>}
        {error && <p className="p-4 text-sm text-danger">预览失败</p>}
        {!loading && !error && isPdf && preview?.url && (
          <PdfHighlightViewer
            url={preview.url}
            page={active.page_start || 1}
            bboxes={bboxes}
          />
        )}
        {!loading && !error && doc && !isPdf && (
          <TextPreview
            pages={pages}
            activePage={active.page_start || 1}
            highlightText={active.quote}
          />
        )}
      </div>
    </aside>
  );
}
