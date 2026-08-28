import { Zap } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/toast/useToast';
import { ApiError } from '@/lib/http';
import type { SearchHit } from '../api';
import { useKbSearch } from '../hooks';

const TOP_K_OPTIONS = [5, 8, 10, 15, 20];

export function KbRetrievalPanel() {
  const { kbId = '' } = useParams();
  const toast = useToast();
  const search = useKbSearch(kbId);
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(8);
  const [rerank, setRerank] = useState(true);
  const [results, setResults] = useState<SearchHit[]>([]);
  const [rewritten, setRewritten] = useState<string | null>(null);
  const [stats, setStats] = useState<{ total_ms: number } | null>(null);

  async function runSearch() {
    const q = query.trim();
    if (!q) {
      toast.error('请输入检索问题');
      return;
    }
    try {
      const resp = await search.mutateAsync({ query: q, top_k: topK, rerank });
      setResults(resp.results);
      setRewritten(resp.query);
      setStats(resp.stats);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : '检索失败');
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">知识检索测试</h2>
        <p className="mt-1 text-sm text-slate-500">
          测试当前知识库与行业模板下的召回效果。此处参数不会自动同步到问答页；改模板请前往
          <Link to={`/knowledge/${kbId}/settings`} className="mx-1 text-indigo-600 hover:underline">
            配置
          </Link>
          。
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_1fr]">
        <aside className="panel space-y-4 p-4">
          <h3 className="text-sm font-medium text-slate-800">检索参数</h3>

          <label className="block text-sm">
            <span className="mb-1.5 block text-slate-500">Top-K（召回条数）</span>
            <select
              className="field-input w-full"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            >
              {TOP_K_OPTIONS.map((k) => (
                <option key={k} value={k}>
                  前 {k} 条
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center justify-between gap-3 text-sm text-slate-700">
            <span>Rerank 重排</span>
            <input
              type="checkbox"
              checked={rerank}
              onChange={(e) => setRerank(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/30"
            />
          </label>

          <p className="text-xs leading-relaxed text-slate-400">
            混合检索（向量 + 全文 + RRF）由行业模板控制；相似度阈值与向量/全文权重暂不支持在线调节。
          </p>

          <div className="border-t border-slate-100 pt-4">
            <label htmlFor="retrieval-query" className="mb-1.5 block text-sm text-slate-500">
              测试问题
            </label>
            <textarea
              id="retrieval-query"
              rows={4}
              className="field-input resize-y"
              placeholder="输入业务口吻的检索问题…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <Button
              className="mt-3 w-full"
              disabled={search.isPending || !query.trim()}
              onClick={() => void runSearch()}
            >
              <Zap className="h-4 w-4" strokeWidth={1.5} />
              {search.isPending ? '检索中…' : '运行'}
            </Button>
          </div>
        </aside>

        <section className="panel flex min-h-[420px] flex-col p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <h3 className="text-sm font-medium text-slate-800">
              测试结果
              <span className="ml-2 font-normal text-slate-400">显示 {results.length} 条</span>
            </h3>
            {stats ? (
              <span className="text-xs tabular-nums text-slate-400">
                耗时 {stats.total_ms.toFixed(0)} ms
              </span>
            ) : null}
          </div>

          {rewritten && rewritten !== query.trim() ? (
            <p className="mb-3 text-xs text-slate-500">
              改写后查询：<span className="font-medium text-slate-700">{rewritten}</span>
            </p>
          ) : null}

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto">
            {results.length === 0 ? (
              <EmptyState
                compact
                className="h-full"
                title="尚未进行测试"
                description="输入问题并点击运行，召回的分块将显示在这里"
              />
            ) : (
              results.map((hit, idx) => (
                <HitCard key={hit.chunk_id} index={idx + 1} hit={hit} kbId={kbId} />
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function HitCard({ index, hit, kbId }: { index: number; hit: SearchHit; kbId: string }) {
  const scoreParts = [
    hit.scores.rrf != null ? `RRF ${hit.scores.rrf.toFixed(4)}` : null,
    hit.scores.vector != null ? `向量 ${hit.scores.vector.toFixed(4)}` : null,
    hit.scores.fulltext != null ? `全文 ${hit.scores.fulltext.toFixed(4)}` : null,
    hit.scores.rerank != null ? `Rerank ${hit.scores.rerank.toFixed(4)}` : null,
  ].filter(Boolean);

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="text-xs font-semibold text-indigo-600">#{index}</span>
          <Link
            to={`/knowledge/${kbId}/documents/${hit.document_id}?chunk=${hit.chunk_id}`}
            className="ml-2 text-sm font-medium text-slate-800 hover:text-indigo-600 hover:underline"
          >
            {hit.document_title}
          </Link>
          <p className="mt-0.5 text-[11px] text-slate-400">
            第 {hit.page_start}
            {hit.page_end !== hit.page_start ? `–${hit.page_end}` : ''} 页
            {hit.heading_path.length ? ` · ${hit.heading_path.join(' › ')}` : ''}
          </p>
        </div>
        {scoreParts.length ? (
          <p className="shrink-0 text-[11px] tabular-nums text-slate-500">{scoreParts.join(' · ')}</p>
        ) : null}
      </div>
      <p className="mt-2 line-clamp-4 text-sm leading-relaxed text-slate-600">{hit.content}</p>
    </article>
  );
}
