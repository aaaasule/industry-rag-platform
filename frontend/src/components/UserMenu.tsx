import { useEffect, useId, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LogOut,
  MoreVertical,
  PieChart,
  UserCog,
} from 'lucide-react';

import { cn } from '@/components/ui/cn';
import type { SessionInfo } from '@/features/auth/api';

type Props = {
  session: SessionInfo;
  collapsed?: boolean;
  switchPending?: boolean;
  onSwitchTenant: (tenantId: string) => void;
  onLogout: () => void;
};

/** DeepSeek 风格：侧栏底部用户区 + 上拉菜单 */
export function UserMenu({
  session,
  collapsed = false,
  switchPending,
  onSwitchTenant,
  onLogout,
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const navigate = useNavigate();

  const { user, current_tenant: tenant, tenants } = session;
  const initial = (user.display_name || '?').slice(0, 1);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const go = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  return (
    <div ref={rootRef} className="relative">
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl p-1.5 transition-all duration-200',
          collapsed ? 'justify-center' : 'hover:bg-slate-100',
        )}
      >
        <button
          type="button"
          title={collapsed ? user.display_name : undefined}
          aria-label={collapsed ? `用户 ${user.display_name}` : undefined}
          onClick={() => {
            if (collapsed) setOpen((v) => !v);
            else go('/settings/profile');
          }}
          className={cn(
            'flex min-w-0 items-center gap-2.5 rounded-lg text-left transition-all duration-200',
            collapsed ? 'justify-center p-0.5' : 'flex-1 px-1 py-0.5',
          )}
        >
          <span
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-xs font-semibold text-white"
            aria-hidden
          >
            {initial}
          </span>
          {!collapsed && (
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold text-slate-800">
                {user.display_name}
              </span>
              <span className="block truncate text-xs text-slate-500">{tenant.name}</span>
            </span>
          )}
        </button>

        {!collapsed && (
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={open}
            aria-controls={menuId}
            aria-label="更多操作"
            onClick={() => setOpen((v) => !v)}
            className={cn(
              'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-all duration-200',
              'hover:bg-slate-200/70 hover:text-slate-700',
              open && 'bg-slate-200/70 text-slate-700',
            )}
          >
            <MoreVertical className="h-4 w-4" strokeWidth={1.5} />
          </button>
        )}
      </div>

      {open && (
        <div
          id={menuId}
          role="menu"
          className={cn(
            'absolute z-50 w-56 rounded-xl border border-slate-200/80 bg-white p-1.5 shadow-xl animate-fade-up',
            collapsed
              ? 'bottom-0 left-full ml-2'
              : 'bottom-full left-0 right-0 mb-2 w-full min-w-[14rem]',
          )}
        >
          <div className="px-2.5 py-2">
            <p className="truncate text-sm font-semibold text-slate-800">{user.display_name}</p>
            <p className="mt-0.5 truncate text-xs text-slate-500">{user.email}</p>
          </div>

          {tenants.length > 1 && (
            <>
              <div className="mx-1 my-1 h-px bg-slate-100" />
              <div className="px-2.5 py-1.5">
                <label className="mb-1 block text-[11px] font-medium text-slate-400">
                  切换租户
                </label>
                <select
                  aria-label="切换租户"
                  value={tenant.id}
                  disabled={switchPending}
                  onChange={(e) => {
                    onSwitchTenant(e.target.value);
                    setOpen(false);
                  }}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                >
                  {tenants.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div className="mx-1 my-1 h-px bg-slate-100" />

          <MenuItem icon={UserCog} label="个人设置" onClick={() => go('/settings/profile')} />
          {(tenant.role === 'owner' || tenant.role === 'admin') && (
            <MenuItem icon={PieChart} label="使用统计" onClick={() => go('/usages')} />
          )}
          <div className="mx-1 my-1 h-px bg-slate-100" />
          <MenuItem
            icon={LogOut}
            label="退出登录"
            danger
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
          />
        </div>
      )}
    </div>
  );
}

function MenuItem({
  icon: Icon,
  label,
  onClick,
  danger = false,
}: {
  icon: typeof UserCog;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors duration-200',
        danger ? 'text-red-600 hover:bg-red-50' : 'text-slate-700 hover:bg-slate-100',
      )}
    >
      <Icon className="h-4 w-4 shrink-0" strokeWidth={1.5} aria-hidden />
      {label}
    </button>
  );
}
