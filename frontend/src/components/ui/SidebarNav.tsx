import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Library,
  MessageSquare,
  BarChart3,
  Settings2,
  type LucideIcon,
} from 'lucide-react';

import { cn } from './cn';

type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  icon: LucideIcon;
  roles?: ReadonlyArray<'owner' | 'admin' | 'member'>;
};

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: '概览', end: true, icon: LayoutDashboard },
  { to: '/knowledge', label: '知识库', icon: Library },
  { to: '/chat', label: '问答', icon: MessageSquare },
  { to: '/usages', label: '用量', icon: BarChart3, roles: ['owner', 'admin'] },
  { to: '/admin', label: '运营', icon: Settings2, roles: ['owner', 'admin'] },
];

type Props = {
  role: 'owner' | 'admin' | 'member' | undefined;
  onNavigate?: () => void;
  collapsed?: boolean;
};

export function SidebarNav({ role, onNavigate, collapsed = false }: Props) {
  const items = NAV_ITEMS.filter(
    (item) => item.roles == null || (role != null && item.roles.includes(role)),
  );

  return (
    <nav
      className={cn('flex flex-col gap-1 p-3', collapsed && 'items-center px-2')}
      aria-label="主导航"
    >
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end ?? false}
            onClick={onNavigate}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              cn(
                'group relative flex h-10 items-center rounded-lg text-sm transition-all duration-200 ease-in-out',
                collapsed ? 'w-10 justify-center px-0' : 'gap-3 px-4',
                isActive
                  ? 'bg-indigo-50 font-medium text-indigo-600'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
              )
            }
          >
            {({ isActive }) => (
              <>
                {!collapsed && (
                  <span
                    className={cn(
                      'absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-indigo-600 transition-opacity duration-200',
                      isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-30',
                    )}
                    aria-hidden
                  />
                )}
                <Icon className="h-5 w-5 shrink-0" strokeWidth={1.5} aria-hidden />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
