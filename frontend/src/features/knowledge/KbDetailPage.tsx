import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '@/lib/http';
import { statusLabel } from './api';
import {
  useDeleteDocument,
  useDocuments,
  useKnowledgeBase,
  useProfiles,
  useReingest,
  useUpdateKnowledgeBase,
  useUploadDocument,
} from './hooks';

export function KbDetailPage() {
  const { kbId = '' } = useParams();
  const { data: kb } = useKnowledgeBase(kbId);
  const { data: profiles = [] } = useProfiles();
  const { data: docs = [], isLoading } = useDocuments(kbId);
  const upload = useUploadDocument(kbId);
  const updateKb = useUpdateKnowledgeBase(kbId);
  const reingest = useReingest(kbId);
  const remove = useDeleteDocument(kbId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [profileCode, setProfileCode] = useState('');

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
      setMessage(null);
      const list = Array.from(files);
      for (const file of list) {
        try {
          await upload.mutateAsync({ file });
          setMessage(`已提交：${file.name}`);
        } catch (err) {
          setMessage(err instanceof Error ? err.message : '上传失败');
        }
      }
    },
    [upload],
  );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Link to="/knowledge" className="text-sm text-ink-muted transition-colors hover:text-ink">
          ← 知识库
        </Link>
        <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
          {kb?.name ?? '知识库'}
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          {kb ? `${kb.doc_count} 文档 · ${kb.chunk_count} 分块` : '加载中…'}
        </p>
      </div>

      <section className="panel flex flex-wrap items-end gap-3 p-4">
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
            setMessage(null);
            updateKb
              .mutateAsync({ profile_code: profileCode })
              .then(() => setMessage(`已改绑模板：${profileCode}`))
              .catch((err: unknown) =>
                setMessage(err instanceof ApiError ? err.message : '改绑失败'),
              );
          }}
          className="btn-primary"
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
            : 'border-line bg-surface hover:border-brand-500',
        ].join(' ')}
        style={{ borderRadius: 'var(--radius-md)' }}
      >
        <p className="text-sm font-medium text-ink">拖拽 PDF 到此处，或点击选择文件</p>
        <p className="mt-1 text-xs text-ink-faint">经 API 中转上传，单文件建议不超过 32MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf,.txt,text/plain"
          className="hidden"
          multiple
          onChange={(e) => {
            if (e.target.files?.length) void onFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </div>

      {message && <p className="text-sm text-ink-muted">{message}</p>}
      {upload.isPending && <p className="text-sm text-brand-700">上传中…</p>}

      <section className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line bg-canvas/80 text-xs uppercase tracking-wider text-ink-faint">
            <tr>
              <th className="px-4 py-3 font-medium">标题</th>
              <th className="px-4 py-3 font-medium">状态</th>
              <th className="px-4 py-3 font-medium">页数</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-ink-muted">
                  加载中…
                </td>
              </tr>
            )}
            {!isLoading && docs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-ink-muted">
                  暂无文档
                </td>
              </tr>
            )}
            {docs.map((doc) => (
              <tr
                key={doc.id}
                className="border-b border-line/60 transition-colors last:border-0 hover:bg-brand-50/40"
              >
                <td className="px-4 py-3">
                  <Link
                    to={`/knowledge/${kbId}/documents/${doc.id}`}
                    className="font-medium text-ink hover:text-brand-700 hover:underline"
                  >
                    {doc.title}
                  </Link>
                  {doc.status === 'failed' && doc.error_detail && (
                    <div className="mt-1 max-w-md truncate text-xs text-danger">
                      {doc.error_detail}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="px-4 py-3 tabular-nums text-ink-muted">{doc.page_count ?? '—'}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {doc.status === 'failed' && (
                      <button
                        type="button"
                        className="text-xs text-brand-700 hover:underline"
                        disabled={reingest.isPending}
                        onClick={() => void reingest.mutateAsync(doc.id)}
                      >
                        重试
                      </button>
                    )}
                    <button
                      type="button"
                      className="text-xs text-ink-faint hover:text-danger"
                      disabled={remove.isPending}
                      onClick={() => {
                        if (confirm(`删除「${doc.title}」？`)) void remove.mutateAsync(doc.id);
                      }}
                    >
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    {
      ready: 'bg-ok/10 text-ok',
      failed: 'bg-danger/10 text-danger',
      pending: 'bg-canvas text-ink-muted',
      parsing: 'bg-warn/10 text-warn',
      chunking: 'bg-warn/10 text-warn',
      embedding: 'bg-warn/10 text-warn',
    }[status] ?? 'bg-canvas text-ink-muted';

  return (
    <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${tone}`}>
      {statusLabel(status)}
    </span>
  );
}
