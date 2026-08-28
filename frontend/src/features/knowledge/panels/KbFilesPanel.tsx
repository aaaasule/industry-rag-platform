import { CloudUpload, Plus, Search } from 'lucide-react';
import { useCallback, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { IngestProgress } from '@/components/IngestProgress';
import { Skeleton } from '@/components/Skeleton';
import { DocumentStatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/toast/useToast';
import { IN_PROGRESS } from '../api';
import {
  useDeleteDocument,
  useDocuments,
  useKnowledgeBase,
  useReingest,
  useUploadDocument,
} from '../hooks';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function KbFilesPanel() {
  const { kbId = '' } = useParams();
  const toast = useToast();
  const { data: kb } = useKnowledgeBase(kbId);
  const { data: docs = [], isLoading } = useDocuments(kbId);
  const upload = useUploadDocument(kbId);
  const reingest = useReingest(kbId);
  const remove = useDeleteDocument(kbId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [query, setQuery] = useState('');
  const [expandedErrorId, setExpandedErrorId] = useState<string | null>(null);

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

  const inProgressCount = docs.filter((d) => IN_PROGRESS.has(d.status)).length;
  const failedCount = docs.filter((d) => d.status === 'failed').length;
  const totalBytes = docs.reduce((sum, d) => sum + (d.file_size ?? 0), 0);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">文件列表</h2>
        <p className="mt-1 text-sm text-slate-500">
          上传文档并完成解析后，方可用于检索与问答。
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
        <Button onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
          <Plus className="h-4 w-4" strokeWidth={1.5} />
          新增文件
        </Button>
      </div>

      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files.length) void onFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={[
          'panel cursor-pointer border-2 border-dashed p-8 text-center transition-all duration-150',
          dragOver
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40',
          upload.isPending ? 'pointer-events-none opacity-70' : '',
        ].join(' ')}
      >
        <span className="mx-auto inline-flex rounded-full bg-indigo-50 p-3 text-indigo-600">
          <CloudUpload className="h-6 w-6" strokeWidth={1.5} />
        </span>
        <p className="mt-3 text-sm font-medium text-slate-800">
          {upload.isPending ? '上传中…' : '拖拽文件到此处，或点击选择（支持多选）'}
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
              <th className="px-4 py-3">名称</th>
              <th className="px-4 py-3">上传时间</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">页数</th>
              <th className="px-4 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 3 }, (_, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td colSpan={5} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))}
            {!isLoading && filtered.length === 0 ? (
              <tr>
                <td colSpan={5}>
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
              return (
                <tr
                  key={doc.id}
                  className={[
                    'border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50/80',
                    failed ? 'bg-red-50/40' : '',
                  ].join(' ')}
                >
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
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
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
    </div>
  );
}
