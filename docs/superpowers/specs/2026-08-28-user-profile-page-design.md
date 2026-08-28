# 个人资料页（账号设置）

> 状态：已实现  
> 日期：2026-08-28  
> 路由：`/settings/profile`  
> 前置：壳层侧栏用户区已落地；`GET /auth/me`、`POST /auth/switch-tenant` 已有

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | 完整账号页：改显示名 + 改密码 + 租户列表/切换 |
| 头像 | 仅首字母渐变，不上传 |
| 形态 | 独立路由页（方案 A），非 Popover / 非运营 Tab |
| 入口 | 侧栏底部头像区域可点击 |

## 1. 目标

任意登录用户可在统一账号页查看与维护本人资料，并在多租户间切换；视觉与现有 Indigo SaaS 壳层一致。

## 2. 入口与导航

- 路由：`/settings/profile`（挂在 `RequireAuth` + `AppLayout` 下）
- 侧栏底部用户区（展开/收起）点击进入该页；`title` / tooltip：「个人资料」
- 本页不占用主导航高亮项；登出仍留在侧栏底部，不迁入本页

## 3. 页面信息架构

背景 `canvas`（`#F8FAFC`），内容区 `max-w-3xl` 左右居中，纵向 `gap-6` 三张白卡片（`rounded-2xl` / `shadow-panel` / `p-6|p-8`）。

### 3.1 卡片 A · 基本资料

| 字段 | 交互 |
| --- | --- |
| 头像 | 显示名首字符，Indigo→Violet 渐变圆，只读 |
| 邮箱 | 只读 |
| 状态 | 只读徽章（如 `active` →「正常」） |
| 显示名 | 可编辑输入框 |
| 保存 | 脏检查；未改或提交中禁用 |

成功：toast「已更新显示名」，并刷新会话缓存（侧栏姓名同步）。

### 3.2 卡片 B · 修改密码

| 字段 | 规则 |
| --- | --- |
| 当前密码 | 必填 |
| 新密码 | `min_length=8`、`max_length=128`（与登录一致）；不得与当前密码相同 |
| 确认新密码 | 须与新密码一致（前端校验即可） |

成功：toast + 清空三字段。失败：当前密码错误等服务端错误文案展示在卡片内。

### 3.3 卡片 C · 我的租户

- 行：租户名、slug、角色徽章；当前租户标「当前」
- 多租户：非当前行「切换」→ 复用现有 `switchTenant`，成功后 toast 并刷新会话
- 单租户：只展示，无切换按钮

## 4. API

### 4.1 `PATCH /api/v1/auth/me`

Request:

```json
{ "display_name": "张三" }
```

- `display_name`：trim 后 1–128 字符  
Response：`SessionInfo`（与 `GET /me` 同形，便于前端一次替换缓存）

### 4.2 `POST /api/v1/auth/change-password`

Request:

```json
{
  "current_password": "...",
  "new_password": "..."
}
```

- 两者均 `min_length=8`、`max_length=128`  
- 校验当前密码；错误 → `401` 或业务码 `invalid_credentials`（与登录风格对齐，文案：「当前密码不正确」）  
- 新密码与当前相同 → `422`  
- 成功 → `204 No Content`  
- 无状态 JWT：改密后**不强制**吊销既有 access token（与现有 logout 策略一致）；可选后续加 jti 黑名单

### 4.3 已有能力复用

- `GET /auth/me`：首屏数据  
- `POST /auth/switch-tenant`：租户切换  

## 5. 前端落点

| 路径 | 说明 |
| --- | --- |
| `frontend/src/features/auth/ProfilePage.tsx` | 页面 |
| `frontend/src/features/auth/api.ts` / `hooks.ts` | `updateProfile`、`changePassword` + mutation |
| `frontend/src/app/routes.tsx` | 注册路由 |
| `frontend/src/app/AppLayout.tsx` | 用户区链到 `/settings/profile` |

视觉：Phosphor 图标；输入 focus `ring-accent/20`；主按钮沿用现有 `Button`。

## 6. 非目标

头像上传、改邮箱、SSO / 2FA、注销账号、改密后全局踢下线、成员「只看自己用量」。

## 7. 验收

- [ ] 侧栏点击头像进入 `/settings/profile`
- [ ] 改显示名后侧栏与本页同步
- [ ] 改密码：旧密错失败；成功后可用新密码登录
- [ ] 多租户切换成功；单租户无切换按钮
- [ ] member / admin / owner 均可访问（不绑运营权限）
- [ ] `pnpm lint && pnpm typecheck`；后端相关 pytest 通过
