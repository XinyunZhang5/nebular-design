# 关键流程

每条流程标出授权检查点、信任边界穿越、以及产生的副作用。

---

## 1. 注册

`POST /api/auth/register` → `auth.py:32`

| 步骤 | 授权检查 | 副作用 |
| --- | --- | --- |
| 1. 校验入参 | Pydantic：用户名 3–20 字符、邮箱格式、密码 ≥6 位（`schemas.py:16`） | — |
| 2. 查重邮箱 | 无（公开接口） | 已存在 → 409 |
| 3. 查重用户名 | 无 | 已存在 → 409 |
| 4. bcrypt 哈希密码 | — | — |
| 5. 写 `users` | — | **新增用户行** |
| 6. 签发 JWT | — | 返回 7 天有效令牌 |

⚠️ **无速率限制** —— 可被脚本批量注册。
⚠️ **无邮箱验证** —— 任意邮箱地址均可注册，无所有权证明。
⚠️ 密码强度下限仅 6 位，无复杂度要求。
🔸 步骤 2、3 分两次查询后再插入，存在竞态窗口；数据库唯一约束是最后防线（会抛未捕获的 IntegrityError → 500 而非 409）。

## 2. 登录

`POST /api/auth/login` → `auth.py:59`

用户不存在和密码错误返回**同一条** `401 Invalid email or password` —— 正确做法，避免用户枚举。

⚠️ **无速率限制** —— 可被暴力破解。这是当前最需要补限流的接口之一。
⚠️ 用户不存在时会跳过 bcrypt 校验直接返回，响应时间差异理论上可用于时序侧信道枚举用户。实践中风险低。

## 3. 上传照片并生成乐高方案（核心流程）

`POST /api/images/upload` → `images.py:21`

| 步骤 | 授权检查 | 信任边界 | 副作用 |
| --- | --- | --- | --- |
| 1. 身份认证 | ✅ `get_current_user`，无 token 直接 401 | 浏览器 → API | — |
| 2. 校验 MIME 类型 | 白名单 jpeg/png/webp/gif（`images.py:16`） | — | 不合格 → 400 |
| 3. 读取并校验大小 | ≤15 MB | — | 超限 → 413 |
| 4. 存储原图 | — | API → S3 / 本地磁盘 | **写入文件** |
| 5. 深度估计 | — | 本地推理，无出站 | 首次调用加载模型（约 30 秒） |
| 6. Claude 分析 | — | **API → Anthropic** | **用户照片离开服务器**；消耗额度 |
| 7. 写 `projects` | 归属当前用户 | API → PostgreSQL | **新增作品行** |

⚠️ **整个流程在单个 HTTP 请求内同步完成**，冷启动可达 60 秒以上。步骤 4–6 是串行 `await`，尽管代码注释声称并行。
⚠️ **仅凭 `Content-Type` header 判断文件类型** —— 该值由客户端提供，可伪造。未校验文件魔数（magic bytes）。恶意文件可以伪装成 `image/jpeg` 上传；虽然 Pillow 解码失败会被 `estimate_depth` 捕获，但文件已经落盘。
⚠️ **无速率限制** —— 每次调用消耗 Anthropic 额度（约 $0.01–0.03），可被刷爆账单。
⚠️ Claude 失败时静默返回 `MOCK_RESULT`（`bricks.py:178`），用户无从得知拿到的是假数据。

## 4. 查询单个作品

`GET /api/images/status/{project_id}` → `images.py:58`

✅ **授权正确**：`if not project or project.user_id != current_user.id → 404`（`images.py:65`）。用 404 而非 403，不泄露资源是否存在。

🔸 该接口的**命名和 README 描述**（"poll one build for progress"）暗示这是轮询进度用的，但实际上传已返回完整结果，此处只能查已完成的记录。文档与实现不符。

## 5. 查询作品历史

`GET /api/images/history` → `images.py:71`

✅ 查询直接约束 `Project.user_id == current_user.id`，上限 50 条。无越权风险。
🔸 硬编码 `limit(50)`，无分页参数。

## 6. 好友请求

`POST /api/friends/request` → `friends.py:25`

| 检查 | 位置 |
| --- | --- |
| ✅ 需登录 | `get_current_user` |
| ✅ 不能加自己 | `friends.py:31` |
| ✅ 目标用户须存在 | `friends.py:36` → 404 |
| ✅ 双向查重（A→B 或 B→A 已存在即拒绝） | `friends.py:47` → 409 |

⚠️ **无速率限制** —— 可批量骚扰。
⚠️ **无屏蔽机制** —— 删除好友关系后对方可立即重新发起请求。
⚠️ **缺少 `rejected` 状态** —— `models.py:56` 的枚举只有 `pending | accepted`。`plan.txt` 验收标准要求支持"拒绝"，当前只能靠 DELETE 删除整条记录，语义上无法区分"从未加过"和"已被拒绝"。

## 7. 接受好友请求

`POST /api/friends/accept/{friendship_id}` → `friends.py:59`

✅ **授权正确**：`f.receiver_id != current_user.id → 404`。只有接收方能接受，请求方不能自我批准。
✅ 状态机校验：非 `pending` 状态 → 400，防止重复接受。

## 8. 删除好友关系

`DELETE /api/friends/{friendship_id}` → `friends.py:77`

✅ **授权正确**：必须是请求方或接收方之一，否则 404。
🔸 该接口同时承担"拒绝请求"和"解除好友"两种语义。

## 9. 公开聊天室（WebSocket）

`WS /api/chat/ws/chatroom?token=<jwt>` → `chat.py:79`

| 步骤 | 授权检查 | 副作用 |
| --- | --- | --- |
| 1. 解析 token | 🔴 **失败也继续** —— `_resolve_ws_user` 返回 `None` 不阻断连接 | — |
| 2. 接受连接 | 🔴 **无条件接受** | 加入内存广播列表 |
| 3. 推送历史 | 无 —— 未登录也能读到全部公开消息 | 读最近 60 条 |
| 4. 收消息 | 内容截断至 500 字符 | 登录用户 → **写库并广播**；游客 → **仅广播不写库** |

### 🔴 严重缺陷：游客可冒充任意用户

`chat.py:117` 的游客分支中，广播消息的身份字段**直接取自客户端 JSON**：

```python
"sender_username": data.get("username", "Guest"),
"sender_avatar": data.get("avatar", "⚪"),
```

未注册用户可连上 WebSocket，把 `username` 设为任意已有用户名，在公开聊天室冒充他人发言。消息不入库，但会实时推送给所有在线用户，且前端无法区分。

这也与 `plan.txt` 的验收标准"用户需注册登录才能使用核心功能"相抵触。

**修复方向**：拒绝未认证连接；或强制游客身份为服务端生成的不可伪造标识，并在前端明确标注。

## 10. 私信（WebSocket）

`WS /api/dm/ws/dm/{friend_id}?token=<jwt>` → `dm.py:84`

✅ **授权正确，且是全项目最严谨的一处**：

1. token 解析失败 → `close(4001)`（`dm.py:87`）
2. `_assert_friends` 校验双方为 `accepted` 好友 → 否则 `close(4003)`（`dm.py:93`）
3. 历史消息查询双向约束 sender/receiver（`dm.py:105`）

`GET /api/dm/history/{friend_id}` 同样先调 `_assert_friends` → 403。

🔸 消息投递给双方（`dm.py:143`）；接收方不在线则该消息不会实时送达，但已入库，下次连接读历史可见。
🔸 无"已读"状态、无未读计数。
