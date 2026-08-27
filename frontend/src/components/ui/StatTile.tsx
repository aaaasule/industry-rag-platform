import { Link } from 'react-router-dom';

import { cn } from './cn';

type Tone = 'default' | 'ok' | 'warn' | 'danger';

type Props = {
  label: string;
  value: string;
  hint: string;
  to: string;
  tone?: Tone;
};

const toneClass: Record<Tone, string> = {
  default: 'text-ink',
  ok: 'text-ok',
  warn: 'text-warn',
  danger: 'text-danger',
};

export function StatTile({ label, value, hint, to, tone = 'default' }: Props) {
  return (
    <Link
      to={to}
      className="panel block p-4 transition-all duration-150 hover:border-accent hover:shadow-elevated"
    >
      <p className="text-xs font-medium text-ink-faint">{label}</p>
      <p className={cn('mt-1 text-2xl font-semibold tabular-nums', toneClass[tone])}>{value}</p>
      <p className="mt-1 text-xs text-ink-muted">{hint}</p>
    </Link>
  );
}
