"""导出 OpenAPI schema，供前端 openapi-typescript 生成类型。

用法（在 backend/ 下）：
    uv run python -m scripts.export_openapi [输出路径]

默认写出到 ../frontend/src/types/openapi.json。不依赖已启动的 HTTP 服务，
因此可以在 CI 里作为契约校验的第一步。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    default = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "openapi.json"
    target = Path(args[0]) if args else default

    # 延迟导入：保证脚本本身可被 --help 类工具探测而不触发配置加载失败
    from app.main import create_app

    schema = create_app().openapi()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target} ({len(schema.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
