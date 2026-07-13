# NotebookLM Gateway REST API

本文对应网关 `0.2.0` 和 `notebooklm-py==0.7.3`。运行服务后，`/docs` 提供由实际 Pydantic Schema 生成的交互式 OpenAPI。

## 约定

Base URL 示例：`http://localhost:18388`。

除 `/healthz`、静态页面和 OpenAPI 外，所有接口使用：

```http
Authorization: Bearer <TOKEN>
```

Token 分为两类，不能混用：

| 类型 | 可访问范围 |
| --- | --- |
| 管理 Token | `POST /v1/auth/credentials`、`/admin/api/*` |
| 用户 API Key | `GET /v1/server/info`、`/v1/notebooks/*` |

管理 Token 调用业务 API 返回 `403`；无效、缺失或停用的用户 Key 返回 `401`。

普通 JSON 错误格式为：

```json
{"detail": "error message"}
```

上游 SDK 错误另有 `"upstream": true`。常见状态码：`400` 参数错误、`401/403` 认证错误、`404` 不存在、`409` 冲突、`413` 文件过大、`422` Schema 校验失败、`429` 上游限流、`502` 上游错误、`504` 等待超时。

## 管理和账户

### 上传或刷新凭据

`POST /v1/auth/credentials`，使用管理 Token。

```json
{
  "email": "user@example.com",
  "api_key": "unique-user-api-key",
  "storage_state": "{\"cookies\":[...],\"origins\":[]}",
  "master_token": "",
  "android_id": ""
}
```

- `api_key`：16–256 字符，不能含空白；不同账户必须唯一。
- `storage_state`：JSON 字符串，顶层必须是对象且包含 `cookies` 数组。
- `master_token`、`android_id`：只为旧数据兼容保留，方案 A 不依赖它们。
- 同一邮箱再次上传会更新凭据、使旧 SDK 客户端失效，并把账户状态恢复为 `active`。

### 管理路由

| 方法 | 路径 | 请求体/说明 |
| --- | --- | --- |
| `GET` | `/admin/api/accounts` | 账户列表 |
| `DELETE` | `/admin/api/accounts/{account_id}` | 删除账户与其任务记录 |
| `PUT` | `/admin/api/accounts/{account_id}/status` | `{"status":"active|disabled|expired"}` |
| `PUT` | `/admin/api/accounts/{account_id}/key` | `{"api_key":"new-unique-key"}` |

管理控制台位于 `/admin`。

## 系统信息

`GET /v1/server/info` 返回网关版本、SDK 版本、当前账户和能力列表：

```json
{
  "name": "notebooklm-gateway",
  "version": "0.2.0",
  "sdk_version": "0.7.3",
  "account": {"id": 1, "email": "user@example.com", "status": "active"},
  "capabilities": {
    "multi_tenant": true,
    "persistent_jobs": true,
    "artifact_types": ["audio", "video", "cinematic_video", "report", "quiz", "flashcards", "infographic", "slide_deck", "data_table", "mind_map"]
  }
}
```

`GET /healthz` 无需认证，成功返回 `{"status":"ok"}`。

## 笔记本

| 方法 | 路径 | 请求体/响应 |
| --- | --- | --- |
| `GET` | `/v1/notebooks` | `{"notebooks":[...]}` |
| `POST` | `/v1/notebooks` | `{"title":"标题"}`，返回 `201` |
| `GET` | `/v1/notebooks/{notebook_id}` | 获取详情 |
| `PATCH` | `/v1/notebooks/{notebook_id}` | `{"title":"新标题"}` |
| `DELETE` | `/v1/notebooks/{notebook_id}` | 返回 `204` |
| `GET` | `/v1/notebooks/{notebook_id}/description` | 描述、摘要和建议主题 |
| `GET` | `/v1/notebooks/{notebook_id}/suggested-prompts` | `{"suggestions":[...]}` |

## 来源

所有路径以 `/v1/notebooks/{notebook_id}` 开头。

| 方法 | 后缀 | 请求体/说明 |
| --- | --- | --- |
| `GET` | `/sources` | `{"sources":[...]}` |
| `GET` | `/sources/{source_id}` | 来源详情 |
| `POST` | `/sources/url` | `{"url":"https://..."}` |
| `POST` | `/sources/text` | `{"title":"标题","text":"正文"}` |
| `POST` | `/sources/drive` | `{"file_id":"...","title":"...","mime_type":"application/vnd.google-apps.document"}` |
| `POST` | `/sources/batch` | `{"urls":["https://...",...]}`，最多 50 条，分别返回成功与错误 |
| `POST` | `/sources/file` | `multipart/form-data`，字段名 `file` |
| `POST` | `/sources/wait` | `{"source_ids":[],"timeout":120,"interval":1}`；空列表等待全部来源 |
| `GET` | `/sources/{source_id}/text` | 获取去噪全文；`/content` 是同义路径 |
| `GET` | `/sources/{source_id}/guide` | 来源学习指南 |
| `PATCH` | `/sources/{source_id}` | `{"title":"新标题"}` |
| `DELETE` | `/sources/{source_id}` | 返回 `204` |

文件上传限制由 `GATEWAY_MAX_UPLOAD_BYTES` 控制，临时文件在成功或失败后都会删除。

## 对话

### 提问

`POST /v1/notebooks/{notebook_id}/chat`

```json
{
  "question": "归纳三项关键结论",
  "source_ids": ["source-id"],
  "conversation_id": null
}
```

返回 SDK 的完整对话响应，包括回答、会话 ID 和引用信息。这是普通 JSON 响应，不是 SSE；NoteWeb 在客户端执行渐显效果。

### 配置

`POST /v1/notebooks/{notebook_id}/chat/configure`

使用预设模式：

```json
{"chat_mode":"learning_guide"}
```

`chat_mode` 可选 `default`、`learning_guide`、`concise`、`detailed`。

或使用目标配置：

```json
{
  "chat_mode": null,
  "goal": "custom",
  "response_length": "longer",
  "custom_prompt": "以资深研究员身份回答"
}
```

`goal` 可选 `default`、`custom`、`learning_guide`；`response_length` 可选 `default`、`shorter`、`longer`。

## 深度研究

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/v1/notebooks/{notebook_id}/research` | `{"query":"...","source":"web|drive","mode":"fast|deep"}`，返回 `202` |
| `GET` | `/v1/notebooks/{notebook_id}/research/{run_id}` | 查询进度和结果 |
| `POST` | `/v1/notebooks/{notebook_id}/research/{run_id}/import` | 导入结果来源；请求体可省略，也可传 `{"sources":[...]}` |
| `DELETE` | `/v1/notebooks/{notebook_id}/research/{run_id}` | 稳定版 SDK 无公开取消 API，固定返回 `501` |

## 笔记

| 方法 | 路径 | 请求体/说明 |
| --- | --- | --- |
| `GET` | `/v1/notebooks/{notebook_id}/notes` | `{"notes":[...]}` |
| `GET` | `/v1/notebooks/{notebook_id}/notes/{note_id}` | 获取笔记 |
| `POST` | `/v1/notebooks/{notebook_id}/notes` | `{"title":"...","content":"..."}`，返回 `201` |
| `PUT` | `/v1/notebooks/{notebook_id}/notes/{note_id}` | 同上 |
| `DELETE` | `/v1/notebooks/{notebook_id}/notes/{note_id}` | 返回 `204` |

## Studio 生成物

### 创建

`POST /v1/notebooks/{notebook_id}/artifacts`，成功返回 `202`。公共参数：

```json
{
  "type": "audio",
  "source_ids": ["source-id"],
  "language": "zh_Hans",
  "instructions": "面向初学者，先讲概念再讲案例"
}
```

- `type` 必填。
- `source_ids` 省略或为 `null` 时使用上游默认（通常为全部来源）。
- `language` 默认 `zh_Hans`。NoteWeb 还提供 `zh_Hant`、`en`、`ja`、`ko`、`es`、`fr`、`de`。
- `instructions` 最长 20,000 字符。

类型参数：

| `type` | 专属字段 | 可选值 |
| --- | --- | --- |
| `audio` | `audio_format` | `deep_dive`、`brief`、`critique`、`debate` |
|  | `audio_length` | `short`、`default`、`long` |
| `video` | `video_format` | `explainer`、`brief`、`cinematic` |
|  | `video_style` | `auto_select`、`custom`、`classic`、`whiteboard`、`kawaii`、`anime`、`watercolor`、`retro_print`、`heritage`、`paper_craft` |
|  | `style_prompt` | 自定义视觉风格，最长 10,000 字符；`video_style=custom` 时使用 |
| `cinematic_video` | 无 | 使用公共参数 |
| `report` | `report_format` | `briefing_doc`、`study_guide`、`blog_post`、`custom` |
|  | `custom_prompt` | 自定义报告结构 |
|  | `extra_instructions` | 附加写作要求；未提供时回退到 `instructions` |
| `quiz` / `flashcards` | `quantity` | `fewer`、`standard`、`more` |
|  | `difficulty` | `easy`、`medium`、`hard` |
| `infographic` | `orientation` | `landscape`、`portrait`、`square` |
|  | `detail_level` | `concise`、`standard`、`detailed` |
|  | `infographic_style` | `auto_select`、`sketch_note`、`professional`、`bento_grid`、`editorial`、`instructional`、`bricks`、`clay`、`anime`、`kawaii`、`scientific` |
| `slide_deck` | `slide_format` | `detailed_deck`、`presenter_slides` |
|  | `slide_length` | `default`、`short` |
| `data_table` / `mind_map` | 无 | 使用公共参数 |

完整示例：

```json
{
  "type": "video",
  "source_ids": ["source-a", "source-b"],
  "language": "zh_Hans",
  "instructions": "制作五分钟产品说明",
  "video_format": "explainer",
  "video_style": "custom",
  "style_prompt": "深色编辑风格、蓝色数据可视化、克制的镜头运动"
}
```

### 查询与任务持久化

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/v1/notebooks/{notebook_id}/artifacts` | 上游生成物与本网关未完成任务的合并列表；同时返回 `jobs` |
| `GET` | `/v1/notebooks/{notebook_id}/artifacts/{task_id}` | 轮询本网关登记的任务；跨账户、跨笔记本或未知任务返回 `404` |
| `GET` | `/v1/notebooks/{notebook_id}/artifacts/{artifact_id}/prompt` | 返回创建时记录的指令和完整参数 |
| `PATCH` | `/v1/notebooks/{notebook_id}/artifacts/{artifact_id}` | `{"title":"新标题"}` |
| `POST` | `/v1/notebooks/{notebook_id}/artifacts/{artifact_id}/retry` | 重试有本网关任务记录的失败生成物，返回 `202` |
| `DELETE` | `/v1/notebooks/{notebook_id}/artifacts/{artifact_id}` | 返回 `204` |

任务记录写入 SQLite，因此进程重启不会丢失。`prompt` 返回的是本网关保存的创建参数，不调用上游私有 Prompt API。

### 下载

`POST /v1/notebooks/{notebook_id}/artifacts/download`

```json
{
  "type": "slide_deck",
  "artifact_id": "artifact-id",
  "output_format": "pptx"
}
```

`artifact_id` 必填，以避免误下载“最新”生成物。下载对应关系：

| 类型 | 默认格式 | 可选 `output_format` |
| --- | --- | --- |
| `audio` | MP3 | — |
| `video` | MP4 | — |
| `report` | Markdown | — |
| `quiz` / `flashcards` | JSON | `markdown` |
| `infographic` | PNG | — |
| `slide_deck` | PDF | `pptx` |
| `data_table` | CSV | — |
| `mind_map` | JSON | — |

`cinematic_video` 完成后在上游表现为视频生成物，下载时使用 `type: "video"`。

## 共享

| 方法 | 路径 | 请求体/说明 |
| --- | --- | --- |
| `GET` | `/v1/notebooks/{notebook_id}/share` | 当前公开状态、URL 与协作者 |
| `POST` | `/v1/notebooks/{notebook_id}/share/public` | `{"public":true}` |
| `POST` | `/v1/notebooks/{notebook_id}/share/users` | `{"email":"a@example.com","permission":"viewer|editor","notify":true,"welcome_message":""}` |
| `PATCH` | `/v1/notebooks/{notebook_id}/share/users/{email}` | `{"permission":"viewer|editor"}`；邮箱需 URL 编码 |
| `DELETE` | `/v1/notebooks/{notebook_id}/share/users/{email}` | 返回 `204` |
| `POST` | `/v1/notebooks/{notebook_id}/share/view-level` | `{"level":"full_notebook|chat_only"}` |

## 兼容性原则

网关只导入 `notebooklm` 顶层公开对象和公开类型；不保证兼容旧版内嵌 Server 的私有路由、字段或 SSE 格式。SDK 升级必须先核对公开签名、更新 Schema 与本文档，并完成测试后再修改精确版本锁。
