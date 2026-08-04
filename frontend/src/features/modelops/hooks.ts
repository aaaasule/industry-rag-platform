import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ApiError } from '@/lib/http';
import * as modelopsApi from './api';
import type { ModelConnectionCreate, ModelConnectionUpdate } from './api';

export function useConnections(enabled: boolean) {
  return useQuery({
    queryKey: modelopsApi.CONNECTION_LIST_KEY,
    queryFn: modelopsApi.listConnections,
    enabled,
    staleTime: 30_000,
  });
}

export function useRoutes(enabled: boolean) {
  return useQuery({
    queryKey: modelopsApi.ROUTES_KEY,
    queryFn: modelopsApi.listRoutes,
    enabled,
    staleTime: 30_000,
  });
}

export function useCreateConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ModelConnectionCreate) => modelopsApi.createConnection(body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: modelopsApi.CONNECTION_LIST_KEY });
      await qc.invalidateQueries({ queryKey: modelopsApi.ROUTES_KEY });
    },
  });
}

export function useUpdateConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ModelConnectionUpdate }) =>
      modelopsApi.updateConnection(id, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: modelopsApi.CONNECTION_LIST_KEY });
      await qc.invalidateQueries({ queryKey: modelopsApi.ROUTES_KEY });
    },
  });
}

export function useUpdateCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, apiKey }: { id: string; apiKey: string }) =>
      modelopsApi.updateCredential(id, apiKey),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: modelopsApi.CONNECTION_LIST_KEY });
    },
  });
}

export function useTestConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => modelopsApi.testConnection(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: modelopsApi.CONNECTION_LIST_KEY });
    },
  });
}

export function useDeleteConnection() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => modelopsApi.deleteConnection(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: modelopsApi.CONNECTION_LIST_KEY });
      await qc.invalidateQueries({ queryKey: modelopsApi.ROUTES_KEY });
    },
  });
}
