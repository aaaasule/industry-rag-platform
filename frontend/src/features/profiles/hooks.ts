import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as api from './api';

export function useProfiles(enabled = true) {
  return useQuery({
    queryKey: api.PROFILES_KEY,
    queryFn: api.listProfiles,
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
