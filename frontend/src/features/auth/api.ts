/**
 * auth 域的接口调用与类型（由 OpenAPI 派生，后端改字段时前端编译报错）。
 */

import { api, tokenStore } from '@/lib/http';
import type { components } from '@/types/openapi.gen';

export type TokenPair = components['schemas']['TokenPair'];
export type UserProfile = components['schemas']['UserProfile'];
export type LoginPayload = components['schemas']['LoginRequest'];
export type UpdateProfilePayload = components['schemas']['UpdateProfileRequest'];
export type ChangePasswordPayload = components['schemas']['ChangePasswordRequest'];

/** OpenAPI 将 role 标为 string；前端导航/RBAC 需要字面量联合 */
export type TenantRole = 'owner' | 'admin' | 'member';
export type TenantBrief = Omit<components['schemas']['TenantBrief'], 'role'> & {
  role: TenantRole;
};
export type SessionInfo = Omit<components['schemas']['SessionInfo'], 'current_tenant' | 'tenants'> & {
  current_tenant: TenantBrief;
  tenants: TenantBrief[];
};

export async function login(payload: LoginPayload): Promise<TokenPair> {
  const pair = await api.post<TokenPair>('/auth/login', payload);
  tokenStore.set(pair.access_token, pair.refresh_token);
  return pair;
}

export function fetchSession(): Promise<SessionInfo> {
  return api.get<SessionInfo>('/auth/me');
}

export async function switchTenant(tenantId: string): Promise<TokenPair> {
  const pair = await api.post<TokenPair>('/auth/switch-tenant', { tenant_id: tenantId });
  tokenStore.set(pair.access_token, pair.refresh_token);
  return pair;
}

export async function logout(): Promise<void> {
  try {
    await api.post<void>('/auth/logout');
  } finally {
    // 服务端调用失败也必须清本地凭证，否则用户会卡在"看似已登出"的状态
    tokenStore.clear();
  }
}

export function updateProfile(payload: UpdateProfilePayload): Promise<SessionInfo> {
  return api.patch('/auth/me', payload);
}

export function changePassword(payload: ChangePasswordPayload): Promise<void> {
  return api.post('/auth/change-password', payload);
}
