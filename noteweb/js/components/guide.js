/**
 * NoteWeb - Notebook Guide Component
 * 管理笔记本综合指南：AI 综合摘要流式提取、包含的文档来源列表与快速阅读、快速 Studio 工具跳转、引导提问快捷发送
 */

export function initGuide() {
  const btnRegen = document.getElementById('btn-regenerate-summary');

  // 重新生成摘要按钮
  btnRegen.addEventListener('click', () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId) return;
    
    // 清除缓存并重新提炼
    if (window.state.summaryCache) {
      delete window.state.summaryCache[notebookId];
    }
    renderSummary(notebookId);
  });

  // 绑定右侧“快捷学习工作室”按钮事件
  document.querySelectorAll('.qaction-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const actionType = btn.getAttribute('data-action');
      
      // 切换到 Studio 标签页
      window.switchTab('studio');
      
      // 自动选中对应的生成物类型按钮，并触发点击重新渲染子表单
      const typeBtn = document.querySelector(`.artifact-type-btn[data-type="${actionType}"]`);
      if (typeBtn) {
        typeBtn.click();
      }
    });
  });
}

export async function renderGuideTab() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;

  // 1. 渲染/生成 AI 综合摘要
  renderSummary(notebookId);

  // 2. 渲染包含的文档参考源列表
  renderGuideSourcesList();

  // 3. 渲染引导提问建议列表
  renderGuideSuggestions(notebookId);
}

// 提炼并渲染 AI 摘要 (Stream 格式)
async function renderSummary(notebookId) {
  const container = document.getElementById('guide-summary-content');
  if (!container) return;

  // 检查是否有缓存的摘要
  if (window.state.summaryCache && window.state.summaryCache[notebookId]) {
    container.innerHTML = window.renderMarkdown(window.state.summaryCache[notebookId]);
    return;
  }

  // 如果笔记本没有任何参考文档，提示先添加参考源
  if (!window.state.sources || window.state.sources.length === 0) {
    container.innerHTML = `
      <p style="color: var(--text-muted); font-size:0.88rem; text-align:center; padding: 2rem 0;">
        📭 当前笔记本内尚无任何参考文档。<br>请点击左侧的 <strong>“参考文档来源” + 号按钮</strong> 上传文件、网页或粘贴文本，AI 才能为您生成综合提炼指南。
      </p>
    `;
    return;
  }

  // 开启 AI 提炼
  container.innerHTML = `
    <div class="spinner-wave" style="justify-content: flex-start;">
      <span></span><span></span><span></span><span></span>
    </div>
    <p id="summary-loading-tip" style="margin-top:0.5rem; font-size:0.85rem; color:var(--neon-blue);">正在深度阅读并精炼本笔记本中所有载入的参考文档...</p>
  `;

  let accumulatedText = '';
  const prompt = '请用中文对当前笔记本载入的所有参考文档进行一个全面细致的摘要提炼，并列出3到5个最核心的主题词或知识结构脉络，帮助我快速掌握这些资料的内容核心。';

  try {
    await window.apiClient.chatStream(
      notebookId,
      prompt,
      null,
      // onChunk
      (chunk) => {
        // 清除等待提示
        const tip = document.getElementById('summary-loading-tip');
        if (tip) {
          container.innerHTML = '';
        }
        accumulatedText += chunk;
        container.innerHTML = window.renderMarkdown(accumulatedText);
      },
      // onDone
      () => {
        if (!accumulatedText) {
          container.innerHTML = '<p>AI 提炼综合摘要为空。</p>';
        } else {
          // 写入本地缓存
          if (!window.state.summaryCache) window.state.summaryCache = {};
          window.state.summaryCache[notebookId] = accumulatedText;
        }
      },
      // onError
      (err) => {
        container.innerHTML = `<p style="color:var(--neon-red);">提炼摘要失败: ${err.message}</p>`;
      }
    );
  } catch (err) {
    container.innerHTML = `<p style="color:var(--neon-red);">请求失败: ${err.message}</p>`;
  }
}

// 渲染指南中的参考文档列表
function renderGuideSourcesList() {
  const container = document.getElementById('guide-sources-list');
  if (!container) return;

  const sources = window.state.sources || [];
  if (sources.length === 0) {
    container.innerHTML = '<div class="empty-state" style="padding:1rem;">当前没有参考文档</div>';
    return;
  }

  container.innerHTML = sources.map(src => {
    let icon = '📄';
    if (src.type === 'text') icon = '✍️';
    else if (src.type === 'url') icon = '🔗';
    else if (src.type === 'drive') icon = '💾';

    return `
      <div class="guide-source-item">
        <div class="guide-source-info">
          <span style="font-size:1.1rem; flex-shrink:0;">${icon}</span>
          <span class="item-name" style="font-size:0.85rem;" title="${src.title}">${src.title}</span>
        </div>
        <button class="btn btn-sm btn-primary read-guide-src-btn" data-id="${src.id}" style="padding:0.3rem 0.6rem; font-size:0.75rem;">阅读正文</button>
      </div>
    `;
  }).join('');

  // 绑定点击阅读按钮
  container.querySelectorAll('.read-guide-src-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const srcId = btn.getAttribute('data-id');
      
      // 动态载入 sources.js 中的阅读函数
      const { renderSourcesList } = await import('./sources.js');
      // 直接触发查看脱水正文抽屉
      const titleDisplay = document.getElementById('source-viewer-title');
      const contentDisplay = document.getElementById('source-viewer-content');
      
      const src = window.state.sources.find(s => s.id === srcId);
      titleDisplay.textContent = src ? src.title : '文档内容查看';
      contentDisplay.innerHTML = '<div class="spinner-wave"><span></span><span></span><span></span><span></span></div><p style="text-align:center; color:var(--neon-blue); font-size:0.85rem; margin-top:0.5rem;">正在加载脱水文本...</p>';
      
      window.showSlideover('slideover-source-viewer');

      try {
        const text = await window.apiClient.getSourceText(window.state.currentNotebookId, srcId);
        contentDisplay.innerHTML = window.renderMarkdown(text || "该参考源无文本内容。");
      } catch (err) {
        contentDisplay.innerHTML = `<p style="color:var(--neon-red);">加载失败: ${err.message}</p>`;
      }
    });
  });
}

// 渲染指南中的引导提问建议列表
async function renderGuideSuggestions(notebookId) {
  const container = document.getElementById('guide-suggestions-list');
  if (!container) return;

  try {
    const suggestions = await window.apiClient.getSuggestedPrompts(notebookId);
    if (suggestions && suggestions.length > 0) {
      container.innerHTML = suggestions.map(s => `
        <div class="guide-suggestion-item" data-prompt="${encodeURIComponent(s.prompt)}">
          <div style="font-weight:600; color:var(--neon-blue); margin-bottom:0.15rem;">${s.title}</div>
          <div style="font-size:0.75rem; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${s.prompt}</div>
        </div>
      `).join('');

      // 绑定点击提问事件
      container.querySelectorAll('.guide-suggestion-item').forEach(item => {
        item.addEventListener('click', () => {
          const promptText = decodeURIComponent(item.getAttribute('data-prompt'));
          
          // 切换到 Chat 标签页
          window.switchTab('chat');
          
          // 填入输入框并直接发送
          const chatInput = document.getElementById('chat-input');
          chatInput.value = promptText;
          chatInput.style.height = 'auto';
          chatInput.style.height = `${Math.min(chatInput.scrollHeight, 150)}px`;
          
          // 触发发送
          document.getElementById('btn-chat-send').click();
        });
      });
    } else {
      container.innerHTML = '<div class="empty-state" style="padding:1rem;">本笔记本无建议提问</div>';
    }
  } catch (err) {
    console.warn('指南获取提问建议失败:', err);
    container.innerHTML = '<div class="empty-state" style="padding:1rem;">加载提问建议失败</div>';
  }
}
