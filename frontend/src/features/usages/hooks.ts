import { useQuery } from '@tanstack/react-query';

import type { ApiError } from '@/lib/http';
import * as usagesApi from './api';
import type { TopDimension, UsageRange } from './api';

export function useUsageSummary(timezone: string, enabled: boolean) {
  return useQuery({
    queryKey: ['usages', 'summary', timezone],
    queryFn: () => usagesApi.fetchUsageSummary({ period: 'month', timezone }),
    enabled,
    staleTime: 60_000,
  });
}

export function useUsageSeries(
  range: UsageRange,
  groupBy: 'purpose' | 'model' | 'connection_id',
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['usages', 'series', range, groupBy],
    queryFn: () =>
      usagesApi.fetchUsageSeries({
        from: range.from,
        to: range.to,
        timezone: range.timezone,
        granularity: range.granularity,
        group_by: groupBy,
      }),
    enabled,
    staleTime: 60_000,
  });
}

export function useUsageBreakdown(
  range: UsageRange,
  dimension: 'model' | 'purpose' | 'connection' | 'user' | 'knowledge_base',
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['usages', 'breakdown', range, dimension],
    queryFn: () =>
      usagesApi.fetchUsageBreakdown({
        from: range.from,
        to: range.to,
        dimension,
        metric: 'cost',
        top: 10,
      }),
    enabled,
    staleTime: 60_000,
  });
}

export function useTopBreakdown(range: UsageRange, dimension: TopDimension, enabled: boolean) {
  return useUsageBreakdown(range, dimension, enabled);
}

export function useModelConnections(enabled: boolean) {
  return useQuery<usagesApi.ModelConnection[], ApiError>({
    queryKey: ['model-connections'],
    queryFn: usagesApi.listModelConnections,
    enabled,
    staleTime: 60_000,
  });
}
