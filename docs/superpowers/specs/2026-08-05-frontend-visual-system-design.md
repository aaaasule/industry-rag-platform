# 整站视觉系统升级（工业控制台）

> 状态：已被 [`2026-08-27-frontend-refresh-p1-design.md`](./2026-08-27-frontend-refresh-p1-design.md) 取代  
> 日期：2026-08-05  
> 分支建议：`feat/ui-visual-system`（可拆多 PR）

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | **D→A**：整站视觉系统升级，信息架构 / 路由不动 |
| 气质 | **工业控制台**：冷静、高对比、实用 |
| 实施策略 | **Token-first**：CSS 变量 + Tailwind 扩展；分 PR |
| 强调色 | 铁青（非紫、非沿用旧 brand 蓝为主色） |

前置：M5 功能已合入；本切片**只改观感与共享样式**，不改业务逻辑。

---

## 1. 目标与非目标

### 1.1 目标

- 建立统一 design tokens（色 / 字 / 半径 / 阴影）
- 壳层（顶栏、Login）与全局背景具备可识别的工业气质
- 各业务页在不大改布局的前提下对齐新语言
- 分 PR 可审、可回滚

### 1.2 非目标

- 侧栏导航、路由重组
- 行业模板「表单 + JSON 双视图」功能开发（仅样式对齐现有 JSON 编辑）
- Chat 三栏信息架构重做
- 暗色主题（本轮不做）

---

## 2. Design tokens

在 `frontend/src/index.css` 的 `:root` 定义变量，并在 `tailwind.config.js` 映射。

### 2.1 颜色

| Token | 用途 | 建议值 |
| --- | --- | --- |
| `--bg-canvas` | 页面底 | `#F2F1ED` |
| `--bg-surface` | 面板 / 纸面 | `#FFFEFB` |
| `--ink` | 主文字 | `#1A1F24` |
| `--ink-muted` | 次级文字 | `#5C6570` |
| `--line` | 边框 / 分割 | `#D5D8DC` |
| `--accent` | 主操作 / active | `#2F6F7E` |
| `--accent-hover` | hover | `#275A66` |
| `--accent-soft` | 浅底（nav active） | `#E4F0F2` |
| `--ok` | 成功 | `#3D6B4F` |
| `--warn` | 警告 | `#B8792A` |
| `--danger` | 错误 | `#A33B2B` |

Tailwind：将现有 `brand.*` **重映射**到铁青系（或新增 `accent` 并逐步替换 `brand`，同一 PR 内完成主路径替换以免双色并存）。

### 2.2 字体

| 角色 | 字体 | 加载 |
| --- | --- | --- |
| UI / 标题 | IBM Plex Sans | Google Fonts 或 npm `@fontsource` |
| 中文正文 | Noto Sans SC（或思源黑体 Web） | 同上，`font-display: swap` |
| 等宽 | IBM Plex Mono | 代码 / JSON textarea |

`fontFamily.sans` 顺序：`"IBM Plex Sans", "Noto Sans SC", ...system fallbacks`（系统字体仅作 fallback，不作主视觉）。

### 2.3 形状与阴影

| Token | 值 |
| --- | --- |
| `--radius-sm` | `4px` |
| `--radius-md` | `6px` |
| 阴影 | 默认无；必要时 `0 1px 0 rgba(26,31,36,0.06)` 极轻 |

禁止大圆角 pill、多层彩色 glow。

### 2.4 背景氛围

- `body`：`--bg-canvas` + 极淡网格（CSS `repeating-linear-gradient` 或 1–2% noise SVG）
- 不抢内容；打印/对比度保持可读

---

## 3. 壳层与页面约定

### 3.1 AppLayout

- 顶栏：`--bg-surface`，底边 `--line`；高度约 56–60px
- 品牌「工业知识库平台」：字重大、字号略大于 nav，作为顶栏锚点
- Nav：文字链；active = 铁青字色 + 底边 2px 或 `--accent-soft` 浅底（二选一，全站统一）
- 右侧租户/用户：次级字色，控件圆角 `--radius-sm`

### 3.2 Login

- 全页 canvas；左侧或顶区品牌条（产品名 + 一句说明）
- 表单在 surface 上，边框 `--line`，**无**居中玻璃卡 + 紫雾背景
- 主按钮：实心 `--accent`

### 3.3 内容页（知识库 / 问答 / 用量 / 运营）

- 保持现有 `max-w-*` 与布局结构
- 替换：页面底色、卡片/表格边框、按钮、表头样式、focus ring（铁青）
- Overview：在占位基础上做成「轻工作台」——问候 + 快捷入口（知识库 / 问答 / 运营），仍可不接真实统计 API

### 3.4 动效

- 进页：顶栏 / main 子元素 `opacity` + `translateY(4px)` stagger，总时长 ≤ 300ms
- 交互：`transition-colors` 150ms
- `prefers-reduced-motion: reduce` 时关闭进场动画

---

## 4. 文件落点（预期）

| 文件 | 变更 |
| --- | --- |
| `frontend/src/index.css` | `:root` tokens、网格背景、共享 `.btn-*` / `.field-*` |
| `frontend/tailwind.config.js` | colors / fontFamily / borderRadius |
| `frontend/index.html` 或字体 import | 字体加载 |
| `app/AppLayout.tsx` | 顶栏 / nav 样式 |
| `features/auth/LoginPage.tsx` | 登录构图 |
| `app/placeholders.tsx` | 轻工作台概览 |
| 各 feature 页 | 批量替换明显的旧 `brand` / 过圆 / 过重阴影（可分批） |

---

## 5. PR 切片

| PR | 内容 | 验收 |
| --- | --- | --- |
| **P1 壳层** | tokens、字体、AppLayout、Login、全局 CSS | 登录后顶栏与 Login 已是新气质；无业务回归 |
| **P2 内容** | Overview + Knowledge 列表/详情样式 | 列表/上传区对齐新语言 |
| **P3 运营+其余** | Admin / Profiles / Usages / Chat 表面样式 | 表格表单一致；Chat 布局不变 |

每 PR：`pnpm lint && pnpm typecheck && pnpm build`。

---

## 6. 风险

| 风险 | 缓解 |
| --- | --- |
| `brand` 与 `accent` 双色并存 | P1 内完成 Tailwind 映射与主路径替换 |
| 中文字体体积 | 子集或仅加载 400/500/600；`font-display: swap` |
| Chat 复杂布局误伤 | P3 只改颜色/边框/按钮，不动 DOM 结构 |

---

## 7. 自检

- [x] 决策表完整  
- [x] 非目标明确（无侧栏 / 无 profile 功能双视图）  
- [x] 色值与字体可实施  
- [x] PR 切片可独立验收  
- [x] 无 TBD 占位  

---

## 8. 批准后下一步

用户确认本规格文件后 → `writing-plans` 产出 `docs/superpowers/plans/2026-08-05-frontend-visual-system.md` → 从 **P1 壳层** 开工。
