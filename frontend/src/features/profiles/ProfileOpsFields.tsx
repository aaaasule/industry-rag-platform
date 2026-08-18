type Props = {
  parseRules: Record<string, unknown>;
  metadataSchema: Record<string, unknown>;
  onParseRules: (next: Record<string, unknown>) => void;
  onMetadataSchema: (next: Record<string, unknown>) => void;
};

const TYPES = ['string', 'number', 'boolean'] as const;

export function ProfileOpsFields({
  parseRules,
  metadataSchema,
  onParseRules,
  onMetadataSchema,
}: Props) {
  const dictionary = arrayOfStrings(parseRules.dictionary).join('\n');
  const synonyms = Object.entries(asStringMap(parseRules.synonyms));
  const fields = Object.entries(metadataSchema);

  return (
    <div className="space-y-5">
      <label className="block text-xs text-ink-muted">
        术语表（一行一词，写入 jieba 用户词典）
        <textarea
          className="field-input mt-1 min-h-[88px] font-mono text-xs"
          rows={4}
          value={dictionary}
          onChange={(e) =>
            onParseRules({
              ...parseRules,
              dictionary: e.target.value
                .split('\n')
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
          placeholder={'液压缸座总成\nHYD-2201'}
        />
      </label>

      <fieldset className="space-y-2">
        <legend className="text-xs font-medium text-ink-muted">同义词（查询侧替换）</legend>
        {synonyms.map(([alias, canonical], i) => (
          <div key={`syn-${i}`} className="flex gap-2">
            <input
              className="field-input flex-1"
              placeholder="别名，如 泵浦"
              value={alias}
              onChange={(e) => onParseRules({ ...parseRules, synonyms: rowsToMap(replacePair(synonyms, i, e.target.value, canonical)) })}
            />
            <span className="self-center text-ink-faint">→</span>
            <input
              className="field-input flex-1"
              placeholder="规范词，如 泵"
              value={canonical}
              onChange={(e) => onParseRules({ ...parseRules, synonyms: rowsToMap(replacePair(synonyms, i, alias, e.target.value)) })}
            />
            <button
              type="button"
              className="btn-ghost shrink-0 text-xs"
              onClick={() => onParseRules({ ...parseRules, synonyms: rowsToMap(synonyms.filter((_, j) => j !== i)) })}
            >
              删
            </button>
          </div>
        ))}
        <button
          type="button"
          className="text-xs text-brand-700 hover:underline"
          onClick={() => onParseRules({ ...parseRules, synonyms: rowsToMap([...synonyms, ['', '']]) })}
        >
          + 添加同义词
        </button>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-xs font-medium text-ink-muted">文档元数据字段</legend>
        {fields.map(([key, spec], i) => {
          const s = spec && typeof spec === 'object' && !Array.isArray(spec) ? (spec as Record<string, unknown>) : {};
          const typ = typeof s.type === 'string' ? s.type : 'string';
          const required = s.required === true;
          return (
            <div key={`meta-${i}`} className="flex flex-wrap items-center gap-2">
              <input
                className="field-input min-w-[8rem] flex-1 font-mono"
                placeholder="字段名"
                value={key}
                onChange={(e) => onMetadataSchema(replaceMetaKey(metadataSchema, key, e.target.value, s))}
              />
              <select
                className="field-input w-28"
                value={TYPES.includes(typ as (typeof TYPES)[number]) ? typ : 'string'}
                onChange={(e) =>
                  onMetadataSchema({
                    ...metadataSchema,
                    [key]: { ...s, type: e.target.value },
                  })
                }
              >
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-1 text-xs text-ink-muted">
                <input
                  type="checkbox"
                  checked={required}
                  onChange={(e) =>
                    onMetadataSchema({
                      ...metadataSchema,
                      [key]: { ...s, required: e.target.checked },
                    })
                  }
                />
                必填
              </label>
              <button
                type="button"
                className="btn-ghost text-xs"
                onClick={() => {
                  const next = { ...metadataSchema };
                  delete next[key];
                  onMetadataSchema(next);
                }}
              >
                删
              </button>
            </div>
          );
        })}
        <button
          type="button"
          className="text-xs text-brand-700 hover:underline"
          onClick={() => {
            const name = unusedKey(metadataSchema);
            onMetadataSchema({ ...metadataSchema, [name]: { type: 'string', required: false } });
          }}
        >
          + 添加字段
        </button>
      </fieldset>
    </div>
  );
}

function arrayOfStrings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((x): x is string => typeof x === 'string');
}

function asStringMap(value: unknown): Record<string, string> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (typeof v === 'string') out[k] = v;
  }
  return out;
}

function replacePair(
  rows: [string, string][],
  index: number,
  alias: string,
  canonical: string,
): [string, string][] {
  return rows.map((row, i) => (i === index ? [alias, canonical] : row));
}

function rowsToMap(rows: [string, string][]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [alias, canonical] of rows) {
    const src = alias.trim();
    if (!src) continue;
    out[src] = canonical.trim();
  }
  return out;
}

function replaceMetaKey(
  schema: Record<string, unknown>,
  oldKey: string,
  nextKey: string,
  spec: Record<string, unknown>,
): Record<string, unknown> {
  const next: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(schema)) {
    if (k === oldKey) next[nextKey] = spec;
    else next[k] = v;
  }
  return next;
}

function unusedKey(schema: Record<string, unknown>): string {
  let i = 1;
  while (`field_${i}` in schema) i += 1;
  return `field_${i}`;
}
