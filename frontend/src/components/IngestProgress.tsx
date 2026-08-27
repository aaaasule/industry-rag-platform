const STEPS = [
  { key: 'pending', label: '排队' },
  { key: 'parsing', label: '解析' },
  { key: 'chunking', label: '分块' },
  { key: 'embedding', label: '向量化' },
  { key: 'ready', label: '就绪' },
] as const;

function stepIndex(status: string): number {
  const i = STEPS.findIndex((s) => s.key === status);
  return i >= 0 ? i : 0;
}

/** 文档摄取阶段进度（排队 → 解析 → 分块 → 向量化 → 就绪） */
export function IngestProgress({
  status,
  errorCode,
}: {
  status: string;
  errorCode?: string | null;
}) {
  if (status === 'ready') return null;

  if (status === 'failed') {
    return (
      <div className="mt-1.5 space-y-0.5 text-[11px] text-danger">
        <div className="flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-danger" />
          摄取失败
        </div>
        {errorCode ? (
          <code className="block font-mono text-[10px] text-danger/80">{errorCode}</code>
        ) : null}
      </div>
    );
  }

  const idx = stepIndex(status);
  const pct = Math.round(((idx + 0.45) / (STEPS.length - 1)) * 100);
  const current = STEPS[idx]?.label ?? status;

  return (
    <div className="mt-1.5 min-w-[140px] max-w-[200px]">
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-warn">{current}</span>
        <span className="tabular-nums text-ink-faint">{Math.min(pct, 95)}%</span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-canvas">
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
          style={{ width: `${Math.min(pct, 95)}%` }}
        />
      </div>
      <div className="mt-1.5 flex justify-between gap-0.5">
        {STEPS.slice(0, -1).map((step, i) => {
          const done = i < idx;
          const active = i === idx;
          return (
            <span
              key={step.key}
              className={[
                'h-1 flex-1 rounded-full',
                done || active ? 'bg-accent' : 'bg-line',
                active ? 'animate-pulse' : '',
              ].join(' ')}
              title={step.label}
            />
          );
        })}
      </div>
    </div>
  );
}
