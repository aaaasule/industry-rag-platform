# M5 切片 A 实施计划：profile resolve

> 规格：`docs/superpowers/specs/2026-08-04-m5-profile-resolve-design.md`

## 步骤

1. `app/modules/profile/{schemas,service}.py` — EffectiveProfile + merge + resolve  
2. `ingestion/tasks.py` — 分块用 `resolve` + `to_ingestion_chunk_rules`  
3. `IndustryProfileOut.chunk_rules` — 列表调试可见  
4. `tests/test_profile_resolve.py`  
5. 更新 `docs/07-progress.md`  
