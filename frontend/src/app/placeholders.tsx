/**
 * 概览：轻工作台入口（不接真实统计 API）。
 */

import { Link } from 'react-router-dom';

import { useSession } from '@/features/auth/hooks';

type Shortcut = {
  to: string;
  title: string;
  desc: string;
  roles?: ReadonlyArray<'owner' | 'admin' | 'member'>;
};

const SHORTCUTS: Shortcut[] = [
  {
    to: '/knowledge',
    title: '知识库',
    desc: '上传手册、跟踪摄取，为检索与问答准备语料',
  },
  {
    to: '/chat',
    title: '问答',
    desc: '选择知识库提问，右侧核对证据与引用',
  },
  {
    to: '/usages',
    title: '用量',
    desc: '查看 Token、成本与分布',
    roles: ['owner', 'admin'],
  },
  {
    to: '/admin',
    title: '运营',
    desc: '接入点、行业模板、成员与审计',
    roles: ['owner', 'admin'],
  },
];

export function OverviewPage() {
  const { session } = useSession();
  if (!session) return null;

  const role = session.current_tenant.role;
  const links = SHORTCUTS.filter(
    (item) => item.roles == null || item.roles.includes(role),
  );

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-brand-700">工作台</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
          你好，{session.user.display_name}
        </h1>
        <p className="mt-1.5 text-sm text-ink-muted">
          当前租户{' '}
          <span className="font-medium text-ink">{session.current_tenant.name}</span>
          <span className="text-ink-faint"> · {session.current_tenant.slug}</span>
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2">
        {links.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="panel group block p-5 transition-colors duration-150 hover:border-brand-500 hover:bg-brand-50/40"
          >
            <h2 className="text-sm font-semibold text-ink group-hover:text-brand-700">
              {item.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">{item.desc}</p>
            <span className="mt-4 inline-block text-xs font-medium text-brand-700">进入 →</span>
          </Link>
        ))}
      </section>

      <section className="panel p-5">
        <h2 className="text-xs font-medium uppercase tracking-wider text-ink-faint">能力摘要</h2>
        <ul className="mt-3 space-y-2 text-sm text-ink-muted">
          <li>混合检索与 SSE 流式问答，回答带可核验证据</li>
          <li>行业模板驱动分块 / 提示词 / 检索参数（运营中配置）</li>
          <li>多租户隔离；管理员可查看用量与接入点健康</li>
        </ul>
      </section>
    </div>
  );
}
