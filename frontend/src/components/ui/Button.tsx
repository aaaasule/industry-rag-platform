import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { cn } from './cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

const variantClass: Record<Variant, string> = {
  primary:
    'bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-sm hover:-translate-y-0.5 hover:shadow-md disabled:translate-y-0 disabled:bg-line disabled:from-line disabled:to-line disabled:text-ink-muted disabled:shadow-none',
  secondary:
    'border border-line bg-surface text-ink hover:border-accent/40 hover:bg-accent-soft',
  ghost: 'text-ink-muted hover:bg-accent-soft hover:text-ink',
  danger:
    'border border-danger/30 bg-surface text-danger hover:bg-danger/5 disabled:opacity-50',
};

export function Button({
  variant = 'primary',
  className,
  children,
  type = 'button',
  ...rest
}: Props) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold',
        'transition-all duration-200 active:scale-[0.98] disabled:cursor-not-allowed',
        variantClass[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
