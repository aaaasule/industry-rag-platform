"""提示词组装。"""

from __future__ import annotations

from app.modules.retrieval.base import SearchHit

SYSTEM_PROMPT = """你是工业知识库助手。请仅根据下列编号证据回答用户问题。
规则：
1. 每个事实陈述后标注来源编号，如 [1]、[2]。
2. 数值、型号、标准号必须与证据一致，不得换算或臆造。
3. 若证据不足以回答，明确说明缺少哪些信息。
"""


def build_evidence_block(hits: list[SearchHit]) -> str:
    parts: list[str] = []
    for i, h in enumerate(hits, start=1):
        path = " > ".join(h.heading_path) if h.heading_path else ""
        header = f"[{i}] 《{h.document_title}》"
        if path:
            header += f" / {path}"
        header += f" p.{h.page_start}"
        parts.append(f"{header}\n{h.content}")
    return "\n\n".join(parts)


def build_messages(
    user_text: str,
    hits: list[SearchHit],
    *,
    system_override: str | None = None,
) -> list[dict[str, str]]:
    """组装 LLM 消息；`system_override` 非空时替换默认 SYSTEM_PROMPT。"""
    base = system_override.strip() if system_override and system_override.strip() else SYSTEM_PROMPT
    evidence = build_evidence_block(hits)
    system = base + "\n\n证据：\n" + evidence
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]
