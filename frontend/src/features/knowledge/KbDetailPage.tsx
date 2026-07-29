import { useCallback, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { statusLabel } from './api';
import {
  useDeleteDocument,
  useDocuments,
  useKnowledgeBase,
  useReingest,
  useUploadDocument,
} from './hooks';

export function KbDetailPage() {
  const { kbId = '' } = useParams();
  const { data: kb } = useKnowledgeBase(kbId);
  const { data: docs = [], isLoading } = useDocuments(kbId);
  const upload = useUploadDocument(kbId);
  const reingest = useReingest(kbId);
  const remove = useDeleteDocument(kbId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

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
        <Link to="/knowledge" className="text-sm text-slate-500 hover:text-slate-800">
          ← 知识库
        </Link>
        <h1 className="mt-2 text-xl font-semibold text-slate-900">{kb?.name ?? '知识库'}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {kb ? `${kb.doc_count} 文档 · ${kb.chunk_count} 分块` : '加载中…'}
        </p>
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
          'cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition',
          dragOver
            ? 'border-brand-400 bg-brand-50'
            : 'border-slate-300 bg-white hover:border-brand-300',
        ].join(' ')}
      >
        <p className="text-sm font-medium text-slate-800">拖拽 PDF 到此处，或点击选择文件</p>
        <p className="mt-1 text-xs text-slate-500">经 API 中转上传，单文件建议不超过 32MB</p>
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

      {message && <p className="text-sm text-slate-600">{message}</p>}
      {upload.isPending && <p className="text-sm text-brand-700">上传中…</p>}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase text-slate-500">
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
                <td colSpan={4} className="px-4 py-6 text-slate-500">
                  加载中…
                </td>
              </tr>
            )}
            {!isLoading && docs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-slate-500">
                  暂无文档
                </td>
              </tr>
            )}
            {docs.map((doc) => (
              <tr key={doc.id} className="border-b border-slate-50 last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{doc.title}</div>
                  {doc.status === 'failed' && doc.error_detail && (
                    <div className="mt-1 max-w-md truncate text-xs text-red-600">
                      {doc.error_detail}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="px-4 py-3 text-slate-600">{doc.page_count ?? '—'}</td>
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
                      className="text-xs text-slate-500 hover:text-red-600"
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
      ready: 'bg-emerald-50 text-emerald-700',
      failed: 'bg-red-50 text-red-700',
      pending: 'bg-slate-100 text-slate-600',
      parsing: 'bg-amber-50 text-amber-700',
      chunking: 'bg-amber-50 text-amber-700',
      embedding: 'bg-amber-50 text-amber-700',
    }[status] ?? 'bg-slate-100 text-slate-600';

  return (
    <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${tone}`}>
      {statusLabel(status)}
    </span>
  );
}
