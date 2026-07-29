"""游标分页。

主键是 UUID v7（时间有序），所以"按创建时间倒序翻页"可以退化成对主键的
单列比较，不需要复合游标，也不会因为同一毫秒内的并发插入而漏记录。

游标对外是不透明字符串：客户端不得解析或构造，服务端因此可以随时改内部结构。
"""

from __future__ import annotations

import base64
import binascii
import uuid
from dataclasses import dataclass
from typing import Annotated, Generic, Protocol, TypeVar, cast

from fastapi import Query
from pydantic import BaseModel, Field

from app.platform.errors import AppError


class HasId(Protocol):
    id: uuid.UUID


T = TypeVar("T")

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


class InvalidCursor(AppError):
    code = "invalid_cursor"
    message = "分页游标无效"


def encode_cursor(last_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(last_id.bytes).decode().rstrip("=")


def decode_cursor(cursor: str) -> uuid.UUID:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        return uuid.UUID(bytes=base64.urlsafe_b64decode(padded))
    except (ValueError, binascii.Error) as exc:
        raise InvalidCursor() from exc


@dataclass(frozen=True, slots=True)
class PageParams:
    limit: int
    after: uuid.UUID | None

    @property
    def fetch_limit(self) -> int:
        """多取一条用于判断是否还有下一页，避免额外的 count 查询。"""
        return self.limit + 1


def page_params(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query()] = None,
) -> PageParams:
    return PageParams(limit=limit, after=decode_cursor(cursor) if cursor else None)


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = Field(default=None, description="为空表示已到末页")

    @classmethod
    def build(cls, rows: list[T], params: PageParams) -> Page[T]:
        """rows 需按 fetch_limit 取出（多取一条），本方法裁掉哨兵行并生成游标。

        元素必须带 UUID v7 的 `id` 字段——游标依赖它的时间有序性。
        """
        has_more = len(rows) > params.limit
        items = rows[: params.limit]
        next_cursor = encode_cursor(cast(HasId, items[-1]).id) if has_more and items else None
        return cls(items=items, next_cursor=next_cursor)
