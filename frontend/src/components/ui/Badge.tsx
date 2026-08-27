import type { ReactNode } from 'react';

import { cn } from './cn';

type Tone = 'default' | 'ok' | 'warn' | 'danger' | 'accent';

type Props = {
  children: ReactNode;
  tone?: Tone;
  className?: string;
};

const toneClass: Record<Tone, string> = {
  default: 'border-line bg-elevated text-ink-muted',
  ok: 'border-ok/20 bg-ok/10 text-ok',
  warn: 'border-warn/20 bg-warn/10 text-warn',
  danger: 'border-danger/20 bg-danger/10 text-danger',
  accent: 'border-accent/20 bg-accent-soft text-accent',
};

export function Badge({ children, tone = 'default', className }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        toneClass[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
