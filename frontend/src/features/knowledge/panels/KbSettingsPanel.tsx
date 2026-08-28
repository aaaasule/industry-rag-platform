import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/toast/useToast';
import { ApiError } from '@/lib/http';
import { KbGrantsPanel } from '../KbGrantsPanel';
import {
  useKnowledgeBase,
  useProfiles,
  useUpdateKnowledgeBase,
} from '../hooks';

function readNum(obj: Record<string, unknown> | undefined, key: string, fallback: string): string {
  const v = obj?.[key];
  if (typeof v === 'number') return String(v);
  if (typeof v === 'boolean') return v ? '是' : '否';
  return fallback;
}

export function KbSettingsPanel() {
  const { kbId = '' } = useParams();
  const toast = useToast();
  const { data: kb } = useKnowledgeBase(kbId);
  const { data: profiles = [] } = useProfiles();
  const updateKb = useUpdateKnowledgeBase(kbId);

  const [kbName, setKbName] = useState('');
  const [kbDescription, setKbDescription] = useState('');
  const [profileCode, setProfileCode] = useState('');

  useEffect(() => {
    if (!kb) return;
    setKbName(kb.name);
    setKbDescription(kb.description ?? '');
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed on kb.id
  }, [kb?.id]);

  useEffect(() => {
    if (!kb?.profile_id) {
      setProfileCode('');
      return;
    }
    const match = profiles.find((p) => p.id === kb.profile_id);
    setProfileCode(match?.code ?? '');
  }, [kb?.profile_id, profiles]);

  const boundProfile = useMemo(
    () => profiles.find((p) => p.id === kb?.profile_id),
    [profiles, kb?.profile_id],
  );

  const basicDirty =
    kb != null &&
    (kbName.trim() !== kb.name || kbDescription.trim() !== (kb.description ?? ''));

  const profileDirty =
    kb != null && profileCode !== '' && profiles.find((p) => p.id === kb.profile_id)?.code !== profileCode;

  function saveBasic() {
    if (!kb) return;
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
    if (!profileCode) return;
    void updateKb
      .mutateAsync({ profile_code: profileCode })
      .then(() => toast.success(`已绑定模板：${profileCode}`))
      .catch((err: unknown) =>
        toast.error(err instanceof ApiError ? err.message : '改绑失败'),
      );
  }

  const chunk = boundProfile?.chunk_rules;
  const retrieval = boundProfile?.retrieval_rules;

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">配置</h2>
        <p className="mt-1 text-sm text-slate-500">
          管理知识库基本信息与行业模板。切块/检索细则由模板定义；深度编辑请前往运营 → 行业模板。
        </p>
      </header>

      <section className="panel space-y-4 p-4">
        <h3 className="text-sm font-semibold text-slate-800">基础信息</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="名称"
            value={kbName}
            maxLength={200}
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
            disabled={!basicDirty || !kbName.trim() || updateKb.isPending}
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
            disabled={!profileCode || !profileDirty || updateKb.isPending}
            onClick={saveProfile}
          >
            保存模板
          </Button>
        </div>

        {boundProfile ? (
          <div className="grid gap-3 rounded-lg border border-slate-100 bg-slate-50/80 p-4 sm:grid-cols-2 lg:grid-cols-3">
            <ReadOnlyField label="建议切块大小 (tokens)" value={readNum(chunk, 'max_tokens', '512')} />
            <ReadOnlyField label="重叠 (tokens)" value={readNum(chunk, 'overlap_tokens', '64')} />
            <ReadOnlyField label="条款式分块" value={readNum(chunk, 'clause_mode', '否')} />
            <ReadOnlyField label="召回 Top-K" value={readNum(retrieval, 'top_k', '8')} />
            <ReadOnlyField
              label="Rerank"
              value={
                retrieval?.rerank_enabled === true
                  ? '开'
                  : retrieval?.rerank_enabled === false
                    ? '关'
                    : '跟随环境默认'
              }
            />
            <ReadOnlyField label="模板 code" value={boundProfile.code} />
          </div>
        ) : (
          <p className="text-sm text-slate-500">绑定行业模板后可查看切块与检索规则摘要。</p>
        )}

        <p className="text-xs text-slate-400">
          参考 UI 中的 PDF 解析器、PageIndex、知识图谱、RAPTOR 等能力尚未在本平台实现，见设计书「非目标」。
        </p>
      </section>

      {kbId ? <KbGrantsPanel kbId={kbId} /> : null}
    </div>
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
