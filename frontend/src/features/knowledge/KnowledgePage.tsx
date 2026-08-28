import { Library, Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { SideSheet } from '@/components/SideSheet';
import { Skeleton } from '@/components/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { PageHeader } from '@/components/ui/PageHeader';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/toast/useToast';
import { useCreateKnowledgeBase, useKnowledgeBases, useProfiles } from './hooks';

export function KnowledgePage() {
  const toast = useToast();
  const { data: bases = [], isLoading } = useKnowledgeBases();
  const { data: profiles = [] } = useProfiles();
  const createKb = useCreateKnowledgeBase();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [name, setName] = useState('');
  const [profileCode, setProfileCode] = useState('general');
  const [error, setError] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await createKb.mutateAsync({
        name: name.trim(),
        profile_code: profileCode,
      });
      setName('');
      setSheetOpen(false);
      toast.success(`已创建知识库「${created.name}」`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建失败';
      setError(msg);
      toast.error(msg);
    }
  }

  return (
    <div className="page-shell space-y-6">
      <PageHeader
        title="知识库"
        description="上传文档、跟踪摄取进度，为问答准备语料。"
        actions={
          <Button onClick={() => setSheetOpen(true)}>
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            新建知识库
          </Button>
        }
      />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {isLoading &&
          Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="panel space-y-3 p-4">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))}
        {!isLoading && bases.length === 0 && (
          <div className="panel border-dashed sm:col-span-2 xl:col-span-3">
            <EmptyState
              title="还没有知识库"
              description="创建第一个知识库，然后上传设备手册或工艺文档"
              action={
                <Button onClick={() => setSheetOpen(true)}>
                  <Plus className="h-4 w-4" strokeWidth={1.5} />
                  新建知识库
                </Button>
              }
            />
          </div>
        )}
        {bases.map((kb) => {
          const profileName =
            profiles.find((p) => p.id === kb.profile_id)?.name ??
            (kb.profile_id ? '已绑定模板' : '通用');
          return (
          <Link
            key={kb.id}
            to={`/knowledge/${kb.id}/files`}
            className="panel group block p-5 transition-all duration-200 hover:border-indigo-200 hover:shadow-md"
          >
            <div className="flex items-start gap-3">
              <span className="inline-flex rounded-lg bg-indigo-50 p-2 text-indigo-600">
                <Library className="h-5 w-5" strokeWidth={1.5} aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="truncate font-semibold text-slate-800 group-hover:text-indigo-600">
                  {kb.name}
                </h2>
                {kb.description ? (
                  <p className="mt-1 line-clamp-2 text-sm text-ink-muted">{kb.description}</p>
                ) : null}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge tone="accent">{profileName}</Badge>
                  <span className="text-xs tabular-nums text-ink-faint">
                    {kb.doc_count} 文档 · {kb.chunk_count} 分块
                  </span>
                </div>
              </div>
            </div>
          </Link>
          );
        })}
      </section>

      <SideSheet open={sheetOpen} onClose={() => setSheetOpen(false)} title="新建知识库">
        <form onSubmit={(e) => void onCreate(e)} className="space-y-4">
          <Input
            label="名称"
            id="kb-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：设备手册"
            required
          />
          <Select
            label="行业模板"
            id="kb-profile"
            value={profileCode}
            onChange={(e) => setProfileCode(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.code}>
                {p.name}
              </option>
            ))}
            {profiles.length === 0 && <option value="general">通用</option>}
          </Select>
          {error ? (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          ) : null}
          <div className="flex gap-2 pt-2">
            <Button type="submit" disabled={createKb.isPending || !name.trim()} className="flex-1">
              {createKb.isPending ? '创建中…' : '创建'}
            </Button>
            <Button variant="secondary" type="button" onClick={() => setSheetOpen(false)}>
              取消
            </Button>
          </div>
        </form>
      </SideSheet>
    </div>
  );
}
