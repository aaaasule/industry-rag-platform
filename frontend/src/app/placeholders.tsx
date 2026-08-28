/**
 * 概览：工作台入口 + 轻量真实摘要。
 */

import {
  ArrowRight,
  BarChart3,
  Library,
  MessageSquare,
  Settings2,
  type LucideIcon,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { CardSkeleton } from '@/components/Skeleton';
import { PageHeader, StatTile } from '@/components/ui';
import { useSession } from '@/features/auth/hooks';
import { useConversations } from '@/features/chat/hooks';
import { useKnowledgeBases } from '@/features/knowledge/hooks';
import { useModelConnections, useUsageSummary } from '@/features/usages/hooks';

type Shortcut = {
  to: string;
  title: string;
  desc: string;
  hint?: string | null;
  icon: LucideIcon;
  large?: boolean;
  roles?: ReadonlyArray<'owner' | 'admin' | 'member'>;
};

const CAPABILITIES = [
  '混合检索与 SSE 流式问答，回答带可核验证据',
  '行业模板驱动分块、提示词与检索参数',
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

  const shortcuts: Shortcut[] = [
    {
      to: '/knowledge',
      title: '知识库',
      desc: '上传手册、跟踪摄取，为检索与问答准备语料',
      hint: !kbQ.isLoading ? `${kbCount} 个库 · ${docCount} 文档` : null,
      icon: Library,
      large: true,
    },
    {
      to: '/chat',
      title: '问答',
      desc: '选择知识库提问，右侧核对证据与引用',
      hint: !convQ.isLoading ? `${convCount} 个会话` : null,
      icon: MessageSquare,
      large: true,
    },
  ];

  if (isAdmin) {
    shortcuts.push(
      {
        to: '/usages',
        title: '用量',
        desc: '查看 Token、成本与分布',
        hint: summaryQ.data
          ? `近 7 日 ${summaryQ.data.call_count.toLocaleString('zh-CN')} 次调用`
          : null,
        icon: BarChart3,
      },
      {
        to: '/admin',
        title: '运营',
        desc: '接入点、行业模板、成员与审计',
        hint:
          !connQ.isLoading && connections.length > 0
            ? `接入点 ${healthyCount}/${connections.length} 正常`
            : null,
        icon: Settings2,
      },
    );
  }

  return (
    <div className="page-shell space-y-8">
      <PageHeader
        title={`你好，${session.user.display_name}`}
        description={`当前租户 ${session.current_tenant.name} · ${session.current_tenant.slug}`}
      />

      <section
        className={[
          'grid gap-3',
          stats.length >= 4 ? 'sm:grid-cols-2 xl:grid-cols-4' : 'sm:grid-cols-2',
        ].join(' ')}
      >
        {statsLoading
          ? Array.from({ length: isAdmin ? 4 : 2 }, (_, i) => <CardSkeleton key={i} />)
          : stats.map((stat) => (
              <StatTile
                key={stat.label}
                label={stat.label}
                value={stat.value}
                hint={stat.hint}
                to={stat.to}
                tone={stat.tone}
              />
            ))}
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        {shortcuts.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={[
                'panel group relative flex flex-col overflow-hidden transition-all duration-200 hover:border-indigo-200 hover:shadow-md',
                item.large ? 'min-h-[160px] p-6 lg:col-span-1' : 'min-h-[120px] p-5',
              ].join(' ')}
            >
              <div className="flex items-start justify-between gap-4">
                <span className="inline-flex rounded-lg bg-indigo-50 p-2 text-indigo-600">
                  <Icon className="h-5 w-5" strokeWidth={1.5} aria-hidden />
                </span>
                <ArrowRight
                  className="h-4 w-4 shrink-0 text-slate-300 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-indigo-500"
                  strokeWidth={1.5}
                  aria-hidden
                />
              </div>
              <h2 className="mt-4 text-base font-semibold text-slate-800 group-hover:text-indigo-600">
                {item.title}
              </h2>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{item.desc}</p>
              {item.hint ? (
                <p className="mt-auto pt-3 text-xs tabular-nums text-slate-400">{item.hint}</p>
              ) : null}
            </Link>
          );
        })}
      </section>

      <section className="panel p-5">
        <h2 className="text-sm font-semibold text-slate-800">平台能力</h2>
        <ul className="mt-3 space-y-2">
          {CAPABILITIES.map((text) => (
            <li key={text} className="flex gap-2 text-sm text-slate-500">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-indigo-500" aria-hidden />
              {text}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
