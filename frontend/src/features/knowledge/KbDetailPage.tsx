import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { IngestProgress } from '@/components/IngestProgress';
import { Skeleton } from '@/components/Skeleton';
import { DocumentStatusBadge } from '@/components/StatusBadge';
import { useToast } from '@/components/toast/useToast';
import { ApiError } from '@/lib/http';
import { IN_PROGRESS } from './api';
import {
  useDeleteDocument,
  useDocuments,
  useKnowledgeBase,
  useProfiles,
  useReingest,
  useUpdateKnowledgeBase,
  useUploadDocument,
} from './hooks';
import { KbGrantsPanel } from './KbGrantsPanel';
export function KbDetailPage() {
  const { kbId = '' } = useParams();
  const toast = useToast();
  const { data: kb } = useKnowledgeBase(kbId);
  const { data: profiles = [] } = useProfiles();
  const { data: docs = [], isLoading } = useDocuments(kbId);
  const upload = useUploadDocument(kbId);
  const updateKb = useUpdateKnowledgeBase(kbId);
  const reingest = useReingest(kbId);
  const remove = useDeleteDocument(kbId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [profileCode, setProfileCode] = useState('');
  const [expandedErrorId, setExpandedErrorId] = useState<string | null>(null);

  useEffect(() => {
    if (!kb?.profile_id) {
      setProfileCode('');
      return;
    }
    const match = profiles.find((p) => p.id === kb.profile_id);
    setProfileCode(match?.code ?? '');
  }, [kb?.profile_id, profiles]);

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

  const inProgressCount = docs.filter((d) => IN_PROGRESS.has(d.status)).length;

  return (
    <div className="page-shell space-y-6">
      <div>
        <Link to="/knowledge" className="text-sm text-ink-muted transition-colors hover:text-ink">
          ← 知识库
        </Link>
        <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
          {kb?.name ?? '知识库'}
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          {kb ? `${kb.doc_count} 文档 · ${kb.chunk_count} 分块` : '加载中…'}
          {inProgressCount > 0 ? (
            <span className="ml-2 text-warn">· {inProgressCount} 个摄取中</span>
          ) : null}
        </p>
      </div>

      <section className="flex flex-wrap items-end gap-3 rounded-md border border-line/80 bg-canvas/50 px-4 py-3">
        <label className="block text-xs text-ink-muted">
          行业模板
          <select
            value={profileCode}
            onChange={(e) => setProfileCode(e.target.value)}
            className="field-input mt-1 min-w-[220px]"
          >
            <option value="">未绑定</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.code}>
                {p.name} ({p.code})
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!profileCode || updateKb.isPending}
          onClick={() => {
            updateKb
              .mutateAsync({ profile_code: profileCode })
              .then(() => toast.success(`已绑定模板：${profileCode}`))
              .catch((err: unknown) =>
                toast.error(err instanceof ApiError ? err.message : '改绑失败'),
              );
          }}
          className="btn-ghost border border-line bg-surface font-medium text-ink hover:border-brand-500"
        >
          保存绑定
        </button>
      </section>

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
          'cursor-pointer border-2 border-dashed p-10 text-center transition-colors duration-150',
          dragOver
            ? 'border-brand-500 bg-brand-50'
            : 'border-line bg-surface hover:border-brand-500 hover:bg-brand-50/30',
          upload.isPending ? 'pointer-events-none opacity-70' : '',
        ].join(' ')}
        style={{ borderRadius: 'var(--radius-md)' }}
      >
        <p className="text-sm font-semibold text-ink">
          {upload.isPending ? '上传中…' : '拖拽文件到此处，或点击选择'}
        </p>
        <p className="mt-1 text-xs text-ink-faint">
          支持 PDF / Word / Excel / PPT / Markdown / TXT，单文件建议不超过 32MB
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
          <thead className="border-b border-line bg-canvas/80 text-xs uppercase tracking-wider text-ink-faint">
            <tr>
              <th className="px-4 py-3 font-medium">标题</th>
              <th className="px-4 py-3 font-medium">状态 / 进度</th>
              <th className="px-4 py-3 font-medium">页数</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 3 }, (_, i) => (
                <tr key={i} className="border-b border-line/60">
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-48" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-24" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-10" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-12" />
                  </td>
                </tr>
              ))}
            {!isLoading && docs.length === 0 && (
              <tr>
                <td colSpan={4}>
                  <EmptyState
                    compact
                    title="暂无文档"
                    description="拖拽上方区域上传 PDF，完成后会出现在此列表"
                  />
                </td>
              </tr>
            )}
            {docs.map((doc) => {
              const failed = doc.status === 'failed';
              const detailExpanded = expandedErrorId === doc.id;
              return (
                <tr
                  key={doc.id}
                  className={[
                    'border-b border-line/60 transition-colors last:border-0 hover:bg-brand-50/40',
                    failed ? 'bg-danger/[0.03]' : '',
                  ].join(' ')}
                >
                  <td className="max-w-md px-4 py-3">
                    <Link
                      to={`/knowledge/${kbId}/documents/${doc.id}`}
                      title={doc.title}
                      className="block truncate font-medium text-ink hover:text-brand-700 hover:underline"
                    >
                      {doc.title}
                    </Link>
                    {failed && doc.error_detail ? (
                      <div className="mt-1.5 max-w-lg">
                        <p
                          className={[
                            'text-xs text-danger',
                            detailExpanded ? 'whitespace-pre-wrap break-words' : 'truncate',
                          ].join(' ')}
                        >
                          {doc.error_detail}
                        </p>
                        {doc.error_detail.length > 48 ? (
                          <button
                            type="button"
                            className="mt-0.5 text-[11px] text-ink-muted hover:text-brand-700"
                            onClick={() =>
                              setExpandedErrorId((id) => (id === doc.id ? null : doc.id))
                            }
                          >
                            {detailExpanded ? '收起详情' : '查看详情'}
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <DocumentStatusBadge status={doc.status} />
                    <IngestProgress status={doc.status} errorCode={doc.error_code} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-ink-muted">
                    {doc.page_count ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {failed ? (
                        <button
                          type="button"
                          className="btn-primary !px-2.5 !py-1 text-xs"
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
                          {reingest.isPending ? '提交中…' : '重试'}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="text-xs text-ink-faint hover:text-danger"
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

      {kbId ? <KbGrantsPanel kbId={kbId} /> : null}
    </div>
  );
}
