#!/usr/bin/env python3
"""工业 PDF 解析体检。

在写任何摄取代码之前，用真实文档验证 docs/04-rag-pipeline.md 里的解析假设
是否成立。退出码：0 全部通过，1 存在需关注项，2 存在不通过项。

    python check.py ~/samples                    # 体检整个目录
    python check.py a.pdf b.pdf --render 1,2,5   # 顺带导出坐标可视化
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import traceback

import extract
import render
from probes import default_probes
from report import DocResult, print_document, print_verdict, write_json

EXIT_OK, EXIT_WARN, EXIT_FAIL = 0, 1, 2


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pdfs = _collect_pdfs(args.paths)
    if not pdfs:
        print("未找到任何 PDF 文件", file=sys.stderr)
        return EXIT_FAIL

    probes = default_probes(with_tables=not args.no_tables)
    render_pages = _parse_pages(args.render)

    results = []
    for path in pdfs:
        result = _check_one(path, probes, args, render_pages)
        if result is not None:
            print_document(result)
            results.append(result)

    if not results:
        return EXIT_FAIL

    overall = print_verdict(results)
    write_json(results, args.out)
    print(f"\nJSON 报告：{args.out}")
    return {"ok": EXIT_OK, "skip": EXIT_OK, "warn": EXIT_WARN, "fail": EXIT_FAIL}[overall]


def _check_one(path: pathlib.Path, probes, args, render_pages: list[int]) -> DocResult | None:
    try:
        doc = extract.load(path, max_pages=args.max_pages)
    except Exception:  # 解析直接崩溃本身就是重要结论，不能让它中断整批体检
        print(f"[!] {path.name} 解析失败：", file=sys.stderr)
        traceback.print_exc()
        return None

    findings = {probe.name: probe.run(doc) for probe in probes}
    rendered = (
        render.render_overlay(path, args.out.parent / "overlay", render_pages)
        if render_pages
        else []
    )
    return DocResult(doc=doc, findings=findings, rendered=rendered)


def _collect_pdfs(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(path.rglob("*.pdf")))
        elif path.suffix.lower() == ".pdf":
            found.append(path)
    return found


def _parse_pages(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(part) for part in raw.split(",") if part.strip().isdigit()]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="工业 PDF 解析体检",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("paths", nargs="+", type=pathlib.Path, help="PDF 文件或目录")
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=pathlib.Path("out/report.json"),
        help="JSON 报告路径（默认 out/report.json）",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="每份文档最多分析多少页，用于快速试跑"
    )
    parser.add_argument(
        "--render", type=str, default=None, help="导出坐标可视化的页码，逗号分隔，如 1,2,5"
    )
    parser.add_argument("--no-tables", action="store_true", help="跳过表格检测（pdfplumber 较慢）")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
