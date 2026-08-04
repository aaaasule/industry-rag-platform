import { api, tokenStore, ApiError } from '@/lib/http';

export interface IndustryProfile {
  id: string;
  code: string;
  name: string;
  is_builtin: boolean;
  tenant_id: string | null;
  chunk_rules?: Record<string, unknown>;
  prompt_overrides?: Record<string, unknown>;
  retrieval_rules?: Record<string, unknown>;
  parse_rules?: Record<string, unknown>;
  metadata_schema?: Record<string, unknown>;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  embedding_model: string;
  embedding_dim: number;
  visibility: string;
  doc_count: number;
  chunk_count: number;
  profile_id: string | null;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  kb_id: string;
  title: string;
  mime_type: string;
  file_size: number;
  checksum: string;
  page_count: number | null;
  status: string;
  error_code: string | null;
  error_detail: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreated {
  document_id: string;
  status: string;
  job_id: string | null;
}

export function listProfiles(): Promise<IndustryProfile[]> {
  return api.get('/industry-profiles');
}

export function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return api.get('/knowledge-bases');
}

export function createKnowledgeBase(payload: {
  name: string;
  description?: string;
  profile_code?: string;
}): Promise<KnowledgeBase> {
  return api.post('/knowledge-bases', payload);
}

export function getKnowledgeBase(kbId: string): Promise<KnowledgeBase> {
  return api.get(`/knowledge-bases/${kbId}`);
}

export function updateKnowledgeBase(
  kbId: string,
  payload: {
    name?: string;
    description?: string;
    visibility?: string;
    profile_code?: string;
  },
): Promise<KnowledgeBase> {
  return api.patch(`/knowledge-bases/${kbId}`, payload);
}

export function listDocuments(kbId: string): Promise<DocumentItem[]> {
  return api.get(`/knowledge-bases/${kbId}/documents`);
}

export function getDocument(docId: string): Promise<DocumentItem> {
  return api.get(`/documents/${docId}`);
}

export function getPreviewUrl(docId: string): Promise<{ url: string; expires_in: number }> {
  return api.get(`/documents/${docId}/preview-url`);
}

export interface ChunkItem {
  id: string;
  seq: number;
  content: string;
  heading_path: string[];
  page_start: number;
  page_end: number;
  bboxes: { page: number; bbox: number[] }[];
  chunk_type: string;
}

export function listChunks(docId: string): Promise<ChunkItem[]> {
  return api.get(`/documents/${docId}/chunks`);
}

export function reingestDocument(docId: string): Promise<DocumentCreated> {
  return api.post(`/documents/${docId}/reingest`);
}

export function deleteDocument(docId: string): Promise<void> {
  return api.delete(`/documents/${docId}`);
}

/** 经 API 中转的 multipart 上传（≤32MB），避免浏览器直传 MinIO 的 CORS 问题。 */
export async function uploadDocument(
  kbId: string,
  file: File,
  title?: string,
): Promise<DocumentCreated> {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);

  const headers: Record<string, string> = {};
  if (tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`;

  const resp = await fetch(`/api/v1/knowledge-bases/${kbId}/documents/upload`, {
    method: 'POST',
    headers,
    body: form,
  });

  if (!resp.ok) {
    try {
      const payload = (await resp.json()) as {
        error: { code: string; message: string; details?: Record<string, unknown>; request_id?: string };
      };
      throw new ApiError(
        payload.error.code,
        payload.error.message,
        resp.status,
        payload.error.details ?? {},
        payload.error.request_id,
      );
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('unexpected_response', `上传失败（${resp.status}）`, resp.status);
    }
  }
  return (await resp.json()) as DocumentCreated;
}

export const IN_PROGRESS = new Set(['pending', 'parsing', 'chunking', 'embedding']);

export function statusLabel(status: string): string {
  return (
    {
      pending: '排队中',
      parsing: '解析中',
      chunking: '分块中',
      embedding: '向量化',
      ready: '就绪',
      failed: '失败',
    }[status] ?? status
  );
}
