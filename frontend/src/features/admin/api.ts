import { api } from '@/lib/http';
import type { components } from '@/types/openapi.gen';

export type MemberOut = {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
  created_user?: boolean;
  temporary_password?: string | null;
};
export type MembershipList = { items: MemberOut[] };
export type AuditLogOut = components['schemas']['AuditLogOut'];
export type AuditLogList = components['schemas']['AuditLogList'];

export type MemberRole = 'member' | 'admin' | 'owner';

export const MEMBERSHIPS_KEY = ['memberships'] as const;

function toQuery(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue;
    sp.set(k, String(v));
  }
  const q = sp.toString();
  return q ? `?${q}` : '';
}

export function listMemberships(): Promise<MembershipList> {
  return api.get('/memberships');
}

export function addMember(body: {
  email: string;
  role?: MemberRole;
  create_if_missing?: boolean;
  display_name?: string;
}): Promise<MemberOut> {
  return api.post('/memberships', body);
}

export function updateMemberRole(userId: string, role: MemberRole): Promise<MemberOut> {
  return api.patch(`/memberships/${userId}`, { role });
}

export function removeMember(userId: string): Promise<void> {
  return api.delete(`/memberships/${userId}`);
}

export function listAuditLogs(params: {
  action?: string | undefined;
  actor_id?: string | undefined;
  from?: string | undefined;
  to?: string | undefined;
  limit?: number | undefined;
  offset?: number | undefined;
}): Promise<AuditLogList> {
  return api.get(`/admin/audit-logs${toQuery(params)}`);
}

export const AUDIT_ACTIONS = [
  'auth.login',
  'auth.switch_tenant',
  'membership.add',
  'membership.role_change',
  'membership.remove',
  'model_connection.create',
  'model_connection.update',
  'model_connection.credential_update',
  'model_connection.delete',
  'model_connection.test',
  'kb_grant.create',
  'kb_grant.update',
  'kb_grant.delete',
  'knowledge_base.delete',
] as const;
