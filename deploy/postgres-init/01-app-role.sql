-- 开发环境的应用角色。生产环境由基础设施预置同名角色并使用强口令。
--
-- 为什么必须分两个角色：POSTGRES_USER（irp）是超级用户，超级用户无条件绕过
-- 行级安全策略。如果应用直接用它连库，RLS 会静默失效——测试全绿、隔离却没有。
-- 应用一律用 irp_app 连接，它既非超级用户也不是表属主，策略才真正生效。

CREATE ROLE irp_app WITH LOGIN PASSWORD 'irp_app' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
GRANT CONNECT ON DATABASE irp TO irp_app;
