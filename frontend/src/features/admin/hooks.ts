import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ApiError } from '@/lib/http';
import * as adminApi from './api';
import type { MemberRole } from './api';

export function useMemberships(enabled: boolean) {
  return useQuery({
    queryKey: adminApi.MEMBERSHIPS_KEY,
    queryFn: adminApi.listMemberships,
    enabled,
    staleTime: 30_000,
  });
}

export function useAddMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      email: string;
      role?: MemberRole;
      create_if_missing?: boolean;
      display_name?: string;
    }) => adminApi.addMember(body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: adminApi.MEMBERSHIPS_KEY });
    },
  });
}

export function useUpdateMemberRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: MemberRole }) =>
      adminApi.updateMemberRole(userId, role),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: adminApi.MEMBERSHIPS_KEY });
    },
  });
}

export function useRemoveMember() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (userId) => adminApi.removeMember(userId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: adminApi.MEMBERSHIPS_KEY });
    },
  });
}

export function useAuditLogs(
  params: {
    action?: string | undefined;
    from?: string | undefined;
    to?: string | undefined;
    limit: number;
    offset: number;
  },
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => adminApi.listAuditLogs(params),
    enabled,
    staleTime: 15_000,
  });
}
