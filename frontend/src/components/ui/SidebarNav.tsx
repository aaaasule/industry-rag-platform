import { NavLink } from 'react-router-dom';
import {
  ChartBar,
  ChatCircleDots,
  GearSix,
  House,
  Books,
} from '@phosphor-icons/react';

import { cn } from './cn';

type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  icon: typeof House;
  roles?: ReadonlyArray<'owner' | 'admin' | 'member'>;
};

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: '概览', end: true, icon: House },
  { to: '/knowledge', label: '知识库', icon: Books },
  { to: '/chat', label: '问答', icon: ChatCircleDots },
  { to: '/usages', label: '用量', icon: ChartBar, roles: ['owner', 'admin'] },
  { to: '/admin', label: '运营', icon: GearSix, roles: ['owner', 'admin'] },
];

type Props = {
  role: 'owner' | 'admin' | 'member' | undefined;
  onNavigate?: () => void;
};

export function SidebarNav({ role, onNavigate }: Props) {
  const items = NAV_ITEMS.filter(
    (item) => item.roles == null || (role != null && item.roles.includes(role)),
  );

  return (
    <nav className="flex flex-col gap-1 p-3">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end ?? false}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150',
                isActive
                  ? 'bg-accent-soft font-medium text-accent'
                  : 'text-ink-muted hover:bg-elevated hover:text-ink',
              )
            }
          >
            <Icon size={20} weight="duotone" aria-hidden />
            {item.label}
          </NavLink>
        );
      })}
    </nav>
  );
}
