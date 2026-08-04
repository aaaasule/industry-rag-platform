/**
 * HTTP 客户端。
 *
 * 三件事收敛在这里，业务代码不再重复：Bearer 注入、401 自动刷新、后端错误
 * 结构到 ApiError 的转换。任何直接 fetch 的调用都会绕过这三件事，因此禁止。
 */

const BASE_URL = '/api/v1';

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details: Record<string, unknown> = {},
    readonly requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type TokenListener = (accessToken: string | null) => void;

class TokenStore {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private listeners = new Set<TokenListener>();

  constructor() {
    this.refreshToken = localStorage.getItem('irp.refresh_token');
  }

  get access(): string | null {
    return this.accessToken;
  }

  get refresh(): string | null {
    return this.refreshToken;
  }

  set(access: string, refresh: string): void {
    this.accessToken = access;
    this.refreshToken = refresh;
    // access token 只放内存：XSS 拿不到刷新后的长期凭证，降低被持久窃取的面
    localStorage.setItem('irp.refresh_token', refresh);
    this.listeners.forEach((fn) => fn(access));
  }

  clear(): void {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('irp.refresh_token');
    this.listeners.forEach((fn) => fn(null));
  }

  subscribe(fn: TokenListener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
}

export const tokenStore = new TokenStore();

/** 并发请求同时遇到 401 时，只发起一次刷新，其余等待同一个 Promise。 */
let refreshInFlight: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const token = tokenStore.refresh;
  if (!token) return false;

  refreshInFlight ??= (async () => {
    try {
      const resp = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: token }),
      });
      if (!resp.ok) {
        tokenStore.clear();
        return false;
      }
      const data = (await resp.json()) as { access_token: string; refresh_token: string };
      tokenStore.set(data.access_token, data.refresh_token);
      return true;
    } catch {
      tokenStore.clear();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** 内部使用：标记这是刷新后的重试，避免无限循环 */
  retried?: boolean;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, retried, headers, ...rest } = options;

  const resp = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: buildHeaders(headers),
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  if (resp.status === 401 && !retried && (await refreshAccessToken())) {
    return request<T>(path, { ...options, retried: true });
  }

  if (!resp.ok) throw await toApiError(resp);
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

function buildHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extra as Record<string, string> | undefined),
  };
  if (tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`;
  return headers;
}

async function toApiError(resp: Response): Promise<ApiError> {
  try {
    const payload = (await resp.json()) as ApiErrorBody;
    return new ApiError(
      payload.error.code,
      payload.error.message,
      resp.status,
      payload.error.details ?? {},
      payload.error.request_id,
    );
  } catch {
    // 网关层返回的非结构化错误（502 HTML 页之类）也要有稳定的 code
    return new ApiError('unexpected_response', `请求失败（${resp.status}）`, resp.status);
  }
}
