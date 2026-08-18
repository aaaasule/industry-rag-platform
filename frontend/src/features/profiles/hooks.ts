import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ApiError } from '@/lib/http';

import * as api from './api';

export function useProfiles(enabled = true, includeDeleted = false) {
  return useQuery({
    queryKey: [...api.PROFILES_KEY, includeDeleted] as const,
    queryFn: () => api.listProfiles(includeDeleted),
    enabled,
  });
}

export function useCreateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createProfile,
    onSuccess: () => void qc.invalidateQueries({ queryKey: api.PROFILES_KEY }),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: api.IndustryProfileUpdate }) =>
      api.updateProfile(id, body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: api.PROFILES_KEY }),
  });
}

export function useDeleteProfile() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: api.deleteProfile,
    onSuccess: () => void qc.invalidateQueries({ queryKey: api.PROFILES_KEY }),
  });
}

export function useRestoreProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.restoreProfile,
    onSuccess: () => void qc.invalidateQueries({ queryKey: api.PROFILES_KEY }),
  });
}
