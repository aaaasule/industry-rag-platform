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
      <header className="flex h-14 shrink-0 items-center gap-6 border-b border-slate-200 bg-white px-6">
        <span className="text-sm font-semibold text-slate-900">工业知识库平台</span>

        <nav className="flex items-center gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                [
                  'rounded-md px-3 py-1.5 text-sm transition',
                  isActive
                    ? 'bg-brand-50 font-medium text-brand-700'
                    : 'text-slate-600 hover:bg-slate-100',
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
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            >
              {session.tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          )}

          {session && (
            <span className="text-sm text-slate-600">
              {session.user.display_name}
              <span className="ml-1.5 text-xs text-slate-400">
                {roleLabel(session.current_tenant.role)}
              </span>
            </span>
          )}

          <button
            type="button"
            onClick={() => void logout()}
            className="text-sm text-slate-500 hover:text-slate-900"
          >
            登出
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}

function roleLabel(role: string): string {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role;
}
