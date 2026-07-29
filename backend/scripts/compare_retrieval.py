"""召回对比：对固定 query 调用 /search，输出 JSON + Markdown 摘要。

用法（API 已启动且已登录环境）：

  cd backend && uv run python scripts/compare_retrieval.py \\
    --kb-id <uuid> --label real-rerank --rerank true

  uv run python scripts/compare_retrieval.py \\
    --kb-id <uuid> --label real-rrf --rerank false

  uv run python scripts/compare_retrieval.py \\
    --diff artifacts/retrieval-compare/fake.json artifacts/retrieval-compare/real-rerank.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

DEFAULT_QUERIES = [
    "烟花爆竹流向登记有哪些要求？",
    "危险化学品重大危险源安全包保责任",
    "液压泵 HYD-2201 保养周期",
]


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
    rerank: bool,
) -> dict:
    resp = client.post(
        f"{base}/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": query,
            "kb_ids": [kb_id],
            "top_k": top_k,
            "options": {"rerank": rerank, "expand_context": 1},
        },
    )
    resp.raise_for_status()
    return resp.json()


def cmd_run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    queries = list(DEFAULT_QUERIES)
    if args.queries_file:
        queries = [
            line.strip()
            for line in Path(args.queries_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    with httpx.Client(timeout=120.0) as client:
        token = _login(client, args.base, args.email, args.password, args.tenant)
        runs = []
        for q in queries:
            body = _search(
                client,
                args.base,
                token,
                query=q,
                kb_id=args.kb_id,
                top_k=args.top_k,
                rerank=args.rerank,
            )
            runs.append(
                {
                    "query": q,
                    "rewritten_query": body.get("query"),
                    "stats": body.get("stats"),
                    "hit_ids": [r["chunk_id"] for r in body.get("results", [])],
                    "hits": [
                        {
                            "chunk_id": r["chunk_id"],
                            "document_title": r.get("document_title"),
                            "page_start": r.get("page_start"),
                            "scores": r.get("scores"),
                            "content_preview": (r.get("content") or "")[:160],
                        }
                        for r in body.get("results", [])
                    ],
                }
            )

    payload = {
        "label": args.label,
        "kb_id": args.kb_id,
        "rerank": args.rerank,
        "generated_at": datetime.now(UTC).isoformat(),
        "runs": runs,
    }
    json_path = out_dir / f"{args.label}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = out_dir / f"{args.label}.md"
    lines = [
        f"# Retrieval compare: {args.label}",
        "",
        f"- kb_id: `{args.kb_id}`",
        f"- rerank: `{args.rerank}`",
        f"- generated_at: `{payload['generated_at']}`",
        "",
    ]
    for run in runs:
        lines.append(f"## {run['query']}")
        lines.append("")
        lines.append(f"stats: `{json.dumps(run['stats'], ensure_ascii=False)}`")
        lines.append("")
        for i, h in enumerate(run["hits"], start=1):
            lines.append(f"{i}. p.{h['page_start']} {h['document_title']} scores={h['scores']}")
            lines.append(f"   > {h['content_preview']}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def cmd_diff(args: argparse.Namespace) -> None:
    a = json.loads(Path(args.left).read_text(encoding="utf-8"))
    b = json.loads(Path(args.right).read_text(encoding="utf-8"))
    by_q_a = {r["query"]: r for r in a["runs"]}
    by_q_b = {r["query"]: r for r in b["runs"]}
    lines = [
        f"# Diff: {a.get('label')} vs {b.get('label')}",
        "",
    ]
    for q in sorted(set(by_q_a) | set(by_q_b)):
        ra, rb = by_q_a.get(q), by_q_b.get(q)
        lines.append(f"## {q}")
        if ra is None or rb is None:
            lines.append("- missing on one side")
            lines.append("")
            continue
        sa, sb = set(ra["hit_ids"]), set(rb["hit_ids"])
        overlap = len(sa & sb)
        lines.append(f"- overlap: {overlap}/{max(len(sa), len(sb), 1)}")
        lines.append(f"- only_left: {sorted(sa - sb)}")
        lines.append(f"- only_right: {sorted(sb - sa)}")
        lines.append(f"- order_left: {ra['hit_ids']}")
        lines.append(f"- order_right: {rb['hit_ids']}")
        lines.append(f"- stats_left: `{ra['stats']}`")
        lines.append(f"- stats_right: `{rb['stats']}`")
        lines.append("")
    out = Path(args.out) if args.out else Path(args.right).with_suffix(".diff.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="跑一轮 /search 并落盘")
    run_p.add_argument("--base", default="http://127.0.0.1:8000/api/v1")
    run_p.add_argument("--email", default="owner@acme.example")
    run_p.add_argument("--password", default="Passw0rd!2026")
    run_p.add_argument("--tenant", default="acme-machinery")
    run_p.add_argument("--kb-id", required=True)
    run_p.add_argument("--label", required=True)
    run_p.add_argument("--rerank", type=lambda s: s.lower() in {"1", "true", "yes"}, default=False)
    run_p.add_argument("--top-k", type=int, default=5)
    run_p.add_argument("--out-dir", default="artifacts/retrieval-compare")
    run_p.add_argument("--queries-file", default="")
    run_p.set_defaults(func=cmd_run)

    diff_p = sub.add_parser("diff", help="对比两份 JSON 报告")
    diff_p.add_argument("left")
    diff_p.add_argument("right")
    diff_p.add_argument("--out", default="")
    diff_p.set_defaults(func=cmd_diff)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
