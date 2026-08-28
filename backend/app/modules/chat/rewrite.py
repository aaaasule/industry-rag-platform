"""多轮指代消解：检索前将含代词的追问改写为独立问句。"""

from __future__ import annotations

from app.platform.llm.base import LLMProvider, Message

COREFERENCE_SYSTEM = (
    "你是查询改写助手，负责指代消解。"
    "根据会话历史，将用户当前问题中的代词或省略主语补全为完整、可独立检索的问句。"
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


def _parse_rewrite(raw: str) -> str | None:
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


async def resolve_query(
    llm: LLMProvider,
    *,
    history: list[tuple[str, str]],
    current: str,
) -> str:
    """有 ≥1 条历史用户消息时用 LLM 消解指代；否则或失败时返回 current。"""
    text = (current or "").strip()
    if not text:
        return current
    recent = history[-4:] if history else []
    if not any(role == "user" for role, _ in recent):
        return current

    messages: list[Message] = [Message(role="system", content=COREFERENCE_SYSTEM)]
    for role, content in recent:
        if role not in ("user", "assistant", "system"):
            continue
        messages.append(Message(role=role, content=content))  # type: ignore[arg-type]
    messages.append(Message(role="user", content=text))

    try:
        result = await llm.chat(messages, temperature=0.0, max_tokens=256)
        rewritten = _parse_rewrite(result.content)
        return rewritten if rewritten is not None else current
    except Exception:
        return current
