import { Link, useSearchParams } from 'react-router-dom';

import { useSession } from '@/features/auth/hooks';
import { ConnectionsPanel } from '@/features/modelops/ConnectionsPanel';
import { ProfilesPanel } from '@/features/profiles/ProfilesPanel';
import { AuditPanel } from './AuditPanel';
import { MembersPanel } from './MembersPanel';

type TabId = 'connections' | 'members' | 'audit' | 'profiles';

const TABS: { id: TabId; label: string }[] = [
  { id: 'connections', label: '接入点' },
  { id: 'profiles', label: '行业模板' },
  { id: 'members', label: '成员' },
  { id: 'audit', label: '审计' },
];

function parseTab(raw: string | null): TabId {
  if (raw === 'members' || raw === 'audit' || raw === 'connections' || raw === 'profiles') {
    return raw;
  }
  return 'connections';
}

export function AdminPage() {
  const { session } = useSession();
  const [params, setParams] = useSearchParams();
  const tab = parseTab(params.get('tab'));
  const role = session?.current_tenant.role;
  const canView = role === 'owner' || role === 'admin';

  if (!session) return null;

  if (!canView) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h1 className="text-lg font-medium text-slate-900">无权访问运营</h1>
        <p className="mt-2 text-sm text-slate-500">运营管理仅对租户 owner / admin 开放。</p>
        <Link to="/" className="mt-4 inline-block text-sm text-brand-700 hover:underline">
          返回概览
        </Link>
      </div>
    );
  }

  function setTab(next: TabId) {
    const sp = new URLSearchParams(params);
    sp.set('tab', next);
    setParams(sp, { replace: true });
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">运营</h1>
        <p className="mt-1 text-sm text-slate-500">
          租户 {session.current_tenant.name} · 接入点 / 行业模板 / 成员 / 审计
        </p>
      </header>

      <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={[
              '-mb-px border-b-2 px-3 py-2 text-sm transition',
              tab === t.id
                ? 'border-brand-600 font-medium text-brand-700'
                : 'border-transparent text-slate-600 hover:text-slate-900',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'connections' ? <ConnectionsPanel enabled={canView} /> : null}
      {tab === 'profiles' ? <ProfilesPanel enabled={canView} /> : null}
      {tab === 'members' ? <MembersPanel enabled={canView} /> : null}
      {tab === 'audit' ? <AuditPanel enabled={canView} /> : null}
    </div>
  );
}
