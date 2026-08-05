/**
 * 概览：工作台入口 + 轻量真实摘要（知识库 / 会话 / 用量 / 接入点）。
 */

import { Link } from 'react-router-dom';

import { CardSkeleton } from '@/components/Skeleton';
import { useSession } from '@/features/auth/hooks';
import { useConversations } from '@/features/chat/hooks';
import { useKnowledgeBases } from '@/features/knowledge/hooks';
import { useModelConnections, useUsageSummary } from '@/features/usages/hooks';

type Shortcut = {
  to: string;
  title: string;
  desc: string;
  accent: string;
  roles?: ReadonlyArray<'owner' | 'admin' | 'member'>;
};

const SHORTCUTS: Shortcut[] = [
  {
    to: '/knowledge',
    title: '知识库',
    desc: '上传手册、跟踪摄取，为检索与问答准备语料',
    accent: 'bg-brand-600',
  },
  {
    to: '/chat',
    title: '问答',
    desc: '选择知识库提问，右侧核对证据与引用',
    accent: 'bg-ok',
  },
  {
    to: '/usages',
    title: '用量',
    desc: '查看 Token、成本与分布',
    accent: 'bg-warn',
    roles: ['owner', 'admin'],
  },
  {
    to: '/admin',
    title: '运营',
    desc: '接入点、行业模板、成员与审计',
    accent: 'bg-ink-muted',
    roles: ['owner', 'admin'],
  },
];

const CAPABILITIES = [
  '混合检索与 SSE 流式问答，回答带可核验证据',
  '行业模板驱动分块 / 提示词 / 检索参数（运营中配置）',
  '多租户隔离；管理员可查看用量与接入点健康',
];

type StatTone = 'default' | 'ok' | 'warn' | 'danger';

type StatCard = {
  label: string;
  value: string;
  hint: string;
  to: string;
  tone: StatTone;
};

export function OverviewPage() {
  const { session } = useSession();
  const role = session?.current_tenant.role;
  const isAdmin = role === 'owner' || role === 'admin';

  const kbQ = useKnowledgeBases();
  const convQ = useConversations();
  const summaryQ = useUsageSummary('Asia/Shanghai', Boolean(isAdmin), 'week');
  const connQ = useModelConnections(Boolean(isAdmin));

  if (!session || role == null) return null;

  const links = SHORTCUTS.filter(
    (item) => item.roles == null || item.roles.includes(role),
  );

  const bases = kbQ.data ?? [];
  const kbCount = bases.length;
  const docCount = bases.reduce((sum, b) => sum + b.doc_count, 0);
  const chunkCount = bases.reduce((sum, b) => sum + b.chunk_count, 0);
  const convCount = (convQ.data ?? []).length;

  const connections = connQ.data ?? [];
  const healthyCount = connections.filter((c) => c.health === 'healthy').length;
  const downCount = connections.filter((c) => c.health === 'down').length;
  const connTone: StatTone =
    downCount > 0 ? 'danger' : healthyCount > 0 ? 'ok' : 'default';

  const statsLoading =
    kbQ.isLoading || convQ.isLoading || (isAdmin && (summaryQ.isLoading || connQ.isLoading));

  const usageHint = summaryQ.data
    ? `${summaryQ.data.total_tokens.toLocaleString('zh-CN')} Token · $${summaryQ.data.total_cost.toFixed(2)}`
    : '用量摘要暂不可用';
  const connHint =
    connections.length === 0
      ? '尚未配置'
      : downCount > 0
        ? `${downCount} 个异常`
        : healthyCount === connections.length
          ? '全部正常'
          : `${connections.length - healthyCount} 个未知/降级`;

  const stats: StatCard[] = [
    {
      label: '知识库',
      value: String(kbCount),
      hint: `${docCount} 文档 · ${chunkCount} 分块`,
      to: '/knowledge',
      tone: 'default',
    },
    {
      label: '会话',
      value: String(convCount),
      hint: '历史问答会话',
      to: '/chat',
      tone: 'default',
    },
  ];

  if (isAdmin) {
    stats.push({
      label: '近 7 日调用',
      value: summaryQ.data ? summaryQ.data.call_count.toLocaleString('zh-CN') : '—',
      hint: usageHint,
      to: '/usages',
      tone: 'default',
    });
    stats.push({
      label: '接入点健康',
      value: connections.length === 0 ? '0' : `${healthyCount}/${connections.length}`,
      hint: connHint,
      to: '/admin?tab=connections',
      tone: connTone,
    });
  }

  function shortcutHint(to: string): string | null {
    if (to === '/knowledge' && !kbQ.isLoading) {
      return `${kbCount} 个库 · ${docCount} 文档`;
    }
    if (to === '/chat' && !convQ.isLoading) {
      return `${convCount} 个会话`;
    }
    if (to === '/usages' && summaryQ.data) {
      return `近 7 日 ${summaryQ.data.call_count.toLocaleString('zh-CN')} 次调用`;
    }
    if (to === '/admin' && !connQ.isLoading && connections.length > 0) {
      return `接入点 ${healthyCount}/${connections.length} 正常`;
    }
    return null;
  }

  return (
    <div className="page-shell space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line/80 pb-5">
        <div>
          <p className="section-title text-brand-700">工作台</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            你好，{session.user.display_name}
          </h1>
          <p className="mt-1.5 text-sm text-ink-muted">
            当前租户{' '}
            <span className="font-medium text-ink">{session.current_tenant.name}</span>
            <span className="text-ink-faint"> · {session.current_tenant.slug}</span>
          </p>
        </div>
      </header>

      <section
        className={[
          'grid gap-3',
          stats.length >= 4 ? 'sm:grid-cols-2 xl:grid-cols-4' : 'sm:grid-cols-2',
        ].join(' ')}
      >
        {statsLoading
          ? Array.from({ length: isAdmin ? 4 : 2 }, (_, i) => <CardSkeleton key={i} />)
          : stats.map((stat) => <StatLink key={stat.label} stat={stat} />)}
      </section>

      <section
        className={[
          'grid gap-3',
          links.length >= 4 ? 'sm:grid-cols-2 xl:grid-cols-4' : 'sm:grid-cols-2 lg:grid-cols-3',
        ].join(' ')}
      >
        {links.map((item) => {
          const hint = shortcutHint(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className="panel group relative block min-h-[140px] overflow-hidden p-5 pl-6 transition-colors duration-150 hover:border-brand-500 hover:bg-brand-50/40"
            >
              <span
                aria-hidden
                className={`absolute inset-y-3 left-0 w-[3px] rounded-r ${item.accent}`}
              />
              <h2 className="text-sm font-semibold text-ink group-hover:text-brand-700">
                {item.title}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{item.desc}</p>
              {hint ? (
                <p className="mt-3 text-xs tabular-nums text-ink-faint">{hint}</p>
              ) : null}
              <span className="mt-3 inline-block text-xs font-medium text-brand-700 transition-transform duration-150 group-hover:translate-x-0.5">
                进入 →
              </span>
            </Link>
          );
        })}
      </section>

      <section className="panel grid gap-0 divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {CAPABILITIES.map((text) => (
          <div key={text} className="px-5 py-4">
            <p className="text-xs leading-relaxed text-ink-muted">{text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

function StatLink({ stat }: { stat: StatCard }) {
  const toneClass =
    stat.tone === 'ok'
      ? 'text-ok'
      : stat.tone === 'warn'
        ? 'text-warn'
        : stat.tone === 'danger'
          ? 'text-danger'
          : 'text-ink';

  return (
    <Link
      to={stat.to}
      className="panel block p-4 transition-colors duration-150 hover:border-brand-500 hover:bg-brand-50/30"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">{stat.label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${toneClass}`}>{stat.value}</p>
      <p className="mt-1 text-xs text-ink-muted">{stat.hint}</p>
    </Link>
  );
}
