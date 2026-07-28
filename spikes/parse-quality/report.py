"""体检结果的呈现：控制台表格 + JSON 存档。

控制台面向"现在要不要改设计"这个即时判断，JSON 面向归档与对比——换了解析
参数之后要能和上一次的结果 diff。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import re
from typing import Any

from probes.base import DocSnapshot, Finding, Level, worst

try:
    from rich.console import Console
    from rich.table import Table

    _console: Console | None = Console()
except ImportError:
    _console = None

_MARKUP = re.compile(r"\[/?[a-z ]*\]")
_MARK: dict[Level, str] = {"ok": "✓", "warn": "!", "fail": "✗", "skip": "-"}
_STYLE: dict[Level, str] = {"ok": "green", "warn": "yellow", "fail": "red", "skip": "dim"}


@dataclasses.dataclass
class DocResult:
    doc: DocSnapshot
    findings: dict[str, list[Finding]]
    rendered: list[pathlib.Path] = dataclasses.field(default_factory=list)

    @property
    def level(self) -> Level:
        return worst([f.level for group in self.findings.values() for f in group])

    def flat(self) -> list[Finding]:
        return [f for group in self.findings.values() for f in group]


def print_document(result: DocResult) -> None:
    doc = result.doc
    title = (
        f"{pathlib.Path(doc.path).name}  ·  {doc.page_count} 页  ·  "
        f"{doc.file_size / 1024 / 1024:.1f} MB"
    )
    if _console is None:
        _print_plain(title, result)
        return

    table = Table(title=title, title_justify="left", header_style="bold")
    table.add_column("", width=2)
    table.add_column("探针", style="cyan", no_wrap=True)
    table.add_column("检查项", no_wrap=True)
    table.add_column("结果")
    table.add_column("说明", overflow="fold")

    for probe_name, findings in result.findings.items():
        for i, f in enumerate(findings):
            table.add_row(
                f"[{_STYLE[f.level]}]{_MARK[f.level]}[/]",
                probe_name if i == 0 else "",
                f.metric,
                f"[{_STYLE[f.level]}]{f.value}[/]",
                f.note,
            )
    _console.print(table)

    for f in result.flat():
        if f.level in ("warn", "fail") and f.impact:
            _console.print(f"  [{_STYLE[f.level]}]→ {f.metric}：{f.impact}[/]")
    if result.rendered:
        _console.print(f"  [dim]坐标可视化已导出：{result.rendered[0].parent}[/]")
    _console.print()


def print_verdict(results: list[DocResult]) -> Level:
    overall = worst([r.level for r in results])
    lines = _verdict_lines(results, overall)
    if _console is None:
        print("\n--- 结论 ---")
        print("\n".join(_MARKUP.sub("", line) for line in lines))
        return overall
    _console.rule("[bold]结论")
    for line in lines:
        _console.print(line)
    return overall


def _verdict_lines(results: list[DocResult], overall: Level) -> list[str]:
    fails = [(r, f) for r in results for f in r.flat() if f.level == "fail"]
    warns = [(r, f) for r in results for f in r.flat() if f.level == "warn"]

    lines = [f"共体检 {len(results)} 份文档，{len(fails)} 项不通过，{len(warns)} 项需关注。"]
    for r, f in fails:
        lines.append(f"[red]✗ {pathlib.Path(r.doc.path).name} · {f.metric} = {f.value}[/]")
        if f.impact:
            lines.append(f"   {f.impact}")

    if overall == "fail":
        lines.append("")
        lines.append("[bold red]建议：先回改设计文档再进入 M0，不要带着已知的解析缺陷开工。[/]")
    elif overall == "warn":
        lines.append("")
        lines.append("[bold yellow]建议：可以进入 M0，但把上述关注项写进 M1 的验收用例。[/]")
    else:
        lines.append("")
        lines.append("[bold green]建议：解析假设成立，可以按现有设计进入 M0。[/]")
    return lines


def write_json(results: list[DocResult], target: pathlib.Path) -> None:
    payload: list[dict[str, Any]] = [
        {
            "document": pathlib.Path(r.doc.path).name,
            "path": r.doc.path,
            "page_count": r.doc.page_count,
            "file_size": r.doc.file_size,
            "encrypted": r.doc.encrypted,
            "has_outline": r.doc.has_outline,
            "level": r.level,
            "findings": {
                probe: [dataclasses.asdict(f) for f in findings]
                for probe, findings in r.findings.items()
            },
        }
        for r in results
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_plain(title: str, result: DocResult) -> None:
    print(f"\n=== {title} ===")
    for probe_name, findings in result.findings.items():
        for f in findings:
            print(f"  [{_MARK[f.level]}] {probe_name} / {f.metric}: {f.value} — {f.note}")
            if f.level in ("warn", "fail") and f.impact:
                print(f"      → {f.impact}")
