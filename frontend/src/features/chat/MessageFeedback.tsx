import { useState } from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';

import { cn } from '@/components/ui/cn';

import * as chatApi from './api';
import type { FeedbackReason } from './api';

const REASONS: { value: FeedbackReason; label: string }[] = [
  { value: 'irrelevant', label: '答非所问' },
  { value: 'bad_citation', label: '引用不准' },
  { value: 'other', label: '其他' },
];

type Props = {
  messageId: string;
  initial?: { rating: 'up' | 'down'; reason?: string | null } | null | undefined;
  disabled?: boolean;
};

export function MessageFeedback({ messageId, initial, disabled }: Props) {
  const [rating, setRating] = useState<'up' | 'down' | null>(initial?.rating ?? null);
  const [reason, setReason] = useState<string | null>(initial?.reason ?? null);
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(next: 'up' | 'down', nextReason?: FeedbackReason) {
    if (disabled || busy || messageId.startsWith('local-')) return;
    setBusy(true);
    setError(null);
    try {
      const res = await chatApi.submitFeedback(messageId, {
        rating: next,
        ...(nextReason ? { reason: nextReason } : {}),
      });
      setRating(res.rating);
      setReason(res.reason ?? null);
      setPicking(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => void submit('up')}
        className={cn(
          'inline-flex h-7 w-7 items-center justify-center rounded-full transition-all duration-200 hover:bg-slate-100',
          rating === 'up' ? 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200' : 'text-slate-400',
        )}
        title="有用"
      >
        <ThumbsUp
          className={cn('h-3.5 w-3.5', rating === 'up' && 'fill-current')}
          strokeWidth={1.5}
        />
      </button>
      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => setPicking((v) => !v)}
        className={cn(
          'inline-flex h-7 w-7 items-center justify-center rounded-full transition-all duration-200 hover:bg-slate-100',
          rating === 'down' ? 'bg-red-50 text-red-600 ring-1 ring-red-200' : 'text-slate-400',
        )}
        title="没用"
      >
        <ThumbsDown
          className={cn('h-3.5 w-3.5', rating === 'down' && 'fill-current')}
          strokeWidth={1.5}
        />
      </button>
      {rating === 'down' && reason && !picking && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-500">
          {REASONS.find((r) => r.value === reason)?.label ?? reason}
        </span>
      )}
      {picking && (
        <span className="flex flex-wrap gap-1">
          {REASONS.map((r) => (
            <button
              key={r.value}
              type="button"
              className="rounded-full border border-slate-200 bg-white px-2.5 py-0.5 transition-all duration-200 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600"
              onClick={() => void submit('down', r.value)}
            >
              {r.label}
            </button>
          ))}
        </span>
      )}
      {error && <span className="text-danger">{error}</span>}
    </div>
  );
}
