# M4 切片：运营管理 UI

> 状态：已实现（待开 PR） 
> 日期：2026-08-04  
> 前置：成员/审计/接入点/用量仪表盘后端与用量前端已合入

## 1. 目标

`owner` / `admin` 在统一「运营」入口管理：模型接入点、租户成员、审计日志。客户可演示质量。

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| IA | A：单入口 `/admin` + Tab（connections / members / audit） |
| 导航 | 「模型接入」改为「运营」；admin/owner 可见 |
| 兼容 | `/modelops` → `/admin?tab=connections` |
| 类型 | 使用已有 `openapi.gen.ts`；`api.put` 补齐 |
| 非目标 | KB grants UI、邀请注册、平台接入点编辑 |

## 3. Tab 能力

- **接入点**：CRUD（租户）、凭证只写、test（读 `ok`）、routes 表；平台点只读
- **成员**：列表、邮箱加人、改角色、移除；owner/自我保护
- **审计**：时间 / action / 分页；actor 映射成员显示名

## 4. 技术

- `features/admin/`：`AdminPage` 壳 + Members / Audit 面板
- `features/modelops/`：api / hooks / ConnectionsPanel
- 与 usages 共享 `['model-connections']` queryKey
- 顺手修 `worker.py` 多余 F401 noqa

## 5. 验收

- admin 三 Tab 可用；member 无导航 / 友好无权限
- 平台接入点无写操作；test 失败展示 error_message
- 成员操作遵守后端 owner 规则；审计可翻页筛选
