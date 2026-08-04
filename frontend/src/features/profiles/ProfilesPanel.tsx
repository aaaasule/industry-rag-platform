import { useState, type FormEvent } from 'react';

import { ApiError } from '@/lib/http';
import type { IndustryProfile } from './api';
import { useCreateProfile, useProfiles, useUpdateProfile } from './hooks';

function rulesJson(p: IndustryProfile): string {
  return JSON.stringify(
    {
      chunk_rules: p.chunk_rules ?? {},
      prompt_overrides: p.prompt_overrides ?? {},
      retrieval_rules: p.retrieval_rules ?? {},
      parse_rules: p.parse_rules ?? {},
      metadata_schema: p.metadata_schema ?? {},
    },
    null,
    2,
  );
}

export function ProfilesPanel({ enabled }: { enabled: boolean }) {
  const listQ = useProfiles(enabled);
  const createM = useCreateProfile();
  const updateM = useUpdateProfile();

  const [deriveFrom, setDeriveFrom] = useState<IndustryProfile | null>(null);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [edit, setEdit] = useState<IndustryProfile | null>(null);
  const [editName, setEditName] = useState('');
  const [editJson, setEditJson] = useState('');
  const [error, setError] = useState<string | null>(null);

  const rows = listQ.data ?? [];

  async function onDerive(e: FormEvent) {
    e.preventDefault();
    if (!deriveFrom) return;
    setError(null);
    try {
      const body: { base_code: string; code: string; name?: string } = {
        base_code: deriveFrom.code,
        code: newCode.trim(),
      };
      const trimmedName = newName.trim();
      if (trimmedName) body.name = trimmedName;
      await createM.mutateAsync(body);
      setDeriveFrom(null);
      setNewCode('');
      setNewName('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '派生失败');
    }
  }

  function openEdit(p: IndustryProfile) {
    setEdit(p);
    setEditName(p.name);
    setEditJson(rulesJson(p));
    setError(null);
  }

  async function onSaveEdit(e: FormEvent) {
    e.preventDefault();
    if (!edit) return;
    setError(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(editJson) as Record<string, unknown>;
    } catch {
      setError('JSON 无法解析');
      return;
    }
    try {
      await updateM.mutateAsync({
        id: edit.id,
        body: {
          name: editName.trim() || edit.name,
          chunk_rules: (parsed.chunk_rules as Record<string, unknown>) ?? {},
          prompt_overrides: (parsed.prompt_overrides as Record<string, unknown>) ?? {},
          retrieval_rules: (parsed.retrieval_rules as Record<string, unknown>) ?? {},
          parse_rules: (parsed.parse_rules as Record<string, unknown>) ?? {},
          metadata_schema: (parsed.metadata_schema as Record<string, unknown>) ?? {},
        },
      });
      setEdit(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '保存失败');
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        内置模板只读；派生后可编辑 chunk / prompt / retrieval 等 JSON 规则。
      </p>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {listQ.isLoading ? <p className="text-sm text-slate-500">加载中…</p> : null}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">code</th>
              <th className="px-4 py-3 font-medium">名称</th>
              <th className="px-4 py-3 font-medium">类型</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} className="border-b border-slate-50 last:border-0">
                <td className="px-4 py-3 font-mono text-xs text-slate-800">{p.code}</td>
                <td className="px-4 py-3 text-slate-800">{p.name}</td>
                <td className="px-4 py-3 text-slate-500">
                  {p.is_builtin ? '内置' : '自定义'}
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    className="mr-3 text-brand-700 hover:underline"
                    onClick={() => {
                      setDeriveFrom(p);
                      setNewCode(`${p.code}_custom`);
                      setNewName(`${p.name}（自定义）`);
                      setError(null);
                    }}
                  >
                    派生
                  </button>
                  {!p.is_builtin ? (
                    <button
                      type="button"
                      className="text-brand-700 hover:underline"
                      onClick={() => openEdit(p)}
                    >
                      编辑
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!listQ.isLoading && rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-slate-500">
                  暂无模板（请先 seed）
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {deriveFrom ? (
        <form
          onSubmit={(e) => void onDerive(e)}
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-4"
        >
          <h2 className="text-sm font-medium text-slate-900">
            从 {deriveFrom.code} 派生
          </h2>
          <label className="block text-xs text-slate-500">
            新 code
            <input
              required
              pattern="^[a-z][a-z0-9_]*$"
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm"
            />
          </label>
          <label className="block text-xs text-slate-500">
            名称
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createM.isPending}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
            >
              创建
            </button>
            <button
              type="button"
              className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              onClick={() => setDeriveFrom(null)}
            >
              取消
            </button>
          </div>
        </form>
      ) : null}

      {edit ? (
        <form
          onSubmit={(e) => void onSaveEdit(e)}
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-4"
        >
          <h2 className="text-sm font-medium text-slate-900">编辑 {edit.code}</h2>
          <label className="block text-xs text-slate-500">
            名称
            <input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-xs text-slate-500">
            规则 JSON
            <textarea
              value={editJson}
              onChange={(e) => setEditJson(e.target.value)}
              rows={16}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={updateM.isPending}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
            >
              保存
            </button>
            <button
              type="button"
              className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              onClick={() => setEdit(null)}
            >
              取消
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
