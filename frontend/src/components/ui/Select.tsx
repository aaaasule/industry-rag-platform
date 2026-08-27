import type { ReactNode, SelectHTMLAttributes } from 'react';

import { cn } from './cn';

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  error?: string;
  children: ReactNode;
};

export function Select({ label, error, className, id, children, ...rest }: Props) {
  const selectId = id ?? (label ? `select-${label}` : undefined);
  return (
    <div className="w-full">
      {label ? (
        <label htmlFor={selectId} className="mb-1.5 block text-sm font-medium text-ink">
          {label}
        </label>
      ) : null}
      <select
        id={selectId}
        className={cn('field-input', error ? 'border-danger' : '', className)}
        aria-invalid={error ? true : undefined}
        {...rest}
      >
        {children}
      </select>
      {error ? (
        <p role="alert" className="mt-1.5 text-xs text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}
