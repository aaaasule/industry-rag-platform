/**
 * M0 的页面占位。每个占位标注了它将在哪个里程碑被真正实现，
 * 这样骨架本身就是一份可执行的进度表。
 */

import { useSession } from '@/features/auth/hooks';

export function OverviewPage() {
  const { session } = useSession();
  if (!session) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">你好，{session.user.display_name}</h1>
        <p className="mt-1 text-sm text-slate-500">
          当前租户：{session.current_tenant.name}（{session.current_tenant.slug}）
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-medium text-slate-900">M2 检索与问答已接入</h2>
        <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
          <li>· 知识库摄取（M1）与混合检索 / SSE 问答（M2）可用</li>
          <li>· 前往「问答」页选择知识库并发问，右侧查看证据</li>
          <li>· 下一步 M3：引用高亮与反馈</li>
        </ul>
      </section>
    </div>
  );
}

export const ModelOpsPlaceholder = () => <Placeholder title="模型接入管理" milestone="M4" />;

function Placeholder({ title, milestone }: { title: string; milestone: string }) {
  return (
    <div className="mx-auto max-w-3xl rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
      <h1 className="text-lg font-medium text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">该功能计划在 {milestone} 交付。</p>
    </div>
  );
}
