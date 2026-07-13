# 📖 NotebookLM Gateway API 接口参考手册 (完全体)

本手册详细梳理了 NotebookLM 极简部署网关服务的**所有 API 规范**。网关服务采用多账户隔离架构，通过不同的外部调用 API Key 进行租户路由。

---

## 🔑 鉴权说明

本网关包含两套独立的鉴权体系：
1.  **网关管理员鉴权 (Admin Auth)**:
    *   **接口范围**：控制台管理 API、客户端同步凭证 API
    *   **Header 格式**：`Authorization: Bearer <GATEWAY_ADMIN_TOKEN>`
2.  **租户业务鉴权 (User Auth)**:
    *   **接口范围**：笔记本、文档来源、对话、深度探索、笔记、智能生成物及共享管理等业务功能
    *   **Header 格式**：`Authorization: Bearer <USER_API_KEY>`

---

## 🔒 1. 网关管理员管理 API

### 1.1 一键同步/上传客户端凭证
*   **方法/路径**：`POST /v1/auth/credentials`
*   **用途**：供本地桌面凭证助手同步登录抓取的 Google 账号凭证。
*   **请求 Body (JSON)**：
    ```json
    {
      "email": "xxxxxx@gmail.com",
      "api_key": "nmlg_example_key_12345",
      "master_token": "oauth2_rt_1/...",
      "storage_state": "{\"cookies\": [...]}"
    }
    ```
*   **返回示例**：
    ```json
    {
      "ok": true,
      "message": "Credentials for xxxxxx@gmail.com uploaded and updated successfully."
    }
    ```

### 1.2 列出所有托管账户
*   **方法/路径**：`GET /admin/api/accounts`
*   **返回示例**：
    ```json
    {
      "ok": true,
      "accounts": [
        {
          "id": 1,
          "email": "xxxxxx@gmail.com",
          "api_key": "nmlg_example_key_12345",
          "status": "active",
          "updated_at": "2026-07-13 02:40:00"
        }
      ]
    }
    ```

### 1.3 修改特定账户的调用 Key
*   **方法/路径**：`PUT /admin/api/accounts/{account_id}/key`
*   **请求 Body (JSON)**：
    ```json
    {
      "api_key": "nmlg_new_random_key_67890"
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
*   **请求 Body (JSON)**：
    ```json
    {
      "status": "expired" // 可选: active / expired
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
*   **返回示例**：
    ```json
    {
      "ok": true,
      "message": "Account deleted successfully."
    }
    ```

---

## 🌐 2. 租户业务 API (基于 API Key 路由)

### 2.1 系统与元数据 (System & Meta)

#### 2.1.1 获取服务器认证与健康信息
*   **方法/路径**：`GET /v1/server/info`
*   **参数**：`include_account=true` (可选，返回当前 API Key 所映射的 Google 账户配额限制及 Identity)
*   **返回示例**：
    ```json
    {
      "server": "notebooklm-server",
      "version": "1.0.0",
      "auth": {
        "authenticated": true,
        "storage_exists": true,
        "json_valid": true,
        "cookies_present": true,
        "sid_cookie": true,
        "profile": "default"
      },
      "account": {
        "email": "xxxxxx@gmail.com",
        "authuser": "0",
        "available": true,
        "notebook_limit": 100,
        "source_limit": 50,
        "tier": "free",
        "output_language": "zh"
      }
    }
    ```

---

### 2.2 笔记本管理 (Notebooks)

#### 2.2.1 获取笔记本列表
*   **方法/路径**：`GET /v1/notebooks`
*   **返回示例**：
    ```json
    {
      "notebooks": [
        {
          "id": "c725a1a9-1b46-4565-9297-f2281acfa9dd",
          "title": "量子力学研究",
          "sources_count": 2,
          "created_at": "2026-07-13T12:00:00Z"
        }
      ]
    }
    ```

#### 2.2.2 创建笔记本
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

#### 2.2.3 获取笔记本详情
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}`
*   **返回示例**：
    ```json
    {
      "id": "c725a1a9-1b46-4565-9297-f2281acfa9dd",
      "title": "新探索的主题",
      "sources_count": 0
    }
    ```

#### 2.2.4 重命名笔记本
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

#### 2.2.5 删除笔记本
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}`
*   **返回状态**：`204 No Content`

#### 2.2.6 获取笔记本 AI 摘要描述与建议问题
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/description`
*   **用途**：获取笔记本内预加载的 AI 综合描述 (Summary) 和 Suggested Topics 引导词。
*   **返回示例**：
    ```json
    {
      "summary": "这是关于此笔记本内所有参考源的综合内容摘要...",
      "suggested_topics": [
        "量子纠缠在超导电路中的最新进展是什么？",
        "本文提及的量子退相干时间大概是多少？"
      ]
    }
    ```

---

### 2.3 文档来源管理 (Sources)

#### 2.3.1 添加自定义文本来源
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

#### 2.3.2 上传本地物理文件
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/file`
*   **请求格式**：`multipart/form-data`
*   **表单参数**：
    *   `file`: 物理文件二进制流
*   **返回示例**：
    ```json
    {
      "id": "8f095783-9acc-4f0f-88f3-54d32f0022ff",
      "title": "太空物理研究.pdf"
    }
    ```

#### 2.3.3 添加网页 URL 来源
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/url`
*   **请求 Body (JSON)**：
    ```json
    {
      "url": "https://example.com/page",
      "allow_internal": false
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "9f095783-9acc-4f0f-88f3-54d32f0033aa",
      "title": "网页抓取标题"
    }
    ```

#### 2.3.4 添加 Google Drive 文档来源
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/drive`
*   **请求 Body (JSON)**：
    ```json
    {
      "document_id": "1A2B3C4D...",
      "mime_type": "google-doc", // 可填: google-doc / google-sheet / pdf 等
      "title": "可选的自定义文件标题"
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "9f095783-9acc-4f0f-88f3-54d32f0044bb",
      "title": "可选的自定义文件标题"
    }
    ```

#### 2.3.5 批量导入网页来源
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/batch`
*   **说明**：最多支持在一次请求中并行拉取并录入 20 个 URL。
*   **请求 Body (JSON)**：
    ```json
    {
      "urls": [
        "https://example.com/page1",
        "https://example.com/page2"
      ],
      "allow_internal": false
    }
    ```
*   **返回示例**：
    ```json
    {
      "imported": [
        {
          "id": "src_12345a",
          "title": "页面1"
        },
        {
          "id": "src_12345b",
          "title": "页面2"
        }
      ]
    }
    ```

#### 2.3.6 获取文档来源列表
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

#### 2.3.7 获取特定文档来源的详情/解析状态
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/sources/{source_id}`
*   **返回示例**：
    ```json
    {
      "id": "7f085783-9acc-4f0f-88f3-54d32f0011e8",
      "title": "深空探测技术简史",
      "status": "ready", // pending / ready / failed
      "word_count": 1420
    }
    ```

#### 2.3.8 获取文档来源的脱水正文文本
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/sources/{source_id}/text`
*   **用途**：获取已上传文档被 Google 解析去噪后的原始纯文本（脱水 Markdown）。
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "source_id": "7f085783-9acc-4f0f-88f3-54d32f0011e8",
      "text": "# 深空探测技术简史\n深空探测是指航天器在距离地球200万公里以上的空间..."
    }
    ```

#### 2.3.9 同步阻塞等待文档来源就绪
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/sources/wait`
*   **用途**：在添加文档后，挂起请求等待其在 Google 云端完成全文解析索引（避免未就绪时发起对话报错）。
*   **请求 Body (JSON)**：
    ```json
    {
      "source_ids": ["7f085783-9acc-4f0f-88f3-54d32f0011e8"], // 留空则等待全部来源就绪
      "timeout": 120.0, // 超时时间（秒）
      "interval": 1.0 // 轮询间隔（秒）
    }
    ```
*   **返回示例**：
    ```json
    {
      "ready": true,
      "source_ids": ["7f085783-9acc-4f0f-88f3-54d32f0011e8"]
    }
    ```

#### 2.3.10 重命名来源标题
*   **方法/路径**：`PATCH /v1/notebooks/{notebook_id}/sources/{source_id}`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "全新改写后的参考文件名称"
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "7f085783-9acc-4f0f-88f3-54d32f0011e8",
      "title": "全新改写后的参考文件名称"
    }
    ```

#### 2.3.11 删除特定文档来源
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/sources/{source_id}`
*   **返回状态**：`204 No Content`

---

### 2.4 智能对话与配置 (Chat)

#### 2.4.1 配置对话行为 / Preset (含自定义 Persona/Goal 设定)
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/chat/configure`
*   **说明**：支持选用 predefined 预设，或使用 `"goal"` 来直接传递自由意志的个性化 System Prompt 指令！
*   **请求 Body (JSON)**：
    *   *方式 A：经典预设模式*
    ```json
    {
      "chat_mode": "concise" // default / learning-guide / concise / detailed
    }
    ```
    *   *方式 B：自定义 Persona 设定*
    ```json
    {
      "chat_mode": null,
      "goal": "你是一个深空探索的领航员，请用富有科幻感和冷酷理性的语气回答问题。",
      "response_length": "short" // short / default / long
    }
    ```
*   **返回示例**：
    ```json
    {
      "status": "configured"
    }
    ```

#### 2.4.2 获取引导提问的建议提示词
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

#### 2.4.3 发起对话 (支持 SSE 流式返回)
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
    data: [DONE]
    ```

---

### 2.5 深度探索与搜索集成 (Deep Research)

#### 2.5.1 启动研究会话
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/research`
*   **请求 Body (JSON)**：
    *   `query`: 搜索/研究关键词
    *   `source`: 数据来源 (可填 `web` / `drive`)，默认为 `web`
    *   `mode`: 研究深度 (可填 `fast` / `deep`)，默认为 `fast`
    ```json
    {
      "query": "2026年量子计算机最新进展",
      "source": "web",
      "mode": "fast"
    }
    ```
*   **返回示例**：
    ```json
    {
      "task_id": "res_task_9a2b8c3d4e",
      "poll_id": "res_task_9a2b8c3d4e",
      "notebook_id": "c725a1a9..."
    }
    ```

#### 2.5.2 轮询研究进度与结果
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/research/{run_id}`
*   **说明**：`run_id` 为上一接口返回的 `poll_id`
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "run_id": "res_task_9a2b8c3d4e",
      "status": "completed",
      "sources": [
        {
          "title": "量子芯片进展报告",
          "url": "https://example.com/quantum"
        }
      ],
      "report": "量子计算机在拓扑量子比特纠错上取得了重要突破..."
    }
    ```

#### 2.5.3 取消进行中的研究任务
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/research/{run_id}`
*   **返回示例**：
    ```json
    {
      "status": "cancelled",
      "notebook_id": "c725a1a9...",
      "run_id": "res_task_9a2b8c3d4e",
      "cancelled": true
    }
    ```

#### 2.5.4 将研究成果源导入到笔记本中
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/research/{run_id}/import`
*   **返回示例**：
    ```json
    {
      "status": "imported",
      "notebook_id": "c725a1a9...",
      "run_id": "res_task_9a2b8c3d4e",
      "sources_found": 1,
      "imported": [
        {
          "id": "src_quantum_abcde",
          "title": "量子芯片进展报告"
        }
      ]
    }
    ```

---

### 2.6 笔记管理 (Notes)

#### 2.6.1 创建笔记
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/notes`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "我的航天梦笔记",
      "content": "宇宙的尽头是无尽的奥秘待发掘。"
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "0f0d1b7c-4468-45a3-b380-96c7406985cb",
      "title": "我的航天梦笔记",
      "content": "宇宙的尽头是无尽的奥秘待发掘。"
    }
    ```

#### 2.6.2 获取全部笔记列表
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/notes`
*   **返回示例**：
    ```json
    {
      "notes": [
        {
          "id": "0f0d1b7c-4468-45a3-b380-96c7406985cb",
          "title": "我的航天梦笔记",
          "content": "宇宙的尽头是无尽的奥秘待发掘。"
        }
      ]
    }
    ```

#### 2.6.3 修改笔记内容
*   **方法/路径**：`PUT /v1/notebooks/{notebook_id}/notes/{note_id}`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "我的航天梦笔记(已修改)",
      "content": "修改后的内容：引力波与量子物理学正在加速融合。"
    }
    ```
*   **返回示例**：
    ```json
    {
      "id": "0f0d1b7c-4468-45a3-b380-96c7406985cb",
      "title": "我的航天梦笔记(已修改)",
      "content": "修改后的内容：引力波与量子物理学正在加速融合。"
    }
    ```

#### 2.6.4 删除笔记
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/notes/{note_id}`
*   **返回状态**：`204 No Content`

---

### 2.7 智能生成物构建 (Artifacts & Studio)

#### 2.7.1 发起异步生成物构建
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/artifacts`
*   **说明**：向 NotebookLM Studio 发起构建指令，此操作为非阻塞（异步），会直接秒级返回任务 ID，您可以稍后轮询任务进度。
*   **请求 Body (JSON) 详细选项规范**：
    *   `type`: 生成类型 (`audio` [音频播客] / `video` [视频] / `slide-deck` [幻灯片] / `quiz` [测验] / `flashcards` [闪卡] / `infographic` [信息图] / `data-table` [数据表格] / `mind-map` [脑图] / `report` [研究简报])
    *   不同类型专属的可选参数：
        *   `audio` (播客) -> `audio_format` (`deep-dive` / `brief` / `critique` / `debate`), `audio_length` (`short` / `default` / `long`)
        *   `video` (视频) -> `video_format` (`explainer` / `brief` / `cinematic` / `short`), `style` (`auto` / `custom` / `watercolor` / `anime` 等)
        *   `slide-deck` (幻灯片) -> `deck_format` (`detailed` / `presenter`), `deck_length` (`default` / `short`)
        *   `quiz` (测验) & `flashcards` (闪卡) -> `quantity` (`fewer` / `standard` / `more`), `difficulty` (`easy` / `medium` / `hard`)
        *   `infographic` (信息图) -> `orientation` (`landscape` / `portrait` / `square`), `detail` (`concise` / `standard` / `detailed`), `style`
        *   `mind-map` (脑图) -> `map_kind` (`interactive` / `note-backed`)
        *   `report` (研究简报) -> `report_format` (`briefing-doc` / `study-guide` / `blog-post` / `custom`)
    *   *示例 (一键生成高品质答卷测验)*：
    ```json
    {
      "type": "quiz",
      "quantity": "standard",
      "difficulty": "hard",
      "instructions": "出一份关于量子纠缠的硬核单选题测试卷。"
    }
    ```
*   **返回示例**：
    ```json
    {
      "task_id": "gen_task_6f8b9a1c2d3e"
    }
    ```

#### 2.7.2 获取全部生成物列表
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/artifacts`
*   **返回示例**：
    ```json
    {
      "artifacts": [
        {
          "id": "art_pod_12345",
          "title": "我的航天梦-音频对话播客",
          "type": "audio"
        }
      ]
    }
    ```

#### 2.7.3 轮询生成任务进度与状态
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/artifacts/{task_id}`
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "task_id": "gen_task_6f8b9a1c2d3e",
      "status": "completed" // PENDING / IN_PROGRESS / COMPLETED / FAILED
    }
    ```

#### 2.7.4 获取针对该生成物的背景 Prompt
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/artifacts/{artifact_id}/prompt`
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "artifact_id": "art_pod_12345",
      "prompt": "帮我把目前的所有文档提炼为一份高层研究简报。"
    }
    ```

#### 2.7.5 重命名生成物标题
*   **方法/路径**：`PATCH /v1/notebooks/{notebook_id}/artifacts/{artifact_id}`
*   **请求 Body (JSON)**：
    ```json
    {
      "title": "我的航天梦-精选版播客"
    }
    ```
*   **返回示例**：
    ```json
    {
      "status": "renamed",
      "notebook_id": "c725a1a9...",
      "artifact_id": "art_pod_12345",
      "new_title": "我的航天梦-精选版播客"
    }
    ```

#### 2.7.6 重试失败的生成任务
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/artifacts/{artifact_id}/retry`
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "artifact_id": "art_pod_12345",
      "task_id": "art_pod_12345",
      "status": "pending"
    }
    ```

#### 2.7.7 下载及导出已生成的智能生成物文件
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/artifacts/download`
*   **请求 Body 参数 (JSON)**：
    *   `type` (必填): 下载类型，支持如下：
        *   `audio`: 音频播客 (导出格式: `.mp3`)
        *   `video`: 视频 (导出格式: `.mp4`)
        *   `slide-deck`: 幻灯片 (默认格式: `.pdf`，可选配置 `output_format`)
        *   `infographic`: 信息图 (导出格式: `.png`)
        *   `report`: 研究简报 (导出格式: `.md`)
        *   `mind-map`: 思维导图 (导出格式: `.json`)
        *   `data-table`: 数据表格 (导出格式: `.csv`)
        *   `quiz`: 思考测验 (默认格式: `.json`，可选配置 `output_format`)
        *   `flashcards`: 互动闪卡 (默认格式: `.json`，可选配置 `output_format`)
    *   `output_format` (可选): 指定导出文件格式扩展名：
        *   `slide-deck` 允许: `pdf` / `pptx`
        *   `quiz` & `flashcards` 允许: `json` / `markdown` / `html`
    *   *示例 1 (下载默认播客 MP3)*：
    ```json
    {
      "type": "audio"
    }
    ```
    *   *示例 2 (将试卷测验导出为 Markdown 格式下载)*：
    ```json
    {
      "type": "quiz",
      "output_format": "markdown"
    }
    ```
*   **返回流**：对应格式的二进制字节流 (以 `FileResponse` 形式返回物理文件，网关会在传输完成后安全自动清理服务器生成的临时缓存文件)。

#### 2.7.8 彻底删除生成物
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/artifacts/{artifact_id}`
*   **返回状态**：`204 No Content`

---

### 2.8 笔记本共享管理 (Share)

#### 2.8.1 获取共享状态
*   **方法/路径**：`GET /v1/notebooks/{notebook_id}/share`
*   **返回示例**：
    ```json
    {
      "public_access": "disabled",
      "shared_users": [
        {
          "email": "collaborator@example.com",
          "permission": "viewer"
        }
      ]
    }
    ```

#### 2.8.2 开启/禁用公开链接分享
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/share/public`
*   **请求 Body (JSON)**：
    ```json
    {
      "enable": true
    }
    ```
*   **返回示例**：
    ```json
    {
      "public_access": "enabled",
      "shared_users": []
    }
    ```

#### 2.8.3 添加协作者
*   **方法/路径**：`POST /v1/notebooks/{notebook_id}/share/users`
*   **请求 Body (JSON)**：
    *   `permission`: 可填 `viewer` / `editor`
    ```json
    {
      "email": "partner@example.com",
      "permission": "editor",
      "notify": false
    }
    ```
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "email": "partner@example.com",
      "permission": "editor",
      "notify": false
    }
    ```

#### 2.8.4 更改协作者的读写权限
*   **方法/路径**：`PATCH /v1/notebooks/{notebook_id}/share/users/{email}`
*   **请求 Body (JSON)**：
    ```json
    {
      "permission": "viewer"
    }
    ```
*   **返回示例**：
    ```json
    {
      "notebook_id": "c725a1a9...",
      "email": "partner@example.com",
      "permission": "viewer"
    }
    ```

#### 2.8.5 移除协作者权限
*   **方法/路径**：`DELETE /v1/notebooks/{notebook_id}/share/users/{email}`
*   **返回状态**：`204 No Content`
