import { NavLink, Outlet } from 'react-router-dom';

import { useLogout, useSession, useSwitchTenant } from '@/features/auth/hooks';

type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  roles?: ReadonlyArray<'owner' | 'admin' | 'member'>;
};

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: '概览', end: true },
  { to: '/knowledge', label: '知识库' },
  { to: '/chat', label: '问答' },
  { to: '/usages', label: '用量', roles: ['owner', 'admin'] },
  { to: '/admin', label: '运营', roles: ['owner', 'admin'] },
];

export function AppLayout() {
  const { session } = useSession();
  const switchTenant = useSwitchTenant();
  const logout = useLogout();
  const role = session?.current_tenant.role;
  const navItems = NAV_ITEMS.filter(
    (item) => item.roles == null || (role != null && item.roles.includes(role)),
  );

  return (
    <div className="flex h-full flex-col">
      <header className="app-enter flex h-14 shrink-0 items-center gap-8 border-b border-line bg-surface px-6">
        <span className="text-[15px] font-semibold tracking-tight text-ink">工业知识库平台</span>

        <nav className="flex h-full items-stretch gap-0.5">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                [
                  'relative flex items-center px-3 text-sm transition-colors duration-150',
                  isActive
                    ? 'font-medium text-brand-700 after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:bg-brand-600'
                    : 'text-ink-muted hover:text-ink',
                ].join(' ')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          {session && session.tenants.length > 1 && (
            <select
              aria-label="切换租户"
              value={session.current_tenant.id}
              disabled={switchTenant.isPending}
              onChange={(e) => switchTenant.mutate(e.target.value)}
              className="rounded border border-line bg-surface px-2 py-1 text-sm text-ink"
            >
              {session.tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          )}

          {session && (
            <span className="text-sm text-ink-muted">
              {session.user.display_name}
              <span className="ml-1.5 text-xs text-ink-faint">
                {roleLabel(session.current_tenant.role)}
              </span>
            </span>
          )}

          <button type="button" onClick={() => void logout()} className="btn-ghost">
            登出
          </button>
        </div>
      </header>

      <main className="app-enter flex-1 overflow-auto p-6 [animation-delay:40ms]">
        <Outlet />
      </main>
    </div>
  );
}

function roleLabel(role: string): string {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role;
}
