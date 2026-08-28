import type { FormEvent } from 'react';
import { Loader2, Send, Square } from 'lucide-react';

import { cn } from '@/components/ui/cn';

type Props = {
  input: string;
  streaming: boolean;
  error: string | null;
  onInputChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  onStop: () => void;
};

export function ChatComposer({
  input,
  streaming,
  error,
  onInputChange,
  onSubmit,
  onStop,
}: Props) {
  return (
    <>
      <form
        onSubmit={onSubmit}
        className="border-t border-slate-200/60 bg-white px-4 py-3 sm:px-5 sm:py-4"
      >
        <div
          className={cn(
            'flex items-end gap-2 rounded-2xl border border-slate-200 bg-[#F9FAFB] p-2',
            'transition-all duration-200 ease-in-out',
            'focus-within:border-indigo-300 focus-within:bg-white focus-within:ring-2 focus-within:ring-indigo-500/15',
          )}
        >
          <textarea
            className="min-h-[44px] flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400 disabled:text-slate-400"
            rows={2}
            value={input}
            disabled={streaming}
            placeholder="输入问题，Enter 发送，Shift+Enter 换行"
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
          />
          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-red-200 bg-red-50 text-red-600 transition-all duration-200 hover:bg-red-100"
              aria-label="停止生成"
            >
              <Square className="h-4 w-4" strokeWidth={1.5} fill="currentColor" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className={cn(
                'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
                'bg-indigo-600 text-white transition-all duration-200',
                'hover:bg-indigo-700 active:scale-95',
                'disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400',
              )}
              aria-label="发送"
            >
              <Send className="h-4 w-4" strokeWidth={1.5} />
            </button>
          )}
        </div>
        {streaming && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-400">
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
            正在生成回答…
            <span className="inline-flex gap-0.5 pl-1" aria-hidden>
              <span className="h-1 w-1 animate-pulse rounded-full bg-indigo-400 [animation-delay:0ms]" />
              <span className="h-1 w-1 animate-pulse rounded-full bg-indigo-400 [animation-delay:150ms]" />
              <span className="h-1 w-1 animate-pulse rounded-full bg-indigo-400 [animation-delay:300ms]" />
            </span>
          </p>
        )}
      </form>
      {error ? <p className="px-4 pb-3 text-sm text-danger">{error}</p> : null}
    </>
  );
}
