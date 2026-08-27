import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { cn } from './cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

const variantClass: Record<Variant, string> = {
  primary:
    'bg-accent text-white hover:bg-accent-hover disabled:bg-line disabled:text-ink-muted',
  secondary:
    'border border-line bg-surface text-ink hover:border-accent hover:bg-accent-soft',
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
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold',
        'transition-colors duration-150 active:scale-[0.98] disabled:cursor-not-allowed',
        variantClass[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
