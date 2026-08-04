"""最小检索评测：登录 → POST /search → Recall@k / MRR。

用法：

  cd backend && uv run python scripts/evaluate.py \\
    --base http://127.0.0.1:8000/api/v1 \\
    --email owner@acme.example --password '...' --tenant acme-machinery \\
    --kb-id <uuid> --golden evals/golden.jsonl --k 10

golden.jsonl 每行 JSON：
  query (必填)
  kb_id (可选，覆盖 CLI)
  expected_document_ids (uuid 列表，优先)
  expected_document_titles (标题子串匹配，次选)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


def _login(client: httpx.Client, base: str, email: str, password: str, tenant: str) -> str:
    resp = client.post(
        f"{base}/auth/login",
        json={"email": email, "password": password, "tenant_slug": tenant},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _search(
    client: httpx.Client,
    base: str,
    token: str,
    *,
    query: str,
    kb_id: str,
    top_k: int,
) -> list[dict]:
    resp = client.post(
        f"{base}/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "kb_ids": [kb_id], "top_k": top_k},
    )
    resp.raise_for_status()
    return list(resp.json().get("results") or [])


def _relevant_rank(hits: list[dict], row: dict) -> int | None:
    """返回首个相关命中的 1-based 排名；无关则 None。"""
    ids = {str(x) for x in (row.get("expected_document_ids") or [])}
    titles = [str(t).lower() for t in (row.get("expected_document_titles") or []) if t]
    if not ids and not titles:
        return None
    for i, h in enumerate(hits, start=1):
        doc_id = str(h.get("document_id") or "")
        title = str(h.get("document_title") or "").lower()
        if ids and doc_id in ids:
            return i
        if titles and any(t in title for t in titles):
            return i
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="检索评测 Recall@k / MRR")
    p.add_argument("--base", default="http://127.0.0.1:8000/api/v1")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--tenant", required=True)
    p.add_argument("--kb-id", required=True, help="默认知识库；golden 行可覆盖")
    p.add_argument("--golden", type=Path, default=Path("evals/golden.jsonl"))
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--out", type=Path, default=None, help="可选 JSON 报告路径")
    args = p.parse_args()

    if not args.golden.is_file():
        print(f"golden 不存在: {args.golden}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for line in args.golden.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))

    if not rows:
        print("golden 为空，跳过", file=sys.stderr)
        return 0

    recalls: list[float] = []
    rr_list: list[float] = []
    details: list[dict] = []

    with httpx.Client(timeout=120.0) as client:
        token = _login(client, args.base, args.email, args.password, args.tenant)
        for row in rows:
            query = str(row["query"])
            kb_id = str(row.get("kb_id") or args.kb_id)
            hits = _search(client, args.base, token, query=query, kb_id=kb_id, top_k=args.k)
            rank = _relevant_rank(hits, row)
            has_label = bool(
                row.get("expected_document_ids") or row.get("expected_document_titles")
            )
            if not has_label:
                details.append({"query": query, "skipped": True, "reason": "no expected labels"})
                continue
            hit = 1.0 if rank is not None else 0.0
            rr = 1.0 / rank if rank is not None else 0.0
            recalls.append(hit)
            rr_list.append(rr)
            details.append(
                {
                    "query": query,
                    "kb_id": kb_id,
                    "rank": rank,
                    "recall": hit,
                    "rr": rr,
                    "hit_titles": [h.get("document_title") for h in hits[:5]],
                }
            )

    n = len(recalls)
    report = {
        "n": n,
        "k": args.k,
        "recall_at_k": sum(recalls) / n if n else None,
        "mrr": sum(rr_list) / n if n else None,
        "details": details,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
