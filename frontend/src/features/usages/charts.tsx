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

import type { BreakdownItem, ModelConnection, SeriesGroup } from './api';
import { mergeSeriesPoints } from './api';

const COLORS = ['#0f766e', '#0369a1', '#b45309', '#7c3aed', '#be123c', '#334155', '#059669'];

function ChartShell({
  title,
  hint = null,
  empty = false,
  loading = false,
  children,
}: {
  title: string;
  hint?: string | null;
  empty?: boolean;
  loading?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="flex min-h-[280px] flex-col panel p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-ink">{title}</h3>
        {hint ? <span className="text-xs text-ink-faint">{hint}</span> : null}
      </div>
      <div className="min-h-0 flex-1">
        {loading ? (
          <p className="flex h-full items-center justify-center text-sm text-ink-faint">加载中…</p>
        ) : empty ? (
          <p className="flex h-full items-center justify-center text-sm text-ink-faint">暂无数据</p>
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
            stroke="#0f766e"
            fill="#99f6e4"
            name="prompt"
          />
          <Area
            type="monotone"
            dataKey="completion"
            stackId="1"
            stroke="#0369a1"
            fill="#bae6fd"
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
            stroke="#b45309"
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
    >
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#0f766e" name="USD" radius={[4, 4, 0, 0]} />
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
            stroke="#059669"
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
    >
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={96} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#7c3aed" name="USD" radius={[0, 4, 4, 0]} />
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
    <ChartShell title="接入点健康与延迟" loading={loading ?? false} empty={!rows.length}>
      <div className="overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-ink-muted">
            <tr>
              <th className="pb-2 font-medium">名称</th>
              <th className="pb-2 font-medium">模型</th>
              <th className="pb-2 font-medium">健康</th>
              <th className="pb-2 font-medium">P95 (ms)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((c) => (
              <tr key={c.id}>
                <td className="py-2 pr-2 text-ink">{c.name}</td>
                <td className="py-2 pr-2 text-ink-muted">{c.model}</td>
                <td className="py-2 pr-2">
                  <HealthBadge health={c.health} />
                </td>
                <td className="py-2 text-ink">
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
                stroke="#0369a1"
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

function HealthBadge({ health }: { health: string }) {
  const tone =
    health === 'healthy'
      ? 'bg-ok/10 text-ok'
      : health === 'down'
        ? 'bg-danger/10 text-danger'
        : 'bg-canvas text-ink-muted';
  const label = health === 'healthy' ? '正常' : health === 'down' ? '故障' : health || '未知';
  return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${tone}`}>{label}</span>;
}
