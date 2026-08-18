import { api } from '@/lib/http';

export interface IndustryProfile {
  id: string;
  code: string;
  name: string;
  is_builtin: boolean;
  tenant_id: string | null;
  chunk_rules: Record<string, unknown>;
  prompt_overrides: Record<string, unknown>;
  retrieval_rules: Record<string, unknown>;
  parse_rules: Record<string, unknown>;
  metadata_schema: Record<string, unknown>;
  deleted_at?: string | null;
}

export interface IndustryProfileCreate {
  base_code: string;
  code: string;
  name?: string;
  chunk_rules?: Record<string, unknown>;
  prompt_overrides?: Record<string, unknown>;
  retrieval_rules?: Record<string, unknown>;
  parse_rules?: Record<string, unknown>;
  metadata_schema?: Record<string, unknown>;
}

export interface IndustryProfileUpdate {
  name?: string;
  chunk_rules?: Record<string, unknown>;
  prompt_overrides?: Record<string, unknown>;
  retrieval_rules?: Record<string, unknown>;
  parse_rules?: Record<string, unknown>;
  metadata_schema?: Record<string, unknown>;
}

export const PROFILES_KEY = ['industry-profiles'] as const;

export function listProfiles(includeDeleted = false): Promise<IndustryProfile[]> {
  const q = includeDeleted ? '?include_deleted=true' : '';
  return api.get(`/industry-profiles${q}`);
}

export function createProfile(body: IndustryProfileCreate): Promise<IndustryProfile> {
  return api.post('/industry-profiles', body);
}

export function updateProfile(id: string, body: IndustryProfileUpdate): Promise<IndustryProfile> {
  return api.patch(`/industry-profiles/${id}`, body);
}

export function deleteProfile(id: string): Promise<void> {
  return api.delete(`/industry-profiles/${id}`);
}

export function restoreProfile(id: string): Promise<IndustryProfile> {
  return api.post(`/industry-profiles/${id}/restore`, {});
}
