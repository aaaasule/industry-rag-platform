import { api } from '@/lib/http';
import { streamEvents } from '@/lib/sse';

export interface Conversation {
  id: string;
  kb_ids: string[];
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  index_no: number;
  chunk_id: string | null;
  document_id: string;
  document_title?: string;
  quote: string;
  page_start: number;
  bboxes: Record<string, unknown>[];
  score: number;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  status: string;
  citations: Citation[];
  created_at: string;
}

export interface ChatCompletionBody {
  conversation_id?: string | null;
  kb_ids?: string[] | null;
  message: string;
  options?: Record<string, unknown>;
}

export function listConversations(): Promise<Conversation[]> {
  return api.get('/conversations');
}

export function createConversation(payload: {
  kb_ids: string[];
  title?: string;
}): Promise<Conversation> {
  return api.post('/conversations', payload);
}

export function deleteConversation(id: string): Promise<void> {
  return api.delete(`/conversations/${id}`);
}

export function listMessages(conversationId: string): Promise<ChatMessage[]> {
  return api.get(`/conversations/${conversationId}/messages`);
}

export function streamChatCompletions(
  body: ChatCompletionBody,
  signal?: AbortSignal,
) {
  return streamEvents('/chat/completions', body, signal ? { signal } : {});
}
