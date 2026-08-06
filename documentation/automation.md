# 嵌入式 AI

系统里只有一处 AI 调用：`app/services/bricks.py` 的 `analyze_image()`。它不是一个能自主决策的 agent，而是一次**单轮、无工具、纯生成**的模型调用。

## 触发方式

| 项 | 内容 |
| --- | --- |
| 触发点 | 用户 `POST /api/images/upload`，无其他入口 |
| 触发条件 | 仅在 `ANTHROPIC_API_KEY` 非空时真实调用；为空则直接返回 `MOCK_RESULT` |
| 频率控制 | ❌ **无** —— 无速率限制、无每用户配额、无每日预算上限 |
| 调用模型 | `claude-sonnet-4-6`，`max_tokens=2500` |

## 工具面

**无。** 模型不能调用任何函数、不能访问数据库、不能发起网络请求、不能读写文件。它只接收输入、返回一段文本。

这是很好的安全属性：**即使 prompt 被注入，模型能造成的最大伤害也只是返回一份内容错误的零件清单。** 它没有任何可以被劫持的副作用通道。

## 输入

发送给 Anthropic 的内容（`bricks.py:143`）：

1. **用户上传的原始照片**，base64 编码，完整分辨率，未做任何脱敏或裁剪
2. **深度分析特征**，一个约 11 个字段的 JSON（尺寸、深度方差、边缘强度、分层分布等）
3. 固定的 system prompt 和 user prompt 模板

⚠️ **隐私提示**：用户照片会完整离开你的服务器发往 Anthropic。产品界面目前**没有任何地方告知用户这一点**。

⚠️ **注意**：深度数据是本地模型算出来的纯数值，不含用户可控文本，因此从深度数据侧注入 prompt 是不可能的。唯一的用户可控输入是图片本身 —— 理论上存在图像内嵌文字的间接注入，但因为没有工具面，危害有限。

## 引导 vs 硬护栏

区分这两者很重要：**引导（steering）**是"请你这样做"，模型可能不听；**硬护栏（hard guardrail）**是代码强制，模型没得选。

| 约束 | 类型 | 说明 |
| --- | --- | --- |
| "只返回 JSON，不要 markdown 代码块" | 🔸 引导 | 写在 system prompt 里，模型可能不遵守 |
| "10–16 种零件、5–8 个步骤" | 🔸 引导 | 纯提示词约束，无代码校验 |
| "只用真实可购买的乐高颜色" | 🔸 引导 | 无法验证。README 已诚实承认零件号"plausible rather than verified" |
| "`estimatedPieceCount` 等于各零件数量之和" | 🔸 引导 | **无代码校验，很可能对不上** |
| `max_tokens=2500` | 🔒 硬护栏 | 强制截断 |
| 从首个 `{` 到末个 `}` 提取 JSON | 🔒 硬护栏 | `bricks.py:170`，容忍模型输出多余文字 |
| 任何异常 → 返回 `MOCK_RESULT` | 🔒 硬护栏 | `bricks.py:178`，保证接口不会 500 |

## 输出契约

代码期望的结构：

```
buildingName: string
difficulty: "Beginner" | "Intermediate" | "Expert"
estimatedPieceCount: int
estimatedTime: string
colorPalette: string[]
bricks: [{ name, partId, color, quantity, description }]
steps: [{ step, title, description, bricksUsed, tip? }]
```

🔴 **这个契约没有被强制执行。** `bricks.py:174` 只做了 `json.loads()`，**没有用 Pydantic 校验结构**。`schemas.py` 里有一个 `DepthData` 模型，但**没有对应的分析结果模型**。

后果：如果 Claude 返回的 JSON 少了 `steps` 字段或字段类型不对，它会被原样存进 `projects.result_json`（JSONB 不做结构校验），前端渲染时才崩溃。这是一个**延迟到用户界面才暴露的错误**。

**修复方向**：定义 `AnalysisResult` Pydantic 模型，`analyze_image` 返回前先校验；校验失败按调用失败处理。前端的 `src/lib/api.ts` 已经有对应的 TypeScript 类型定义，后端补一个对称的即可。

## 副作用

| 副作用 | 是否需要用户批准 |
| --- | --- |
| 写一条 `projects` 记录 | ❌ 不需要 —— 上传行为本身即用户意图 |
| 消耗 Anthropic 额度（约 $0.01–0.03/次） | ❌ 不需要 —— **但无任何用量上限，这是账单风险** |
| 照片发往第三方 | ❌ 未征得同意，**建议补上告知** |

模型**不会**：修改用户数据、发消息、改好友关系、删除任何东西。副作用面很窄，这是好事。

## 降级行为

失败时（无 key、API 报错、JSON 解析失败）一律返回 `MOCK_RESULT` —— 一份写死的"Classic Town House"零件清单。

✅ 好处：接口永不 500，上传流程始终可点通，本地开发不需要 key。

🔴 问题：**用户完全无法分辨自己拿到的是真实分析还是假数据。** 界面上没有任何标记，`projects.result_json` 里也没有存来源标识。用户可能拿着一份和自己照片毫无关系的清单去买零件。

**修复方向**：在结果里加一个来源字段（如 `source: "claude" | "fallback"`），前端对 fallback 结果明确提示"AI 分析暂时不可用，以下为示例数据"。
