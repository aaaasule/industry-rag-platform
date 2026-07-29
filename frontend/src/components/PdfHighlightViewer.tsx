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

export function PdfHighlightViewer({
  url,
  page = 1,
  bboxes = [],
  className,
  onPageChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [width, setWidth] = useState(480);
  const [error, setError] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState<{ w: number; h: number } | null>(null);

  const safePage = Math.max(1, Math.min(page, numPages || page));

  const pageBboxes = useMemo(
    () => bboxes.filter((b) => Number(b.page) === safePage && Array.isArray(b.bbox)),
    [bboxes, safePage],
  );

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
    setPageSize(null);
  }, [url]);

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

  return (
    <div className={['flex h-full min-h-0 flex-col', className].filter(Boolean).join(' ')}>
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-xs text-slate-600">
        <button
          type="button"
          className="rounded px-2 py-1 hover:bg-slate-100 disabled:opacity-40"
          disabled={safePage <= 1}
          onClick={() => onPageChange?.(safePage - 1)}
        >
          上一页
        </button>
        <span>
          {safePage} / {numPages || '…'}
        </span>
        <button
          type="button"
          className="rounded px-2 py-1 hover:bg-slate-100 disabled:opacity-40"
          disabled={!numPages || safePage >= numPages}
          onClick={() => onPageChange?.(safePage + 1)}
        >
          下一页
        </button>
      </div>

      <div ref={containerRef} className="relative min-h-0 flex-1 overflow-auto bg-slate-100 p-2">
        {error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : (
          <Document
            file={url}
            loading={<p className="p-4 text-sm text-slate-500">加载 PDF…</p>}
            onLoadSuccess={(info) => setNumPages(info.numPages)}
            onLoadError={(err) => setError(err.message || 'PDF 加载失败')}
          >
            <div className="relative mx-auto inline-block shadow-sm">
              <Page
                pageNumber={safePage}
                width={width - 16}
                renderTextLayer
                renderAnnotationLayer={false}
                onRenderSuccess={(pageProxy) => {
                  const vp = pageProxy.getViewport({ scale: 1 });
                  setPageSize({ w: vp.width, h: vp.height });
                }}
              />
              {pageSize &&
                pageBboxes.map((b, i) => {
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
                  const scale = (width - 16) / pageSize.w;
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
                })}
            </div>
          </Document>
        )}
      </div>
    </div>
  );
}
