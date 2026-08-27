import { useState } from 'react';
import { List } from '@phosphor-icons/react';
import { Outlet } from 'react-router-dom';

import { BrandMark } from '@/components/BrandMark';
import { SideSheet } from '@/components/SideSheet';
import { Button } from '@/components/ui/Button';
import { SidebarNav } from '@/components/ui/SidebarNav';
import { useLogout, useSession, useSwitchTenant } from '@/features/auth/hooks';

export function AppLayout() {
  const { session } = useSession();
  const switchTenant = useSwitchTenant();
  const logout = useLogout();
  const [navOpen, setNavOpen] = useState(false);
  const role = session?.current_tenant.role;

  return (
    <div className="flex h-full flex-col bg-canvas">
      <header
        className="app-enter flex shrink-0 items-center gap-3 border-b border-line bg-surface px-4 lg:px-6"
        style={{ height: 'var(--shell-header-h)' }}
      >
        <Button
          variant="ghost"
          className="!px-2 lg:hidden"
          aria-label="打开导航"
          onClick={() => setNavOpen(true)}
        >
          <List size={22} weight="bold" />
        </Button>

        <div className="flex min-w-0 items-center gap-2.5">
          <BrandMark size={28} />
          <span className="hidden truncate text-[15px] font-semibold tracking-tight text-ink sm:inline">
            工业知识库平台
          </span>
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-3">
          {session && session.tenants.length > 1 && (
            <select
              aria-label="切换租户"
              value={session.current_tenant.id}
              disabled={switchTenant.isPending}
              onChange={(e) => switchTenant.mutate(e.target.value)}
              className="field-input !w-auto !py-1.5 text-sm"
            >
              {session.tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          )}

          {session && (
            <span className="hidden text-sm text-ink-muted md:inline">
              {session.user.display_name}
              <span className="ml-1.5 text-xs text-ink-faint">{roleLabel(role ?? '')}</span>
            </span>
          )}

          <Button variant="ghost" onClick={() => void logout()}>
            登出
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside
          className="hidden shrink-0 border-r border-line bg-elevated lg:block"
          style={{ width: 'var(--sidebar-w)' }}
        >
          <SidebarNav role={role} />
        </aside>

        <main className="workbench app-enter min-h-0 flex-1 overflow-hidden [animation-delay:40ms]">
          <div className="workbench-pad min-h-0 h-full overflow-auto">
            <Outlet />
          </div>
        </main>
      </div>

      <SideSheet open={navOpen} onClose={() => setNavOpen(false)} title="导航" side="left">
        <SidebarNav role={role} onNavigate={() => setNavOpen(false)} />
      </SideSheet>
    </div>
  );
}

function roleLabel(role: string): string {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role;
}
