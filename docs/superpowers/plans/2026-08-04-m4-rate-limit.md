# Rate Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** chat QPS+并发、search QPS，429 + Retry-After。

**Architecture:** Redis 滑动窗口 + inflight 计数；chat StreamingResponse 包装 finally 释放。

**Tech Stack:** FastAPI、Redis、现有 RateLimited。

## Global Constraints

- Redis 故障放行；limit≤0 关闭；并发占满 SSE 全生命周期

---

### Task 1

- [ ] Settings + RateLimited.retry_after + RateLimiter
- [ ] deps + chat/search 挂载
- [ ] tests + progress
