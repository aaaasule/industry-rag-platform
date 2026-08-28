import type { Conversation } from './api';

export type ConversationGroupKey = 'today' | 'yesterday' | 'week' | 'month';

export type ConversationGroup = {
  key: ConversationGroupKey;
  label: string;
  items: Conversation[];
};

const GROUP_ORDER: ConversationGroupKey[] = ['today', 'yesterday', 'week', 'month'];

const GROUP_LABELS: Record<ConversationGroupKey, string> = {
  today: '今天',
  yesterday: '昨天',
  week: '7天内',
  month: '30天内',
};

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function daysBetween(from: Date, to: Date): number {
  return Math.floor((startOfDay(to).getTime() - startOfDay(from).getTime()) / 86_400_000);
}

/** 按创建日归入今天 / 昨天 / 7天内 / 30天内；超过 30 天不展示 */
export function classifyConversationDay(
  createdAt: string,
  now = new Date(),
): ConversationGroupKey | null {
  const created = new Date(createdAt);
  if (Number.isNaN(created.getTime())) return null;
  const diff = daysBetween(created, now);
  if (diff < 0) return 'today';
  if (diff === 0) return 'today';
  if (diff === 1) return 'yesterday';
  if (diff >= 2 && diff <= 7) return 'week';
  if (diff >= 8 && diff <= 30) return 'month';
  return null;
}

export function filterConversationsByTitle(
  conversations: Conversation[],
  query: string,
): Conversation[] {
  const q = query.trim().toLowerCase();
  if (!q) return conversations;
  return conversations.filter((c) => (c.title || '').toLowerCase().includes(q));
}

/** 过滤 → 分组 → 组内按创建时间倒序；空分组省略 */
export function groupConversations(
  conversations: Conversation[],
  query = '',
  now = new Date(),
): ConversationGroup[] {
  const filtered = filterConversationsByTitle(conversations, query);
  const buckets: Record<ConversationGroupKey, Conversation[]> = {
    today: [],
    yesterday: [],
    week: [],
    month: [],
  };

  for (const c of filtered) {
    const key = classifyConversationDay(c.created_at, now);
    if (key) buckets[key].push(c);
  }

  for (const key of GROUP_ORDER) {
    buckets[key].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }

  return GROUP_ORDER.filter((key) => buckets[key].length > 0).map((key) => ({
    key,
    label: GROUP_LABELS[key],
    items: buckets[key],
  }));
}
