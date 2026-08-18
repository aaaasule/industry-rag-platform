import { useEffect, useMemo, useRef } from 'react';

export type PreviewPage = {
  page_no: number;
  plain_text: string;
  source: string;
};

type Props = {
  pages: PreviewPage[];
  activePage?: number | null | undefined;
  highlightText?: string | null | undefined;
};

export function TextPreview({ pages, activePage, highlightText }: Props) {
  useEffect(() => {
    if (activePage == null) return;
    document
      .getElementById(`preview-page-${activePage}`)
      ?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [activePage, highlightText, pages]);

  if (pages.length === 0) {
    return <p className="p-6 text-sm text-ink-muted">暂无解析文本。</p>;
  }

  return (
    <div className="h-full overflow-auto p-4">
      {pages.map((page) => {
        const active = activePage != null && page.page_no === activePage;
        return (
          <section
            key={page.page_no}
            id={`preview-page-${page.page_no}`}
            className={[
              'mb-4 rounded-md border px-3 py-2',
              active ? 'border-brand-500 bg-brand-50/60' : 'border-line',
            ].join(' ')}
          >
            <div className="mb-2 text-xs text-ink-faint">第 {page.page_no} 页</div>
            <HighlightedPlainText text={page.plain_text} needle={active ? highlightText : null} />
          </section>
        );
      })}
    </div>
  );
}

function HighlightedPlainText({
  text,
  needle,
}: {
  text: string;
  needle?: string | null | undefined;
}) {
  const markRef = useRef<HTMLElement | null>(null);
  const parts = useMemo(() => splitHighlight(text, needle), [text, needle]);

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [parts]);

  return (
    <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-ink">
      {parts.map((part, i) =>
        part.hit ? (
          <mark key={i} ref={markRef} className="rounded bg-brand-100 px-0.5 text-ink">
            {part.text}
          </mark>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </pre>
  );
}

function splitHighlight(
  text: string,
  needle?: string | null,
): { text: string; hit: boolean }[] {
  const raw = (needle ?? '').trim();
  if (!raw) return [{ text, hit: false }];
  const idx = text.indexOf(raw);
  if (idx >= 0) {
    return [
      { text: text.slice(0, idx), hit: false },
      { text: text.slice(idx, idx + raw.length), hit: true },
      { text: text.slice(idx + raw.length), hit: false },
    ].filter((p) => p.text.length > 0);
  }
  const short = raw.slice(0, 80);
  const i = short.length >= 12 ? text.indexOf(short) : -1;
  if (i < 0) return [{ text, hit: false }];
  return [
    { text: text.slice(0, i), hit: false },
    { text: text.slice(i, i + short.length), hit: true },
    { text: text.slice(i + short.length), hit: false },
  ].filter((p) => p.text.length > 0);
}
