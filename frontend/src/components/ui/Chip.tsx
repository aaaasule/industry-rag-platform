import type { ButtonHTMLAttributes } from 'react';

import { cn } from './cn';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean;
};

export function Chip({ active, className, children, ...rest }: Props) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex max-w-full items-center truncate rounded-full px-3 py-1 text-xs font-medium',
        'transition-colors duration-150',
        active
          ? 'bg-accent text-white'
          : 'border border-line bg-surface text-ink-muted hover:border-accent hover:text-ink',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
