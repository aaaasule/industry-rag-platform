"""自适应查询扩展：弱召回时 LLM 改写后再二次检索融合。"""

from __future__ import annotations

from app.platform.llm.base import LLMProvider, Message

EXPAND_RRF_FLOOR = 0.016

EXPAND_SYSTEM = (
    "你是查询扩展助手，负责检索查询扩展。"
    "将用户检索问题改写为一条语义相近、便于检索的独立问句（可换同义词或补充行业术语）。"
    "要求：只输出一个完整问句，不要解释，不要多余标点包装。"
)

_QUOTE_PAIRS = (
    ('"', '"'),
    ("'", "'"),
    ("“", "”"),
    ("‘", "’"),
    ("「", "」"),
    ("『", "』"),
)


def should_expand(*, enabled: bool, fused: list[tuple[str, float]]) -> bool:
    """enabled 且（无命中或首名 RRF < EXPAND_RRF_FLOOR）时触发扩展。"""
    if not enabled:
        return False
    if not fused:
        return True
    return fused[0][1] < EXPAND_RRF_FLOOR


def _parse_expand(raw: str) -> str | None:
    if not raw or not str(raw).strip():
        return None
    line = str(raw).strip().splitlines()[0].strip()
    for left, right in _QUOTE_PAIRS:
        if len(line) >= 2 and line.startswith(left) and line.endswith(right):
            line = line[len(left) : -len(right)].strip()
            break
    if not (1 <= len(line) <= 2000):
        return None
    return line


async def expand_query(llm: LLMProvider, *, query: str) -> str | None:
    """LLM 生成 1 条改写问句；失败/空返回 None。"""
    text = (query or "").strip()
    if not text:
        return None
    messages: list[Message] = [
        Message(role="system", content=EXPAND_SYSTEM),
        Message(role="user", content=text),
    ]
    try:
        result = await llm.chat(messages, temperature=0.0, max_tokens=256)
        return _parse_expand(result.content)
    except Exception:
        return None
