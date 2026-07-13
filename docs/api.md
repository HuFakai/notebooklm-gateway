# REST API

本文对应 Gateway `0.2.0` 与 `notebooklm-py==0.7.3`。运行实例的 `/docs` 是由真实 Schema 生成的完整交互式 OpenAPI；仓库根目录的 `API.md` 包含更详细的请求示例。

## 认证与错误

```http
Authorization: Bearer <TOKEN>
```

管理 Token 仅可访问凭据和 `/admin/api/*`；用户 Key 仅可访问 `/v1/server/info` 与 `/v1/notebooks/*`。两者混用会返回 `401` 或 `403`。

错误通常为 `{"detail":"..."}`；上游 SDK 错误另有 `"upstream":true`。

## 路由概览

| 范围 | 路径 |
| --- | --- |
| 健康检查 | `GET /healthz` |
| 上传凭据 | `POST /v1/auth/credentials` |
| 账户管理 | `/admin/api/accounts*` |
| 系统信息 | `GET /v1/server/info` |
| 笔记本 | `/v1/notebooks*` |
| 来源 | `/v1/notebooks/{id}/sources*` |
| 对话 | `/v1/notebooks/{id}/chat*` |
| 研究 | `/v1/notebooks/{id}/research*` |
| 笔记 | `/v1/notebooks/{id}/notes*` |
| Studio | `/v1/notebooks/{id}/artifacts*` |
| 共享 | `/v1/notebooks/{id}/share*` |

## 上传凭据

`POST /v1/auth/credentials` 使用管理 Token：

```json
{
  "email": "user@example.com",
  "api_key": "unique-user-api-key",
  "storage_state": "{\"cookies\":[...],\"origins\":[]}"
}
```

`storage_state` 必须是包含 `cookies` 数组的 JSON 字符串。建议始终由桌面凭据助手生成。

## Studio 创建

`POST /v1/notebooks/{notebook_id}/artifacts`

```json
{
  "type": "infographic",
  "source_ids": ["source-id"],
  "language": "zh_Hans",
  "instructions": "突出三项关键结论",
  "orientation": "landscape",
  "detail_level": "detailed",
  "infographic_style": "professional"
}
```

支持类型：

- `audio`：`audio_format`、`audio_length`
- `video`：`video_format`、`video_style`、`style_prompt`
- `cinematic_video`
- `report`：`report_format`、`custom_prompt`、`extra_instructions`
- `quiz`、`flashcards`：`quantity`、`difficulty`
- `infographic`：`orientation`、`detail_level`、`infographic_style`
- `slide_deck`：`slide_format`、`slide_length`
- `data_table`、`mind_map`

公共字段是 `source_ids`、`language` 和 `instructions`。创建返回 `task_id` 后使用：

```http
GET /v1/notebooks/{notebook_id}/artifacts/{task_id}
```

任务按账户和笔记本持久化，未知或跨租户任务返回 `404`。

## Studio 下载

`POST /v1/notebooks/{notebook_id}/artifacts/download`

```json
{"type":"slide_deck","artifact_id":"artifact-id","output_format":"pptx"}
```

`artifact_id` 必填。默认格式：音频 MP3、视频 MP4、报告 Markdown、测验/闪卡 JSON、信息图 PNG、幻灯片 PDF、数据表 CSV、思维导图 JSON。测验/闪卡可选 `markdown`，幻灯片可选 `pptx`。

## 稳定版边界

- 研究取消路由返回 `501`，因为 0.7.3 没有公开取消 API。
- 对话返回普通 JSON，不是网关 SSE。
- Prompt 查询返回本网关保存的创建参数，不调用上游私有接口。
- `master_token` 和 `android_id` 仅作为旧数据兼容字段保留。

请求字段、枚举值、全部 CRUD 与共享路由请查看运行实例的 `/docs` 或仓库根目录 `API.md`。
