# 📖 NotebookLM Gateway API 接口介绍文档

本接口文档详细梳理了 NotebookLM 极简部署网关服务的**所有 API 规范**，分为**管理员鉴权接口**（同步与管理多账户）与**用户业务接口**（调用 NotebookLM 功能）两大类。

---

## 🔒 1. 网关管理员鉴权与管理 API
> **安全要求**：必须在请求头部携带网关部署时配置的管理员 Token。
> 格式：`Authorization: Bearer <GATEWAY_ADMIN_TOKEN>`

### 1.1 一键同步/同步客户端凭证
*   **方法/路径**：`POST /v1/auth/credentials`
*   **用途**：供本地桌面凭证助手同步登录抓取的 Google 账号凭证和为该账号分配的外部 API Key。
*   **请求 Body (JSON)**：
    ```json
    {
      "email": "guyue7737@gmail.com",
      "api_key": "my_notebooklm_key_snkj888",
      "master_token": "oauth2_rt_1/...",
      "storage_state": "{\"cookies\": [...]}"
    }
    ```
*   **返回示例**：
    ```json
    {
      "ok": true,
      "message": "Credentials for guyue7737@gmail.com uploaded and updated successfully."
    }
    ```

### 1.2 列出所有托管账户
*   **方法/路径**：`GET /admin/api/accounts`
*   **用途**：获取所有在 SQLite 数据库中录入的托管账户。
*   **返回示例**：
    ```json
    {
      "ok": true,
      "accounts": [
        {
          "id": 1,
          "email": "guyue7737@gmail.com",
          "api_key": "my_notebooklm_key_snkj888",
          "status": "active",
          "updated_at": "2026-07-12 17:48:40"
        }
      ]
    }
    ```

### 1.3 修改特定账户的调用 Key
*   **方法/路径**：`PUT /admin/api/accounts/{account_id}/key`
*   **用途**：手动或随机更新指定邮箱关联的外部调用 Key，新 Key 会在网关端实时生效，同时旧 Key 的缓存连接会被安全切断。
*   **请求 Body (JSON)**：
    ```json
    {
      "api_key": "nmlg_9fa7b6c5a8d9e2f1"
    }
    ```
*   **返回示例**：
    ```json
    {
      "ok": true,
      "message": "API Key updated successfully."
    }
    ```

### 1.4 切换账户会话状态
*   **方法/路径**：`PUT /admin/api/accounts/{account_id}/status`
*   **用途**：强制切换会话状态，用于临时停用（`expired`）或激活（`active`）该账号。
*   **请求 Body (JSON)**：
    ```json
    {
      "status": "expired"
    }
    ```
*   **返回示例**：
    ```json
    {
      "ok": true,
      "message": "Account status updated to expired."
    }
    ```

### 1.5 删除托管账户
*   **方法/路径**：`DELETE /admin/api/accounts/{account_id}`
*   **用途**：彻底从网关数据库中删除该 Google 账户，并清理其内存连接。
*   **返回示例**：
    ```json
    {
      "ok": true,
      "message": "Account deleted successfully."
    }
    ```

---

## 🌐 2. 用户业务 API
> **安全要求**：请求头中必须携带该托管账号分配的外部 API Key。
> 格式：`Authorization: Bearer <USER_API_KEY>`

### 2.1 笔记本管理 (Notebooks)

#### 2.1.1 获取笔记本列表
*   **方法/路径**：`GET /v1/notebooks`
*   **返回示例**：
    ```json
    {
      "notebooks": [
        {
          "id": "c725a1a9-1b46-4565-9297-f2281acfa9dd",
          "title": "量子力学研究",
          "sources_count": 2,
          "created_at": "2026-07-12T12:00:00Z"
        }
      ]
    }
    ```

#### 2.1.2 创建笔记本
*   **方法/路径**：`POST /v1/notebooks`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "新探索的主题"
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "c725a1a9-1b46-4565-9297-f2281acfa9dd",
      "title": "新探索的主题",
      "sources_count": 0
    }
    ```

#### 2.1.3 获取笔记本详情
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}`
*   **返回示例**：
    ```json
    {
      "id": "c725a1a9-1b46-4565-9297-f2281acfa9dd",
      "title": "新探索的主题",
      "sources_count": 0
    }
    ```

#### 2.1.4 重命名笔记本
*   **方法/路径**：`PATCH /v1/notebooks/{notebook_id}`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "改名后的新笔记本"
    }
    ```
*   **返回示例**：
    ```json
    {
      "status": "renamed",
      "id": "c725a1a9-1b46-4565-9297-f2281acfa9dd"
    }
    ```

#### 2.1.5 删除笔记本
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}`
*   **返回状态**：`204 No Content` (成功删除且无返回值)。

---

### 2.2 文档来源管理 (Sources)

#### 2.2.1 添加自定义文本来源
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/text`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "深空探测技术简史",
      "text": "文本来源的主体内容..."
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "7f085783-9acc-4f0f-88f3-54d32f0011e8",
      "title": "深空探测技术简史"
    }
    ```

#### 2.2.2 上传本地物理文件
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/file`
*   **请求格式**：`multipart/form-data`
*   **表单参数**：
    *   `file`: 上传的文件二进制流（支持 txt、pdf、md、docx 等）
*   **返回示例**：
    ```json
    {
      "id": "8f095783-9acc-4f0f-88f3-54d32f0022ff",
      "title": "上传的文件名.txt"
    }
    ```

#### 2.2.3 获取笔记本下的所有文档来源
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/sources`
*   **返回示例**：
    ```json
    {
      "sources": [
        {
          "id": "7f085783-9acc-4f0f-88f3-54d32f0011e8",
          "title": "深空探测技术简史",
          "type": "text"
        }
      ]
    }
    ```

#### 2.2.4 删除特定文档来源
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/sources/{source_id}`
*   **返回状态**：`204 No Content` (成功删除)。

---

### 2.3 智能对话与配置 (Chat)

#### 2.3.1 配置对话行为 / Preset
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/chat/configure`
*   **请求 Body (JSON)**：
    *   `chat_mode`: enum 预设模式 (`default` / `learning-guide` / `concise` / `detailed`)。
    *   示例 (修改为简洁回答模式)：
    ```json
    {
      "chat_mode": "concise"
    }
    ```
*   **返回示例**：
    ```json
    {
      "status": "configured"
    }
    ```

#### 2.3.2 获取引导提问的建议提示词
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/suggested-prompts`
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "suggestions": [
        {
          "title": "关于这篇简史的3个核心推论是什么？",
          "prompt": "基于已载入的文章内容，梳理并向我阐释..."
        }
      ]
    }
    ```

#### 2.3.2 发起对话 (支持流式打字机效果 SSE)
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/chat`
*   **请求 Body (JSON)**：
    ```json
    {
      "question": "中国嫦娥探测器起到了什么作用？",
      "conversation_id": null
    }
    ```
*   **响应流 (Server-Sent Events)**：返回格式为 `data: <JSON>` 字符串，直到以 `data: [DONE]` 截止：
    ```text
    data: {"text": "中"}
    data: {"text": "国"}
    data: {"text": "的"}
    data: {"text": "嫦娥探测器..."}
    data: [DONE]
    ```

---

### 2.4 笔记管理 (Notes)

#### 2.4.1 创建测试笔记
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/notes`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "我的航天梦笔记",
      "content": "正文内容..."
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "0f0d1b7c-4468-45a3-b380-96c7406985cb",
      "title": "我的航天梦笔记",
      "content": "正文内容..."
    }
    ```

#### 2.4.2 列出所有笔记
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/notes`
*   **返回示例**：
    ```json
    {
      "notes": [
        {
          "id": "0f0d1b7c-4468-45a3-b380-96c7406985cb",
          "title": "我的航天梦笔记",
          "content": "正文内容..."
        }
      ]
    }
    ```

#### 2.4.3 修改笔记内容
*   **方法/路径**：`PUT /v1/notebooks/{notebook_id}/notes/{note_id}`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "修改后的标题",
      "content": "修改后的内容..."
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "0f0d1b7c-4468-45a3-b380-96c7406985cb",
      "title": "修改后的标题",
      "content": "修改后的内容..."
    }
    ```

#### 2.4.4 删除笔记
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/notes/{note_id}`
*   **返回状态**：`204 No Content`。

---

### 2.5 共享管理 (Share)

#### 2.5.1 获取笔记本共享状态
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/share`
*   **返回示例**：
    ```json
    {
      "public_access": "disabled",
      "shared_users": []
    }
    ```

---

### 2.6 智能生成物构建 (Artifacts)

#### 2.6.1 发起异步生成物构建 (例如播客音频、研究简报、答卷卡)
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/artifacts`
*   **说明**：向 NotebookLM Studio 发起构建指令，此操作为非阻塞（异步），会直接秒级返回任务 ID，您可以稍后轮询任务进度。
*   **请求 Body (JSON)**：
    *   `type`: enum 构建种类 (`audio` [音频播客] / `video` [视频] / `slide-deck` [幻灯片] / `quiz` [测验] / `flashcards` [闪卡] / `report` [研究简报])
    *   示例 (一键异步生成研究简报)：
    ```json
    {
      "type": "report",
      "report_format": "briefing-doc",
      "instructions": "帮我把目前的所有文档提炼为一份高层研究简报。"
    }
    ```
*   **返回示例**：
    ```json
    {
      "task_id": "gen_task_6f8b9a1c2d3e"
    }
    ```
