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
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <header className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-slate-900">工业知识库平台</h1>
          <p className="mt-1.5 text-sm text-slate-500">登录以访问您的知识库</p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
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
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {login.error.message}
            </p>
          )}

          <button type="submit" disabled={login.isPending} className="btn-primary w-full">
            {login.isPending ? '登录中…' : '登录'}
          </button>
        </form>
      </div>
    </div>
  );
}

export function FullscreenHint({ text }: { text: string }) {
  return (
    <div className="flex min-h-full items-center justify-center text-sm text-slate-500">{text}</div>
  );
}

/** 登录后回到被拦截前的页面，而不是一律回首页。 */
function redirectTarget(location: ReturnType<typeof useLocation>): string {
  const from = (location.state as { from?: string } | null)?.from;
  return from && from !== '/login' ? from : '/';
}
