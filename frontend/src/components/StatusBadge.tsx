type Tone = 'ok' | 'warn' | 'danger' | 'neutral' | 'brand';

const TONE_CLASS: Record<Tone, string> = {
  ok: 'bg-ok/10 text-ok',
  warn: 'bg-warn/10 text-warn',
  danger: 'bg-danger/10 text-danger',
  neutral: 'bg-canvas text-ink-muted',
  brand: 'bg-brand-50 text-brand-700',
};

type BadgeProps = {
  label: string;
  tone?: Tone;
  className?: string;
};

export function StatusBadge({ label, tone = 'neutral', className = '' }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex rounded px-2 py-0.5 text-xs font-medium',
        TONE_CLASS[tone],
        className,
      ].join(' ')}
    >
      {label}
    </span>
  );
}

/** 文档摄取状态 */
export function DocumentStatusBadge({ status }: { status: string }) {
  const tone: Tone =
    (
      {
        ready: 'ok',
        failed: 'danger',
        pending: 'neutral',
        parsing: 'warn',
        chunking: 'warn',
        embedding: 'warn',
      } as Record<string, Tone>
    )[status] ?? 'neutral';

  const label =
    (
      {
        pending: '排队中',
        parsing: '解析中',
        chunking: '分块中',
        embedding: '向量化',
        ready: '就绪',
        failed: '失败',
      } as Record<string, string>
    )[status] ?? status;

  return <StatusBadge label={label} tone={tone} />;
}

/** 接入点健康态：未知用中性灰，避免误读为告警 */
export function HealthStatusBadge({ health }: { health: string }) {
  const tone: Tone =
    health === 'healthy'
      ? 'ok'
      : health === 'down'
        ? 'danger'
        : health === 'degraded'
          ? 'warn'
          : 'neutral';

  const label =
    health === 'healthy'
      ? '正常'
      : health === 'down'
        ? '故障'
        : health === 'degraded'
          ? '降级'
          : '未知';

  return <StatusBadge label={label} tone={tone} />;
}
