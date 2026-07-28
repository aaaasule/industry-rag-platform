"""表格检测：验证"表格原子化"这条分块规则有没有落地的基础。

用 pdfplumber 而非 PyMuPDF，对应 04 文档 2.1 节里刻意的混用——PyMuPDF 快且
能拿字符级坐标，pdfplumber 的表格结构还原更强。pdfplumber 较慢，因此默认
只扫前若干页。
"""

from __future__ import annotations

import pathlib

from probes.base import DocSnapshot, Finding

DEFAULT_SCAN_PAGES = 30


class TableProbe:
    name = "表格"

    def __init__(self, scan_pages: int = DEFAULT_SCAN_PAGES) -> None:
        self.scan_pages = scan_pages

    def run(self, doc: DocSnapshot) -> list[Finding]:
        try:
            import pdfplumber
        except ImportError:
            return [
                Finding(
                    metric="表格检测",
                    value="未执行",
                    level="skip",
                    note="未安装 pdfplumber，跳过；pip install pdfplumber 后重跑",
                )
            ]

        tables = self._scan(pdfplumber, pathlib.Path(doc.path))
        scanned = min(self.scan_pages, doc.page_count)

        if not tables:
            return [
                Finding(
                    metric="表格数量",
                    value=f"0（扫描前 {scanned} 页）",
                    level="ok",
                    note="未检出表格；若你确信文档里有表格，说明表格是图片或无边框，需另行处理",
                )
            ]

        rows = [t["rows"] for t in tables]
        thin = [t for t in tables if t["rows"] <= 1 or t["cols"] <= 1]

        findings = [
            Finding(
                metric="表格数量",
                value=f"{len(tables)}（扫描前 {scanned} 页）",
                level="ok",
                note=f"最大 {max(rows)} 行，平均 {sum(rows) / len(rows):.1f} 行",
                impact="超过 max_tokens 的大表需按行切分并重复表头，见 04 文档 3.1 第 3 条",
            ),
            Finding(
                metric="跨页表格嫌疑",
                value=len(_cross_page_candidates(tables)),
                level="warn" if _cross_page_candidates(tables) else "ok",
                note="相邻页各有一张表且上表贴近页底，大概率是同一张表被页面切断",
                impact="跨页表格需在解析阶段合并，否则下半张表会丢失表头",
            ),
        ]

        if thin:
            findings.append(
                Finding(
                    metric="疑似误检表格",
                    value=len(thin),
                    level="warn",
                    note="单行或单列，通常是版面线条被误判为表格边框",
                )
            )
        return findings

    def _scan(self, pdfplumber, path: pathlib.Path) -> list[dict]:
        found: list[dict] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[: self.scan_pages]:
                for table in page.find_tables():
                    data = table.extract()
                    found.append(
                        {
                            "page_no": page.page_number,
                            "rows": len(data),
                            "cols": max((len(r) for r in data), default=0),
                            "bottom": table.bbox[3],
                            "page_height": float(page.height),
                        }
                    )
        return found


def _cross_page_candidates(tables: list[dict]) -> list[int]:
    by_page = {t["page_no"] for t in tables}
    return [
        t["page_no"]
        for t in tables
        if t["page_no"] + 1 in by_page and t["bottom"] > t["page_height"] * 0.88
    ]
