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
          ? 'bg-indigo-600 text-white'
          : 'border border-slate-200 bg-white text-slate-500 hover:border-indigo-300 hover:text-slate-800',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
