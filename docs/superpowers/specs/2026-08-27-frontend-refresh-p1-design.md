# 前端视觉改版 P1（Cobalt + Slate）

> 状态：已完成  
> 日期：2026-08-27  
> 分支：`feat/ui-refresh-p1`  
> 取代：[`2026-08-05-frontend-visual-system-design.md`](./2026-08-05-frontend-visual-system-design.md)（铁青顶栏方案，已由本规格 supersede）

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | P1：壳层 + 登录 / 概览 / 知识库 / 问答 |
| 气质 | B2B 可信、冷色专业（Cobalt + Slate） |
| 壳层 | 左侧 Sidebar + 精简顶栏；`< lg` drawer |
| 路由 | 不变 |
| 暗色 | P1 不做默认暗色，仅预留 token |

## 1. Design tokens

见计划文档 §2；实现落点：`frontend/src/index.css`、`frontend/tailwind.config.js`。

## 2. 组件层

`frontend/src/components/ui/`：Button、Input、Select、Card、PageHeader、Chip、Badge、StatTile、AppShell。

## 3. 页面清单

| 页面 | 文件 | P1 变更 |
| --- | --- | --- |
| 登录 | `LoginPage.tsx` | 新视觉 + Card 表单 |
| 概览 | `placeholders.tsx` | StatTile + 非对称快捷入口 |
| 知识库列表 | `KnowledgePage.tsx` | SideSheet 创建 |
| 知识库详情 | `KbDetailPage.tsx` | 上传区 + 表格 |
| 问答 | `ChatPage.tsx` | 抛光 + 子组件拆分 |

## 4. 非目标

- 运营 / 用量 / 文档预览深度改版
- Chat 三栏 DOM 重构
- Tailwind v4

## 5. 验收

- `pnpm lint && pnpm typecheck && pnpm build`
- 核心旅程：登录 → 概览 → 建库 → 问答 → 证据
