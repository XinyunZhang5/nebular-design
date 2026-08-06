# 架构

> 技术事实速查。教学版和上线指南见 [系统架构与上线指南.md](./系统架构与上线指南.md)。

## 系统概览

前后端分离的单体应用。Next.js 前端（纯客户端渲染）经 HTTP + WebSocket 访问一个 FastAPI 后端；后端串联本地深度估计模型和 Anthropic API，结果落 PostgreSQL。

```
浏览器 (Next.js, 全 'use client')
   │ HTTP + WebSocket，JWT 存 localStorage
   ▼
FastAPI 单体进程 (uvicorn)
   ├─► PostgreSQL      users / projects / friendships / messages
   ├─► S3 或本地磁盘    原图
   ├─► Anthropic API   图片 + 深度数据 → 零件清单
   └─► HuggingFace     启动时下载 Depth Anything V2 权重
```

## 技术栈

| 层 | 技术 | 版本 |
| --- | --- | --- |
| 前端 | Next.js App Router / React / Tailwind / Framer Motion / react-dropzone | 16.2.6 / 19.2.4 / v4 |
| 后端 | FastAPI / Uvicorn | 0.115.5 / 0.32.1 |
| 数据 | SQLAlchemy 2 async / asyncpg / PostgreSQL | 2.0.36 / 0.30.0 |
| 认证 | python-jose (HS256) / passlib + bcrypt | 3.3.0 / 1.7.4 + 4.0.1 |
| 视觉 | Transformers + PyTorch (CPU) / Depth Anything V2 Small | 4.47.1 / 2.5.1 |
| 推理 | Anthropic SDK, `claude-sonnet-4-6` | 0.40.0 |
| 存储 | boto3 → S3，或 StaticFiles → `backend/uploads/` | 1.35.80 |

## 认证流程

1. `POST /api/auth/register` 或 `/login` → 后端签发 HS256 JWT，payload 为 `{sub: user_id, exp}`，有效期 7 天（`ACCESS_TOKEN_EXPIRE_MINUTES=10080`）。
2. 前端存进 `localStorage`：`nebular_token`（令牌）、`nebular_user`（用户对象）。
3. REST 请求走 `Authorization: Bearer <token>`（`dependencies.py:get_current_user`）。
4. WebSocket 走 **URL 查询参数** `?token=<jwt>`（`chat.py:_resolve_ws_user`）—— 浏览器 WebSocket API 不支持自定义 header，这是常见妥协，代价是 token 可能出现在服务器访问日志里。

**无刷新令牌，无令牌吊销机制。** token 签发后 7 天内一律有效，改密码或登出都不会使其失效。

## 信任边界

| # | 边界 | 跨越的数据 | 校验方式 |
| --- | --- | --- | --- |
| 1 | 浏览器 → FastAPI | 凭据、图片、消息 | JWT + Pydantic schema 校验 |
| 2 | FastAPI → PostgreSQL | 全部业务数据 | SQLAlchemy 参数化查询（无裸 SQL 拼接） |
| 3 | FastAPI → Anthropic | **用户上传的原始照片（base64）+ 深度特征** | API key；⚠️ 用户未被告知 |
| 4 | FastAPI → S3 | 原始照片 | AWS 凭据 |
| 5 | FastAPI → HuggingFace | 无出站数据，仅下载权重 | 无（首次启动拉取远程模型文件） |

边界 3 是隐私上最需要留意的一条：用户照片会离开你控制的服务器。

## 可扩展性天花板

**WebSocket 连接状态存在进程内存**（`app/ws/manager.py` 的 `_chatroom` 列表和 `_dm` 字典）。多实例部署时，连在不同实例的用户互相收不到消息。要水平扩展必须引入 Redis Pub/Sub。当前规模下应保持**单实例**。

`ThreadPoolExecutor(max_workers=2)`（`depth.py:21`）限制了并发深度估计数；模型全局单例 + `asyncio.Lock` 保证只加载一次。

## 优雅降级设计

代码里有两处刻意的降级，值得保留：

- `estimate_depth()` 出错返回 `{"error": ..., "fallback": True}`，不中断流程（`depth.py:109`）。
- `analyze_image()` 在无 API key 或调用失败时返回 `MOCK_RESULT`（`bricks.py:127, 178`）。

⚠️ 但第二条**对用户不可见** —— 分析失败时用户拿到的是一份假清单，界面上没有任何提示。这一点需要修。

## 未实现的能力

| 能力 | 状态 |
| --- | --- |
| 邮件通知 | ❌ 不存在。无邮件发送代码，故不产出 `emails.md` |
| 定时任务 / cron | ❌ 不存在。无调度器、无后台周期作业，故不产出 `cron.md` |
| SEO | 🔸 仅 `layout.tsx` 有全局 `metadata`；所有页面是 `'use client'`，无逐页 metadata、无 sitemap、无 robots.txt。内容型页面少，影响有限 |
| 后台任务队列 | ❌ 不存在。上传是同步长请求 |
| 数据库迁移 | ❌ 装了 alembic 但未使用，靠 `create_all` |
| 测试 | ❌ 前后端均无 |
| CI/CD | ❌ 无 `.github/workflows/` |

## 相关文档

- [flows.md](./flows.md) —— 关键流程与授权检查点
- [permissions.md](./permissions.md) —— 角色与资源权限矩阵
- [variables.md](./variables.md) —— 配置与密钥风险表
- [automation.md](./automation.md) —— 嵌入式 AI（Claude）的调用契约与护栏
- [系统架构与上线指南.md](./系统架构与上线指南.md) —— 教学版，含部署平台选型与上线步骤
