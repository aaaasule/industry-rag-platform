import type { IndustryProfile } from './api';

/** 编辑草稿：整包规则，表单只改常用键，其余键保留。 */
export type ProfileDraft = {
  name: string;
  chunk_rules: Record<string, unknown>;
  prompt_overrides: Record<string, unknown>;
  retrieval_rules: Record<string, unknown>;
  parse_rules: Record<string, unknown>;
  metadata_schema: Record<string, unknown>;
};

const CHUNK_DEFAULTS = {
  max_tokens: 512,
  min_tokens: 80,
  overlap_tokens: 64,
  clause_mode: false,
  keep_heading_prefix: true,
} as const;

export function draftFromProfile(p: IndustryProfile): ProfileDraft {
  return {
    name: p.name,
    chunk_rules: { ...CHUNK_DEFAULTS, ...(p.chunk_rules ?? {}) },
    prompt_overrides: { ...(p.prompt_overrides ?? {}) },
    retrieval_rules: { top_k: 8, ...(p.retrieval_rules ?? {}) },
    parse_rules: { ...(p.parse_rules ?? {}) },
    metadata_schema: { ...(p.metadata_schema ?? {}) },
  };
}

export function draftToJson(d: ProfileDraft): string {
  return JSON.stringify(
    {
      chunk_rules: d.chunk_rules,
      prompt_overrides: d.prompt_overrides,
      retrieval_rules: d.retrieval_rules,
      parse_rules: d.parse_rules,
      metadata_schema: d.metadata_schema,
    },
    null,
    2,
  );
}

export function draftFromJson(text: string, name: string): ProfileDraft {
  const parsed = JSON.parse(text) as Record<string, unknown>;
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('根节点必须是对象');
  }
  return {
    name,
    chunk_rules: asObj(parsed.chunk_rules, CHUNK_DEFAULTS),
    prompt_overrides: asObj(parsed.prompt_overrides, {}),
    retrieval_rules: asObj(parsed.retrieval_rules, { top_k: 8 }),
    parse_rules: asObj(parsed.parse_rules, {}),
    metadata_schema: asObj(parsed.metadata_schema, {}),
  };
}

function asObj(value: unknown, fallback: Record<string, unknown>): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return { ...fallback, ...(value as Record<string, unknown>) };
  }
  return { ...fallback };
}

export function numField(obj: Record<string, unknown>, key: string, fallback: number): number {
  const v = obj[key];
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback;
}

export function boolField(obj: Record<string, unknown>, key: string, fallback: boolean): boolean {
  const v = obj[key];
  return typeof v === 'boolean' ? v : fallback;
}

export function strField(obj: Record<string, unknown>, key: string): string {
  const v = obj[key];
  return typeof v === 'string' ? v : '';
}

/** rerank：null=跟随环境，true/false=强制 */
export function rerankSelectValue(obj: Record<string, unknown>): 'default' | 'on' | 'off' {
  const v = obj.rerank_enabled;
  if (v === true) return 'on';
  if (v === false) return 'off';
  return 'default';
}

export function applyRerankSelect(
  obj: Record<string, unknown>,
  value: 'default' | 'on' | 'off',
): Record<string, unknown> {
  const next = { ...obj };
  if (value === 'default') {
    delete next.rerank_enabled;
  } else {
    next.rerank_enabled = value === 'on';
  }
  return next;
}

export function toUpdateBody(d: ProfileDraft) {
  return {
    name: d.name.trim() || d.name,
    chunk_rules: d.chunk_rules,
    prompt_overrides: d.prompt_overrides,
    retrieval_rules: d.retrieval_rules,
    parse_rules: d.parse_rules,
    metadata_schema: d.metadata_schema,
  };
}
