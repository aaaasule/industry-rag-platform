import { FileText } from 'lucide-react';
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
          'inline-flex items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 text-slate-400',
          compact ? 'h-8 w-8' : 'h-10 w-10',
        ].join(' ')}
      >
        <FileText className={compact ? 'h-4 w-4' : 'h-5 w-5'} strokeWidth={1.5} />
      </span>
      <div className="max-w-xs space-y-1">
        <p className={compact ? 'text-sm text-slate-600' : 'text-sm font-medium text-slate-800'}>
          {title}
        </p>
        {description ? (
          <p className="text-xs leading-relaxed text-slate-400">{description}</p>
        ) : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
