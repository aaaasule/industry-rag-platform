# M4 切片：kb_grants + 跨租户验收 — 设计说明

**日期**：2026-07-29  
**分支**：`feat/m4-kb-grants`  
**状态**：已确认，实施中  
**依据**：用户确认矩阵方案 2 + 后端闭环 + 架构方案 A

---

## 1. 目标与非目标

### 目标

1. 实现 `identity.visible_kb_ids(user, permission)`，作为唯一权限入口。
2. KB list/get、文档读写、search、chat 的 kb 范围均基于该集合。
3. Grants CRUD：`GET/PUT/DELETE /knowledge-bases/{kb_id}/grants[/{user_id}]`。
4. CI 覆盖：跨租户 404、private 无 grant 403、授/撤权、owner/admin 绕过。

### 非目标

前端授权 UI；成员管理；模型接入台；用量仪表盘；新建迁移（表已在 0002）。

---

## 2. 权限矩阵

| 条件 | read | write | manage |
| --- | --- | --- | --- |
| 租户 `owner` / `admin` | ✓ 全部 KB | ✓ | ✓ |
| `visibility=tenant` 普通成员 | ✓ | grant≥write | grant≥manage |
| `visibility=private` | 创建者或 grant≥read | 创建者或 grant≥write | 创建者或 grant≥manage |

权限包含：`manage` ⊃ `write` ⊃ `read`。

错误语义：
- 跨租户 / ID 不存在 → **404**
- 同租户资源存在但无权 → **403**（get/写/grants）；list/search 静默过滤

---

## 3. 架构

```
IdentityService.visible_kb_ids(claims, permission) -> set[UUID]
KnowledgeService：list/get/_require_* / grants CRUD
RetrievalService.search(..., user_id)：kb_ids ∩ visible(read)
ChatService：创建/覆盖 kb_ids 时预检 read
```

ORM：`KbGrant` 对齐已有表。

---

## 4. API

| 方法 | 路径 | 权限 |
| --- | --- | --- |
| GET | `/knowledge-bases/{kb_id}/grants` | manage |
| PUT | `/knowledge-bases/{kb_id}/grants/{user_id}` | manage；body `{permission}` |
| DELETE | `/knowledge-bases/{kb_id}/grants/{user_id}` | manage |

写文档 / 改 KB / 删 KB：需 `write`（删 KB 建议 `manage`，本切片：PATCH/DELETE KB 与 upload 用 `write`；grants 用 `manage`）。

---

## 5. 验收用例

1. A 建 private KB → 同租户无 grant 的 B：list 不见、get 403  
2. 授 B `read` → get/search OK；撤权后再 403  
3. 另一租户 token 访问该 kb → 404  
4. owner/admin 无 grant 亦可 list/get/manage  

---

## 6. 规格自检

- [x] 无 TBD  
- [x] 与 02/03 一致（owner/admin 绕过为产品确认增强）  
- [x] 范围仅后端闭环  
