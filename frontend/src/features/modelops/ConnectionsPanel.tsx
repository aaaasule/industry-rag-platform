import { useState, type FormEvent, type ReactNode } from 'react';

import { ApiError } from '@/lib/http';
import type { ModelConnection, Purpose } from './api';
import {
  useConnections,
  useCreateConnection,
  useDeleteConnection,
  useRoutes,
  useTestConnection,
  useUpdateConnection,
  useUpdateCredential,
} from './hooks';

const PURPOSES: Purpose[] = ['chat', 'embedding', 'rerank', 'title'];

type ProviderType = 'openai_compatible' | 'fake';

const emptyForm = {
  name: '',
  provider_type: 'openai_compatible' as ProviderType,
  base_url: 'https://api.openai.com/v1',
  model: '',
  purposes: ['chat'] as Purpose[],
  priority: 100,
  enabled: true,
  api_key: '',
};

export function ConnectionsPanel({ enabled }: { enabled: boolean }) {
  const listQ = useConnections(enabled);
  const routesQ = useRoutes(enabled);
  const createM = useCreateConnection();
  const updateM = useUpdateConnection();
  const credM = useUpdateCredential();
  const testM = useTestConnection();
  const deleteM = useDeleteConnection();

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<{
    name: string;
    model: string;
    base_url: string;
    priority: number;
    enabled: boolean;
    purposes: Purpose[];
  } | null>(null);
  const [credDraft, setCredDraft] = useState<Record<string, string>>({});
  const [testMsg, setTestMsg] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const rows = listQ.data ?? [];

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createM.mutateAsync({
        name: form.name,
        provider_type: form.provider_type,
        base_url: form.base_url,
        model: form.model,
        purposes: form.purposes,
        priority: form.priority,
        enabled: form.enabled,
        api_key: form.provider_type === 'fake' ? null : form.api_key || null,
      });
      setForm(emptyForm);
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '创建失败');
    }
  }

  async function onSaveEdit(id: string) {
    if (!editDraft) return;
    setError(null);
    try {
      await updateM.mutateAsync({
        id,
        body: {
          name: editDraft.name,
          model: editDraft.model,
          base_url: editDraft.base_url,
          priority: editDraft.priority,
          enabled: editDraft.enabled,
          purposes: editDraft.purposes,
        },
      });
      setEditId(null);
      setEditDraft(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '更新失败');
    }
  }

  async function onSaveCred(id: string) {
    const key = credDraft[id]?.trim();
    if (!key) return;
    setError(null);
    try {
      await credM.mutateAsync({ id, apiKey: key });
      setCredDraft((prev) => ({ ...prev, [id]: '' }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '凭证更新失败');
    }
  }

  async function onTest(id: string) {
    setTestMsg((prev) => ({ ...prev, [id]: '探测中…' }));
    try {
      const r = await testM.mutateAsync(id);
      setTestMsg((prev) => ({
        ...prev,
        [id]: r.ok
          ? `成功 · ${r.latency_ms != null ? `${Math.round(r.latency_ms)}ms` : ''}`
          : `失败 · ${r.error_message ?? r.error_code ?? 'unknown'}`,
      }));
    } catch (err) {
      setTestMsg((prev) => ({
        ...prev,
        [id]: err instanceof ApiError ? err.message : '探测请求失败',
      }));
    }
  }

  async function onDelete(c: ModelConnection) {
    if (!window.confirm(`确认删除接入点「${c.name}」？`)) return;
    setError(null);
    try {
      await deleteM.mutateAsync(c.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '删除失败');
    }
  }

  function startEdit(c: ModelConnection) {
    setEditId(c.id);
    setEditDraft({
      name: c.name,
      model: c.model,
      base_url: c.base_url,
      priority: c.priority,
      enabled: c.enabled,
      purposes: (c.purposes.filter((p) => PURPOSES.includes(p as Purpose)) as Purpose[]) || [
        'chat',
      ],
    });
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-ink-muted">
          管理租户模型接入点。平台接入点只读；凭证只写不回显。priority 越小越优先。
        </p>
        <button type="button" className="btn-primary" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? '取消创建' : '新建接入点'}
        </button>
      </div>

      {error ? (
        <p className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}

      {showCreate ? (
        <form
          onSubmit={(e) => void onCreate(e)}
          className="space-y-3 panel p-4"
        >
          <h3 className="text-sm font-medium text-ink">新建接入点</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="名称">
              <input
                className="field-input"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </Field>
            <Field label="Provider">
              <select
                className="field-input"
                value={form.provider_type}
                onChange={(e) =>
                  setForm({
                    ...form,
                    provider_type: e.target.value as ProviderType,
                  })
                }
              >
                <option value="openai_compatible">openai_compatible</option>
                <option value="fake">fake</option>
              </select>
            </Field>
            <Field label="Base URL">
              <input
                className="field-input"
                required
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              />
            </Field>
            <Field label="Model">
              <input
                className="field-input"
                required
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
              />
            </Field>
            <Field label="Priority（越小越优先）">
              <input
                type="number"
                className="field-input"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
              />
            </Field>
            <Field label="API Key（openai_compatible 必填）">
              <input
                type="password"
                className="field-input"
                autoComplete="new-password"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              />
            </Field>
          </div>
          <PurposePicker
            value={form.purposes}
            onChange={(purposes) => setForm({ ...form, purposes })}
          />
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
            启用
          </label>
          <button type="submit" className="btn-primary" disabled={createM.isPending}>
            {createM.isPending ? '创建中…' : '创建'}
          </button>
        </form>
      ) : null}

      {listQ.isLoading ? (
        <p className="text-sm text-ink-faint">加载中…</p>
      ) : rows.length === 0 ? (
        <p className="panel border-dashed p-8 text-center text-sm text-ink-muted">
          暂无接入点
        </p>
      ) : (
        <ul className="space-y-3">
          {rows.map((c) => {
            const readonly = c.scope === 'platform';
            const editing = editId === c.id && editDraft;
            return (
              <li key={c.id} className="panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-medium text-ink">{c.name}</h3>
                      <HealthBadge health={c.health} />
                      <ScopeBadge scope={c.scope} />
                      {!c.enabled ? (
                        <span className="rounded bg-canvas px-1.5 py-0.5 text-xs text-ink-muted">
                          已停用
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-xs text-ink-muted">
                      {c.provider_type} · {c.model} · priority {c.priority}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-faint">
                      用途：{c.purposes.join(', ')} · 凭证 {c.credential_masked}
                    </p>
                    {testMsg[c.id] ? (
                      <p className="mt-1 text-xs text-ink-muted">{testMsg[c.id]}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded-md border border-line px-2.5 py-1 text-xs text-ink hover:bg-canvas"
                      onClick={() => void onTest(c.id)}
                      disabled={testM.isPending}
                    >
                      测试
                    </button>
                    {!readonly ? (
                      <>
                        <button
                          type="button"
                          className="rounded-md border border-line px-2.5 py-1 text-xs text-ink hover:bg-canvas"
                          onClick={() => startEdit(c)}
                        >
                          编辑
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-danger/30 px-2.5 py-1 text-xs text-danger hover:bg-danger/5"
                          onClick={() => void onDelete(c)}
                        >
                          删除
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>

                {editing ? (
                  <div className="mt-4 space-y-3 border-t border-line pt-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Field label="名称">
                        <input
                          className="field-input"
                          value={editDraft.name}
                          onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })}
                        />
                      </Field>
                      <Field label="Model">
                        <input
                          className="field-input"
                          value={editDraft.model}
                          onChange={(e) => setEditDraft({ ...editDraft, model: e.target.value })}
                        />
                      </Field>
                      <Field label="Base URL">
                        <input
                          className="field-input"
                          value={editDraft.base_url}
                          onChange={(e) => setEditDraft({ ...editDraft, base_url: e.target.value })}
                        />
                      </Field>
                      <Field label="Priority">
                        <input
                          type="number"
                          className="field-input"
                          value={editDraft.priority}
                          onChange={(e) =>
                            setEditDraft({ ...editDraft, priority: Number(e.target.value) })
                          }
                        />
                      </Field>
                    </div>
                    <PurposePicker
                      value={editDraft.purposes}
                      onChange={(purposes) => setEditDraft({ ...editDraft, purposes })}
                    />
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={editDraft.enabled}
                        onChange={(e) => setEditDraft({ ...editDraft, enabled: e.target.checked })}
                      />
                      启用
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={() => void onSaveEdit(c.id)}
                        disabled={updateM.isPending}
                      >
                        保存
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-line px-3 py-2 text-sm"
                        onClick={() => {
                          setEditId(null);
                          setEditDraft(null);
                        }}
                      >
                        取消
                      </button>
                    </div>
                    <div className="flex flex-wrap items-end gap-2 border-t border-line pt-3">
                      <Field label="更新 API Key（只写）">
                        <input
                          type="password"
                          className="field-input"
                          autoComplete="new-password"
                          placeholder="输入新密钥"
                          value={credDraft[c.id] ?? ''}
                          onChange={(e) =>
                            setCredDraft((prev) => ({ ...prev, [c.id]: e.target.value }))
                          }
                        />
                      </Field>
                      <button
                        type="button"
                        className="rounded-md bg-ink px-3 py-2 text-sm text-white"
                        onClick={() => void onSaveCred(c.id)}
                        disabled={credM.isPending}
                      >
                        更新凭证
                      </button>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      <section className="panel p-4">
        <h3 className="text-sm font-medium text-ink">用途路由（当前命中）</h3>
        {routesQ.isLoading ? (
          <p className="mt-3 text-sm text-ink-faint">加载中…</p>
        ) : (
          <table className="mt-3 w-full text-left text-sm">
            <thead className="text-xs text-ink-muted">
              <tr>
                <th className="pb-2 font-medium">用途</th>
                <th className="pb-2 font-medium">来源</th>
                <th className="pb-2 font-medium">接入点</th>
                <th className="pb-2 font-medium">模型</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {(routesQ.data?.items ?? []).map((r) => (
                <tr key={r.purpose}>
                  <td className="py-2 pr-2">{r.purpose}</td>
                  <td className="py-2 pr-2">
                    <SourceBadge source={r.source} />
                  </td>
                  <td className="py-2 pr-2 text-ink">{r.name ?? '—'}</td>
                  <td className="py-2 text-ink-muted">{r.model}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

function PurposePicker({
  value,
  onChange,
}: {
  value: Purpose[];
  onChange: (v: Purpose[]) => void;
}) {
  return (
    <div>
      <p className="field-label">用途</p>
      <div className="flex flex-wrap gap-3">
        {PURPOSES.map((p) => {
          const checked = value.includes(p);
          return (
            <label key={p} className="flex items-center gap-1.5 text-sm text-ink">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => {
                  if (checked) {
                    const next = value.filter((x) => x !== p);
                    if (next.length) onChange(next);
                  } else {
                    onChange([...value, p]);
                  }
                }}
              />
              {p}
            </label>
          );
        })}
      </div>
    </div>
  );
}

function HealthBadge({ health }: { health: string }) {
  const tone =
    health === 'healthy'
      ? 'bg-ok/10 text-ok'
      : health === 'down'
        ? 'bg-danger/10 text-danger'
        : health === 'degraded'
          ? 'bg-warn/10 text-warn'
          : 'bg-canvas text-ink-muted';
  const label =
    health === 'healthy'
      ? '正常'
      : health === 'down'
        ? '故障'
        : health === 'degraded'
          ? '降级'
          : '未知';
  return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${tone}`}>{label}</span>;
}

function ScopeBadge({ scope }: { scope: string }) {
  return (
    <span className="rounded bg-canvas px-1.5 py-0.5 text-xs text-ink-muted">
      {scope === 'platform' ? '平台' : '租户'}
    </span>
  );
}

function SourceBadge({ source }: { source: string }) {
  const label = source === 'env' ? '环境变量' : source === 'platform' ? '平台' : '租户';
  return <span className="text-ink">{label}</span>;
}
