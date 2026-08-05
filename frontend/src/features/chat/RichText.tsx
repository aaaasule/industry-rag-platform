type Block =
  | { type: 'p'; text: string }
  | { type: 'h'; level: 1 | 2 | 3; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'code'; lang: string; code: string }
  | { type: 'quote'; text: string }
  | { type: 'table'; rows: string[][] };

type Props = {
  content: string;
  activeCitation: number | null;
  onCitationClick: (n: number) => void;
};

/**
 * 轻量 Markdown 子集渲染：标题 / 段落 / 列表 / 引用 / 代码块 / 表格，
 * 以及行内粗体、行内代码、引用角标 [n]。不执行 HTML。
 */
export function RichText({ content, activeCitation, onCitationClick }: Props) {
  const blocks = parseBlocks(content);
  if (blocks.length === 0) return <span>…</span>;

  return (
    <div className="chat-prose space-y-2.5">
      {blocks.map((block, i) => (
        <BlockView
          key={i}
          block={block}
          activeCitation={activeCitation}
          onCitationClick={onCitationClick}
        />
      ))}
    </div>
  );
}

function BlockView({
  block,
  activeCitation,
  onCitationClick,
}: {
  block: Block;
  activeCitation: number | null;
  onCitationClick: (n: number) => void;
}) {
  const inline = (text: string) => (
    <InlineWithBreaks
      text={text}
      activeCitation={activeCitation}
      onCitationClick={onCitationClick}
    />
  );

  switch (block.type) {
    case 'h': {
      const cls =
        block.level === 1
          ? 'text-base font-semibold text-ink'
          : block.level === 2
            ? 'text-[15px] font-semibold text-ink'
            : 'text-sm font-semibold text-ink';
      return <p className={cls}>{inline(block.text)}</p>;
    }
    case 'ul':
      return (
        <ul className="list-disc space-y-1 pl-5 text-ink">
          {block.items.map((item, i) => (
            <li key={i}>{inline(item)}</li>
          ))}
        </ul>
      );
    case 'ol':
      return (
        <ol className="list-decimal space-y-1 pl-5 text-ink">
          {block.items.map((item, i) => (
            <li key={i}>{inline(item)}</li>
          ))}
        </ol>
      );
    case 'code':
      return (
        <pre className="overflow-x-auto rounded border border-line bg-canvas px-3 py-2 font-mono text-xs leading-relaxed text-ink">
          {block.lang ? (
            <div className="mb-1.5 text-[10px] uppercase tracking-wider text-ink-faint">
              {block.lang}
            </div>
          ) : null}
          <code>{block.code}</code>
        </pre>
      );
    case 'quote':
      return (
        <blockquote className="border-l-2 border-brand-500/50 pl-3 text-ink-muted">
          {inline(block.text)}
        </blockquote>
      );
    case 'table': {
      const [header, ...body] = block.rows;
      if (!header) return null;
      return (
        <div className="overflow-x-auto rounded border border-line">
          <table className="w-full min-w-[200px] border-collapse text-left text-xs">
            <thead className="bg-canvas">
              <tr>
                {header.map((cell, i) => (
                  <th
                    key={i}
                    className="border-b border-line px-2.5 py-1.5 font-semibold text-ink"
                  >
                    {inline(cell)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, ri) => (
                <tr key={ri} className="border-b border-line/60 last:border-0">
                  {row.map((cell, ci) => (
                    <td key={ci} className="px-2.5 py-1.5 text-ink align-top">
                      {inline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    default:
      return <p className="text-ink">{inline(block.text)}</p>;
  }
}

function InlineWithBreaks({
  text,
  activeCitation,
  onCitationClick,
}: {
  text: string;
  activeCitation: number | null;
  onCitationClick: (n: number) => void;
}) {
  const lines = text.split('\n');
  return (
    <>
      {lines.map((line, i) => (
        <span key={i}>
          {i > 0 ? <br /> : null}
          <InlineText
            text={line}
            activeCitation={activeCitation}
            onCitationClick={onCitationClick}
          />
        </span>
      ))}
    </>
  );
}

function InlineText({
  text,
  activeCitation,
  onCitationClick,
}: {
  text: string;
  activeCitation: number | null;
  onCitationClick: (n: number) => void;
}) {
  const parts = text.split(/(\[\d+\]|`[^`]+`|\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (!part) return null;

        const cite = /^\[(\d+)\]$/.exec(part);
        if (cite) {
          const n = Number(cite[1]);
          const active = activeCitation === n;
          return (
            <button
              key={i}
              type="button"
              onClick={() => onCitationClick(n)}
              className={[
                'mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded px-1 align-middle text-xs font-medium',
                active
                  ? 'bg-brand-600 text-white'
                  : 'bg-brand-50 text-brand-700 ring-1 ring-brand-100',
              ].join(' ')}
            >
              {n}
            </button>
          );
        }

        const code = /^`([^`]+)`$/.exec(part);
        if (code) {
          return (
            <code
              key={i}
              className="rounded bg-canvas px-1 py-0.5 font-mono text-[12px] text-brand-700"
            >
              {code[1]}
            </code>
          );
        }

        const bold = /^\*\*([^*]+)\*\*$/.exec(part);
        if (bold) {
          return (
            <strong key={i} className="font-semibold text-ink">
              {bold[1]}
            </strong>
          );
        }

        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function isTableLine(line: string): boolean {
  const t = line.trim();
  return t.startsWith('|') && t.includes('|', 1);
}

function isTableSeparator(line: string): boolean {
  const t = line.trim();
  return /^\|?[\s:|-]+\|[\s:|-]*$/.test(t) && t.includes('-');
}

function splitTableCells(line: string): string[] {
  const t = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  return t.split('|').map((c) => c.trim());
}

function parseBlocks(content: string): Block[] {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i] ?? '';

    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i += 1;
      while (i < lines.length && !(lines[i] ?? '').startsWith('```')) {
        codeLines.push(lines[i] ?? '');
        i += 1;
      }
      if (i < lines.length) i += 1;
      blocks.push({ type: 'code', lang, code: codeLines.join('\n') });
      continue;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      const level = heading[1]!.length as 1 | 2 | 3;
      blocks.push({ type: 'h', level, text: heading[2] ?? '' });
      i += 1;
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i] ?? '')) {
        quoteLines.push((lines[i] ?? '').replace(/^>\s?/, ''));
        i += 1;
      }
      blocks.push({ type: 'quote', text: quoteLines.join('\n') });
      continue;
    }

    if (isTableLine(line)) {
      const rows: string[][] = [];
      while (i < lines.length && isTableLine(lines[i] ?? '')) {
        const cur = lines[i] ?? '';
        if (!isTableSeparator(cur)) {
          rows.push(splitTableCells(cur));
        }
        i += 1;
      }
      if (rows.length > 0) blocks.push({ type: 'table', rows });
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i] ?? '')) {
        items.push((lines[i] ?? '').replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i] ?? '')) {
        items.push((lines[i] ?? '').replace(/^\d+\.\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'ol', items });
      continue;
    }

    if (!line.trim()) {
      i += 1;
      continue;
    }

    const para: string[] = [];
    while (i < lines.length) {
      const cur = lines[i] ?? '';
      if (!cur.trim()) break;
      if (cur.startsWith('```')) break;
      if (/^#{1,3}\s+/.test(cur)) break;
      if (/^>\s?/.test(cur)) break;
      if (isTableLine(cur)) break;
      if (/^[-*]\s+/.test(cur)) break;
      if (/^\d+\.\s+/.test(cur)) break;
      para.push(cur);
      i += 1;
    }
    if (para.length) blocks.push({ type: 'p', text: para.join('\n') });
  }

  return blocks;
}
