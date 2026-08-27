import type { ReactNode } from 'react';

import { cn } from './cn';

type Props = {
  children: ReactNode;
  className?: string;
  header?: ReactNode;
  padding?: boolean;
};

export function Card({ children, className, header, padding = true }: Props) {
  return (
    <div className={cn('panel overflow-hidden', className)}>
      {header ? <div className="border-b border-line px-4 py-3">{header}</div> : null}
      <div className={padding ? 'p-4' : undefined}>{children}</div>
    </div>
  );
}
