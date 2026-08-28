import type { Citation, ChatMessage, TokenUsage } from './api';

export const EXAMPLE_QUESTIONS = [
  'HYD-2201 保养周期是多久？',
  '设备检修作业有哪些安全规范？',
  'Agent 的组成部分是什么？',
];

export type UiMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: string;
  citations?: Citation[];
  used_citations?: number[] | undefined;
  feedback?: ChatMessage['feedback'];
  token_usage?: TokenUsage | null;
  took_ms?: number | null;
};

export function formatTookMs(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  const sec = ms / 1000;
  return sec < 10 ? `${sec.toFixed(1)} s` : `${Math.round(sec)} s`;
}

export function formatTokenUsage(usage: TokenUsage | null | undefined): string | null {
  if (!usage) return null;
  const prompt = Number(usage.prompt_tokens ?? 0);
  const completion = Number(usage.completion_tokens ?? 0);
  const total = prompt + completion;
  if (!Number.isFinite(total) || total <= 0) return null;
  if (prompt > 0 || completion > 0) {
    return `${total.toLocaleString()} tokens（提示 ${prompt.toLocaleString()} · 生成 ${completion.toLocaleString()}）`;
  }
  return `${total.toLocaleString()} tokens`;
}
