import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/toast/useToast';
import { ApiError } from '@/lib/http';
import { KbGrantsPanel } from '../KbGrantsPanel';
import type { KbChunkRules, KbRetrievalRules, KnowledgeBase, KbSettings } from '../api';
import {
  useKnowledgeBase,
  useProfiles,
  useUpdateKnowledgeBase,
} from '../hooks';

const CHUNK_DEFAULTS: Required<KbChunkRules> = {
  max_tokens: 512,
  min_tokens: 80,
  overlap_tokens: 64,
  clause_mode: false,
  keep_heading_prefix: true,
};

type ChunkForm = Required<KbChunkRules>;
type RetrievalForm = {
  top_k: number;
  rerank: 'default' | 'on' | 'off';
  query_expand: boolean;
};

function rulesFromKb(kb: KnowledgeBase): { chunk: ChunkForm; retrieval: RetrievalForm } {
  const settingsChunk = kb.settings?.chunk_rules ?? {};
  const effectiveChunk = kb.effective_chunk_rules ?? {};
  const chunkSrc = { ...CHUNK_DEFAULTS, ...effectiveChunk, ...settingsChunk };

  const settingsRet = kb.settings?.retrieval_rules ?? {};
  const effectiveRet = kb.effective_retrieval_rules ?? {};
  // 表单优先展示 KB 覆盖；无覆盖时用 effective（已含 Profile/默认）
  const retSrc = { ...effectiveRet, ...settingsRet };

  let rerank: RetrievalForm['rerank'] = 'default';
  if ('rerank_enabled' in settingsRet) {
    if (settingsRet.rerank_enabled === true) rerank = 'on';
    else if (settingsRet.rerank_enabled === false) rerank = 'off';
    else rerank = 'default';
  } else if (effectiveRet.rerank_enabled === true) {
    rerank = 'on';
  } else if (effectiveRet.rerank_enabled === false) {
    rerank = 'off';
  }

  return {
    chunk: {
      max_tokens: numOr(chunkSrc.max_tokens, CHUNK_DEFAULTS.max_tokens),
      min_tokens: numOr(chunkSrc.min_tokens, CHUNK_DEFAULTS.min_tokens),
      overlap_tokens: numOr(chunkSrc.overlap_tokens, CHUNK_DEFAULTS.overlap_tokens),
      clause_mode: boolOr(chunkSrc.clause_mode, CHUNK_DEFAULTS.clause_mode),
      keep_heading_prefix: boolOr(
        chunkSrc.keep_heading_prefix,
        CHUNK_DEFAULTS.keep_heading_prefix,
      ),
    },
    retrieval: {
      top_k: numOr(retSrc.top_k, 8),
      rerank,
      query_expand: boolOr(retSrc.query_expand, false),
    },
  };
}

function numOr(v: unknown, fallback: number): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback;
}

function boolOr(v: unknown, fallback: boolean): boolean {
  return typeof v === 'boolean' ? v : fallback;
}

/** 相对表单基线只提交脏键；两域皆空则返回 null。 */
function buildSettingsPayload(
  chunk: ChunkForm,
  retrieval: RetrievalForm,
  baseline: { chunk: ChunkForm; retrieval: RetrievalForm },
): KbSettings | null {
  const chunk_rules: KbChunkRules = {};
  (Object.keys(chunk) as (keyof ChunkForm)[]).forEach((key) => {
    if (chunk[key] !== baseline.chunk[key]) {
      (chunk_rules as Record<string, unknown>)[key] = chunk[key];
    }
  });

  const retrieval_rules: KbRetrievalRules = {};
  if (retrieval.top_k !== baseline.retrieval.top_k) {
    retrieval_rules.top_k = retrieval.top_k;
  }
  if (retrieval.query_expand !== baseline.retrieval.query_expand) {
    retrieval_rules.query_expand = retrieval.query_expand;
  }
  if (retrieval.rerank !== baseline.retrieval.rerank) {
    if (retrieval.rerank === 'on') retrieval_rules.rerank_enabled = true;
    else if (retrieval.rerank === 'off') retrieval_rules.rerank_enabled = false;
    // default：本轮不删除已有 rerank_enabled 键
  }

  const settings: KbSettings = {};
  if (Object.keys(chunk_rules).length > 0) settings.chunk_rules = chunk_rules;
  if (Object.keys(retrieval_rules).length > 0) settings.retrieval_rules = retrieval_rules;
  if (!settings.chunk_rules && !settings.retrieval_rules) return null;
  return settings;
}

export function KbSettingsPanel() {
  const { kbId = '' } = useParams();
  const toast = useToast();
  const { data: kb } = useKnowledgeBase(kbId);
  const { data: profiles = [] } = useProfiles();
  const updateKb = useUpdateKnowledgeBase(kbId);
  const canWrite = kb?.my_permission === 'write' || kb?.my_permission === 'manage';

  const [kbName, setKbName] = useState('');
  const [kbDescription, setKbDescription] = useState('');
  const [profileCode, setProfileCode] = useState('');
  const [chunk, setChunk] = useState<ChunkForm>(CHUNK_DEFAULTS);
  const [retrieval, setRetrieval] = useState<RetrievalForm>({
    top_k: 8,
    rerank: 'default',
    query_expand: false,
  });
  const [seededKbId, setSeededKbId] = useState<string | null>(null);

  useEffect(() => {
    if (!kb || seededKbId === kb.id) return;
    setKbName(kb.name);
    setKbDescription(kb.description ?? '');
    const next = rulesFromKb(kb);
    setChunk(next.chunk);
    setRetrieval(next.retrieval);
    setSeededKbId(kb.id);
  }, [kb, seededKbId]);

  useEffect(() => {
    if (!kb?.profile_id) {
      setProfileCode('');
      return;
    }
    const match = profiles.find((p) => p.id === kb.profile_id);
    setProfileCode(match?.code ?? '');
  }, [kb?.profile_id, profiles]);

  const basicDirty =
    kb != null &&
    (kbName.trim() !== kb.name || kbDescription.trim() !== (kb.description ?? ''));

  const profileDirty =
    kb != null && profileCode !== '' && profiles.find((p) => p.id === kb.profile_id)?.code !== profileCode;

  const rulesDirty = (() => {
    if (!kb) return false;
    const baseline = rulesFromKb(kb);
    return (
      JSON.stringify(chunk) !== JSON.stringify(baseline.chunk) ||
      JSON.stringify(retrieval) !== JSON.stringify(baseline.retrieval)
    );
  })();

  function saveBasic() {
    if (!kb || !canWrite) return;
    const name = kbName.trim();
    if (!name) {
      toast.error('名称不能为空');
      return;
    }
    const description = kbDescription.trim();
    const payload: { name?: string; description?: string } = {};
    if (name !== kb.name) payload.name = name;
    if (description !== (kb.description ?? '')) payload.description = description;
    if (Object.keys(payload).length === 0) return;

    void updateKb
      .mutateAsync(payload)
      .then(() => toast.success('已保存基本信息'))
      .catch((err: unknown) =>
        toast.error(err instanceof ApiError ? err.message : '保存失败'),
      );
  }

  function saveProfile() {
    if (!profileCode || !canWrite) return;
    void updateKb
      .mutateAsync({ profile_code: profileCode })
      .then(() => toast.success(`已绑定模板：${profileCode}`))
      .catch((err: unknown) =>
        toast.error(err instanceof ApiError ? err.message : '改绑失败'),
      );
  }

  function saveRules() {
    if (!kb || !canWrite) return;
    if (retrieval.top_k < 1 || retrieval.top_k > 50) {
      toast.error('召回 Top-K 须在 1–50');
      return;
    }
    if (chunk.max_tokens < 1 || chunk.min_tokens < 0 || chunk.overlap_tokens < 0) {
      toast.error('切块参数无效');
      return;
    }
    const settings = buildSettingsPayload(chunk, retrieval, rulesFromKb(kb));
    if (!settings) {
      toast.info('无变更');
      return;
    }
    void updateKb
      .mutateAsync({ settings })
      .then(() => {
        toast.success('已保存切块与召回配置');
        toast.info('已入库文档需重新解析后切块才会变化。');
      })
      .catch((err: unknown) =>
        toast.error(err instanceof ApiError ? err.message : '保存失败'),
      );
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">配置</h2>
        <p className="mt-1 text-sm text-slate-500">
          管理知识库基本信息、行业模板，以及本库对切块/召回的覆盖参数。改绑模板时会保留本库
          settings。
          {!canWrite ? ' 当前为只读权限。' : null}
        </p>
      </header>

      <section className="panel space-y-4 p-4">
        <h3 className="text-sm font-semibold text-slate-800">基础信息</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="名称"
            value={kbName}
            maxLength={200}
            disabled={!canWrite}
            onChange={(e) => setKbName(e.target.value)}
            placeholder="知识库名称"
          />
          <div className="sm:col-span-2">
            <label htmlFor="kb-settings-desc" className="mb-1.5 block text-sm font-medium text-slate-800">
              描述
            </label>
            <textarea
              id="kb-settings-desc"
              rows={3}
              className="field-input resize-y"
              value={kbDescription}
              maxLength={2000}
              disabled={!canWrite}
              placeholder="可选，简要说明该库用途"
              onChange={(e) => setKbDescription(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2 grid gap-3 sm:grid-cols-2">
            <ReadOnlyField label="嵌入模型" value={kb?.embedding_model ?? '—'} />
            <ReadOnlyField
              label="向量维度"
              value={kb?.embedding_dim != null ? String(kb.embedding_dim) : '—'}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button
            variant="secondary"
            disabled={!canWrite || !basicDirty || !kbName.trim() || updateKb.isPending}
            onClick={saveBasic}
          >
            {updateKb.isPending ? '保存中…' : '保存'}
          </Button>
        </div>
      </section>

      <section className="panel space-y-4 p-4">
        <h3 className="text-sm font-semibold text-slate-800">行业模板（摄取 / 检索）</h3>
        <div className="flex flex-wrap items-end gap-3">
          <Select
            label="模板"
            value={profileCode}
            disabled={!canWrite}
            onChange={(e) => setProfileCode(e.target.value)}
            className="min-w-[240px] flex-1"
          >
            <option value="">未绑定</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.code}>
                {p.name} ({p.code})
              </option>
            ))}
          </Select>
          <Button
            variant="secondary"
            disabled={!canWrite || !profileCode || !profileDirty || updateKb.isPending}
            onClick={saveProfile}
          >
            保存模板
          </Button>
        </div>
        <p className="text-xs text-slate-400">
          深度编辑模板默认值请前往运营 → 行业模板；本库覆盖在下方保存，改绑模板后仍保留。
        </p>
      </section>

      <section className="panel space-y-4 p-4">
        <h3 className="text-sm font-semibold text-slate-800">切块与召回（本库覆盖）</h3>
        <p className="text-xs text-slate-500">
          初始值来自当前生效规则（KB settings &gt; 模板 &gt; 默认）。保存后写入本库 settings，不自动重新解析。
        </p>

        <fieldset className="space-y-3" disabled={!canWrite}>
          <legend className="text-xs font-medium uppercase tracking-wider text-slate-400">
            切块 chunk_rules
          </legend>
          <div className="grid gap-3 sm:grid-cols-3">
            <NumField
              label="建议切块大小 (max_tokens)"
              value={chunk.max_tokens}
              min={1}
              onChange={(n) => setChunk((c) => ({ ...c, max_tokens: n }))}
            />
            <NumField
              label="最小块 (min_tokens)"
              value={chunk.min_tokens}
              min={0}
              onChange={(n) => setChunk((c) => ({ ...c, min_tokens: n }))}
            />
            <NumField
              label="重叠 (overlap_tokens)"
              value={chunk.overlap_tokens}
              min={0}
              onChange={(n) => setChunk((c) => ({ ...c, overlap_tokens: n }))}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={chunk.clause_mode}
              onChange={(e) => setChunk((c) => ({ ...c, clause_mode: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/30"
            />
            条款式分块 (clause_mode)
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={chunk.keep_heading_prefix}
              onChange={(e) =>
                setChunk((c) => ({ ...c, keep_heading_prefix: e.target.checked }))
              }
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/30"
            />
            保留标题前缀 (keep_heading_prefix)
          </label>
        </fieldset>

        <fieldset className="space-y-3" disabled={!canWrite}>
          <legend className="text-xs font-medium uppercase tracking-wider text-slate-400">
            召回 retrieval_rules
          </legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <NumField
              label="召回 Top-K"
              value={retrieval.top_k}
              min={1}
              max={50}
              onChange={(n) => setRetrieval((r) => ({ ...r, top_k: n }))}
            />
            <label className="block text-sm">
              <span className="mb-1.5 block text-slate-500">Rerank</span>
              <select
                className="field-input w-full"
                value={retrieval.rerank}
                onChange={(e) =>
                  setRetrieval((r) => ({
                    ...r,
                    rerank: e.target.value as RetrievalForm['rerank'],
                  }))
                }
              >
                <option value="default">跟随环境默认</option>
                <option value="on">强制开启</option>
                <option value="off">强制关闭</option>
              </select>
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={retrieval.query_expand}
              onChange={(e) =>
                setRetrieval((r) => ({ ...r, query_expand: e.target.checked }))
              }
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/30"
            />
            查询扩展 (query_expand)
          </label>
        </fieldset>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-400">
            已入库文档需重新解析后切块才会变化。
          </p>
          <Button
            variant="secondary"
            disabled={!canWrite || !rulesDirty || updateKb.isPending}
            onClick={saveRules}
          >
            {updateKb.isPending ? '保存中…' : '保存切块与召回'}
          </Button>
        </div>
      </section>

      {kbId ? <KbGrantsPanel kbId={kbId} /> : null}
    </div>
  );
}

function NumField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-slate-500">{label}</span>
      <input
        type="number"
        className="field-input w-full"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm text-slate-800">{value}</p>
    </div>
  );
}
