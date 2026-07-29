"""结构感知分块。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

NUMBERING = re.compile(r"^\d+(\.\d+)*(?:[\s、.．]|(?=[\u4e00-\u9fff])|$)")
CLAUSE_INLINE = re.compile(r"^\d+(\.\d+)+(?=[\u4e00-\u9fff])")


@dataclass
class ChunkDraft:
    content: str
    raw_content: str
    heading_path: list[str]
    chunk_type: str
    page_start: int
    page_end: int
    bboxes: list[dict[str, Any]] = field(default_factory=list)
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkRules:
    max_tokens: int = 512
    min_tokens: int = 80
    overlap_tokens: int = 64
    clause_mode: bool = False
    keep_heading_prefix: bool = True


def estimate_tokens(text: str) -> int:
    # 中英混排粗估：约 1.5 字符/token
    return max(1, int(len(text) / 1.5))


def chunk_pages(pages: list[dict[str, Any]], rules: ChunkRules, *, title: str) -> list[ChunkDraft]:
    units = _to_units(pages, rules.clause_mode)
    drafts: list[ChunkDraft] = []
    buffer: list[dict[str, Any]] = []
    path: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        raw = "\n".join(u["text"] for u in buffer).strip()
        if not raw:
            buffer = []
            return
        tokens = estimate_tokens(raw)
        if tokens < rules.min_tokens and drafts:
            # 碎片并入上一块
            prev = drafts[-1]
            prev.raw_content = f"{prev.raw_content}\n{raw}".strip()
            prefix = _prefix(title, prev.heading_path) if rules.keep_heading_prefix else ""
            prev.content = f"{prefix}{prev.raw_content}" if prefix else prev.raw_content
            prev.token_count = estimate_tokens(prev.content)
            prev.page_end = buffer[-1]["page"]
            prev.bboxes.extend(_bboxes(buffer))
            buffer = []
            return

        heading_path = list(path)
        prefix = _prefix(title, heading_path) if rules.keep_heading_prefix else ""
        content = f"{prefix}{raw}" if prefix else raw
        drafts.append(
            ChunkDraft(
                content=content,
                raw_content=raw,
                heading_path=heading_path,
                chunk_type=buffer[0].get("chunk_type", "text"),
                page_start=buffer[0]["page"],
                page_end=buffer[-1]["page"],
                bboxes=_bboxes(buffer),
                token_count=estimate_tokens(content),
            )
        )
        buffer = []

    for unit in units:
        if unit.get("is_heading"):
            flush()
            level = unit.get("level", 1)
            path = [*path[: max(0, level - 1)], unit["text"].strip()]
            continue

        tentative = [*buffer, unit]
        tentative_text = "\n".join(u["text"] for u in tentative)
        if estimate_tokens(tentative_text) > rules.max_tokens and buffer:
            flush()
            buffer = [unit]
        else:
            buffer.append(unit)

    flush()
    return _apply_overlap(drafts, rules.overlap_tokens)


def _to_units(pages: list[dict[str, Any]], clause_mode: bool) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    body_size = _body_size(pages)
    for page in pages:
        for block in page.get("blocks", []):
            text = (block.get("text") or "").strip()
            if not text:
                continue
            is_heading = _is_heading(block, body_size)
            if clause_mode and CLAUSE_INLINE.match(text):
                # 条款边界：断开前一块
                units.append(
                    {
                        "text": text,
                        "page": page["page_no"],
                        "bbox": block.get("bbox"),
                        "is_heading": False,
                        "chunk_type": "text",
                        "clause": True,
                    }
                )
                continue
            if is_heading:
                level = 1
                m = NUMBERING.match(text)
                if m:
                    level = m.group(0).count(".") + 1
                units.append(
                    {
                        "text": text,
                        "page": page["page_no"],
                        "bbox": block.get("bbox"),
                        "is_heading": True,
                        "level": level,
                    }
                )
            else:
                units.append(
                    {
                        "text": text,
                        "page": page["page_no"],
                        "bbox": block.get("bbox"),
                        "is_heading": False,
                        "chunk_type": block.get("type", "text"),
                    }
                )
    # clause_mode：遇到 clause 标记时在结构上先 flush——在主循环用独立处理更清晰
    if clause_mode:
        reshaped: list[dict[str, Any]] = []
        for u in units:
            if u.get("clause") and reshaped and not reshaped[-1].get("is_heading"):
                # 插入伪标题路径节点：用条款号自身
                m = CLAUSE_INLINE.match(u["text"])
                clause_no = m.group(0) if m else u["text"][:8]
                parts = clause_no.split(".")
                path_levels = [".".join(parts[: i + 1]) for i in range(len(parts))]
                for i, p in enumerate(path_levels):
                    reshaped.append(
                        {
                            "text": p,
                            "page": u["page"],
                            "bbox": u.get("bbox"),
                            "is_heading": True,
                            "level": i + 1,
                        }
                    )
            reshaped.append(u)
        return reshaped
    return units


def _is_heading(block: dict[str, Any], body_size: float) -> bool:
    text = (block.get("text") or "").strip()
    if not text or len(text) > 40:
        return False
    score = 0
    if NUMBERING.match(text):
        score += 3
    size = float(block.get("size") or 0)
    if body_size and size > body_size * 1.15:
        score += 2
    if block.get("bold"):
        score += 1
    return score >= 3


def _body_size(pages: list[dict[str, Any]]) -> float:
    from collections import Counter

    counter: Counter[float] = Counter()
    for page in pages:
        for b in page.get("blocks", []):
            size = float(b.get("size") or 0)
            if size:
                counter[size] += len((b.get("text") or "").strip())
    return counter.most_common(1)[0][0] if counter else 0.0


def _prefix(title: str, heading_path: list[str]) -> str:
    parts = [f"《{title}》", *heading_path]
    return " > ".join(parts) + "\n\n"


def _bboxes(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for u in units:
        if u.get("bbox"):
            out.append({"page": u["page"], "bbox": u["bbox"]})
    return out


def _apply_overlap(drafts: list[ChunkDraft], overlap_tokens: int) -> list[ChunkDraft]:
    if overlap_tokens <= 0 or len(drafts) < 2:
        return drafts
    # 简化：仅在 raw_content 尾部保留提示性重叠说明，避免破坏坐标
    return drafts
