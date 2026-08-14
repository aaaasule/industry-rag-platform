# P1 批次 B · KB 授权 UI + 无邮件邀请注册

> 状态：实现中  
> 日期：2026-08-14

## 范围

- `POST /memberships`：用户不存在时创建账号并加入租户，响应返回一次性 `temporary_password`（不发邮件）
- `GrantOut` 附带 `email` / `display_name`；授给非本租户成员 → 404
- 知识库详情页：授权列表 / 授予 / 改权 / 撤权
- Admin 成员面板：新建用户时展示初始口令

## 非目标

SMTP 邮件邀请、SSO、公开自助注册
