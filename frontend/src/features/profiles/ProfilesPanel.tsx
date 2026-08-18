import { useState, type FormEvent } from 'react';

import { useToast } from '@/components/toast/useToast';
import { ApiError } from '@/lib/http';
import type { IndustryProfile } from './api';
import { ProfileEditor } from './ProfileEditor';
import { useCreateProfile, useDeleteProfile, useProfiles, useRestoreProfile } from './hooks';

export function ProfilesPanel({ enabled }: { enabled: boolean }) {
  const toast = useToast();
  const [deriveFrom, setDeriveFrom] = useState<IndustryProfile | null>(null);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [edit, setEdit] = useState<IndustryProfile | null>(null);
  const [showDeleted, setShowDeleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listQ = useProfiles(enabled, showDeleted);
  const createM = useCreateProfile();
  const deleteM = useDeleteProfile();
  const restoreM = useRestoreProfile();

  const rows = listQ.data ?? [];

  async function onDelete(p: IndustryProfile) {
    if (!window.confirm(`确认删除模板「${p.name}」（${p.code}）？`)) return;
    setError(null);
    try {
      await deleteM.mutateAsync(p.id);
      if (edit?.id === p.id) setEdit(null);
      toast.success(`已删除模板 ${p.code}`);
    } catch (err) {
      const msg =
        err instanceof ApiError && err.code === 'profile_in_use'
          ? '仍有知识库绑定'
          : err instanceof ApiError
            ? err.message
            : '删除失败';
      setError(msg);
      toast.error(msg);
    }
  }

  async function onRestore(p: IndustryProfile) {
    setError(null);
    try {
      await restoreM.mutateAsync(p.id);
      toast.success(`已恢复模板 ${p.code}`);
    } catch (err) {
      const msg =
        err instanceof ApiError && err.code === 'profile_code_in_use'
          ? '同 code 的模板已存在，无法恢复'
          : err instanceof ApiError
            ? err.message
            : '恢复失败';
      setError(msg);
      toast.error(msg);
    }
  }

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
      toast.success(`已派生模板 ${body.code}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '派生失败';
      setError(msg);
      toast.error(msg);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-muted">
        内置模板只读；派生后可编辑分块、检索、术语表、同义词与元数据字段。
      </p>
      <label className="flex items-center gap-2 text-sm text-ink-muted">
        <input
          type="checkbox"
          checked={showDeleted}
          onChange={(e) => setShowDeleted(e.target.checked)}
        />
        显示已删除
      </label>
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      {listQ.isLoading ? <p className="text-sm text-ink-muted">加载中…</p> : null}

      <div className="table-scroll panel">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line bg-canvas text-xs uppercase tracking-wider text-ink-faint">
            <tr>
              <th className="px-4 py-3 font-medium">code</th>
              <th className="px-4 py-3 font-medium">名称</th>
              <th className="px-4 py-3 font-medium">类型</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr
                key={p.id}
                className="border-b border-line/60 transition-colors last:border-0 hover:bg-brand-50/40"
              >
                <td className="px-4 py-3 font-mono text-xs text-ink">{p.code}</td>
                <td className="px-4 py-3 text-ink">{p.name}</td>
                <td className="px-4 py-3 text-ink-muted">
                  {p.is_builtin ? '内置' : p.deleted_at ? '已删除' : '自定义'}
                </td>
                <td className="px-4 py-3">
                  {!p.deleted_at ? (
                    <button
                      type="button"
                      className="mr-3 text-brand-700 hover:underline"
                      onClick={() => {
                        setEdit(null);
                        setDeriveFrom(p);
                        setNewCode(`${p.code}_custom`);
                        setNewName(`${p.name}（自定义）`);
                        setError(null);
                      }}
                    >
                      派生
                    </button>
                  ) : null}
                  {!p.is_builtin && !p.deleted_at ? (
                    <>
                      <button
                        type="button"
                        className="mr-3 text-brand-700 hover:underline"
                        onClick={() => {
                          setDeriveFrom(null);
                          setEdit(p);
                          setError(null);
                        }}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="text-danger hover:underline"
                        onClick={() => void onDelete(p)}
                      >
                        删除
                      </button>
                    </>
                  ) : null}
                  {p.deleted_at ? (
                    <button
                      type="button"
                      className="text-brand-700 hover:underline"
                      onClick={() => void onRestore(p)}
                    >
                      恢复
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!listQ.isLoading && rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-ink-muted">
                  暂无模板，请先完成 seed 初始化
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {deriveFrom ? (
        <form onSubmit={(e) => void onDerive(e)} className="panel space-y-3 p-4">
          <h2 className="text-sm font-medium text-ink">从 {deriveFrom.code} 派生</h2>
          <label className="block text-xs text-ink-muted">
            新 code
            <input
              required
              pattern="^[a-z][a-z0-9_]*$"
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              className="field-input mt-1 font-mono"
            />
          </label>
          <label className="block text-xs text-ink-muted">
            名称
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="field-input mt-1"
            />
          </label>
          <div className="flex gap-2">
            <button type="submit" disabled={createM.isPending} className="btn-primary">
              创建
            </button>
            <button type="button" className="btn-ghost" onClick={() => setDeriveFrom(null)}>
              取消
            </button>
          </div>
        </form>
      ) : null}

      {edit ? (
        <ProfileEditor
          key={edit.id}
          profile={edit}
          onClose={() => setEdit(null)}
          onSaved={() => {
            toast.success('模板已保存');
            setEdit(null);
          }}
        />
      ) : null}
    </div>
  );
}
