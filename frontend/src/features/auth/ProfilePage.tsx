import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Building2, Key, UserCircle } from 'lucide-react';

import { useToast } from '@/components/toast/useToast';
import { Badge, Button, Card, Input, PageHeader } from '@/components/ui';
import { ApiError } from '@/lib/http';

import {
  useChangePassword,
  useSession,
  useSwitchTenant,
  useUpdateProfile,
} from './hooks';

function roleLabel(role: string): string {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role;
}

function statusLabel(status: string): string {
  return { active: '正常', disabled: '已停用', invited: '待激活' }[status] ?? status;
}

export function ProfilePage() {
  const toast = useToast();
  const { session, isLoading } = useSession();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const switchTenant = useSwitchTenant();

  const [displayName, setDisplayName] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    if (session) setDisplayName(session.user.display_name);
  }, [session]);

  const dirty = useMemo(() => {
    if (!session) return false;
    return displayName.trim() !== session.user.display_name;
  }, [displayName, session]);

  if (isLoading || !session) {
    return (
      <div className="page-shell mx-auto max-w-3xl">
        <Card className="p-8 text-sm text-ink-muted">加载个人资料…</Card>
      </div>
    );
  }

  const initial = (session.user.display_name || '?').slice(0, 1);

  async function onSaveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileError(null);
    const name = displayName.trim();
    if (!name) {
      setProfileError('显示名不能为空');
      return;
    }
    try {
      await updateProfile.mutateAsync({ display_name: name });
      toast.success('已更新显示名');
    } catch (err) {
      setProfileError(err instanceof ApiError ? err.message : '更新失败');
    }
  }

  async function onChangePassword(e: FormEvent) {
    e.preventDefault();
    setPasswordError(null);
    if (newPassword !== confirmPassword) {
      setPasswordError('两次输入的新密码不一致');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('新密码至少 8 位');
      return;
    }
    try {
      await changePassword.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast.success('密码已修改');
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : '修改失败');
    }
  }

  return (
    <div className="page-shell mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="个人资料"
        description={`${session.user.email} · 当前租户 ${session.current_tenant.name}`}
      />

      <Card padding={false} className="p-6 sm:p-8">
        <div className="mb-5 flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <UserCircle className="h-4 w-4" strokeWidth={1.5} />
          </span>
          <h2 className="text-sm font-semibold text-ink">基本资料</h2>
        </div>

        <div className="mb-6 flex items-center gap-4">
          <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-xl font-semibold text-white shadow-sm">
            {initial}
          </span>
          <div className="min-w-0 space-y-1">
            <p className="truncate text-sm text-ink-muted">{session.user.email}</p>
            <Badge tone="ok">{statusLabel(session.user.status)}</Badge>
          </div>
        </div>

        <form onSubmit={(e) => void onSaveProfile(e)} className="space-y-4">
          <Input
            label="显示名"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={128}
            autoComplete="nickname"
          />
          {profileError ? <p className="text-sm text-danger">{profileError}</p> : null}
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={!dirty || updateProfile.isPending}
              className="!rounded-full !px-6"
            >
              {updateProfile.isPending ? '保存中…' : '保存'}
            </Button>
          </div>
        </form>
      </Card>

      <Card padding={false} className="p-6 sm:p-8">
        <div className="mb-5 flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Key className="h-4 w-4" strokeWidth={1.5} />
          </span>
          <h2 className="text-sm font-semibold text-ink">修改密码</h2>
        </div>
        <form onSubmit={(e) => void onChangePassword(e)} className="space-y-4">
          <Input
            label="当前密码"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <Input
            label="新密码"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            hint="至少 8 位，最长 128 位"
          />
          <Input
            label="确认新密码"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          {passwordError ? <p className="text-sm text-danger">{passwordError}</p> : null}
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={
                changePassword.isPending ||
                !currentPassword ||
                !newPassword ||
                !confirmPassword
              }
              className="!rounded-full !px-6"
            >
              {changePassword.isPending ? '提交中…' : '更新密码'}
            </Button>
          </div>
        </form>
      </Card>

      <Card padding={false} className="p-6 sm:p-8">
        <div className="mb-5 flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Building2 className="h-4 w-4" strokeWidth={1.5} />
          </span>
          <h2 className="text-sm font-semibold text-ink">我的租户</h2>
        </div>
        <ul className="space-y-2.5">
          {session.tenants.map((t) => {
            const current = t.id === session.current_tenant.id;
            return (
              <li
                key={t.id}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-line/80 bg-elevated/40 px-3.5 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-medium text-ink">{t.name}</p>
                    {current ? <Badge tone="accent">当前</Badge> : null}
                  </div>
                  <p className="mt-0.5 truncate text-xs text-ink-faint">
                    {t.slug} · {roleLabel(t.role)}
                  </p>
                </div>
                {!current ? (
                  <Button
                    variant="secondary"
                    className="!rounded-full !px-3 !py-1.5 text-xs"
                    disabled={switchTenant.isPending}
                    onClick={() => {
                      switchTenant.mutate(t.id, {
                        onSuccess: () => toast.success(`已切换到 ${t.name}`),
                        onError: (err) =>
                          toast.error(err instanceof Error ? err.message : '切换失败'),
                      });
                    }}
                  >
                    切换
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
