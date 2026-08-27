import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { CardSkeleton } from '@/components/Skeleton';
import { Chip, PageHeader } from '@/components/ui';
import { useSession } from '@/features/auth/hooks';
import { ApiError } from '@/lib/http';
import {
  formatPct,
  formatStale,
  rangeFromPreset,
  type RangePreset,
  type TopDimension,
} from './api';
import {
  ConnectionHealthPanel,
  CostTrendChart,
  ModelDonutChart,
  PurposeBarChart,
  SuccessRateChart,
  TokenTrendChart,
  TopConsumersChart,
} from './charts';
import {
  useModelConnections,
  useTopBreakdown,
  useUsageBreakdown,
  useUsageSeries,
  useUsageSummary,
} from './hooks';

const PRESETS: { id: RangePreset; label: string }[] = [
  { id: '24h', label: '近 24 小时' },
  { id: '7d', label: '近 7 天' },
  { id: '30d', label: '近 30 天' },
];

export function UsageDashboardPage() {
  const { session } = useSession();
  const role = session?.current_tenant.role;
  const canView = role === 'owner' || role === 'admin';

  const [preset, setPreset] = useState<RangePreset>('7d');
  const [timezone] = useState('Asia/Shanghai');
  const [topDim, setTopDim] = useState<TopDimension>('user');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const range = useMemo(
    () => rangeFromPreset(preset, timezone, { from: customFrom, to: customTo }),
    [preset, timezone, customFrom, customTo],
  );

  const summaryQ = useUsageSummary(timezone, canView);
  const seriesPurposeQ = useUsageSeries(range, 'purpose', canView);
  const seriesConnQ = useUsageSeries(range, 'connection_id', canView);
  const modelBdQ = useUsageBreakdown(range, 'model', canView);
  const purposeBdQ = useUsageBreakdown(range, 'purpose', canView);
  const topQ = useTopBreakdown(range, topDim, canView);
  const connectionsQ = useModelConnections(canView);

  if (!session) return null;

  if (!canView) {
    return (
      <div className="mx-auto max-w-lg panel border-dashed p-10 text-center">
        <h1 className="text-lg font-medium text-ink">无权查看用量</h1>
        <p className="mt-2 text-sm text-ink-muted">用量仪表盘仅对租户 owner / admin 开放。</p>
        <Link to="/" className="mt-4 inline-block text-sm text-accent hover:underline">
          返回概览
        </Link>
      </div>
    );
  }

  const forbidden =
    summaryQ.error instanceof ApiError && summaryQ.error.status === 403 ? summaryQ.error : null;

  if (forbidden) {
    return (
      <div className="mx-auto max-w-lg rounded-lg border border-danger/30 bg-danger/5 p-8 text-center">
        <h1 className="text-lg font-medium text-ink">无法加载用量</h1>
        <p className="mt-2 text-sm text-danger">{forbidden.message}</p>
      </div>
    );
  }

  const summary = summaryQ.data;
  const stale =
    formatStale(summary?.stale_until) ??
    formatStale(seriesPurposeQ.data?.stale_until) ??
    formatStale(modelBdQ.data?.stale_until);

  const quota = summary?.quota as
    | { token_limit?: number; used_ratio?: number; reset_at?: string }
    | null
    | undefined;
  const quotaHint =
    quota?.used_ratio != null
      ? `月度 Token 配额已用 ${(quota.used_ratio * 100).toFixed(1)}%`
      : null;

  const rangeDescription = [
    `租户 ${session.current_tenant.name}`,
    `时区 ${timezone}`,
    stale,
    preset === 'custom' ? `粒度 ${range.granularity}` : `粒度 ${range.granularity === 'hour' ? '小时' : '天'}`,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="page-shell-wide space-y-6">
      <PageHeader
        title="用量仪表盘"
        description={rangeDescription}
        actions={
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <Chip key={p.id} active={preset === p.id} onClick={() => setPreset(p.id)}>
                {p.label}
              </Chip>
            ))}
            <Chip active={preset === 'custom'} onClick={() => setPreset('custom')}>
              自定义
            </Chip>
          </div>
        }
      />

      {preset === 'custom' ? (
        <div className="panel flex flex-wrap gap-3 p-4">
          <label className="text-sm text-ink-muted">
            从
            <input
              type="datetime-local"
              className="field-input ml-2 w-auto"
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
            />
          </label>
          <label className="text-sm text-ink-muted">
            到
            <input
              type="datetime-local"
              className="field-input ml-2 w-auto"
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
            />
          </label>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {summaryQ.isLoading ? (
          <>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </>
        ) : (
          <>
            <SummaryCard
              label="本月 Token"
              value={summary ? summary.total_tokens.toLocaleString('zh-CN') : '—'}
              delta={formatPct(summary?.compare_previous?.total_tokens)}
            />
            <SummaryCard
              label="本月成本 (USD)"
              value={summary ? summary.total_cost.toFixed(2) : '—'}
              delta={formatPct(summary?.compare_previous?.total_cost)}
            />
            <SummaryCard
              label="调用次数"
              value={summary ? summary.call_count.toLocaleString('zh-CN') : '—'}
            />
            <SummaryCard
              label="成功率"
              value={summary ? `${(summary.success_rate * 100).toFixed(2)}%` : '—'}
              sub={quotaHint}
            />
          </>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
        <TokenTrendChart
          groups={seriesPurposeQ.data?.series ?? []}
          loading={seriesPurposeQ.isLoading}
          stale={stale}
        />
        <CostTrendChart
          groups={seriesPurposeQ.data?.series ?? []}
          loading={seriesPurposeQ.isLoading}
          stale={stale}
          quotaHint={quotaHint}
        />
        <ModelDonutChart
          items={modelBdQ.data?.items ?? []}
          others={modelBdQ.data?.others ?? { value: 0, share: 0 }}
          loading={modelBdQ.isLoading}
          stale={stale}
        />
        <PurposeBarChart
          items={purposeBdQ.data?.items ?? []}
          loading={purposeBdQ.isLoading}
          stale={stale}
        />
        <ConnectionHealthPanel
          connections={connectionsQ.data ?? []}
          groups={seriesConnQ.data?.series ?? []}
          loading={connectionsQ.isLoading || seriesConnQ.isLoading}
        />
        <SuccessRateChart
          groups={seriesPurposeQ.data?.series ?? []}
          loading={seriesPurposeQ.isLoading}
          stale={stale}
        />
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-ink-muted">排行维度</span>
          <Chip active={topDim === 'user'} onClick={() => setTopDim('user')}>
            用户
          </Chip>
          <Chip active={topDim === 'knowledge_base'} onClick={() => setTopDim('knowledge_base')}>
            知识库
          </Chip>
        </div>
        <TopConsumersChart items={topQ.data?.items ?? []} loading={topQ.isLoading} stale={stale} />
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  delta,
  sub,
}: {
  label: string;
  value: string;
  delta?: string;
  sub?: string | null;
}) {
  const deltaTone =
    !delta || delta === '—' || delta === '0.0%' || delta === '+0.0%'
      ? 'text-ink-faint'
      : delta.startsWith('+')
        ? 'text-ok'
        : delta.startsWith('-')
          ? 'text-danger'
          : 'text-ink-muted';

  return (
    <div className="panel p-4 transition-shadow duration-150 hover:shadow-elevated">
      <p className="text-xs font-medium text-ink-faint">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">{value}</p>
      {delta && delta !== '—' ? (
        <p className={`mt-1 text-xs ${deltaTone}`}>环比 {delta}</p>
      ) : null}
      {sub ? <p className="mt-1 text-xs text-ink-muted">{sub}</p> : null}
    </div>
  );
}
