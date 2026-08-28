import { useEffect, useMemo, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

export type PdfBBox = {
  page: number;
  bbox: [number, number, number, number] | number[];
};

type Props = {
  url: string;
  page?: number;
  bboxes?: PdfBBox[];
  className?: string;
  onPageChange?: (page: number) => void;
};

type PageSize = { w: number; h: number };

export function PdfHighlightViewer({
  url,
  page = 1,
  bboxes = [],
  className,
  onPageChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const programmaticScroll = useRef(false);
  const [numPages, setNumPages] = useState(0);
  const [width, setWidth] = useState(480);
  const [error, setError] = useState<string | null>(null);
  const [pageSizes, setPageSizes] = useState<Map<number, PageSize>>(new Map());
  const [visiblePage, setVisiblePage] = useState(page);

  const safePage = Math.max(1, Math.min(page, numPages || page));

  const bboxesByPage = useMemo(() => {
    const map = new Map<number, PdfBBox[]>();
    for (const b of bboxes) {
      const p = Number(b.page);
      if (!Number.isFinite(p)) continue;
      const list = map.get(p) ?? [];
      list.push(b);
      map.set(p, list);
    }
    return map;
  }, [bboxes]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 40) setWidth(Math.floor(w));
    });
    ro.observe(node);
    setWidth(Math.floor(node.clientWidth) || 480);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    setError(null);
    setNumPages(0);
    setPageSizes(new Map());
    setVisiblePage(1);
  }, [url]);

  useEffect(() => {
    setVisiblePage(safePage);
  }, [safePage]);

  /** 外部分块选中 → 滚到对应页 */
  useEffect(() => {
    if (!numPages) return;
    const el = pageRefs.current.get(safePage);
    if (!el) return;
    programmaticScroll.current = true;
    el.scrollIntoView({ block: 'start', behavior: 'smooth' });
    const timer = window.setTimeout(() => {
      programmaticScroll.current = false;
    }, 600);
    return () => window.clearTimeout(timer);
  }, [safePage, numPages]);

  /** 滚动时同步当前可见页 */
  useEffect(() => {
    const root = containerRef.current;
    if (!root || numPages === 0) return;

    const ratios = new Map<number, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const pageNum = Number((entry.target as HTMLElement).dataset.page);
          if (pageNum > 0) ratios.set(pageNum, entry.intersectionRatio);
        }
        let best = visiblePage;
        let bestRatio = 0;
        for (const [p, r] of ratios) {
          if (r > bestRatio) {
            bestRatio = r;
            best = p;
          }
        }
        if (bestRatio <= 0 || programmaticScroll.current) return;
        if (best !== visiblePage) {
          setVisiblePage(best);
          onPageChange?.(best);
        }
      },
      { root, threshold: [0, 0.15, 0.35, 0.55, 0.75, 1] },
    );

    for (let i = 1; i <= numPages; i++) {
      const el = pageRefs.current.get(i);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [numPages, onPageChange, visiblePage]);

  if (!url) {
    return (
      <div
        className={['flex items-center justify-center p-6 text-sm text-slate-500', className]
          .filter(Boolean)
          .join(' ')}
      >
        暂无预览地址
      </div>
    );
  }

  const pageWidth = Math.max(200, width - 16);

  return (
    <div className={['flex h-full min-h-0 flex-col', className].filter(Boolean).join(' ')}>
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-slate-100 bg-white/80 px-3 py-2 text-xs text-slate-600 backdrop-blur-sm">
        <span className="text-slate-500">上下滑动浏览全文</span>
        <span className="tabular-nums">
          第 {visiblePage} / {numPages || '…'} 页
        </span>
      </div>

      <div
        ref={containerRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-slate-100 p-3 scroll-smooth"
      >
        {error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : (
          <Document
            file={url}
            loading={<p className="p-4 text-sm text-slate-500">加载 PDF…</p>}
            onLoadSuccess={(info) => setNumPages(info.numPages)}
            onLoadError={(err) => setError(err.message || 'PDF 加载失败')}
          >
            <div className="mx-auto flex max-w-full flex-col items-center gap-4 pb-6">
              {numPages > 0
                ? Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
                    <PageBlock
                      key={pageNum}
                      pageNum={pageNum}
                      pageWidth={pageWidth}
                      bboxes={bboxesByPage.get(pageNum) ?? []}
                      pageSize={pageSizes.get(pageNum) ?? null}
                      registerRef={(el) => {
                        if (el) pageRefs.current.set(pageNum, el);
                        else pageRefs.current.delete(pageNum);
                      }}
                      onRenderSuccess={(size) => {
                        setPageSizes((prev) => {
                          const next = new Map(prev);
                          next.set(pageNum, size);
                          return next;
                        });
                      }}
                    />
                  ))
                : null}
            </div>
          </Document>
        )}
      </div>
    </div>
  );
}

function PageBlock({
  pageNum,
  pageWidth,
  bboxes,
  pageSize,
  registerRef,
  onRenderSuccess,
}: {
  pageNum: number;
  pageWidth: number;
  bboxes: PdfBBox[];
  pageSize: PageSize | null;
  registerRef: (el: HTMLDivElement | null) => void;
  onRenderSuccess: (size: PageSize) => void;
}) {
  const scale = pageSize ? pageWidth / pageSize.w : 1;

  return (
    <div
      ref={registerRef}
      data-page={pageNum}
      id={`pdf-page-${pageNum}`}
      className="relative w-full max-w-full shadow-md ring-1 ring-slate-200/80"
    >
      <Page
        pageNumber={pageNum}
        width={pageWidth}
        renderTextLayer
        renderAnnotationLayer={false}
        onRenderSuccess={(pageProxy) => {
          const vp = pageProxy.getViewport({ scale: 1 });
          onRenderSuccess({ w: vp.width, h: vp.height });
        }}
      />
      {pageSize
        ? bboxes.map((b, i) => {
            const box = b.bbox;
            if (box.length < 4) return null;
            const x0 = box[0];
            const y0 = box[1];
            const x1 = box[2];
            const y1 = box[3];
            if (
              x0 === undefined ||
              y0 === undefined ||
              x1 === undefined ||
              y1 === undefined ||
              [x0, y0, x1, y1].some((v) => Number.isNaN(v))
            ) {
              return null;
            }
            return (
              <div
                key={i}
                className="pointer-events-none absolute bg-amber-300/40 ring-1 ring-amber-500/60"
                style={{
                  left: x0 * scale,
                  top: y0 * scale,
                  width: Math.max(2, (x1 - x0) * scale),
                  height: Math.max(2, (y1 - y0) * scale),
                }}
              />
            );
          })
        : null}
    </div>
  );
}
