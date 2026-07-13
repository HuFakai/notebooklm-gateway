/**
 * NoteWeb - Sources Component
 * 管理文档参考源的列表渲染、多种类型录入（文本、网页、物理文件上传、网盘）、异步等待以及脱水文本阅读
 */

let selectedFile = null;

export async function initSources(notebookId, refreshActiveTab = true) {
  try {
    const sources = await window.apiClient.listSources(notebookId);
    window.state.sources = sources;
    renderSourcesList();
    
    // 如果当前处于 Guide 标签页下，也刷新 Guide 内的文档源及建议等
    if (refreshActiveTab && window.state.activeTab === 'guide') {
      const { renderGuideTab } = await import('./guide.js');
      renderGuideTab();
    }
  } catch (err) {
    console.error('加载参考源失败:', err);
    window.showToast('加载参考源失败', 'error');
  }
}

export function renderSourcesList() {
  const container = document.getElementById('sources-list');
  if (!container) return;

  if (window.state.sources.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无参考文档</div>';
    return;
  }

  container.innerHTML = window.state.sources.map(src => {
    // 根据来源类型匹配图标
    let iconSvg = '';
    if (['text', 'pasted_text'].includes(src.type)) {
      iconSvg = `<svg class="item-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`;
    } else if (['url', 'web_page', 'youtube'].includes(src.type)) {
      iconSvg = `<svg class="item-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`;
    } else if (['drive', 'google_docs', 'google_slides', 'google_sheets'].includes(src.type)) {
      iconSvg = `<svg class="item-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 19L17 5H7L2 19H22Z"/><path d="M12 2V5"/></svg>`;
    } else {
      // 默认文件
      iconSvg = `<svg class="item-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`;
    }

    // 状态修饰
    let statusClass = '';
    let statusTip = '';
    if (['pending', 'processing'].includes(src.status)) {
      statusClass = 'source-pending';
      statusTip = ' [解析中]';
    } else if (['failed', 'error'].includes(src.status)) {
      statusClass = 'source-failed';
      statusTip = ' [失败]';
    }

    return `
      <div class="list-item source-item ${statusClass}" data-id="${window.escapeHTML(src.id)}">
        <div class="item-info">
          ${iconSvg}
          <span class="item-name" title="${window.escapeHTML((src.title || '未命名来源') + statusTip)}">${window.escapeHTML((src.title || '未命名来源') + statusTip)}</span>
        </div>
        <div class="item-actions">
          <button class="section-action-btn delete-src-btn" data-id="${window.escapeHTML(src.id)}" title="删除该来源">
            <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    `;
  }).join('');

  // 绑定查看脱水文本事件
  container.querySelectorAll('.source-item').forEach(el => {
    el.addEventListener('click', (e) => {
      // 如果点击的是删除按钮，则不触发查看
      if (e.target.closest('.delete-src-btn')) return;
      const srcId = el.getAttribute('data-id');
      viewSourceText(srcId);
    });
  });

  // 绑定删除来源事件
  container.querySelectorAll('.delete-src-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const srcId = btn.getAttribute('data-id');
      const confirmed = confirm('确定要从本笔记本中移除该参考源吗？');
      if (!confirmed) return;

      try {
        if (window.state.summaryCache) {
          delete window.state.summaryCache[window.state.currentNotebookId];
        }
        await window.apiClient.deleteSource(window.state.currentNotebookId, srcId);
        window.showToast('参考源已成功删除');
        await initSources(window.state.currentNotebookId);
      } catch (err) {
        window.showToast(`删除参考源失败: ${err.message}`, 'error');
      }
    });
  });
}

// 查看来源去噪正文
async function viewSourceText(sourceId) {
  const titleDisplay = document.getElementById('source-viewer-title');
  const contentDisplay = document.getElementById('source-viewer-content');
  
  const src = window.state.sources.find(s => s.id === sourceId);
  titleDisplay.textContent = src ? src.title : '文档内容查看';
  contentDisplay.innerHTML = '<div class="spinner-wave"><span></span><span></span><span></span><span></span></div><p style="text-align:center; color:var(--neon-blue); font-size:0.85rem; margin-top:0.5rem;">正在从 Google 解析服务器拉取并合成脱水文本...</p>';
  
  window.showSlideover('slideover-source-viewer');

  try {
    const text = await window.apiClient.getSourceText(window.state.currentNotebookId, sourceId);
    contentDisplay.innerHTML = window.renderMarkdown(text || "该参考源无文本内容。");
  } catch (err) {
    contentDisplay.textContent = `拉取正文失败: ${err.message}`;
    contentDisplay.style.color = 'var(--neon-red)';
  }
}

// 异步阻塞等待解析并刷新
async function waitAndRefreshSources(notebookId, sourceIds) {
  window.showToast('文档上传成功，云端 AI 正在对内容进行索引和分析...', 'warning');
  try {
    await window.apiClient.waitSources(notebookId, sourceIds);
    window.showToast('文档索引已就绪！', 'success');
  } catch (err) {
    window.showToast(`文档就绪等待超时或发生错误: ${err.message}`, 'error');
  }
  // 无论是成功还是超时，刷新列表并清空已有的摘要缓存以强制重新生成
  if (window.state.summaryCache) {
    delete window.state.summaryCache[notebookId];
  }
  await initSources(notebookId);
}

// 绑定添加参考来源的相关交互
document.addEventListener('DOMContentLoaded', () => {
  const btnAddSource = document.getElementById('btn-add-source');
  const btnSubmitSource = document.getElementById('btn-submit-source');
  
  // 弹窗内的 Sub-tab 切换
  document.querySelectorAll('.stab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.stab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      document.querySelectorAll('.source-tab-content').forEach(c => c.classList.remove('active'));
      const activeContentId = btn.getAttribute('data-stab');
      document.getElementById(`stab-content-${activeContentId}`).classList.add('active');
    });
  });

  btnAddSource.addEventListener('click', () => {
    // 重置表单
    document.getElementById('source-text-title').value = '';
    document.getElementById('source-text-body').value = '';
    document.getElementById('source-url-input').value = '';
    document.getElementById('source-urls-batch').value = '';
    document.getElementById('source-drive-docid').value = '';
    document.getElementById('source-drive-title').value = '';
    selectedFile = null;
    document.getElementById('source-file-selected').classList.add('hidden');
    document.getElementById('source-file-dropzone').classList.remove('hidden');

    window.showModal('modal-add-source');
  });

  // ==== 拖拽上传物理文件部分 ====
  const dropzone = document.getElementById('source-file-dropzone');
  const fileInput = document.getElementById('source-file-input');
  const fileSelectedStatus = document.getElementById('source-file-selected');
  const btnClearFile = document.getElementById('btn-clear-file');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  btnClearFile.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = '';
    fileSelectedStatus.classList.add('hidden');
    dropzone.classList.remove('hidden');
  });

  function handleFileSelected(file) {
    if (file.size > 20 * 1024 * 1024) {
      window.showToast('文件过大，不能超过 20MB', 'error');
      return;
    }
    selectedFile = file;
    dropzone.classList.add('hidden');
    fileSelectedStatus.classList.remove('hidden');
    fileSelectedStatus.querySelector('.file-name').textContent = `已选择文件：${file.name} (${(file.size/1024/1024).toFixed(2)} MB)`;
  }

  // ==== 提交表单 ====
  btnSubmitSource.addEventListener('click', async () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId) return;

    const activeStab = document.querySelector('.stab-btn.active').getAttribute('data-stab');
    
    try {
      if (activeStab === 'stype-text') {
        // 纯文本录入
        const title = document.getElementById('source-text-title').value.trim();
        const text = document.getElementById('source-text-body').value.trim();
        if (!title || !text) {
          window.showToast('标题和内容均不能为空', 'warning');
          return;
        }
        const res = await window.apiClient.addSourceText(notebookId, title, text);
        window.closeModal('modal-add-source');
        waitAndRefreshSources(notebookId, [res.id]);

      } else if (activeStab === 'stype-url') {
        // 网页录入
        const singleUrl = document.getElementById('source-url-input').value.trim();
        const batchUrlsText = document.getElementById('source-urls-batch').value.trim();
        const allowInternal = document.getElementById('url-allow-internal').checked;

        if (batchUrlsText) {
          // 批量抓取网页
          const urls = batchUrlsText.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
          if (urls.length === 0) {
            window.showToast('无有效的 URL 网址', 'warning');
            return;
          }
          if (urls.length > 20) {
            window.showToast('一次最多导入 20 个 URL 网址', 'warning');
            return;
          }
          const res = await window.apiClient.addSourceBatch(notebookId, urls, allowInternal);
          window.closeModal('modal-add-source');
          const ids = res.imported ? res.imported.map(x => x.id) : [];
          waitAndRefreshSources(notebookId, ids);
        } else if (singleUrl) {
          // 单个抓取
          const res = await window.apiClient.addSourceURL(notebookId, singleUrl, allowInternal);
          window.closeModal('modal-add-source');
          waitAndRefreshSources(notebookId, [res.id]);
        } else {
          window.showToast('请输入 URL 网址', 'warning');
          return;
        }

      } else if (activeStab === 'stype-file') {
        // 本地物理文件上传
        if (!selectedFile) {
          window.showToast('请选择本地物理文件', 'warning');
          return;
        }
        const res = await window.apiClient.addSourceFile(notebookId, selectedFile);
        window.closeModal('modal-add-source');
        waitAndRefreshSources(notebookId, [res.id]);

      } else if (activeStab === 'stype-drive') {
        // Drive 文档添加
        const docId = document.getElementById('source-drive-docid').value.trim();
        const mimeType = document.getElementById('source-drive-mimetype').value;
        const title = document.getElementById('source-drive-title').value.trim() || null;

        if (!docId) {
          window.showToast('Drive 资源 ID 不能为空', 'warning');
          return;
        }
        // 调用 Drive 源接口
        const res = await window.apiClient.request('POST', `/v1/notebooks/${notebookId}/sources/drive`, {
          file_id: docId,
          mime_type: mimeType,
          title: title || docId
        });
        window.closeModal('modal-add-source');
        waitAndRefreshSources(notebookId, [res.id]);
      }
    } catch (err) {
      window.showToast(`添加来源失败: ${err.message}`, 'error');
    }
  });
});
