/**
 * NoteWeb - NotebookLM Gateway API Client
 * 封装与网关后端交互的 HTTP 请求，并为普通 JSON 对话响应提供渐显回调
 */

export class APIClient {
  constructor(baseURL = window.location.origin, apiKey = '') {
    this.baseURL = this.sanitizeURL(baseURL);
    this.apiKey = apiKey;
  }

  sanitizeURL(url) {
    let clean = url.trim();
    if (clean.endsWith('/')) {
      clean = clean.slice(0, -1);
    }
    return clean;
  }

  setCredentials(baseURL, apiKey) {
    this.baseURL = this.sanitizeURL(baseURL);
    this.apiKey = apiKey;
  }

  /**
   * 基础请求封装
   */
  async request(method, path, body = null, options = {}) {
    const url = `${this.baseURL}${path}`;
    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      ...options.headers
    };

    const config = {
      method: method.toUpperCase(),
      headers,
      ...options
    };

    if (body) {
      if (body instanceof FormData) {
        // FormData 上传时不能手动设 Content-Type，浏览器会自动注入 boundary
        config.body = body;
      } else {
        headers['Content-Type'] = 'application/json';
        config.body = JSON.stringify(body);
      }
    }

    try {
      const response = await fetch(url, config);

      if (response.status === 204) {
        return { ok: true, status: 204 };
      }

      const contentType = response.headers.get('content-type') || '';
      let data;
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg = data?.detail || data?.message || `HTTP 错误 ${response.status}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error(`API 请求失败 [${method} ${path}]:`, error);
      throw error;
    }
  }

  // ==========================================
  // 1. 系统与账户信息 (System & Meta)
  // ==========================================
  async getServerInfo() {
    return this.request('GET', '/v1/server/info?include_account=true');
  }

  // ==========================================
  // 2. 笔记本管理 (Notebooks)
  // ==========================================
  async listNotebooks() {
    const res = await this.request('GET', '/v1/notebooks');
    return res.notebooks || [];
  }

  async createNotebook(title) {
    return this.request('POST', '/v1/notebooks', { title });
  }

  async getNotebook(notebookId) {
    return this.request('GET', `/v1/notebooks/${notebookId}`);
  }

  async renameNotebook(notebookId, title) {
    return this.request('PATCH', `/v1/notebooks/${notebookId}`, { title });
  }

  async deleteNotebook(notebookId) {
    return this.request('DELETE', `/v1/notebooks/${notebookId}`);
  }

  // ==========================================
  // 3. 文档来源管理 (Sources)
  // ==========================================
  async listSources(notebookId) {
    const res = await this.request('GET', `/v1/notebooks/${notebookId}/sources`);
    return res.sources || [];
  }

  async addSourceText(notebookId, title, text) {
    return this.request('POST', `/v1/notebooks/${notebookId}/sources/text`, { title, text });
  }

  async addSourceURL(notebookId, url, allowInternal = false) {
    return this.request('POST', `/v1/notebooks/${notebookId}/sources/url`, { url, allow_internal: allowInternal });
  }

  async addSourceBatch(notebookId, urls, allowInternal = false) {
    return this.request('POST', `/v1/notebooks/${notebookId}/sources/batch`, { urls, allow_internal: allowInternal });
  }

  async addSourceFile(notebookId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('POST', `/v1/notebooks/${notebookId}/sources/file`, formData);
  }

  async waitSources(notebookId, sourceIds = [], timeout = 120.0, interval = 1.0) {
    return this.request('POST', `/v1/notebooks/${notebookId}/sources/wait`, {
      source_ids: sourceIds,
      timeout,
      interval
    });
  }

  async getSource(notebookId, sourceId) {
    return this.request('GET', `/v1/notebooks/${notebookId}/sources/${sourceId}`);
  }

  async getSourceText(notebookId, sourceId) {
    const res = await this.request('GET', `/v1/notebooks/${notebookId}/sources/${sourceId}/text`);
    return res.text || '';
  }

  async renameSource(notebookId, sourceId, title) {
    return this.request('PATCH', `/v1/notebooks/${notebookId}/sources/${sourceId}`, { title });
  }

  async deleteSource(notebookId, sourceId) {
    return this.request('DELETE', `/v1/notebooks/${notebookId}/sources/${sourceId}`);
  }

  // ==========================================
  // 4. 智能对话与配置 (Chat)
  // ==========================================
  async configureChat(notebookId, chatMode = 'default', goal = null, responseLength = 'default') {
    const payload = chatMode === 'custom' 
      ? {
          chat_mode: null,
          goal: 'custom',
          custom_prompt: goal,
          response_length: responseLength === 'short' ? 'shorter' : responseLength === 'long' ? 'longer' : 'default'
        }
      : { chat_mode: chatMode };
    return this.request('POST', `/v1/notebooks/${notebookId}/chat/configure`, payload);
  }
  async getSuggestedPrompts(notebookId) {
    const res = await this.request('GET', `/v1/notebooks/${notebookId}/suggested-prompts`);
    return res.suggestions || [];
  }

  async getNotebookDescription(notebookId) {
    return this.request('GET', `/v1/notebooks/${notebookId}/description`);
  }

  /**
   * 发起对话 (模拟流式输出以兼容原版UI动效)
   */
  async chatStream(notebookId, question, conversationId = null, onChunk, onDone, onError) {
    const url = `${this.baseURL}/v1/notebooks/${notebookId}/chat`;
    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({ question, conversation_id: conversationId })
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errMsg = `HTTP 错误 ${response.status}`;
        try {
          const errObj = JSON.parse(errorText);
          errMsg = errObj.detail || errObj.message || errMsg;
        } catch (_) {}
        throw new Error(errMsg);
      }

      const resJson = await response.json();
      const answer = resJson.answer || '';
      
      // 模拟打字机效果流式输出，使得前端流式渐显动画保持流畅
      let index = 0;
      const charsPerTick = 3;
      const timer = setInterval(() => {
        if (index >= answer.length) {
          clearInterval(timer);
          onDone(resJson);
          return;
        }
        const chunk = answer.substring(index, index + charsPerTick);
        index += charsPerTick;
        onChunk(chunk);
      }, 10);
    } catch (error) {
      console.error('对话请求失败:', error);
      onError(error);
    }
  }

  // ==========================================
  // 5. 深度探索 (Deep Research)
  // ==========================================
  async startResearch(notebookId, query, source = 'web', mode = 'fast') {
    return this.request('POST', `/v1/notebooks/${notebookId}/research`, {
      query,
      source,
      mode
    });
  }

  async getResearchStatus(notebookId, runId) {
    return this.request('GET', `/v1/notebooks/${notebookId}/research/${runId}`);
  }

  async cancelResearch(notebookId, runId) {
    return this.request('DELETE', `/v1/notebooks/${notebookId}/research/${runId}`);
  }

  async importResearch(notebookId, runId) {
    return this.request('POST', `/v1/notebooks/${notebookId}/research/${runId}/import`);
  }

  // ==========================================
  // 6. 笔记管理 (Notes)
  // ==========================================
  async listNotes(notebookId) {
    const res = await this.request('GET', `/v1/notebooks/${notebookId}/notes`);
    return res.notes || [];
  }

  async createNote(notebookId, title, content) {
    return this.request('POST', `/v1/notebooks/${notebookId}/notes`, { title, content });
  }

  async updateNote(notebookId, noteId, title, content) {
    return this.request('PUT', `/v1/notebooks/${notebookId}/notes/${noteId}`, { title, content });
  }

  async deleteNote(notebookId, noteId) {
    return this.request('DELETE', `/v1/notebooks/${notebookId}/notes/${noteId}`);
  }

  // ==========================================
  // 7. 智能生成物构建 (Artifacts & Studio)
  // ==========================================
  async listArtifacts(notebookId) {
    const res = await this.request('GET', `/v1/notebooks/${notebookId}/artifacts`);
    return (res.artifacts || []).map(artifact => ({
      ...artifact,
      status: String(artifact.status || 'completed').toLowerCase(),
      type: String(artifact.type || 'unknown').replaceAll('-', '_')
    }));
  }

  async createArtifact(notebookId, payload) {
    return this.request('POST', `/v1/notebooks/${notebookId}/artifacts`, payload);
  }

  async getArtifactStatus(notebookId, taskId) {
    const result = await this.request('GET', `/v1/notebooks/${notebookId}/artifacts/${taskId}`);
    return { ...result, status: String(result.status || '').toLowerCase() };
  }

  async getArtifactPrompt(notebookId, artifactId) {
    return this.request('GET', `/v1/notebooks/${notebookId}/artifacts/${artifactId}/prompt`);
  }

  async renameArtifact(notebookId, artifactId, title) {
    return this.request('PATCH', `/v1/notebooks/${notebookId}/artifacts/${artifactId}`, { title });
  }

  async retryArtifact(notebookId, artifactId) {
    return this.request('POST', `/v1/notebooks/${notebookId}/artifacts/${artifactId}/retry`);
  }

  async deleteArtifact(notebookId, artifactId) {
    return this.request('DELETE', `/v1/notebooks/${notebookId}/artifacts/${artifactId}`);
  }

  /**
   * 下载二进制媒体文件 (返回 Blob 对象)
   */
  async downloadArtifact(notebookId, type, artifactId, outputFormat = null) {
    const url = `${this.baseURL}/v1/notebooks/${notebookId}/artifacts/download`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ type, artifact_id: artifactId, output_format: outputFormat })
    });

    if (!response.ok) {
      let detail = `媒体下载失败: ${response.status}`;
      try { detail = (await response.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }

    return await response.blob();
  }

  // ==========================================
  // 8. 笔记本共享管理 (Share)
  // ==========================================
  async getShareStatus(notebookId) {
    return this.request('GET', `/v1/notebooks/${notebookId}/share`);
  }

  async togglePublicShare(notebookId, enable) {
    return this.request('POST', `/v1/notebooks/${notebookId}/share/public`, { public: enable });
  }

  async addCollaborator(notebookId, email, permission = 'viewer', notify = false) {
    return this.request('POST', `/v1/notebooks/${notebookId}/share/users`, { email, permission, notify });
  }

  async updateCollaborator(notebookId, email, permission) {
    return this.request('PATCH', `/v1/notebooks/${notebookId}/share/users/${encodeURIComponent(email)}`, { permission });
  }

  async removeCollaborator(notebookId, email) {
    return this.request('DELETE', `/v1/notebooks/${notebookId}/share/users/${encodeURIComponent(email)}`);
  }
}
