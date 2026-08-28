import { useEffect, useMemo, useState } from 'react';

import { SideSheet } from '@/components/SideSheet';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import type { DocumentItem } from '../api';

type FieldSpec = {
  key: string;
  type: 'string' | 'number' | 'boolean';
  required: boolean;
};

type Props = {
  open: boolean;
  onClose: () => void;
  document: DocumentItem | null;
  schema: Record<string, unknown>;
  saving?: boolean;
  onSave: (metadata: Record<string, unknown>) => Promise<void>;
};

function parseSchemaFields(schema: Record<string, unknown>): FieldSpec[] {
  const fields: FieldSpec[] = [];
  for (const [key, raw] of Object.entries(schema)) {
    if (!key.trim()) continue;
    const spec =
      raw && typeof raw === 'object' && !Array.isArray(raw)
        ? (raw as Record<string, unknown>)
        : {};
    const typ = typeof spec.type === 'string' ? spec.type : 'string';
    const type: FieldSpec['type'] =
      typ === 'number' || typ === 'boolean' ? typ : 'string';
    fields.push({
      key,
      type,
      required: spec.required === true,
    });
  }
  return fields;
}

function draftFromDoc(
  fields: FieldSpec[],
  meta: Record<string, unknown> | undefined,
): Record<string, string | boolean> {
  const draft: Record<string, string | boolean> = {};
  for (const f of fields) {
    const v = meta?.[f.key];
    if (f.type === 'boolean') {
      draft[f.key] = typeof v === 'boolean' ? v : false;
    } else if (f.type === 'number') {
      draft[f.key] = typeof v === 'number' && Number.isFinite(v) ? String(v) : '';
    } else {
      draft[f.key] = typeof v === 'string' ? v : '';
    }
  }
  return draft;
}

function buildPayload(
  fields: FieldSpec[],
  draft: Record<string, string | boolean>,
): { ok: true; metadata: Record<string, unknown> } | { ok: false; error: string } {
  const metadata: Record<string, unknown> = {};
  for (const f of fields) {
    const raw = draft[f.key];
    if (f.type === 'boolean') {
      metadata[f.key] = Boolean(raw);
      continue;
    }
    const text = typeof raw === 'string' ? raw.trim() : '';
    if (!text) {
      if (f.required) {
        return { ok: false, error: `请填写必填字段：${f.key}` };
      }
      continue;
    }
    if (f.type === 'number') {
      const n = Number(text);
      if (!Number.isFinite(n)) {
        return { ok: false, error: `字段 ${f.key} 须为数字` };
      }
      metadata[f.key] = n;
    } else {
      metadata[f.key] = text;
    }
  }
  return { ok: true, metadata };
}

/** 按行业 profile 的 metadata_schema 编辑文档元数据 */
export function DocumentMetaDrawer({
  open,
  onClose,
  document,
  schema,
  saving = false,
  onSave,
}: Props) {
  const fields = useMemo(() => parseSchemaFields(schema), [schema]);
  const [draft, setDraft] = useState<Record<string, string | boolean>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !document) return;
    setDraft(draftFromDoc(fields, document.metadata));
    setError(null);
  }, [open, document, fields]);

  if (fields.length === 0) return null;

  async function handleSave() {
    const result = buildPayload(fields, draft);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setError(null);
    await onSave(result.metadata);
  }

  return (
    <SideSheet
      open={open && Boolean(document)}
      onClose={onClose}
      title={document ? `元数据 · ${document.title}` : '元数据'}
    >
      <div className="flex h-full flex-col gap-4">
        <p className="text-xs text-slate-500">
          字段来自当前知识库绑定的行业模板；保存后立即生效。
        </p>
        <div className="space-y-4">
          {fields.map((f) => {
            if (f.type === 'boolean') {
              return (
                <label
                  key={f.key}
                  className="flex items-center gap-2 text-sm text-slate-700"
                >
                  <input
                    type="checkbox"
                    checked={draft[f.key] === true}
                    disabled={saving}
                    onChange={(e) =>
                      setDraft((prev) => ({ ...prev, [f.key]: e.target.checked }))
                    }
                    className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="font-mono text-xs">{f.key}</span>
                  {f.required ? <span className="text-xs text-red-500">必填</span> : null}
                </label>
              );
            }
            return (
              <Input
                key={f.key}
                id={`meta-${f.key}`}
                label={`${f.key}${f.required ? ' *' : ''}`}
                type={f.type === 'number' ? 'number' : 'text'}
                value={typeof draft[f.key] === 'string' ? (draft[f.key] as string) : ''}
                disabled={saving}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, [f.key]: e.target.value }))
                }
                placeholder={f.type === 'number' ? '数字' : undefined}
              />
            );
          })}
        </div>
        {error ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}
        <div className="mt-auto flex gap-2 border-t border-slate-100 pt-4">
          <Button
            type="button"
            className="flex-1"
            disabled={saving || !document}
            onClick={() => void handleSave()}
          >
            {saving ? '保存中…' : '保存'}
          </Button>
          <Button variant="secondary" type="button" disabled={saving} onClick={onClose}>
            取消
          </Button>
        </div>
      </div>
    </SideSheet>
  );
}
