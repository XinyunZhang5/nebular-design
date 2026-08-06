# 配置与密钥

配置集中在 `backend/app/config.py` 的 Pydantic `Settings` 类，从 `backend/.env` 或进程环境变量读取。前端只有一个 `NEXT_PUBLIC_*` 变量。

## 后端

| 变量 | 默认值 | 是否密钥 | 风险等级 | 泄露后果 / 备注 |
| --- | --- | --- | --- | --- |
| `SECRET_KEY` | `"change-this-in-production"` | 🔑 是 | 🔴 **极高** | JWT 签名密钥。泄露 = 任何人可伪造任意用户的令牌。**有默认值且生产不校验，忘记设置服务照常启动** |
| `ANTHROPIC_API_KEY` | `""` | 🔑 是 | 🔴 高 | 泄露 = 他人消耗你的额度产生账单。为空时全站静默降级为 mock 数据 |
| `AWS_SECRET_ACCESS_KEY` | `""` | 🔑 是 | 🔴 高 | 泄露 = 存储桶可被读写删。应配最小权限策略，只授予目标桶的 `PutObject`/`DeleteObject` |
| `AWS_ACCESS_KEY_ID` | `""` | 🔑 是 | 🟠 中 | 需与上一条配对才有效 |
| `DATABASE_URL` | 本地 `nebulardb` | 🔑 是（含密码） | 🔴 高 | 泄露 = 数据库直连。Railway 会自动注入，不要手填 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080`（7 天） | 否 | 🟠 中 | 无吊销机制，这个数字就是被盗令牌的最长可用窗口。建议缩短到 1440（1 天）并加刷新令牌 |
| `FRONTEND_URL` | `http://localhost:3000` | 否 | 🟠 中 | CORS 白名单，逗号分隔。**上线后必须加上 Vercel 域名**，否则前端全部请求被浏览器拦截。注意 `config.py:43` 无论如何都会追加 localhost:3000/3001，生产环境这属于多余放行 |
| `USE_S3` | `false` | 否 | 🔴 高（生产） | **生产必须设 `true`**。为 `false` 时文件写本地磁盘，PaaS 容器重建即全部丢失 |
| `S3_BUCKET_NAME` | `nebular-design-uploads` | 否 | 🟡 低 | — |
| `AWS_REGION` | `us-east-1` | 否 | 🟡 低 | — |
| `ENABLE_DEPTH_ESTIMATION` | `true` | 否 | 🟡 低 | 设 `false` 跳过模型加载。CI 和低内存环境应设 false |
| `DEPTH_MODEL` | `depth-anything/Depth-Anything-V2-Small-hf` | 否 | 🟡 低 | 从 HuggingFace 拉取的模型标识 |
| `PORT` | `8000` | 否 | 🟡 低 | Railway 会注入 |

## 前端

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | 后端地址。`NEXT_PUBLIC_` 前缀意味着**会被打包进浏览器可见的 JS**，因此**绝不能放任何密钥** |

⚠️ 即使设了这个变量，`src/app/upload/page.tsx:149` 仍然硬编码了 `http://localhost:8000` 用于拼接本地存储的图片地址。这行必须改。

## 当前本地状态

`backend/.env` 存在且已填入真实的 `ANTHROPIC_API_KEY`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`SECRET_KEY`。

✅ 已确认该文件**未被 git 跟踪**（`.gitignore` 的 `.env` 规则生效），仓库历史中也搜不到 `sk-ant-` 前缀。

🔴 但 `nebular-design/.env.local.example` 里**明文写着一个完整的 Anthropic API key**。该文件同样未进 git（已验证），但：
- 它是一个 `.example` 文件，按惯例是给人抄的模板，放真 key 极易误提交
- 该文件只有 `.gitignore` 的 `.env` 和 `*.env` 规则**碰巧没覆盖到它**（文件名以 `.example` 结尾），保护是脆弱的
- 前端已经不直接调用 Claude 了（`@anthropic-ai/sdk` 是残留依赖），这个变量本身就是多余的

**处置建议**：删掉该文件里的 key 值（改成占位符），或直接删除整个文件；并去 console.anthropic.com 轮换这把 key。

## 上线前的密钥清单

```
□ 用 openssl rand -hex 32 生成全新的 SECRET_KEY，绝不复用本地那个
□ 在 Anthropic 控制台生成新 key，作废本地这把
□ 为 S3/R2 创建专用凭据，权限只限单个桶
□ DATABASE_URL 由 Railway 自动注入，不要手动填写
□ 全部密钥只存在平台的环境变量面板里，不进代码库
□ FRONTEND_URL 填 Vercel 的正式域名
□ USE_S3=true
```

## 建议补上的启动校验

`config.py` 目前对危险配置没有任何拦截。建议加一段：生产环境下若 `SECRET_KEY` 仍为默认值，或 `USE_S3=false`，**直接拒绝启动**。宁可部署失败，也不要带着这两个问题上线。
