import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { PdfHighlightViewer } from '@/components/PdfHighlightViewer';
import type { PdfBBox } from '@/components/PdfHighlightViewer';
import { streamEventsGet } from '@/lib/sse';

import * as kbApi from './api';
import { useDocument, useKnowledgeBase } from './hooks';

type IngestProgressEvent = {
  stage?: string;
  progress?: number;
  page_done?: number;
  page_total?: number;
  chunk_done?: number;
  chunk_total?: number;
  status?: string;
  error_code?: string;
  error_detail?: string;
  chunk_count?: number;
};

export function DocumentDetailPage() {
  const { kbId: kbIdParam = '', docId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const qc = useQueryClient();
  const { data: doc } = useDocument(docId);
  const kbId = kbIdParam && kbIdParam !== '_' ? kbIdParam : (doc?.kb_id ?? '');
  const { data: kb } = useKnowledgeBase(kbId);
  const [ingestHint, setIngestHint] = useState<string | null>(null);

  const chunkParam = searchParams.get('chunk');
  const pageParam = Number(searchParams.get('page') || '0');

  const { data: chunks = [], isLoading: chunksLoading } = useQuery({
    queryKey: ['chunks', docId],
    queryFn: () => kbApi.listChunks(docId),
    enabled: Boolean(docId),
  });

  const { data: preview, error: previewError } = useQuery({
    queryKey: ['preview-url', docId],
    queryFn: () => kbApi.getPreviewUrl(docId),
    enabled: Boolean(docId) && Boolean(doc?.mime_type?.includes('pdf')),
    staleTime: 10 * 60 * 1000,
  });

  const [activeChunkId, setActiveChunkId] = useState<string | null>(chunkParam);
  const [page, setPage] = useState(pageParam > 0 ? pageParam : 1);

  useEffect(() => {
    if (chunkParam) setActiveChunkId(chunkParam);
  }, [chunkParam]);

  useEffect(() => {
    if (pageParam > 0) setPage(pageParam);
  }, [pageParam]);

  const activeChunk = useMemo(
    () => chunks.find((c) => c.id === activeChunkId) ?? null,
    [chunks, activeChunkId],
  );

  const bboxes: PdfBBox[] = useMemo(() => {
    if (!activeChunk) return [];
    return (activeChunk.bboxes || []).map((b) => ({
      page: Number(b.page),
      bbox: b.bbox,
    }));
  }, [activeChunk]);

  useEffect(() => {
    if (activeChunk && !(pageParam > 0)) {
      setPage(activeChunk.page_start || 1);
    }
  }, [activeChunk, pageParam]);

  function selectChunk(chunk: kbApi.ChunkItem) {
    setActiveChunkId(chunk.id);
    setPage(chunk.page_start || 1);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set('chunk', chunk.id);
        next.set('page', String(chunk.page_start || 1));
        return next;
      },
      { replace: true },
    );
  }

  const isPdf = Boolean(doc?.mime_type?.includes('pdf'));
  const inProgress = Boolean(doc && kbApi.IN_PROGRESS.has(doc.status));

  useEffect(() => {
    if (!docId || !inProgress) {
      setIngestHint(null);
      return;
    }
    const ac = new AbortController();
    void (async () => {
      try {
        for await (const ev of streamEventsGet<IngestProgressEvent>(
          `/documents/${docId}/events`,
          { signal: ac.signal },
        )) {
          if (ev.event === 'progress') {
            const d = ev.data;
            const pct = Math.round((d.progress ?? 0) * 100);
            if (d.stage === 'parsing' && d.page_total) {
              setIngestHint(`解析 ${d.page_done ?? 0}/${d.page_total}（${pct}%）`);
            } else if (d.stage === 'embedding' && d.chunk_total) {
              setIngestHint(`向量化 ${d.chunk_done ?? 0}/${d.chunk_total}（${pct}%）`);
            } else {
              setIngestHint(`${d.stage ?? '处理中'} ${pct}%`);
            }
          } else if (ev.event === 'completed' || ev.event === 'failed') {
            setIngestHint(ev.event === 'completed' ? '摄取完成' : `失败：${ev.data.error_code ?? ''}`);
            void qc.invalidateQueries({ queryKey: ['document', docId] });
            void qc.invalidateQueries({ queryKey: ['chunks', docId] });
            if (kbId) void qc.invalidateQueries({ queryKey: ['documents', kbId] });
            break;
          }
        }
      } catch {
        /* 轮询 hook 仍会刷新状态 */
      }
    })();
    return () => ac.abort();
  }, [docId, inProgress, kbId, qc]);

  return (
    <div className="page-fill flex-col gap-3">
      <div>
        <Link
          to={kbId ? `/knowledge/${kbId}` : '/knowledge'}
          className="text-sm text-ink-muted transition-colors hover:text-ink"
        >
          ← {kb?.name ?? '知识库'}
        </Link>
        <h1 className="mt-1 text-lg font-semibold tracking-tight text-ink">
          {doc?.title ?? '文档详情'}
        </h1>
        <p className="text-xs text-ink-faint">
          {doc ? `${kbApi.statusLabel(doc.status)} · ${doc.page_count ?? '—'} 页` : '加载中…'}
          {ingestHint ? ` · ${ingestHint}` : ''}
        </p>
      </div>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-2">
        <section className="panel min-h-0 overflow-hidden">
          {!isPdf && (
            <p className="p-6 text-sm text-ink-muted">当前文件类型暂不支持 PDF 预览。</p>
          )}
          {isPdf && previewError && (
            <p className="p-6 text-sm text-danger">预览地址获取失败</p>
          )}
          {isPdf && preview?.url && (
            <PdfHighlightViewer
              url={preview.url}
              page={page}
              bboxes={bboxes}
              onPageChange={setPage}
            />
          )}
          {isPdf && !preview && !previewError && (
            <p className="p-6 text-sm text-ink-muted">加载预览…</p>
          )}
        </section>

        <aside className="panel flex min-h-0 flex-col overflow-hidden">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-medium text-ink">分块（{chunks.length}）</h2>
          </div>
          <ul className="flex-1 space-y-2 overflow-auto p-3">
            {chunksLoading && (
              <li className="px-2 py-4 text-sm text-ink-faint">加载分块…</li>
            )}
            {!chunksLoading && chunks.length === 0 && (
              <li className="px-2 py-4 text-sm text-ink-faint">暂无分块</li>
            )}
            {chunks.map((c) => {
              const active = c.id === activeChunkId;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => selectChunk(c)}
                    className={[
                      'w-full rounded border px-3 py-2 text-left transition-colors duration-150',
                      active
                        ? 'border-brand-500 bg-brand-50'
                        : 'border-line hover:border-brand-500',
                    ].join(' ')}
                  >
                    <div className="flex items-center gap-2 text-xs text-ink-faint">
                      <span className="font-medium text-ink-muted">#{c.seq}</span>
                      <span>
                        p.{c.page_start}
                        {c.page_end !== c.page_start ? `–${c.page_end}` : ''}
                      </span>
                      {c.heading_path?.length > 0 && (
                        <span className="truncate">{c.heading_path.join(' › ')}</span>
                      )}
                    </div>
                    <p className="mt-1.5 line-clamp-4 text-sm text-ink">{c.content}</p>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>
      </div>
    </div>
  );
}
