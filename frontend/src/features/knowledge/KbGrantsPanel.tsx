import { useMemo, useState, type FormEvent } from 'react';

import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { useToast } from '@/components/toast/useToast';
import { useMemberships } from '@/features/admin/hooks';
import { ApiError } from '@/lib/http';
import type { GrantPermission } from './api';
import { useDeleteGrant, useGrants, useUpsertGrant } from './hooks';

const PERMS: GrantPermission[] = ['read', 'write', 'manage'];

function permLabel(p: string): string {
  if (p === 'manage') return '管理';
  if (p === 'write') return '写入';
  return '只读';
}

/** 知识库级授权：对本租户成员授予 read/write/manage。 */
export function KbGrantsPanel({ kbId }: { kbId: string }) {
  const toast = useToast();
  const grantsQ = useGrants(kbId);
  const membersQ = useMemberships(true);
  const upsert = useUpsertGrant(kbId);
  const remove = useDeleteGrant(kbId);

  const [userId, setUserId] = useState('');
  const [permission, setPermission] = useState<GrantPermission>('read');

  const grants = grantsQ.data ?? [];
  const members = membersQ.data?.items ?? [];
  const grantedIds = useMemo(() => new Set(grants.map((g) => g.user_id)), [grants]);
  const candidates = members.filter((m) => !grantedIds.has(m.user_id));

  async function onGrant(e: FormEvent) {
    e.preventDefault();
    if (!userId) return;
    try {
      await upsert.mutateAsync({ userId, permission });
      toast.success('已更新授权');
      setUserId('');
      setPermission('read');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : '授权失败');
    }
  }

  async function onChangePerm(uid: string, next: GrantPermission) {
    try {
      await upsert.mutateAsync({ userId: uid, permission: next });
      toast.success('权限已更新');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : '更新失败');
    }
  }

  async function onRevoke(uid: string, label: string) {
    if (!window.confirm(`确认撤销「${label}」的知识库授权？`)) return;
    try {
      await remove.mutateAsync(uid);
      toast.success('已撤销授权');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : '撤销失败');
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-ink">知识库授权</h2>
        <p className="mt-1 text-xs text-ink-muted">
          owner/admin 默认拥有全部库权限；此处为普通成员单独授权。仅可授予本租户成员。
        </p>
      </div>

      <form onSubmit={(e) => void onGrant(e)} className="flex flex-wrap items-end gap-3 panel p-4">
        <label className="block min-w-[200px] flex-1 text-sm">
          <span className="field-label">成员</span>
          <select
            className="field-input"
            required
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          >
            <option value="">选择成员…</option>
            {candidates.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.display_name}（{m.email}）
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="field-label">权限</span>
          <select
            className="field-input"
            value={permission}
            onChange={(e) => setPermission(e.target.value as GrantPermission)}
          >
            {PERMS.map((p) => (
              <option key={p} value={p}>
                {permLabel(p)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="btn-primary"
          disabled={upsert.isPending || !userId || candidates.length === 0}
        >
          {upsert.isPending ? '提交中…' : '授予'}
        </button>
      </form>

      {grantsQ.isLoading ? (
        <div className="panel space-y-2 p-4">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-full" />
        </div>
      ) : grants.length === 0 ? (
        <div className="panel border-dashed">
          <EmptyState title="暂无单独授权" description="从上方选择成员并授予权限" />
        </div>
      ) : (
        <div className="table-scroll panel">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">成员</th>
                <th className="px-4 py-3 font-medium">权限</th>
                <th className="px-4 py-3 font-medium">授权时间</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {grants.map((g) => {
                const label = g.display_name || g.email || g.user_id;
                return (
                  <tr key={g.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-ink">{label}</div>
                      {g.email ? <div className="text-xs text-ink-muted">{g.email}</div> : null}
                    </td>
                    <td className="px-4 py-3">
                      <select
                        className="rounded-md border border-line px-2 py-1 text-sm"
                        value={g.permission}
                        disabled={upsert.isPending}
                        onChange={(e) =>
                          void onChangePerm(g.user_id, e.target.value as GrantPermission)
                        }
                      >
                        {PERMS.map((p) => (
                          <option key={p} value={p}>
                            {permLabel(p)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-ink-muted">
                      {new Date(g.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="text-xs text-danger hover:underline disabled:text-ink-faint"
                        disabled={remove.isPending}
                        onClick={() => void onRevoke(g.user_id, label)}
                      >
                        撤销
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
