import { useState, type FormEvent } from 'react';

import { ApiError } from '@/lib/http';
import type { IndustryProfile } from './api';
import {
  applyRerankSelect,
  boolField,
  draftFromJson,
  draftFromProfile,
  draftToJson,
  numField,
  rerankSelectValue,
  strField,
  toUpdateBody,
  type ProfileDraft,
} from './formModel';
import { useUpdateProfile } from './hooks';

type Tab = 'form' | 'json';

export function ProfileEditor({
  profile,
  onClose,
  onSaved,
}: {
  profile: IndustryProfile;
  onClose: () => void;
  onSaved?: () => void;
}) {
  const updateM = useUpdateProfile();
  const [tab, setTab] = useState<Tab>('form');
  const [draft, setDraft] = useState<ProfileDraft>(() => draftFromProfile(profile));
  const [jsonText, setJsonText] = useState(() => draftToJson(draftFromProfile(profile)));
  const [error, setError] = useState<string | null>(null);

  function patchChunk(key: string, value: unknown) {
    setDraft((d) => ({ ...d, chunk_rules: { ...d.chunk_rules, [key]: value } }));
  }

  function switchTab(next: Tab) {
    setError(null);
    if (next === tab) return;
    if (next === 'json') {
      setJsonText(draftToJson(draft));
      setTab('json');
      return;
    }
    // json → form
    try {
      setDraft(draftFromJson(jsonText, draft.name));
      setTab('form');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'JSON 无法解析，请修正后再切换');
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    let payload = draft;
    if (tab === 'json') {
      try {
        payload = draftFromJson(jsonText, draft.name);
        setDraft(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'JSON 无法解析');
        return;
      }
    }
    try {
      await updateM.mutateAsync({ id: profile.id, body: toUpdateBody(payload) });
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '保存失败');
    }
  }

  return (
    <form onSubmit={(e) => void onSave(e)} className="panel space-y-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">编辑 {profile.code}</h2>
        <div className="flex gap-0.5 border-b border-line">
          {(
            [
              ['form', '表单'],
              ['json', 'JSON'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => switchTab(id)}
              className={[
                '-mb-px border-b-2 px-3 py-1.5 text-sm transition-colors',
                tab === id
                  ? 'border-brand-600 font-medium text-brand-700'
                  : 'border-transparent text-ink-muted hover:text-ink',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error ? <p className="text-sm text-danger">{error}</p> : null}

      {tab === 'form' ? (
        <div className="space-y-5">
          <label className="block text-xs text-ink-muted">
            名称
            <input
              className="field-input mt-1"
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            />
          </label>

          <fieldset className="space-y-3">
            <legend className="text-xs font-medium uppercase tracking-wider text-ink-faint">
              分块 chunk_rules
            </legend>
            <div className="grid gap-3 sm:grid-cols-3">
              <NumField
                label="max_tokens"
                value={numField(draft.chunk_rules, 'max_tokens', 512)}
                onChange={(n) => patchChunk('max_tokens', n)}
              />
              <NumField
                label="min_tokens"
                value={numField(draft.chunk_rules, 'min_tokens', 80)}
                onChange={(n) => patchChunk('min_tokens', n)}
              />
              <NumField
                label="overlap_tokens"
                value={numField(draft.chunk_rules, 'overlap_tokens', 64)}
                onChange={(n) => patchChunk('overlap_tokens', n)}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={boolField(draft.chunk_rules, 'clause_mode', false)}
                onChange={(e) => patchChunk('clause_mode', e.target.checked)}
              />
              clause_mode（条款模式）
            </label>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={boolField(draft.chunk_rules, 'keep_heading_prefix', true)}
                onChange={(e) => patchChunk('keep_heading_prefix', e.target.checked)}
              />
              keep_heading_prefix
            </label>
          </fieldset>

          <fieldset className="space-y-3">
            <legend className="text-xs font-medium uppercase tracking-wider text-ink-faint">
              检索 retrieval_rules
            </legend>
            <div className="grid gap-3 sm:grid-cols-2">
              <NumField
                label="top_k"
                value={numField(draft.retrieval_rules, 'top_k', 8)}
                min={1}
                max={50}
                onChange={(n) =>
                  setDraft((d) => ({
                    ...d,
                    retrieval_rules: { ...d.retrieval_rules, top_k: n },
                  }))
                }
              />
              <label className="block text-xs text-ink-muted">
                rerank_enabled
                <select
                  className="field-input mt-1"
                  value={rerankSelectValue(draft.retrieval_rules)}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      retrieval_rules: applyRerankSelect(
                        d.retrieval_rules,
                        e.target.value as 'default' | 'on' | 'off',
                      ),
                    }))
                  }
                >
                  <option value="default">跟随环境默认</option>
                  <option value="on">强制开启</option>
                  <option value="off">强制关闭</option>
                </select>
              </label>
            </div>
          </fieldset>

          <label className="block text-xs text-ink-muted">
            system prompt（prompt_overrides.system）
            <textarea
              className="field-input mt-1 min-h-[120px]"
              rows={5}
              value={strField(draft.prompt_overrides, 'system')}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  prompt_overrides: {
                    ...d.prompt_overrides,
                    system: e.target.value || null,
                  },
                }))
              }
              placeholder="留空则使用平台默认 SYSTEM_PROMPT"
            />
          </label>
          <p className="text-xs text-ink-faint">
            parse_rules / metadata_schema 等请在 JSON 视图编辑。
          </p>
        </div>
      ) : (
        <label className="block text-xs text-ink-muted">
          规则 JSON
          <textarea
            className="field-input mt-1 font-mono text-xs"
            rows={18}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            spellCheck={false}
          />
        </label>
      )}

      <div className="flex gap-2">
        <button type="submit" disabled={updateM.isPending} className="btn-primary">
          {updateM.isPending ? '保存中…' : '保存'}
        </button>
        <button type="button" className="btn-ghost" onClick={onClose}>
          取消
        </button>
      </div>
    </form>
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
    <label className="block text-xs text-ink-muted">
      {label}
      <input
        type="number"
        className="field-input mt-1"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}
