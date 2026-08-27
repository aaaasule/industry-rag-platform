import type { Citation, ChatMessage } from './api';

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
};
