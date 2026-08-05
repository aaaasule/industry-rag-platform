import { useEffect, useMemo, useRef, useState } from 'react';

import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { useToast } from '@/components/toast/useToast';
import { AUDIT_ACTIONS } from './api';
import { useAuditLogs, useMemberships } from './hooks';

const PAGE_SIZE = 20;

export function AuditPanel({ enabled }: { enabled: boolean }) {
  const toast = useToast();
  const [action, setAction] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const toastedError = useRef<string | null>(null);

  const membersQ = useMemberships(enabled);
  const nameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of membersQ.data?.items ?? []) {
      map.set(m.user_id, m.display_name || m.email);
    }
    return map;
  }, [membersQ.data]);

  const params = {
    action: action || undefined,
    from: from ? new Date(from).toISOString() : undefined,
    to: to ? new Date(to).toISOString() : undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const logsQ = useAuditLogs(params, enabled);
  const items = logsQ.data?.items ?? [];
  const total = logsQ.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (!logsQ.isError) {
      toastedError.current = null;
      return;
    }
    const msg = logsQ.error instanceof Error ? logsQ.error.message : '加载审计失败';
    if (toastedError.current === msg) return;
    toastedError.current = msg;
    toast.error(msg);
  }, [logsQ.error, logsQ.isError, toast]);

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-muted">
        审计记录按时间倒序。`to` 为开区间（不含终点）。操作者名称来自成员列表映射。
      </p>

      <div className="flex flex-wrap items-end gap-3 panel p-4">
        <label className="block text-sm">
          <span className="field-label">Action</span>
          <select
            className="field-input min-w-[200px]"
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setPage(0);
            }}
          >
            <option value="">全部</option>
            {AUDIT_ACTIONS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="field-label">从</span>
          <input
            type="datetime-local"
            className="field-input"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setPage(0);
            }}
          />
        </label>
        <label className="block text-sm">
          <span className="field-label">到（不含）</span>
          <input
            type="datetime-local"
            className="field-input"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setPage(0);
            }}
          />
        </label>
      </div>

      {logsQ.isLoading ? (
        <div className="panel space-y-3 p-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      ) : items.length === 0 ? (
        <div className="panel border-dashed">
          <EmptyState title="暂无审计记录" description="调整筛选条件，或等待产生管理操作后再查看" />
        </div>
      ) : (
        <div className="table-scroll panel">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">时间</th>
                <th className="px-4 py-3 font-medium">操作者</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">目标</th>
                <th className="px-4 py-3 font-medium">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {items.map((row) => (
                <tr key={row.id}>
                  <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                    {new Date(row.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    {row.actor_id ? (nameById.get(row.actor_id) ?? shortId(row.actor_id)) : '系统'}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink">{row.action}</td>
                  <td className="px-4 py-3 text-ink-muted">
                    {row.target_type}
                    {row.target_id ? (
                      <span className="ml-1 font-mono text-xs text-ink-faint">
                        {shortId(row.target_id)}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{row.ip ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between text-sm text-ink-muted">
        <span>
          共 {total} 条 · 第 {page + 1}/{pageCount} 页
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-md border border-line px-3 py-1.5 disabled:opacity-40"
            disabled={page <= 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            上一页
          </button>
          <button
            type="button"
            className="rounded-md border border-line px-3 py-1.5 disabled:opacity-40"
            disabled={(page + 1) * PAGE_SIZE >= total}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
}

function shortId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}
