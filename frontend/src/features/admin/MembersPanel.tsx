import { useState, type FormEvent } from 'react';

import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { useToast } from '@/components/toast/useToast';
import { useSession } from '@/features/auth/hooks';
import { ApiError } from '@/lib/http';
import type { MemberRole } from './api';
import { useAddMember, useMemberships, useRemoveMember, useUpdateMemberRole } from './hooks';

const ROLES: MemberRole[] = ['member', 'admin', 'owner'];

export function MembersPanel({ enabled }: { enabled: boolean }) {
  const toast = useToast();
  const { session } = useSession();
  const myRole = session?.current_tenant.role;
  const myUserId = session?.user.id;
  const listQ = useMemberships(enabled);
  const addM = useAddMember();
  const roleM = useUpdateMemberRole();
  const removeM = useRemoveMember();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<MemberRole>('member');
  const [error, setError] = useState<string | null>(null);

  const items = listQ.data?.items ?? [];
  const isOwner = myRole === 'owner';

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await addM.mutateAsync({ email: email.trim(), role });
      setEmail('');
      setRole('member');
      toast.success(`已添加成员 ${email.trim()}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '添加失败';
      setError(msg);
      toast.error(msg);
    }
  }

  async function onRoleChange(userId: string, next: MemberRole) {
    setError(null);
    try {
      await roleM.mutateAsync({ userId, role: next });
      toast.success(`角色已更新为 ${roleLabel(next)}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '角色更新失败';
      setError(msg);
      toast.error(msg);
    }
  }

  async function onRemove(userId: string, name: string) {
    if (!window.confirm(`确认将「${name}」移出本租户？`)) return;
    setError(null);
    try {
      await removeM.mutateAsync(userId);
      toast.success(`已移除「${name}」`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '移除失败';
      setError(msg);
      toast.error(msg);
    }
  }

  function canChangeRole(targetRole: string, targetUserId: string): boolean {
    if (targetUserId === myUserId) return false;
    if (targetRole === 'owner' && !isOwner) return false;
    return true;
  }

  function canRemove(targetRole: string, targetUserId: string): boolean {
    if (targetUserId === myUserId) return false;
    if (targetRole === 'owner' && !isOwner) return false;
    return true;
  }

  function roleOptionsFor(): MemberRole[] {
    if (!isOwner) {
      return ROLES.filter((r) => r !== 'owner');
    }
    return ROLES;
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-muted">
        仅可添加已注册用户（按邮箱）。admin 不能变更或移除 owner；不能移除自己。
      </p>

      {error ? (
        <p className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}

      <form
        onSubmit={(e) => void onAdd(e)}
        className="flex flex-wrap items-end gap-3 panel p-4"
      >
        <label className="block min-w-[220px] flex-1 text-sm">
          <span className="field-label">邮箱</span>
          <input
            type="email"
            required
            className="field-input"
            placeholder="user@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="field-label">角色</span>
          <select
            className="field-input"
            value={role}
            onChange={(e) => setRole(e.target.value as MemberRole)}
          >
            {(isOwner ? ROLES : ROLES.filter((r) => r !== 'owner')).map((r) => (
              <option key={r} value={r}>
                {roleLabel(r)}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn-primary" disabled={addM.isPending}>
          {addM.isPending ? '添加中…' : '添加成员'}
        </button>
      </form>

      {listQ.isLoading ? (
        <div className="panel space-y-3 p-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      ) : items.length === 0 ? (
        <div className="panel border-dashed">
          <EmptyState title="暂无成员" description="通过上方表单按邮箱邀请成员加入租户" />
        </div>
      ) : (
        <div className="table-scroll panel">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">成员</th>
                <th className="px-4 py-3 font-medium">角色</th>
                <th className="px-4 py-3 font-medium">加入时间</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {items.map((m) => {
                const editable = canChangeRole(m.role, m.user_id);
                const removable = canRemove(m.role, m.user_id);
                return (
                  <tr key={m.user_id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-ink">{m.display_name}</div>
                      <div className="text-xs text-ink-muted">{m.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      {editable ? (
                        <select
                          className="rounded-md border border-line px-2 py-1 text-sm"
                          value={m.role}
                          disabled={roleM.isPending}
                          onChange={(e) =>
                            void onRoleChange(m.user_id, e.target.value as MemberRole)
                          }
                        >
                          {roleOptionsFor().map((r) => (
                            <option key={r} value={r}>
                              {roleLabel(r)}
                            </option>
                          ))}
                          {m.role === 'owner' && !roleOptionsFor().includes('owner') ? (
                            <option value="owner">{roleLabel('owner')}</option>
                          ) : null}
                        </select>
                      ) : (
                        <span>{roleLabel(m.role)}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-ink-muted">
                      {new Date(m.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        disabled={!removable || removeM.isPending}
                        className="text-xs text-danger hover:underline disabled:cursor-not-allowed disabled:text-ink-faint"
                        onClick={() => void onRemove(m.user_id, m.display_name)}
                      >
                        移除
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function roleLabel(role: string): string {
  if (role === 'owner') return 'owner';
  if (role === 'admin') return 'admin';
  return 'member';
}
