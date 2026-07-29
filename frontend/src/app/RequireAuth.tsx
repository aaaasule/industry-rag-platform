import type { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { FullscreenHint } from '@/features/auth/LoginPage';
import { useSession } from '@/features/auth/hooks';

/**
 * 路由守卫。会话恢复期间必须渲染占位而非跳转——否则刷新页面会先闪一下登录页。
 */
export function RequireAuth({ children }: { children: ReactElement }) {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useSession();

  if (isLoading) return <FullscreenHint text="正在恢复会话…" />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}
