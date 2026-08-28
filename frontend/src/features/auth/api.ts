/**
 * auth 域的接口调用与类型。
 *
 * 类型现在手写；M1 接入 openapi-typescript 后改为从 openapi.gen.ts 派生，
 * 保持"后端改字段、前端编译报错"的约束。
 */

import { api, tokenStore } from '@/lib/http';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export interface TenantBrief {
  id: string;
  slug: string;
  name: string;
  role: 'owner' | 'admin' | 'member';
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  status: string;
}

export interface SessionInfo {
  user: UserProfile;
  current_tenant: TenantBrief;
  tenants: TenantBrief[];
}

export interface LoginPayload {
  email: string;
  password: string;
  tenant_slug?: string;
}

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

export function updateProfile(payload: { display_name: string }): Promise<SessionInfo> {
  return api.patch('/auth/me', payload);
}

export function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  return api.post('/auth/change-password', payload);
}
