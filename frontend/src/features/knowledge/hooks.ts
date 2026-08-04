import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ApiError } from '@/lib/http';
import * as kbApi from './api';

export const KB_LIST_KEY = ['knowledge-bases'] as const;
export const PROFILES_KEY = ['industry-profiles'] as const;

export function useProfiles() {
  return useQuery({ queryKey: PROFILES_KEY, queryFn: kbApi.listProfiles });
}

export function useKnowledgeBases() {
  return useQuery({ queryKey: KB_LIST_KEY, queryFn: kbApi.listKnowledgeBases });
}

export function useCreateKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: kbApi.createKnowledgeBase,
    onSuccess: () => qc.invalidateQueries({ queryKey: KB_LIST_KEY }),
  });
}

export function useKnowledgeBase(kbId: string) {
  return useQuery({
    queryKey: ['knowledge-bases', kbId],
    queryFn: () => kbApi.getKnowledgeBase(kbId),
    enabled: Boolean(kbId),
  });
}

export function useUpdateKnowledgeBase(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { profile_code?: string; name?: string }) =>
      kbApi.updateKnowledgeBase(kbId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['knowledge-bases', kbId] });
      void qc.invalidateQueries({ queryKey: KB_LIST_KEY });
    },
  });
}

export function useDocuments(kbId: string) {
  return useQuery({
    queryKey: ['documents', kbId],
    queryFn: () => kbApi.listDocuments(kbId),
    enabled: Boolean(kbId),
    refetchInterval: (query) => {
      const rows = query.state.data;
      if (!rows) return false;
      return rows.some((d) => kbApi.IN_PROGRESS.has(d.status)) ? 2000 : false;
    },
  });
}

export function useUploadDocument(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) =>
      kbApi.uploadDocument(kbId, file, title),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['documents', kbId] });
      void qc.invalidateQueries({ queryKey: KB_LIST_KEY });
    },
  });
}

export function useReingest(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => kbApi.reingestDocument(docId),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['documents', kbId] }),
  });
}

export function useDeleteDocument(kbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => kbApi.deleteDocument(docId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['documents', kbId] });
      void qc.invalidateQueries({ queryKey: KB_LIST_KEY });
    },
  });
}

export function useDocument(docId: string) {
  return useQuery({
    queryKey: ['document', docId],
    queryFn: () => kbApi.getDocument(docId),
    enabled: Boolean(docId),
  });
}

export type { ApiError };
