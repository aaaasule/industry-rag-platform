# 本目录是前后端契约的基线。
#
# - openapi.json     : 由 `make openapi`（或 `python -m scripts.export_openapi`）从 FastAPI 导出
# - openapi.gen.ts   : 由 openapi-typescript 从 openapi.json 生成，禁止手改
#
# CI 会重新导出并生成；若与入库版本不一致，说明有人改了接口却忘了跑 make openapi。
