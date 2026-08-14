/**
 * SSE 客户端。
 *
 * 不用浏览器原生 EventSource：它不支持自定义请求头（发不了 Bearer），也不支持
 * POST（问答请求体是 JSON）。因此基于 fetch + ReadableStream 自己解析。
 */

import { ApiError, tokenStore } from './http';

export interface SseEvent<T = unknown> {
  event: string;
  data: T;
}

export interface SseOptions {
  signal?: AbortSignal;
  /** 服务端 event 名到数据类型的解析失败时调用，默认吞掉并继续 */
  onParseError?: (raw: string, error: unknown) => void;
}

/**
 * 以异步迭代器形式消费 SSE，调用方用 for await 逐帧处理。
 * 相比回调式接口，它能让消费端用普通控制流写"收到 done 就 break"。
 */
export async function* streamEvents<T = unknown>(
  path: string,
  body: unknown,
  options: SseOptions = {},
): AsyncGenerator<SseEvent<T>> {
  const resp = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {}),
    },
    body: JSON.stringify(body),
    ...(options.signal ? { signal: options.signal } : {}),
  });

  yield* readSseStream<T>(resp, options);
}

/** GET SSE（摄取进度等）。 */
export async function* streamEventsGet<T = unknown>(
  path: string,
  options: SseOptions = {},
): AsyncGenerator<SseEvent<T>> {
  const resp = await fetch(`/api/v1${path}`, {
    method: 'GET',
    headers: {
      Accept: 'text/event-stream',
      ...(tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {}),
    },
    ...(options.signal ? { signal: options.signal } : {}),
  });

  yield* readSseStream<T>(resp, options);
}

async function* readSseStream<T>(
  resp: Response,
  options: SseOptions,
): AsyncGenerator<SseEvent<T>> {
  if (!resp.ok || !resp.body) {
    throw new ApiError('stream_failed', `流式请求失败（${resp.status}）`, resp.status);
  }

  const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += value;

      let boundary = findBoundary(buffer);
      while (boundary !== null) {
        const rawEvent = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary.length);
        const parsed = parseEvent<T>(rawEvent, options);
        if (parsed) yield parsed;
        boundary = findBoundary(buffer);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function findBoundary(buffer: string): { index: number; length: number } | null {
  const lf = buffer.indexOf('\n\n');
  const crlf = buffer.indexOf('\r\n\r\n');
  if (lf === -1 && crlf === -1) return null;
  if (crlf !== -1 && (lf === -1 || crlf < lf)) return { index: crlf, length: 4 };
  return { index: lf, length: 2 };
}

function parseEvent<T>(raw: string, options: SseOptions): SseEvent<T> | null {
  let event = 'message';
  const dataLines: string[] = [];

  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith(':')) continue; // 心跳注释
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
  }

  if (dataLines.length === 0) return null;
  const payload = dataLines.join('\n');

  try {
    return { event, data: JSON.parse(payload) as T };
  } catch (error) {
    options.onParseError?.(payload, error);
    return null;
  }
}
