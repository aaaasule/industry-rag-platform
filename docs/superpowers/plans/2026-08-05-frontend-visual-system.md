# 整站视觉系统 Implementation Plan

> 规格：`docs/superpowers/specs/2026-08-05-frontend-visual-system-design.md`

**Goal:** Token-first 工业控制台视觉；分 P1 壳层 / P2 内容 / P3 运营。

**Architecture:** CSS 变量 + Tailwind `brand` 重映射铁青；字体 IBM Plex + Noto Sans SC。

## Global Constraints

- 不改路由 / Chat DOM  
- P1 只动壳层与全局样式（brand 重映射惠及全站按钮）

---

### Task P1: 壳层

- [x] tokens + fonts + AppLayout + Login  

### Task P2: 内容

- [x] Overview 轻工作台  
- [x] Knowledge 列表 / KbDetail / DocumentDetail 样式  

### Task P3: 运营与其余

- [x] Admin / Profiles / Connections / Usages / Chat 表面样式  
