import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as chatApi from './api';

export const CONVERSATIONS_KEY = ['conversations'] as const;

export function useConversations() {
  return useQuery({ queryKey: CONVERSATIONS_KEY, queryFn: chatApi.listConversations });
}

export function useMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => chatApi.listMessages(conversationId!),
    enabled: Boolean(conversationId),
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => chatApi.deleteConversation(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: CONVERSATIONS_KEY }),
  });
}
