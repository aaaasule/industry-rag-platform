import { NavLink, Outlet } from 'react-router-dom';

import { BrandMark } from '@/components/BrandMark';
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
    <div className="flex h-full flex-col bg-canvas">
      <header
        className="app-enter flex h-14 shrink-0 items-center gap-6 border-b border-line bg-surface lg:gap-8"
        style={{ paddingLeft: 'var(--workbench-pad-x)', paddingRight: 'var(--workbench-pad-x)' }}
      >
        <div className="flex shrink-0 items-center gap-2.5">
          <BrandMark size={28} />
          <span className="text-[15px] font-semibold tracking-tight text-ink">工业知识库平台</span>
        </div>

        <nav className="flex h-full min-w-0 items-stretch gap-0.5 overflow-x-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                [
                  'relative flex shrink-0 items-center px-3 text-sm transition-colors duration-150',
                  isActive
                    ? 'font-medium text-brand-700 after:absolute after:inset-x-1.5 after:bottom-0 after:h-[3px] after:rounded-t-sm after:bg-brand-600'
                    : 'text-ink-muted hover:text-ink',
                ].join(' ')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-3">
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
            <span className="hidden text-sm text-ink-muted sm:inline">
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

      <main className="workbench app-enter flex min-h-0 flex-1 flex-col overflow-hidden [animation-delay:40ms]">
        <div className="workbench-pad min-h-0 flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function roleLabel(role: string): string {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role;
}
