import { useState, type FormEvent } from 'react';

import { useSession } from '@/features/auth/hooks';
import { ApiError } from '@/lib/http';
import type { MemberRole } from './api';
import { useAddMember, useMemberships, useRemoveMember, useUpdateMemberRole } from './hooks';

const ROLES: MemberRole[] = ['member', 'admin', 'owner'];

export function MembersPanel({ enabled }: { enabled: boolean }) {
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '添加失败');
    }
  }

  async function onRoleChange(userId: string, next: MemberRole) {
    setError(null);
    try {
      await roleM.mutateAsync({ userId, role: next });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '角色更新失败');
    }
  }

  async function onRemove(userId: string, name: string) {
    if (!window.confirm(`确认将「${name}」移出本租户？`)) return;
    setError(null);
    try {
      await removeM.mutateAsync(userId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '移除失败');
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
      <p className="text-sm text-slate-500">
        仅可添加已注册用户（按邮箱）。admin 不能变更或移除 owner；不能移除自己。
      </p>

      {error ? (
        <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </p>
      ) : null}

      <form
        onSubmit={(e) => void onAdd(e)}
        className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4"
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
        <p className="text-sm text-slate-400">加载中…</p>
      ) : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          暂无成员
        </p>
      ) : (
        <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-100 text-xs text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">成员</th>
                <th className="px-4 py-3 font-medium">角色</th>
                <th className="px-4 py-3 font-medium">加入时间</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((m) => {
                const editable = canChangeRole(m.role, m.user_id);
                const removable = canRemove(m.role, m.user_id);
                return (
                  <tr key={m.user_id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{m.display_name}</div>
                      <div className="text-xs text-slate-500">{m.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      {editable ? (
                        <select
                          className="rounded-md border border-slate-200 px-2 py-1 text-sm"
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
                    <td className="px-4 py-3 text-slate-500">
                      {new Date(m.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        disabled={!removable || removeM.isPending}
                        className="text-xs text-rose-600 hover:underline disabled:cursor-not-allowed disabled:text-slate-300"
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
