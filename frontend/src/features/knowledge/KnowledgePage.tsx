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
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-ink">知识库</h1>
        <p className="mt-1 text-sm text-ink-muted">上传文档、跟踪摄取进度，为问答准备语料。</p>
      </header>

      <form onSubmit={(e) => void onCreate(e)} className="panel flex flex-wrap items-end gap-3 p-4">
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
        {error && <p className="w-full text-sm text-danger">{error}</p>}
      </form>

      <section className="space-y-2">
        {isLoading && <p className="text-sm text-ink-muted">加载中…</p>}
        {!isLoading && bases.length === 0 && (
          <p className="panel border-dashed p-10 text-center text-sm text-ink-muted">
            还没有知识库，先创建一个。
          </p>
        )}
        {bases.map((kb) => (
          <Link
            key={kb.id}
            to={`/knowledge/${kb.id}`}
            className="panel block p-4 transition-colors duration-150 hover:border-brand-500 hover:bg-brand-50/30"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-medium text-ink">{kb.name}</h2>
                {kb.description && (
                  <p className="mt-1 text-sm text-ink-muted">{kb.description}</p>
                )}
              </div>
              <div className="shrink-0 text-right text-xs tabular-nums text-ink-faint">
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
