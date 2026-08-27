import { FileText } from '@phosphor-icons/react';
import type { ReactNode } from 'react';

type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  compact?: boolean;
};

/** 统一空状态 */
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
          'inline-flex items-center justify-center rounded-lg border border-dashed border-line bg-elevated text-ink-faint',
          compact ? 'h-8 w-8' : 'h-10 w-10',
        ].join(' ')}
      >
        <FileText size={compact ? 16 : 20} weight="duotone" />
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
