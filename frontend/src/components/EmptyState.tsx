import type { ReactNode } from 'react';

type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  /** 图表卡 / 侧栏等紧凑场景 */
  compact?: boolean;
};

/** 统一空状态：图标 + 标题 + 说明 + 可选 CTA */
export function EmptyState({ title, description, action, className = '', compact }: Props) {
  return (
    <div
      className={[
        'flex flex-col items-center justify-center text-center',
        compact ? 'gap-2 px-3 py-6' : 'gap-3 px-4 py-10',
        className,
      ].join(' ')}
    >
      <span
        aria-hidden
        className={[
          'inline-flex items-center justify-center rounded border border-dashed border-line bg-canvas text-ink-faint',
          compact ? 'h-8 w-8' : 'h-10 w-10',
        ].join(' ')}
      >
        <svg
          width={compact ? 16 : 18}
          height={compact ? 16 : 18}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="4" y="5" width="16" height="14" rx="2" />
          <path d="M8 10h8M8 14h5" />
        </svg>
      </span>
      <div className="max-w-xs space-y-1">
        <p className={compact ? 'text-sm text-ink-muted' : 'text-sm font-medium text-ink'}>
          {title}
        </p>
        {description ? (
          <p className="text-xs leading-relaxed text-ink-faint">{description}</p>
        ) : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
