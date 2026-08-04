import { api } from '@/lib/http';
import type { components } from '@/types/openapi.gen';

export type UsageSummary = components['schemas']['UsageSummaryOut'];
export type UsageSeries = components['schemas']['UsageSeriesOut'];
export type UsageBreakdown = components['schemas']['UsageBreakdownOut'];
export type SeriesPoint = components['schemas']['SeriesPoint'];
export type SeriesGroup = components['schemas']['SeriesGroup'];
export type BreakdownItem = components['schemas']['BreakdownItem'];
export type ModelConnection = components['schemas']['ModelConnectionOut'];

export type RangePreset = '24h' | '7d' | '30d' | 'custom';
export type Granularity = 'hour' | 'day';
export type TopDimension = 'user' | 'knowledge_base';

export interface UsageRange {
  from: string;
  to: string;
  timezone: string;
  granularity: Granularity;
}

function toQuery(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue;
    sp.set(k, String(v));
  }
  const q = sp.toString();
  return q ? `?${q}` : '';
}

export function fetchUsageSummary(params: {
  period?: 'day' | 'week' | 'month';
  timezone: string;
}): Promise<UsageSummary> {
  return api.get(`/usages/summary${toQuery(params)}`);
}

export function fetchUsageSeries(params: {
  from: string;
  to: string;
  timezone: string;
  granularity: Granularity;
  group_by: 'purpose' | 'model' | 'connection_id';
}): Promise<UsageSeries> {
  return api.get(`/usages/series${toQuery(params)}`);
}

export function fetchUsageBreakdown(params: {
  from: string;
  to: string;
  dimension: 'model' | 'purpose' | 'connection' | 'user' | 'knowledge_base';
  metric?: 'cost' | 'call_count' | 'prompt_tokens';
  top?: number;
}): Promise<UsageBreakdown> {
  return api.get(`/usages/breakdown${toQuery({ metric: 'cost', top: 10, ...params })}`);
}

export function listModelConnections(): Promise<ModelConnection[]> {
  return api.get('/model-connections');
}

/** 按预设算出 from/to（UTC ISO）与粒度。 */
export function rangeFromPreset(
  preset: RangePreset,
  timezone: string,
  custom?: { from: string; to: string },
): UsageRange {
  const now = new Date();
  let from: Date;
  let to = now;
  if (preset === 'custom' && custom?.from && custom?.to) {
    from = new Date(custom.from);
    to = new Date(custom.to);
  } else if (preset === '24h') {
    from = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  } else if (preset === '7d') {
    from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  } else {
    from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  }
  const spanMs = to.getTime() - from.getTime();
  const granularity: Granularity = spanMs <= 48 * 60 * 60 * 1000 ? 'hour' : 'day';
  return {
    from: from.toISOString(),
    to: to.toISOString(),
    timezone,
    granularity,
  };
}

/** 将多组 series 按时间桶合并（用于总 Token / 成本趋势）。 */
export function mergeSeriesPoints(groups: SeriesGroup[]): SeriesPoint[] {
  const map = new Map<
    string,
    {
      prompt_tokens: number;
      completion_tokens: number;
      cost: number;
      call_count: number;
      success_weighted: number;
      latency_p95_ms: number | null;
    }
  >();
  for (const g of groups) {
    for (const p of g.points) {
      const cur = map.get(p.t) ?? {
        prompt_tokens: 0,
        completion_tokens: 0,
        cost: 0,
        call_count: 0,
        success_weighted: 0,
        latency_p95_ms: null as number | null,
      };
      cur.prompt_tokens += p.prompt_tokens;
      cur.completion_tokens += p.completion_tokens;
      cur.cost += p.cost;
      cur.call_count += p.call_count;
      cur.success_weighted += p.success_rate * p.call_count;
      if (p.latency_p95_ms != null) {
        cur.latency_p95_ms =
          cur.latency_p95_ms == null
            ? p.latency_p95_ms
            : Math.max(cur.latency_p95_ms, p.latency_p95_ms);
      }
      map.set(p.t, cur);
    }
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([t, c]) => ({
      t,
      prompt_tokens: c.prompt_tokens,
      completion_tokens: c.completion_tokens,
      cost: Number(c.cost.toFixed(6)),
      call_count: c.call_count,
      success_rate: c.call_count ? Number((c.success_weighted / c.call_count).toFixed(4)) : 1,
      latency_p95_ms: c.latency_p95_ms,
    }));
}

export function formatStale(staleUntil?: string | null): string | null {
  if (!staleUntil) return null;
  try {
    const d = new Date(staleUntil);
    return `数据截至 ${d.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', month: 'numeric', day: 'numeric' })}`;
  } catch {
    return null;
  }
}

export function formatPct(ratio: number | undefined): string {
  if (ratio === undefined || Number.isNaN(ratio)) return '—';
  const pct = ratio * 100;
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}
