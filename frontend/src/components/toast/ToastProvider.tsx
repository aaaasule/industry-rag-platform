import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  ToastContext,
  type ToastApi,
  type ToastTone,
} from '@/components/toast/toastContext';

type ToastItem = {
  id: string;
  message: string;
  tone: ToastTone;
};

let toastSeq = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, number>>(new Map());

  const dismiss = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer != null) {
      window.clearTimeout(timer);
      timers.current.delete(id);
    }
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, options?: { tone?: ToastTone; durationMs?: number }) => {
      const id = `toast-${++toastSeq}`;
      const tone = options?.tone ?? 'info';
      const durationMs = options?.durationMs ?? (tone === 'error' ? 4500 : 2800);
      setItems((prev) => [...prev.slice(-4), { id, message, tone }]);
      const timer = window.setTimeout(() => dismiss(id), durationMs);
      timers.current.set(id, timer);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      toast,
      success: (message) => toast(message, { tone: 'success' }),
      error: (message) => toast(message, { tone: 'error' }),
      info: (message) => toast(message, { tone: 'info' }),
    }),
    [toast],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-[80] flex flex-col items-center gap-2 px-4 pb-6"
        aria-live="polite"
        aria-relevant="additions"
      >
        {items.map((item) => (
          <div
            key={item.id}
            className={[
              'pointer-events-auto flex max-w-md items-start gap-3 rounded-md border px-3.5 py-2.5 text-sm shadow-panel animate-fade-up',
              item.tone === 'success'
                ? 'border-ok/30 bg-surface text-ok'
                : item.tone === 'error'
                  ? 'border-danger/30 bg-surface text-danger'
                  : 'border-line bg-surface text-ink',
            ].join(' ')}
            role="status"
          >
            <span className="min-w-0 flex-1 leading-relaxed">{item.message}</span>
            <button
              type="button"
              className="shrink-0 text-xs text-ink-faint hover:text-ink"
              onClick={() => dismiss(item.id)}
              aria-label="关闭通知"
            >
              关闭
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
