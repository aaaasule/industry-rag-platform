import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { useCreateKnowledgeBase, useKnowledgeBases, useProfiles } from './hooks';

export function KnowledgePage() {
  const { data: bases = [], isLoading } = useKnowledgeBases();
  const { data: profiles = [] } = useProfiles();
  const createKb = useCreateKnowledgeBase();
  const [name, setName] = useState('');
  const [profileCode, setProfileCode] = useState('general');
  const [error, setError] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createKb.mutateAsync({ name: name.trim(), profile_code: profileCode });
      setName('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">知识库</h1>
        <p className="mt-1 text-sm text-slate-500">上传文档、跟踪摄取进度，为问答准备语料。</p>
      </div>

      <form
        onSubmit={(e) => void onCreate(e)}
        className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4"
      >
        <div className="min-w-[200px] flex-1">
          <label className="field-label" htmlFor="kb-name">
            名称
          </label>
          <input
            id="kb-name"
            className="field-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：设备手册"
            required
          />
        </div>
        <div className="w-48">
          <label className="field-label" htmlFor="kb-profile">
            行业模板
          </label>
          <select
            id="kb-profile"
            className="field-input"
            value={profileCode}
            onChange={(e) => setProfileCode(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.code}>
                {p.name}
              </option>
            ))}
            {profiles.length === 0 && <option value="general">通用</option>}
          </select>
        </div>
        <button type="submit" className="btn-primary" disabled={createKb.isPending || !name.trim()}>
          {createKb.isPending ? '创建中…' : '新建知识库'}
        </button>
        {error && <p className="w-full text-sm text-red-600">{error}</p>}
      </form>

      <section className="space-y-3">
        {isLoading && <p className="text-sm text-slate-500">加载中…</p>}
        {!isLoading && bases.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            还没有知识库，先创建一个。
          </p>
        )}
        {bases.map((kb) => (
          <Link
            key={kb.id}
            to={`/knowledge/${kb.id}`}
            className="block rounded-xl border border-slate-200 bg-white p-4 transition hover:border-brand-300 hover:shadow-sm"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-medium text-slate-900">{kb.name}</h2>
                {kb.description && (
                  <p className="mt-1 text-sm text-slate-500">{kb.description}</p>
                )}
              </div>
              <div className="shrink-0 text-right text-xs text-slate-500">
                <div>{kb.doc_count} 文档</div>
                <div>{kb.chunk_count} 分块</div>
              </div>
            </div>
          </Link>
        ))}
      </section>
    </div>
  );
}
