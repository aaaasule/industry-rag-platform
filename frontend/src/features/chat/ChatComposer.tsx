import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';

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
        className="flex items-end gap-2 border-t border-line bg-surface p-3"
      >
        <textarea
          className="field-input min-h-[44px] flex-1 resize-none"
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
          <Button variant="danger" className="shrink-0" onClick={onStop}>
            停止
          </Button>
        ) : (
          <Button type="submit" className="shrink-0" disabled={!input.trim()}>
            发送
          </Button>
        )}
      </form>
      {error ? <p className="px-3 pb-3 text-sm text-danger">{error}</p> : null}
    </>
  );
}
