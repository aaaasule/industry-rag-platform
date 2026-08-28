import type { ReactNode } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { EmptyState } from '@/components/EmptyState';
import { ChartSkeleton } from '@/components/Skeleton';
import { HealthStatusBadge } from '@/components/StatusBadge';

import type { BreakdownItem, ModelConnection, SeriesGroup } from './api';
import { mergeSeriesPoints } from './api';

const COLORS = ['#4f46e5', '#6366f1', '#818cf8', '#64748b', '#10b981', '#f59e0b', '#ef4444'];

function ChartShell({
  title,
  hint = null,
  empty = false,
  emptyHint = '所选时间范围内暂无用量记录',
  loading = false,
  children,
}: {
  title: string;
  hint?: string | null;
  empty?: boolean;
  emptyHint?: string;
  loading?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="flex min-h-[280px] flex-col panel p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-800">{title}</h3>
        {hint ? <span className="text-xs text-slate-400">{hint}</span> : null}
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        {loading ? (
          <div className="flex h-full items-center">
            <ChartSkeleton />
          </div>
        ) : empty ? (
          <EmptyState
            compact
            className="h-full"
            title={`${title}暂无数据`}
            description={emptyHint}
          />
        ) : (
          children
        )}
      </div>
    </section>
  );
}

export function TokenTrendChart({
  groups,
  loading,
  stale,
}: {
  groups?: SeriesGroup[];
  loading?: boolean;
  stale?: string | null;
}) {
  const data = mergeSeriesPoints(groups ?? []).map((p) => ({
    t: p.t,
    prompt: p.prompt_tokens,
    completion: p.completion_tokens,
  }));
  return (
    <ChartShell
      title="Token 消耗趋势"
      hint={stale ?? null}
      loading={loading ?? false}
      empty={!data.length}
      emptyHint="产生调用后将显示 Token 随时间变化"
    >
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="t" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Area
            type="monotone"
            dataKey="prompt"
            stackId="1"
            stroke="#4f46e5"
            fill="#c7d2fe"
            name="prompt"
          />
          <Area
            type="monotone"
            dataKey="completion"
            stackId="1"
            stroke="#6366f1"
            fill="#e0e7ff"
            name="completion"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function CostTrendChart({
  groups,
  loading,
  stale,
  quotaHint,
}: {
  groups?: SeriesGroup[];
  loading?: boolean;
  stale?: string | null;
  quotaHint?: string | null;
}) {
  const data = mergeSeriesPoints(groups ?? []).map((p) => ({ t: p.t, cost: p.cost }));
  return (
    <ChartShell
      title="成本趋势"
      hint={(quotaHint ? `${stale ?? ''} · ${quotaHint}`.replace(/^ · /, '') : stale) ?? null}
      loading={loading ?? false}
      empty={!data.length}
      emptyHint="产生调用后将显示成本随时间变化"
    >
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="t" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="cost"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            name="USD"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function ModelDonutChart({
  items,
  others,
  loading,
  stale,
}: {
  items?: BreakdownItem[];
  others?: { value?: number; share?: number };
  loading?: boolean;
  stale?: string | null;
}) {
  const data = [
    ...(items ?? []).map((i) => ({ name: i.label, value: i.value })),
    ...(others && (others.value ?? 0) > 0 ? [{ name: '其他', value: others.value ?? 0 }] : []),
  ];
  return (
    <ChartShell
      title="模型分布（成本）"
      hint={stale ?? null}
      loading={loading ?? false}
      empty={!data.length}
      emptyHint="按模型聚合的成本占比将显示在此"
    >
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
          >
            {data.map((_, idx) => (
              <Cell key={idx} fill={COLORS[idx % COLORS.length] ?? '#334155'} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function PurposeBarChart({
  items,
  loading,
  stale,
}: {
  items?: BreakdownItem[];
  loading?: boolean;
  stale?: string | null;
}) {
  const data = (items ?? []).map((i) => ({ name: i.label, value: i.value }));
  return (
    <ChartShell
      title="用途分布（成本）"
      hint={stale ?? null}
      loading={loading ?? false}
      empty={!data.length}
      emptyHint="chat / embedding 等用途成本将显示在此"
    >
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#4f46e5" name="USD" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function SuccessRateChart({
  groups,
  loading,
  stale,
}: {
  groups?: SeriesGroup[];
  loading?: boolean;
  stale?: string | null;
}) {
  const data = mergeSeriesPoints(groups ?? []).map((p) => ({
    t: p.t,
    rate: Number((p.success_rate * 100).toFixed(2)),
  }));
  return (
    <ChartShell
      title="调用成功率"
      hint={stale ?? null}
      loading={loading ?? false}
      empty={!data.length}
      emptyHint="产生调用后将显示成功率曲线"
    >
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="t" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="rate"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            name="成功率 %"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function TopConsumersChart({
  items,
  loading,
  stale,
}: {
  items?: BreakdownItem[];
  loading?: boolean;
  stale?: string | null;
}) {
  const data = [...(items ?? [])].reverse().map((i) => ({ name: i.label, value: i.value }));
  return (
    <ChartShell
      title="Top 消耗排行"
      hint={stale ?? null}
      loading={loading ?? false}
      empty={!data.length}
      emptyHint="按用户或知识库聚合的消耗排行将显示在此"
    >
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={96} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#6366f1" name="USD" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function ConnectionHealthPanel({
  connections,
  groups,
  loading,
}: {
  connections?: ModelConnection[];
  groups?: SeriesGroup[];
  loading?: boolean;
}) {
  const latestLatency = new Map<string, number | null>();
  for (const g of groups ?? []) {
    const id = g.group.connection_id;
    if (!id) continue;
    const last = g.points[g.points.length - 1];
    latestLatency.set(id, last?.latency_p95_ms ?? null);
  }
  const rows = connections ?? [];
  return (
    <ChartShell
      title="接入点健康与延迟"
      loading={loading ?? false}
      empty={!rows.length}
      emptyHint="配置模型接入点后可在此查看健康与延迟"
    >
      <div className="overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="pb-2 font-medium">名称</th>
              <th className="pb-2 font-medium">模型</th>
              <th className="pb-2 font-medium">健康</th>
              <th className="pb-2 font-medium">P95 (ms)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {rows.map((c) => (
              <tr key={c.id}>
                <td className="py-2 pr-2 text-slate-800">{c.name}</td>
                <td className="py-2 pr-2 text-slate-500">{c.model}</td>
                <td className="py-2 pr-2">
                  <HealthStatusBadge health={c.health} />
                </td>
                <td className="py-2 text-slate-800">
                  {latestLatency.get(c.id) != null ? latestLatency.get(c.id) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(groups?.length ?? 0) > 0 ? (
        <div className="mt-3 h-[120px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mergeConnectionLatency(groups ?? [])}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="t" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="p95"
                stroke="#4f46e5"
                strokeWidth={2}
                dot={false}
                name="P95 ms"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </ChartShell>
  );
}

function mergeConnectionLatency(groups: SeriesGroup[]) {
  return mergeSeriesPoints(groups).map((p) => ({ t: p.t, p95: p.latency_p95_ms ?? 0 }));
}
