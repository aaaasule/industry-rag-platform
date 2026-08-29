import { CloudUpload, Plus, Search } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { IngestProgress } from '@/components/IngestProgress';
import { Skeleton } from '@/components/Skeleton';
import { DocumentStatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/toast/useToast';
import { BATCH_DOCUMENTS_MAX, IN_PROGRESS, type DocumentItem } from '../api';
import {
  useBatchDocuments,
  useDeleteDocument,
  useDocuments,
  useKnowledgeBase,
  usePatchDocument,
  useProfiles,
  useReingest,
  useUploadDocument,
} from '../hooks';
import { DocumentMetaDrawer } from './DocumentMetaDrawer';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function KbFilesPanel() {
  const { kbId = '' } = useParams();
  const toast = useToast();
  const { data: kb } = useKnowledgeBase(kbId);
  const canWrite = kb?.my_permission === 'write' || kb?.my_permission === 'manage';
  const { data: profiles = [] } = useProfiles();
  const { data: docs = [], isLoading } = useDocuments(kbId);
  const upload = useUploadDocument(kbId);
  const reingest = useReingest(kbId);
  const remove = useDeleteDocument(kbId);
  const patchDoc = usePatchDocument(kbId);
  const batch = useBatchDocuments(kbId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [query, setQuery] = useState('');
  const [expandedErrorId, setExpandedErrorId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [metaDoc, setMetaDoc] = useState<DocumentItem | null>(null);

  const metadataSchema = useMemo(() => {
    if (!kb?.profile_id) return {};
    const profile = profiles.find((p) => p.id === kb.profile_id);
    const schema = profile?.metadata_schema;
    return schema && typeof schema === 'object' && !Array.isArray(schema) ? schema : {};
  }, [kb?.profile_id, profiles]);

  const hasMetaSchema = Object.keys(metadataSchema).length > 0;

  useEffect(() => {
    setSelected(new Set());
  }, [kbId]);

  useEffect(() => {
    const ids = new Set(docs.map((d) => d.id));
    setSelected((prev) => {
      let changed = false;
      const next = new Set<string>();
      for (const id of prev) {
        if (ids.has(id)) next.add(id);
        else changed = true;
      }
      return changed || next.size !== prev.size ? next : prev;
    });
  }, [docs]);

  const onFiles = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      for (const file of list) {
        try {
          await upload.mutateAsync({ file });
          toast.success(`已提交上传：${file.name}`);
        } catch (err) {
          toast.error(err instanceof Error ? err.message : '上传失败');
        }
      }
    },
    [toast, upload],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return docs;
    return docs.filter((d) => d.title.toLowerCase().includes(q));
  }, [docs, query]);

  const filteredIds = useMemo(() => filtered.map((d) => d.id), [filtered]);
  const allFilteredSelected =
    filteredIds.length > 0 && filteredIds.every((id) => selected.has(id));
  const someFilteredSelected = filteredIds.some((id) => selected.has(id));
  const selectedCount = selected.size;
  const batchBusy = batch.isPending;

  const inProgressCount = docs.filter((d) => IN_PROGRESS.has(d.status)).length;
  const failedCount = docs.filter((d) => d.status === 'failed').length;
  const totalBytes = docs.reduce((sum, d) => sum + (d.file_size ?? 0), 0);

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAllFiltered() {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allFilteredSelected) {
        for (const id of filteredIds) next.delete(id);
      } else {
        for (const id of filteredIds) next.add(id);
      }
      return next;
    });
  }

  async function onBatchReingest() {
    const ids = [...selected];
    if (ids.length === 0) return;
    if (ids.length > BATCH_DOCUMENTS_MAX) {
      toast.error(`单次最多选择 ${BATCH_DOCUMENTS_MAX} 个文档`);
      return;
    }
    try {
      const res = await batch.mutateAsync({ action: 'reingest', document_ids: ids });
      toast.success(`已提交重新解析：${res.accepted} 个文档`);
      setSelected(new Set());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '批量重新解析失败');
    }
  }

  async function onBatchDelete() {
    const ids = [...selected];
    if (ids.length === 0) return;
    if (ids.length > BATCH_DOCUMENTS_MAX) {
      toast.error(`单次最多选择 ${BATCH_DOCUMENTS_MAX} 个文档`);
      return;
    }
    if (!confirm(`确认删除选中的 ${ids.length} 个文档？此操作不可撤销。`)) return;
    try {
      const res = await batch.mutateAsync({ action: 'delete', document_ids: ids });
      toast.success(`已删除 ${res.accepted} 个文档`);
      setSelected(new Set());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '批量删除失败');
    }
  }

  async function onToggleEnabled(docId: string, enabled: boolean, title: string) {
    setTogglingId(docId);
    try {
      await patchDoc.mutateAsync({ docId, payload: { enabled } });
      toast.success(enabled ? `已启用：${title}` : `已禁用：${title}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '更新启用状态失败');
    } finally {
      setTogglingId(null);
    }
  }

  async function onSaveMetadata(metadata: Record<string, unknown>) {
    if (!metaDoc) return;
    try {
      await patchDoc.mutateAsync({ docId: metaDoc.id, payload: { metadata } });
      toast.success(`已保存元数据：${metaDoc.title}`);
      setMetaDoc(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存元数据失败');
    }
  }

  const colSpan = 8;

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">文件列表</h2>
        <p className="mt-1 text-sm text-slate-500">
          上传文档并完成解析后，方可用于检索与问答。禁用后列表仍可见，但不会参与检索与问答。
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="panel p-4">
          <p className="text-xs font-medium text-slate-400">文件总数</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
            {kb?.doc_count ?? docs.length}
          </p>
          <p className="mt-1 text-xs text-slate-500">合计约 {formatBytes(totalBytes)}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs font-medium text-slate-400">正在处理</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-600">
            {inProgressCount}
          </p>
          <p className="mt-1 text-xs text-slate-500">解析 / 分块 / 向量化</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs font-medium text-slate-400">解析失败</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-red-600">{failedCount}</p>
          <p className="mt-1 text-xs text-slate-500">可重试或删除后重新上传</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative min-w-[200px] flex-1 max-w-md">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            strokeWidth={1.5}
            aria-hidden
          />
          <input
            type="search"
            placeholder="搜索文件名…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="field-input w-full pl-9"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canWrite && selectedCount > 0 ? (
            <>
              <span className="text-xs text-slate-500">已选 {selectedCount}</span>
              <Button
                variant="secondary"
                className="!px-3 !py-1.5 text-xs"
                disabled={batchBusy}
                onClick={() => void onBatchReingest()}
              >
                重新解析
              </Button>
              <Button
                variant="danger"
                className="!px-3 !py-1.5 text-xs"
                disabled={batchBusy}
                onClick={() => void onBatchDelete()}
              >
                删除
              </Button>
            </>
          ) : null}
          <Button
            onClick={() => inputRef.current?.click()}
            disabled={!canWrite || upload.isPending}
          >
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            新增文件
          </Button>
        </div>
      </div>

      <div
        role="button"
        tabIndex={canWrite ? 0 : -1}
        onKeyDown={(e) => {
          if (!canWrite) return;
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
        onDragOver={(e) => {
          if (!canWrite) return;
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (!canWrite) return;
          if (e.dataTransfer.files.length) void onFiles(e.dataTransfer.files);
        }}
        onClick={() => {
          if (canWrite) inputRef.current?.click();
        }}
        className={[
          'panel border-2 border-dashed p-8 text-center transition-all duration-150',
          canWrite ? 'cursor-pointer' : 'cursor-not-allowed opacity-50',
          dragOver
            ? 'border-indigo-400 bg-indigo-50'
            : canWrite
              ? 'border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40'
              : 'border-slate-200',
          upload.isPending ? 'pointer-events-none opacity-70' : '',
        ].join(' ')}
      >
        <span className="mx-auto inline-flex rounded-full bg-indigo-50 p-3 text-indigo-600">
          <CloudUpload className="h-6 w-6" strokeWidth={1.5} />
        </span>
        <p className="mt-3 text-sm font-medium text-slate-800">
          {!canWrite
            ? '仅管理员可上传文件'
            : upload.isPending
              ? '上传中…'
              : '拖拽文件到此处，或点击选择（支持多选）'}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          PDF / Word / Excel / PPT / Markdown / TXT，单文件 ≤ 32MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.xlsx,.pptx,.md,.markdown,.txt,application/pdf,text/plain,text/markdown"
          className="hidden"
          multiple
          onChange={(e) => {
            if (e.target.files?.length) void onFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </div>

      <section className="table-scroll panel">
        <table className="w-full text-left text-sm">
          <thead className="text-xs font-medium text-slate-400">
            <tr>
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  aria-label="全选当前列表"
                  checked={allFilteredSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someFilteredSelected && !allFilteredSelected;
                  }}
                  onChange={toggleAllFiltered}
                  disabled={filteredIds.length === 0}
                  className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
              <th className="px-4 py-3">名称</th>
              <th className="px-4 py-3">上传时间</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">页数</th>
              <th className="px-4 py-3">分块数</th>
              <th className="px-4 py-3">启用</th>
              <th className="px-4 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 3 }, (_, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td colSpan={colSpan} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))}
            {!isLoading && filtered.length === 0 ? (
              <tr>
                <td colSpan={colSpan}>
                  <EmptyState
                    compact
                    title={query ? '无匹配文件' : '暂无文档'}
                    description={
                      query ? '尝试其他关键词' : '上传文档后将显示在此列表'
                    }
                  />
                </td>
              </tr>
            ) : null}
            {filtered.map((doc) => {
              const failed = doc.status === 'failed';
              const detailExpanded = expandedErrorId === doc.id;
              const enabled = doc.enabled !== false;
              const switchBusy = togglingId === doc.id;
              return (
                <tr
                  key={doc.id}
                  className={[
                    'border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50/80',
                    failed ? 'bg-red-50/40' : '',
                    !enabled ? 'opacity-75' : '',
                  ].join(' ')}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label={`选择 ${doc.title}`}
                      checked={selected.has(doc.id)}
                      onChange={() => toggleOne(doc.id)}
                      className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </td>
                  <td className="max-w-md px-4 py-3">
                    <Link
                      to={`/knowledge/${kbId}/documents/${doc.id}`}
                      title={doc.title}
                      className="block truncate font-medium text-slate-800 hover:text-indigo-600 hover:underline"
                    >
                      {doc.title}
                    </Link>
                    {failed && doc.error_detail ? (
                      <div className="mt-1.5 max-w-lg">
                        <p
                          className={[
                            'text-xs text-red-600',
                            detailExpanded ? 'whitespace-pre-wrap break-words' : 'truncate',
                          ].join(' ')}
                        >
                          {doc.error_detail}
                        </p>
                        {doc.error_detail.length > 48 ? (
                          <button
                            type="button"
                            className="mt-0.5 text-[11px] text-slate-500 hover:text-indigo-600"
                            onClick={() =>
                              setExpandedErrorId((id) => (id === doc.id ? null : doc.id))
                            }
                          >
                            {detailExpanded ? '收起' : '详情'}
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                    {new Date(doc.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <DocumentStatusBadge status={doc.status} />
                    <IngestProgress status={doc.status} errorCode={doc.error_code} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-slate-500">
                    {doc.page_count ?? '—'}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-slate-500">
                    {doc.chunk_count ?? 0}
                  </td>
                  <td className="px-4 py-3">
                    <label
                      className={[
                        'relative inline-flex h-5 w-9 items-center',
                        !canWrite || switchBusy
                          ? 'cursor-not-allowed opacity-40'
                          : 'cursor-pointer',
                      ].join(' ')}
                      title={
                        !canWrite
                          ? '仅管理员可修改启用状态'
                          : enabled
                            ? '禁用后不参与检索'
                            : '启用以参与检索'
                      }
                    >
                      <input
                        type="checkbox"
                        role="switch"
                        aria-label={enabled ? `禁用 ${doc.title}` : `启用 ${doc.title}`}
                        checked={enabled}
                        disabled={!canWrite || switchBusy}
                        onChange={(e) => {
                          void onToggleEnabled(doc.id, e.target.checked, doc.title);
                        }}
                        className="peer sr-only"
                      />
                      <span
                        className={[
                          'absolute inset-0 rounded-full transition-colors',
                          !canWrite
                            ? 'bg-slate-200'
                            : enabled
                              ? 'bg-indigo-500'
                              : 'bg-slate-300',
                        ].join(' ')}
                      />
                      <span
                        className={[
                          'absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform',
                          enabled ? 'translate-x-4' : 'translate-x-0',
                        ].join(' ')}
                      />
                    </label>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {canWrite && hasMetaSchema ? (
                        <button
                          type="button"
                          className="text-xs text-indigo-600 hover:underline"
                          onClick={() => setMetaDoc(doc)}
                        >
                          元数据
                        </button>
                      ) : null}
                      {failed ? (
                        <Button
                          className="!px-2.5 !py-1 text-xs"
                          disabled={reingest.isPending}
                          onClick={() => {
                            void reingest
                              .mutateAsync(doc.id)
                              .then(() => toast.info(`已重新提交：${doc.title}`))
                              .catch((err: unknown) =>
                                toast.error(err instanceof Error ? err.message : '重试失败'),
                              );
                          }}
                        >
                          重试
                        </Button>
                      ) : null}
                      <button
                        type="button"
                        className="text-xs text-slate-400 hover:text-red-600"
                        disabled={remove.isPending}
                        onClick={() => {
                          if (!confirm(`删除「${doc.title}」？`)) return;
                          void remove
                            .mutateAsync(doc.id)
                            .then(() => toast.success(`已删除：${doc.title}`))
                            .catch((err: unknown) =>
                              toast.error(err instanceof Error ? err.message : '删除失败'),
                            );
                        }}
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <DocumentMetaDrawer
        open={Boolean(metaDoc)}
        onClose={() => setMetaDoc(null)}
        document={metaDoc}
        schema={metadataSchema}
        saving={patchDoc.isPending}
        onSave={onSaveMetadata}
      />
    </div>
  );
}
