import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';

import { tokenStore } from '@/lib/http';
import type { ApiError } from '@/lib/http';
import * as authApi from './api';
import type { SessionInfo } from './api';

export const SESSION_KEY = ['auth', 'session'] as const;

/**
 * 刷新令牌只存在于 localStorage，页面刷新后需要先换一次 access token 才知道
 * 是否已登录。这个 hook 把"未知 / 已登录 / 未登录"三态显式暴露出来，避免
 * 路由守卫在首帧误判并把用户踢回登录页。
 */
export function useSession() {
  const [hasCredential, setHasCredential] = useState(() => tokenStore.refresh !== null);

  useEffect(() => tokenStore.subscribe(() => setHasCredential(tokenStore.refresh !== null)), []);

  const query = useQuery<SessionInfo, ApiError>({
    queryKey: SESSION_KEY,
    queryFn: authApi.fetchSession,
    enabled: hasCredential,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  return {
    session: query.data ?? null,
    isLoading: hasCredential && query.isLoading,
    isAuthenticated: Boolean(query.data),
    error: query.error,
  };
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation<authApi.TokenPair, ApiError, authApi.LoginPayload>({
    mutationFn: authApi.login,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SESSION_KEY }),
  });
}

export function useSwitchTenant() {
  const queryClient = useQueryClient();
  return useMutation<authApi.TokenPair, ApiError, string>({
    mutationFn: authApi.switchTenant,
    // 租户变了，所有缓存的业务数据都属于旧租户，必须整体作废
    onSuccess: () => queryClient.clear(),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    await authApi.logout();
    queryClient.clear();
  }, [queryClient]);
}
