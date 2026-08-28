import { useEffect, useState } from 'react';
import { BrainCircuit, CircleHelp, Menu, PanelLeftClose, PanelLeft } from 'lucide-react';
import { Outlet } from 'react-router-dom';

import { SideSheet } from '@/components/SideSheet';
import { UserMenu } from '@/components/UserMenu';
import { Button } from '@/components/ui/Button';
import { SidebarNav } from '@/components/ui/SidebarNav';
import { cn } from '@/components/ui/cn';
import { useLogout, useSession, useSwitchTenant } from '@/features/auth/hooks';
import { DOCS_URL } from '@/lib/docs';

const COLLAPSE_KEY = 'irp.sidebar.collapsed';

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1';
  } catch {
    return false;
  }
}

export function AppLayout() {
  const { session } = useSession();
  const switchTenant = useSwitchTenant();
  const logout = useLogout();
  const [navOpen, setNavOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const role = session?.current_tenant.role;

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0');
    } catch {
      /* ignore quota / private mode */
    }
  }, [collapsed]);

  const userBlock = session ? (
    <UserMenu
      session={session}
      collapsed={collapsed}
      switchPending={switchTenant.isPending}
      onSwitchTenant={(id) => switchTenant.mutate(id)}
      onLogout={() => void logout()}
    />
  ) : null;

  return (
    <div className="flex h-full bg-[#F9FAFB]">
      <aside
        className={cn(
          'relative z-20 hidden shrink-0 flex-col border-r border-slate-200/60 bg-white transition-[width] duration-200 ease-in-out lg:flex',
        )}
        style={{
          width: collapsed ? 'var(--sidebar-w-collapsed)' : 'var(--sidebar-w)',
        }}
      >
        <div
          className={cn(
            'flex shrink-0 items-center gap-2 border-b border-slate-100 px-3 py-3',
            collapsed ? 'flex-col gap-2' : 'justify-between',
          )}
        >
          <div
            className={cn(
              'flex min-w-0 items-center gap-2.5',
              collapsed && 'justify-center',
            )}
          >
            <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm">
              <BrainCircuit className="h-5 w-5" strokeWidth={1.5} aria-hidden />
            </span>
            {!collapsed && (
              <div className="min-w-0">
                <p className="truncate text-sm font-bold tracking-tight text-slate-900">
                  工业知识库
                </p>
                <p className="truncate text-[11px] text-slate-400">v2.0 · 智能检索</p>
              </div>
            )}
          </div>
          <button
            type="button"
            aria-label={collapsed ? '展开导航' : '收起导航'}
            aria-expanded={!collapsed}
            onClick={() => setCollapsed((v) => !v)}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-all duration-200 hover:bg-slate-100 hover:text-slate-700"
          >
            {collapsed ? (
              <PanelLeft className="h-4 w-4" strokeWidth={1.5} />
            ) : (
              <PanelLeftClose className="h-4 w-4" strokeWidth={1.5} />
            )}
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <SidebarNav role={role} collapsed={collapsed} />
        </div>

        <div className="shrink-0 space-y-1 border-t border-slate-100 px-2.5 py-2">
          <a
            href={DOCS_URL}
            target="_blank"
            rel="noopener noreferrer"
            title={collapsed ? '帮助文档' : undefined}
            className={cn(
              'flex h-9 items-center rounded-lg text-sm text-slate-500 transition-all duration-200 hover:bg-slate-100 hover:text-slate-700',
              collapsed ? 'justify-center px-0' : 'gap-3 px-3',
            )}
          >
            <CircleHelp className="h-4 w-4 shrink-0" strokeWidth={1.5} aria-hidden />
            {!collapsed && '帮助文档'}
          </a>
          {userBlock}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className="sticky top-0 z-30 flex shrink-0 items-center gap-3 border-b border-slate-200/60 bg-white/90 px-4 backdrop-blur-md lg:hidden"
          style={{ height: 'var(--shell-header-h)' }}
        >
          <Button
            variant="ghost"
            className="!px-2"
            aria-label="打开导航"
            onClick={() => setNavOpen(true)}
          >
            <Menu className="h-5 w-5" strokeWidth={1.5} />
          </Button>
          <div className="flex min-w-0 items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
              <BrainCircuit className="h-4 w-4" strokeWidth={1.5} aria-hidden />
            </span>
            <span className="truncate text-[15px] font-semibold text-slate-800">
              工业知识库
            </span>
          </div>
        </header>

        <main className="workbench app-enter min-h-0 flex-1 overflow-hidden">
          <div className="workbench-pad min-h-0 h-full overflow-auto">
            <Outlet />
          </div>
        </main>
      </div>

      <SideSheet open={navOpen} onClose={() => setNavOpen(false)} title="导航" side="left">
        <div className="flex min-h-full flex-col">
          <div className="mb-2 flex items-center gap-2.5 px-1 pb-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
              <BrainCircuit className="h-5 w-5" strokeWidth={1.5} aria-hidden />
            </span>
            <div>
              <p className="text-sm font-semibold text-ink">工业知识库</p>
              <p className="text-[11px] text-ink-faint">v2.0 · 智能检索</p>
            </div>
          </div>
          <div className="flex-1">
            <SidebarNav role={role} onNavigate={() => setNavOpen(false)} />
          </div>
          <div className="mt-auto space-y-1 border-t border-slate-100 pt-2">
            <a
              href={DOCS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-9 items-center gap-3 rounded-lg px-3 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              <CircleHelp className="h-4 w-4" strokeWidth={1.5} />
              帮助文档
            </a>
          </div>
          {session ? (
            <div className="sticky bottom-0 -mx-3 mt-auto border-t border-line/70 bg-canvas px-3 pt-2">
              <UserMenu
                session={session}
                collapsed={false}
                switchPending={switchTenant.isPending}
                onSwitchTenant={(id) => switchTenant.mutate(id)}
                onLogout={() => void logout()}
              />
            </div>
          ) : null}
        </div>
      </SideSheet>
    </div>
  );
}
