import { CircleCheck, Search, ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { BrandMark } from '@/components/BrandMark';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

import { useLogin, useSession } from './hooks';

const CAPABILITIES = [
  { icon: Search, text: '混合检索与可核验证据引用' },
  { icon: ShieldCheck, text: '行业模板驱动分块与提示词' },
  { icon: CircleCheck, text: '多租户隔离与用量可观测' },
];

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isLoading } = useSession();
  const login = useLogin();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  if (isLoading) return <FullscreenHint text="正在恢复会话…" />;
  if (isAuthenticated) return <Navigate to={redirectTarget(location)} replace />;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate(
      { email, password },
      { onSuccess: () => navigate(redirectTarget(location), { replace: true }) },
    );
  };

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[#F9FAFB] md:flex-row">
      <aside className="app-enter flex flex-col justify-between border-b border-slate-200/60 bg-white px-8 py-10 md:w-[44%] md:border-b-0 md:border-r md:px-12 md:py-16">
        <div>
          <div className="flex items-center gap-3">
            <BrandMark size={36} />
            <p className="text-sm font-semibold text-indigo-600">工业知识库平台</p>
          </div>
          <h1 className="mt-6 text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl">
            让手册与规程变成可检索、可引用的知识资产
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-500">
            面向制造与流程工业的自然语言检索与问答。登录后管理知识库、配置行业模板并开展引用式问答。
          </p>
          <ul className="mt-8 space-y-3">
            {CAPABILITIES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-sm text-slate-500">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-indigo-500" strokeWidth={1.5} />
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-10 hidden text-xs text-slate-400 md:block">
          证据可追溯 · 多租户隔离 · 企业级部署
        </p>
      </aside>

      <div className="app-enter flex flex-1 items-center justify-center px-6 py-12 [animation-delay:60ms] md:px-12">
        <div className="w-full max-w-sm">
          <header className="mb-6">
            <h2 className="text-lg font-semibold text-slate-900">登录</h2>
            <p className="mt-1 text-sm text-slate-500">使用租户账号访问工作区</p>
          </header>

          <Card padding={false}>
            <form onSubmit={handleSubmit} className="space-y-5 p-6">
              <Input
                label="邮箱"
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
              />

              <Input
                label="密码"
                id="password"
                type="password"
                autoComplete="current-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="至少 8 位"
              />

              {login.error && (
                <p
                  role="alert"
                  className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600"
                >
                  {login.error.message}
                </p>
              )}

              <Button type="submit" disabled={login.isPending} className="w-full">
                {login.isPending ? '登录中…' : '登录'}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function FullscreenHint({ text }: { text: string }) {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-[#F9FAFB] text-sm text-slate-500">
      {text}
    </div>
  );
}

function redirectTarget(location: ReturnType<typeof useLocation>): string {
  const from = (location.state as { from?: string } | null)?.from;
  return from && from !== '/login' ? from : '/';
}
