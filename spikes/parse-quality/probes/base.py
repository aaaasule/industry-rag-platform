"""解析体检的共享数据结构。

探针（Probe）只读 DocSnapshot，不直接接触 PDF 库。这样新增一项检查不需要
理解 PyMuPDF 的 API，也便于将来把同一套探针复用到 DOCX / XLSX 上。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

Level = Literal["ok", "warn", "fail", "skip"]

LEVEL_ORDER: dict[Level, int] = {"skip": 0, "ok": 1, "warn": 2, "fail": 3}


@dataclass(frozen=True)
class Span:
    """一段样式连续的文本，是版面分析的最小单位。

    confidence 仅 OCR 来源的 span 有值。文本层提取是确定性的，没有置信度可言。
    """

    text: str
    bbox: tuple[float, float, float, float]
    size: float
    bold: bool
    confidence: float | None = None


@dataclass(frozen=True)
class PageSnapshot:
    page_no: int
    width: float
    height: float
    char_count: int
    image_area_ratio: float
    spans: list[Span]
    source: Literal["text", "ocr"] = "text"
    ocr_ms: int = 0

    @property
    def plain_text(self) -> str:
        return "".join(span.text for span in self.spans)


@dataclass(frozen=True)
class DocSnapshot:
    path: str
    file_size: int
    page_count: int
    encrypted: bool
    outline: list[tuple[int, str, int]]
    pages: list[PageSnapshot]

    @property
    def has_outline(self) -> bool:
        return bool(self.outline)


@dataclass
class Finding:
    """一条检查结论。

    impact 是这个脚本存在的意义所在：它把一个技术指标翻译成"不达标会让哪份
    设计文档的哪个决策失效"，让结果可以直接用于决策，而不是留下一堆数字。
    """

    metric: str
    value: Any
    level: Level
    note: str
    impact: str = ""


class Probe(Protocol):
    name: str

    def run(self, doc: DocSnapshot) -> list[Finding]: ...


def worst(levels: list[Level]) -> Level:
    return max(levels, key=lambda lv: LEVEL_ORDER[lv], default="skip")


def grade(value: float, warn_at: float, fail_at: float) -> Level:
    """按"越大越糟"的指标分级。"""
    if value >= fail_at:
        return "fail"
    if value >= warn_at:
        return "warn"
    return "ok"
