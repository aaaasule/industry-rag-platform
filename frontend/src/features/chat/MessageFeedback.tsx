import { useState } from 'react';

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
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => void submit('up')}
        className={[
          'rounded px-1.5 py-0.5 hover:bg-surface/70',
          rating === 'up' ? 'bg-surface text-ok ring-1 ring-emerald-200' : '',
        ].join(' ')}
        title="有用"
      >
        👍
      </button>
      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => setPicking((v) => !v)}
        className={[
          'rounded px-1.5 py-0.5 hover:bg-surface/70',
          rating === 'down' ? 'bg-surface text-danger ring-1 ring-danger/30' : '',
        ].join(' ')}
        title="没用"
      >
        👎
      </button>
      {rating === 'down' && reason && !picking && (
        <span className="text-ink-faint">
          {REASONS.find((r) => r.value === reason)?.label ?? reason}
        </span>
      )}
      {picking && (
        <span className="flex flex-wrap gap-1">
          {REASONS.map((r) => (
            <button
              key={r.value}
              type="button"
              className="rounded border border-line bg-surface px-2 py-0.5 hover:border-brand-300"
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
