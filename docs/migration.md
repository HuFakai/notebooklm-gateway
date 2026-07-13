# 从旧版内嵌网关迁移

本文面向包含 `gateway_server/notebooklm/` 副本的旧部署。升级后的网关版本为 `0.2.0`，直接依赖 `notebooklm-py==0.7.3`。

## 升级前

1. 停止旧服务，避免迁移时继续写入。
2. 整体备份 `data/` 和 `.env`，确认备份中包含 `gateway.db`。
3. 记录旧的账户邮箱和用户 API Key；不要把凭据粘贴到工单或日志。
4. 为新版本生成至少 32 字节的管理 Token，旧默认值会被拒绝。

```bash
cp -a data "data.backup.$(date +%Y%m%d-%H%M%S)"
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

## 数据库自动迁移

首次启动会原地执行：

- 增加 `api_key_hash`、`android_id` 和生成任务表/索引。
- 生成 `data/.gateway-key`（权限 `0600`），或使用 `GATEWAY_ENCRYPTION_KEY`。
- 加密已有 API Key、Storage State、master token 和 android id。
- 为 API Key 建立 HMAC 查找索引。

迁移前务必备份。迁移后必须一起保留 `gateway.db` 和 `.gateway-key`；只恢复数据库、不恢复密钥将无法解密凭据。

## 推荐升级步骤

```bash
git pull
cp .env.example .env.new
# 把新生成的 GATEWAY_ADMIN_TOKEN 和需要的参数写入实际 .env
docker compose build --no-cache
docker compose up -d
docker compose logs -f gateway
```

验证：

```bash
curl http://localhost:18388/healthz
curl http://localhost:18388/v1/server/info \
  -H "Authorization: Bearer $USER_API_KEY"
```

然后访问 `/admin` 确认账户状态，访问 `/noteweb/` 验证笔记本、来源和 Studio。

## 已部署服务器升级

以下命令只在部署服务器上执行。假设代码位于 `/opt/notebooklm-gateway`，并使用仓库中的 Compose 服务名 `gateway`：

```bash
cd /opt/notebooklm-gateway

# 1. 备份数据库、加密密钥和当前环境配置
stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "../notebooklm-backup-$stamp"
cp -a data .env "../notebooklm-backup-$stamp/"

# 2. 获取已经合并到 main 的版本
git fetch origin
git switch main
git pull --ff-only origin main

# 3. 在服务器重新构建并滚动替换网关
docker compose build --pull gateway
docker compose up -d --no-deps gateway

# 4. 验证健康状态和版本
docker compose ps
curl --fail http://127.0.0.1:${GATEWAY_PORT:-18388}/healthz
docker compose logs --tail=200 gateway
```

不要执行 `docker compose down -v`，它可能移除持久化数据。`data/gateway.db` 与 `data/.gateway-key` 必须作为同一个备份单元；首次运行新版本时数据库会自动加密迁移。

如果服务器前面有 Nginx/Caddy，容器端口和反向代理地址无需变化。NoteWeb 的 LiquidGlass bundle 已提交到仓库并打包进 Python wheel，服务器不需要 Node.js 或 `npm install`。

回滚时停止新容器，切回升级前提交并恢复整份 `data/` 与 `.env` 备份，再重新构建服务；不要让旧版本直接读取已经迁移后的数据库。

## 行为变化

| 旧行为 | 新行为 |
| --- | --- |
| 仓库内嵌并修改 SDK 源码 | 精确依赖 PyPI 稳定版，只用公开 API |
| 管理 Token 可能使用弱默认值或查询参数 | 必须是至少 32 字节的 Bearer Token |
| 管理 Token 可与用户 Key 混用 | 两类 Token 严格隔离 |
| CORS 允许任意 Origin | 默认关闭，只接受显式 `GATEWAY_CORS_ORIGINS` |
| 凭据以明文保存在 SQLite | Fernet 加密，Key 使用 HMAC 查找 |
| 内存保存生成任务 | SQLite 持久化且带账户/笔记本归属 |
| 下载可能选择最新生成物 | 客户端必须传明确的 `artifact_id` |
| 生成类型和参数较少 | 10 类 Studio 生成物及稳定版公开参数 |
| Key 默认长期保存在浏览器 | NoteWeb 默认使用 `sessionStorage`，长期保存需主动勾选 |
| 依赖私有 master-token 刷新 | 使用 `notebooklm login` 和 Storage State Cookie 回写 |
| 提供研究取消入口 | 稳定版无公开取消能力，API 返回 `501`、前端禁用 |

## 外部客户端需要调整

### 认证

统一使用：

```http
Authorization: Bearer <token>
```

不要把管理 Token 放在查询字符串、`X-Admin-Token` 或业务 API 请求中。

### Studio 类型名

使用下划线形式：`cinematic_video`、`slide_deck`、`data_table`、`mind_map`。参数和值详见 [API 文档](/api#studio-创建)。

### 任务和下载

创建返回的 `task_id` 只允许由创建账户在同一笔记本轮询。下载请求必须包含真实生成物的 `artifact_id`：

```json
{"type":"audio","artifact_id":"artifact-id"}
```

### 对话响应

`POST /chat` 返回普通 JSON。旧客户端若期待网关 SSE，需要改为读取 JSON；NoteWeb 的逐字效果在浏览器端完成。

## 凭据失效

新版本不调用私有 master-token 引导接口。当账户状态为 `expired` 或 NotebookLM 返回认证错误时：

1. 打开桌面凭据助手。
2. 使用同一邮箱和用户 API Key 再次执行浏览器登录。
3. 上传新的 `storage_state.json`。
4. 网关会替换凭据、关闭旧客户端并将状态恢复为 `active`。

## 回滚

如果必须回滚：

1. 停止新服务。
2. 保存新版本日志和整个新 `data/` 供排查。
3. 恢复升级前的代码、`.env` 和完整 `data` 备份。
4. 不要把已经加密的新版数据库直接交给不认识该格式的旧服务。

回滚不会撤销已经发送到 NotebookLM 的上游操作。
