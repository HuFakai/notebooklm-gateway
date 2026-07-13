---
layout: home

hero:
  name: NotebookLM Gateway
  text: 稳定版公开 API + 自有薄网关
  tagline: 多租户认证、加密凭据、持久化 Studio 任务与响应式 NoteWeb
  actions:
    - theme: brand
      text: 快速开始
      link: /#快速开始
    - theme: alt
      text: REST API
      link: /api
    - theme: alt
      text: 架构决策
      link: /architecture

features:
  - title: 清晰依赖边界
    details: 精确依赖 notebooklm-py 0.7.3，只调用稳定版公开 Python API，不内嵌上游源码。
  - title: 多租户与数据安全
    details: 管理/用户 Token 隔离，Fernet 加密凭据，HMAC Key 索引，有界 SDK 客户端池。
  - title: 完整 Studio
    details: 10 类智能生成物、公开参数选择、重启可恢复任务、精确 artifact_id 下载和多格式预览。
  - title: Liquid Knowledge Studio
    details: 使用 liquid-glass-react 渐进增强导航、Studio 与配置面板，并为 Safari、Firefox 和低动效设备提供可靠回退。
---

## 快速开始

```bash
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
# 将输出写入 .env 的 GATEWAY_ADMIN_TOKEN
docker compose up -d --build
```

访问：

- NoteWeb：`http://localhost:18388/noteweb/`
- 管理控制台：`http://localhost:18388/admin`
- 交互式 OpenAPI：`http://localhost:18388/docs`
- 健康检查：`http://localhost:18388/healthz`

`GATEWAY_ADMIN_TOKEN` 必须至少 32 字节，示例值与旧版弱默认值会被拒绝。请整体持久化和备份 `data/`，尤其是 `gateway.db` 与 `.gateway-key`。

## 添加账户

凭据助手使用 `notebooklm-py` 文档化的 `notebooklm login`：

```bash
python -m venv .venv-client
source .venv-client/bin/activate
pip install -e '.[client]'
python gateway_client/app.py
```

填写网关地址、管理 Token、账户邮箱和独立用户 API Key，完成系统 Chrome 中的 Google/NotebookLM 登录后上传即可。

## 使用 NoteWeb

打开 `/noteweb/`，输入用户 API Key。Key 默认只保存在当前浏览器会话，只有主动勾选“长期保存”才写入本机长期存储。

Studio 提供：音频、视频、电影视频、报告、测验、闪卡、信息图、幻灯片、数据表和思维导图。每次任务可独立选择来源、语言、格式、长度、风格、难度与内容指令。

## 认证

| Token | 权限 |
| --- | --- |
| 管理 Token | 上传凭据与 `/admin/api/*` |
| 用户 API Key | `/v1/server/info` 与 `/v1/notebooks/*` |

```bash
curl http://localhost:18388/v1/notebooks \
  -H "Authorization: Bearer $USER_API_KEY"
```

两类 Token 不能混用。生产服务应放在 HTTPS 反向代理之后，CORS 默认保持关闭。

## 文档导航

- [REST API](/api)
- [架构决策](/architecture)
- [旧版迁移](/migration)

> 这是基于非官方 SDK 的社区项目，不是 Google 官方产品。上游接口可能变化，升级 SDK 前请完成签名核对和回归验证。
