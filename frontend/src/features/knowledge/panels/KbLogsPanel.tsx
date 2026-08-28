import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { listAuditLogs } from '@/features/admin/api';
import { useMemberships } from '@/features/admin/hooks';
import { useSession } from '@/features/auth/hooks';
import { useQuery } from '@tanstack/react-query';

const KB_ACTIONS = ['kb_grant.create', 'kb_grant.update', 'kb_grant.delete', 'knowledge_base.delete'];

function matchesKb(
  kbId: string,
  row: { action: string; target_id: string | null; payload?: Record<string, unknown> },
): boolean {
  if (row.action === 'knowledge_base.delete' && row.target_id === kbId) return true;
  const payloadKb = row.payload?.kb_id;
  return typeof payloadKb === 'string' && payloadKb === kbId;
}

export function KbLogsPanel() {
  const { kbId = '' } = useParams();
  const { session } = useSession();
  const role = session?.current_tenant.role;
  const canView = role === 'owner' || role === 'admin';
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const membersQ = useMemberships(canView);
  const nameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of membersQ.data?.items ?? []) {
      map.set(m.user_id, m.display_name || m.email);
    }
    return map;
  }, [membersQ.data]);

  const logsQ = useQuery({
    queryKey: ['kb-audit', kbId, page],
    queryFn: async () => {
      const merged: Awaited<ReturnType<typeof listAuditLogs>>['items'] = [];
      for (const action of KB_ACTIONS) {
        const batch = await listAuditLogs({ action, limit: 100, offset: 0 });
        for (const row of batch.items) {
          if (matchesKb(kbId, row)) merged.push(row);
        }
      }
      merged.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      const start = page * pageSize;
      return {
        items: merged.slice(start, start + pageSize),
        total: merged.length,
      };
    },
    enabled: canView && Boolean(kbId),
  });

  useEffect(() => setPage(0), [kbId]);

  if (!canView) {
    return (
      <div className="panel border-dashed p-10 text-center">
        <p className="text-sm text-slate-600">日志仅对租户 owner / admin 开放</p>
      </div>
    );
  }

  const items = logsQ.data?.items ?? [];
  const total = logsQ.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">日志</h2>
        <p className="mt-1 text-sm text-slate-500">
          展示与本知识库相关的授权变更与删除记录。文档上传/摄取尚未写入审计。
        </p>
      </header>

      <section className="table-scroll panel">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs text-slate-500">
            <tr>
              <th className="px-4 py-3">时间</th>
              <th className="px-4 py-3">操作者</th>
              <th className="px-4 py-3">动作</th>
              <th className="px-4 py-3">详情</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {logsQ.isLoading &&
              Array.from({ length: 4 }, (_, i) => (
                <tr key={i}>
                  <td colSpan={4} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))}
            {!logsQ.isLoading && items.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <EmptyState compact title="暂无相关日志" description="授权或删库操作会记录在此" />
                </td>
              </tr>
            ) : null}
            {items.map((row) => (
              <tr key={row.id} className="hover:bg-slate-50/80">
                <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                  {new Date(row.created_at).toLocaleString('zh-CN')}
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {row.actor_id ? (nameById.get(row.actor_id) ?? row.actor_id.slice(0, 8)) : '—'}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-800">{row.action}</td>
                <td className="max-w-md px-4 py-3 text-xs text-slate-500">
                  <pre className="whitespace-pre-wrap break-all font-sans">
                    {JSON.stringify(row.payload ?? {}, null, 0)}
                  </pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {total > pageSize ? (
        <div className="flex items-center justify-between text-sm text-slate-500">
          <span>
            共 {total} 条 · 第 {page + 1} / {pageCount} 页
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 0}
              className="rounded-md border border-slate-200 px-3 py-1.5 disabled:opacity-40"
              onClick={() => setPage((p) => p - 1)}
            >
              上一页
            </button>
            <button
              type="button"
              disabled={page + 1 >= pageCount}
              className="rounded-md border border-slate-200 px-3 py-1.5 disabled:opacity-40"
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
