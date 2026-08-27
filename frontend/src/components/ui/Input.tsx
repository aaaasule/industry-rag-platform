import type { InputHTMLAttributes, ReactNode } from 'react';

import { cn } from './cn';

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  hint?: ReactNode;
};

export function Input({ label, error, hint, className, id, ...rest }: Props) {
  const inputId = id ?? (label ? `input-${label}` : undefined);
  return (
    <div className="w-full">
      {label ? (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        className={cn(
          'field-input',
          error ? 'border-danger focus:border-danger focus:ring-danger/20' : '',
          className,
        )}
        aria-invalid={error ? true : undefined}
        {...rest}
      />
      {error ? (
        <p role="alert" className="mt-1.5 text-xs text-danger">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-ink-faint">{hint}</p>
      ) : null}
    </div>
  );
}
