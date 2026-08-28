import {
  ArrowLeft,
  FileText,
  FlaskConical,
  Library,
  ScrollText,
  Settings2,
} from 'lucide-react';
import { NavLink, Outlet, useParams } from 'react-router-dom';

import { cn } from '@/components/ui/cn';
import { useKnowledgeBase } from './hooks';

const KB_NAV = [
  { to: 'files', label: '文件列表', icon: FileText, end: false },
  { to: 'retrieval', label: '检索测试', icon: FlaskConical, end: false },
  { to: 'logs', label: '日志', icon: ScrollText, end: false },
  { to: 'settings', label: '配置', icon: Settings2, end: false },
] as const;

export function KbWorkspaceLayout() {
  const { kbId = '' } = useParams();
  const { data: kb, isLoading } = useKnowledgeBase(kbId);
  const base = `/knowledge/${kbId}`;

  return (
    <div className="-mx-4 -my-6 flex min-h-[calc(100dvh-3.5rem)] flex-col md:-mx-6 lg:flex-row lg:min-h-[calc(100dvh-0px)]">
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-200 bg-white lg:w-52 lg:border-b-0 lg:border-r">
        <div className="border-b border-slate-100 px-4 py-4">
          <NavLink
            to="/knowledge"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 transition-colors hover:text-indigo-600"
          >
            <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.5} />
            全部知识库
          </NavLink>
          <div className="mt-3 flex items-start gap-2.5">
            <span className="inline-flex rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <Library className="h-4 w-4" strokeWidth={1.5} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-sm font-semibold text-slate-900">
                {kb?.name ?? (isLoading ? '加载中…' : '知识库')}
              </h1>
              <p className="mt-0.5 text-[11px] tabular-nums text-slate-400">
                {kb
                  ? `${kb.doc_count} 文档 · ${kb.chunk_count} 分块`
                  : '—'}
              </p>
              {kb?.created_at ? (
                <p className="mt-0.5 text-[11px] text-slate-400">
                  创建于{' '}
                  {new Date(kb.created_at).toLocaleDateString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                  })}
                </p>
              ) : null}
            </div>
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-2 py-2 lg:flex-col lg:overflow-visible lg:px-2 lg:py-3">
          {KB_NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={`${base}/${to}`}
              end={end}
              className={({ isActive }) =>
                cn(
                  'relative flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors duration-150',
                  isActive
                    ? 'bg-indigo-50 font-medium text-indigo-600'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive ? (
                    <span
                      className="absolute inset-y-1.5 left-0 hidden w-[3px] rounded-full bg-indigo-600 lg:block"
                      aria-hidden
                    />
                  ) : null}
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={1.5} aria-hidden />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-6 md:px-6">
        {!kb && !isLoading ? (
          <div className="panel border-dashed p-10 text-center">
            <p className="text-sm text-slate-600">知识库不存在或无权访问</p>
            <NavLink to="/knowledge" className="mt-3 inline-block text-sm text-indigo-600 hover:underline">
              返回列表
            </NavLink>
          </div>
        ) : (
          <Outlet context={{ kb, kbId }} />
        )}
      </div>
    </div>
  );
}
