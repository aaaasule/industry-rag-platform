"""UUID v7 生成。

02 文档约定主键统一用 UUID v7：时间有序，既不暴露业务量，又保留 B-tree 插入
的局部性。Python 3.13 标准库尚无 uuid7，这里按 RFC 9562 §5.7 实现。

布局（共 128 位）：
    48 位  Unix 毫秒时间戳（大端）
     4 位  版本号 0b0111
    12 位  随机（同毫秒内的次序熵）
     2 位  变体 0b10
    62 位  随机
"""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    timestamp_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")

    value = (timestamp_ms & 0xFFFF_FFFF_FFFF) << 80
    value |= 0x7 << 76
    value |= ((rand >> 62) & 0xFFF) << 64
    value |= 0b10 << 62
    value |= rand & 0x3FFF_FFFF_FFFF_FFFF

    return uuid.UUID(int=value)


def timestamp_of(value: uuid.UUID) -> float:
    """从 UUID v7 反解出生成时刻（秒）。排查问题时很有用。"""
    if value.version != 7:
        raise ValueError(f"不是 UUID v7：{value}")
    return (value.int >> 80) / 1000.0
