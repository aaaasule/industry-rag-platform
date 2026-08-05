import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useLogin, useSession } from './hooks';

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
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="app-enter relative flex flex-col justify-between border-b border-line bg-surface px-8 py-10 md:w-[42%] md:border-b-0 md:border-r md:px-12 md:py-16">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-brand-700">
            Industry RAG
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            工业知识库平台
          </h1>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink-muted">
            面向制造与流程工业的文档检索与问答。登录后管理知识库、配置行业模板并开展引用式问答。
          </p>
        </div>
        <p className="mt-10 hidden text-xs text-ink-faint md:block">
          控制台 · 证据可追溯 · 多租户隔离
        </p>
      </aside>

      <div className="app-enter flex flex-1 items-center justify-center px-6 py-12 [animation-delay:60ms] md:px-12">
        <div className="w-full max-w-sm">
          <header className="mb-6">
            <h2 className="text-lg font-semibold text-ink">登录</h2>
            <p className="mt-1 text-sm text-ink-muted">使用租户账号访问工作区</p>
          </header>

          <form onSubmit={handleSubmit} className="panel space-y-5 p-6">
            <div>
              <label htmlFor="email" className="field-label">
                邮箱
              </label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="field-input"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="field-label">
                密码
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="field-input"
                placeholder="至少 8 位"
              />
            </div>

            {login.error && (
              <p
                role="alert"
                className="rounded border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger"
              >
                {login.error.message}
              </p>
            )}

            <button type="submit" disabled={login.isPending} className="btn-primary w-full">
              {login.isPending ? '登录中…' : '登录'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export function FullscreenHint({ text }: { text: string }) {
  return (
    <div className="flex min-h-full items-center justify-center text-sm text-ink-muted">{text}</div>
  );
}

/** 登录后回到被拦截前的页面，而不是一律回首页。 */
function redirectTarget(location: ReturnType<typeof useLocation>): string {
  const from = (location.state as { from?: string } | null)?.from;
  return from && from !== '/login' ? from : '/';
}
