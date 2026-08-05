type Props = {
  className?: string;
};

/** 通用脉冲占位块 */
export function Skeleton({ className = '' }: Props) {
  return (
    <div aria-hidden className={['animate-pulse rounded bg-line/70', className].join(' ')} />
  );
}

export function SkeletonLines({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={['space-y-2', className].join(' ')}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={i === lines - 1 ? 'h-3 w-2/3' : 'h-3 w-full'} />
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  const bars = [40, 65, 45, 80, 55, 70, 50];
  return (
    <div className="flex h-[160px] items-end gap-2 px-1">
      {bars.map((h, i) => (
        <div
          key={i}
          aria-hidden
          className="w-full animate-pulse rounded-sm bg-line/70"
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
  );
}

export function CardSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={['panel space-y-3 p-4', className].join(' ')}>
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-8 w-28" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}
