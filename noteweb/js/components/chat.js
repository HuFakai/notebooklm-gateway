/**
 * NoteWeb - Chat Component
 * 管理智能对话、推荐提问词列表、自定义 System Prompt / Goal 配置及 SSE 响应式流渲染
 */

let activeConversationId = null;

export function initChat() {
  const btnSend = document.getElementById('btn-chat-send');
  const chatInput = document.getElementById('chat-input');
  const btnChatConfig = document.getElementById('btn-chat-configure');
  const btnSaveChatConfig = document.getElementById('btn-save-chat-config');
  const presetSelector = document.getElementById('chat-config-mode');

  // 发送对话消息
  btnSend.addEventListener('click', sendChatMessage);

  // 输入框自适应高度及回车发送
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = `${Math.min(chatInput.scrollHeight, 150)}px`;
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  // 打开对话行为配置弹窗
  btnChatConfig.addEventListener('click', () => {
    window.showModal('modal-chat-config');
  });

  // 对话配置模式选择器切换
  presetSelector.addEventListener('change', (e) => {
    const isCustom = e.target.value === 'custom';
    const customGoal = document.getElementById('chat-custom-goal-group');
    const customLen = document.getElementById('chat-custom-len-group');
    
    if (isCustom) {
      customGoal.classList.remove('hidden');
      customLen.classList.remove('hidden');
    } else {
      customGoal.classList.add('hidden');
      customLen.classList.add('hidden');
    }
  });

  // 保存对话行为配置
  btnSaveChatConfig.addEventListener('click', async () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId) return;

    const chatMode = presetSelector.value;
    const goal = document.getElementById('chat-config-goal').value.trim();
    const responseLength = document.getElementById('chat-config-length').value;

    try {
      await window.apiClient.configureChat(notebookId, chatMode, goal, responseLength);
      window.showToast('对话行为配置成功！', 'success');
      window.closeModal('modal-chat-config');
    } catch (err) {
      window.showToast(`配置对话行为失败: ${err.message}`, 'error');
    }
  });
}

// 渲染对话界面（加载历史记录与引导词）
export async function renderChatTab() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;

  const messagesList = document.getElementById('chat-messages');
  const welcome = document.querySelector('.chat-welcome');
  const suggestionsContainer = document.getElementById('chat-suggestions');
  const chipsContainer = document.getElementById('suggestions-chips');

  // 1. 获取并展示历史聊天记录
  try {
    const res = await window.apiClient.request('GET', `/v1/notebooks/${notebookId}/chat/history?limit=30`);
    if (res && res.history && res.history.length > 0) {
      activeConversationId = res.conversation_id;
      if (welcome) welcome.classList.add('hidden');
      messagesList.innerHTML = '';

      res.history.forEach(item => {
        // 用户问题
        const userMsg = document.createElement('div');
        userMsg.className = 'message user';
        userMsg.innerHTML = `
          <div class="msg-avatar">👤</div>
          <div class="msg-bubble">${escapeHTML(item.question)}</div>
        `;
        messagesList.appendChild(userMsg);

        // AI 答案
        const aiMsg = document.createElement('div');
        aiMsg.className = 'message assistant';
        
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.innerHTML = window.renderMarkdown(item.answer);
        aiMsg.appendChild(bubble);

        // 操作栏
        const actionBar = document.createElement('div');
        actionBar.className = 'msg-action-bar';
        actionBar.style = 'display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted);';
        
        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn-msg-action';
        saveBtn.style = 'background: none; border: none; color: var(--neon-blue); cursor: pointer; display: flex; align-items: center; gap: 0.2rem; font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 4px; transition: background 0.2s;';
        saveBtn.innerHTML = '📌 <span>保存到笔记</span>';
        saveBtn.onmouseover = () => saveBtn.style.background = 'rgba(255,255,255,0.05)';
        saveBtn.onmouseout = () => saveBtn.style.background = 'none';
        
        saveBtn.addEventListener('click', async () => {
          saveBtn.disabled = true;
          saveBtn.querySelector('span').textContent = '正在保存...';
          try {
            await window.apiClient.createNote(notebookId, item.question.substring(0, 30) || item.answer.substring(0, 20), item.answer);
            window.showToast('成功保存到笔记！', 'success');
            saveBtn.querySelector('span').textContent = '已保存';
            
            const activeTab = document.querySelector('.sidebar-menu-item.active');
            if (activeTab && activeTab.getAttribute('data-tab') === 'notes') {
              const notesModule = await import('./notes.js');
              notesModule.renderNotesTab();
            }
          } catch (err) {
            window.showToast(`保存失败: ${err.message}`, 'error');
            saveBtn.querySelector('span').textContent = '保存到笔记';
            saveBtn.disabled = false;
          }
        });

        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn-msg-action';
        copyBtn.style = 'background: none; border: none; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; gap: 0.2rem; font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 4px; transition: background 0.2s;';
        copyBtn.innerHTML = '📋 <span>复制</span>';
        copyBtn.onmouseover = () => copyBtn.style.background = 'rgba(255,255,255,0.05)';
        copyBtn.onmouseout = () => copyBtn.style.background = 'none';
        copyBtn.addEventListener('click', () => {
          navigator.clipboard.writeText(item.answer);
          window.showToast('已复制到剪贴板', 'success');
        });

        actionBar.appendChild(saveBtn);
        actionBar.appendChild(copyBtn);
        bubble.appendChild(actionBar);
        messagesList.appendChild(aiMsg);
      });
      messagesList.scrollTop = messagesList.scrollHeight;
    } else {
      messagesList.innerHTML = '';
      if (welcome) welcome.classList.remove('hidden');
      activeConversationId = null;
    }
  } catch (err) {
    console.warn('获取历史对话记录失败:', err);
  }

  // 2. 加载引导推荐词
  try {
    const suggestions = await window.apiClient.getSuggestedPrompts(notebookId);
    if (suggestions && suggestions.length > 0) {
      suggestionsContainer.classList.remove('hidden');
      chipsContainer.innerHTML = suggestions.map(s => `
        <div class="suggestion-chip" data-prompt="${encodeURIComponent(s.prompt)}">${s.title}</div>
      `).join('');

      chipsContainer.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
          const promptText = decodeURIComponent(chip.getAttribute('data-prompt'));
          const chatInput = document.getElementById('chat-input');
          chatInput.value = promptText;
          chatInput.style.height = 'auto';
          chatInput.style.height = `${Math.min(chatInput.scrollHeight, 150)}px`;
          sendChatMessage();
        });
      });
    } else {
      suggestionsContainer.classList.add('hidden');
    }
  } catch (err) {
    console.warn('获取推荐提问词失败:', err);
    suggestionsContainer.classList.add('hidden');
  }
}

// 发送提问并在消息框内流式渲染 SSE 结果
async function sendChatMessage() {
  const notebookId = window.state.currentNotebookId;
  const inputEl = document.getElementById('chat-input');
  const question = inputEl.value.trim();
  
  if (!notebookId || !question) return;

  // 清空输入框
  inputEl.value = '';
  inputEl.style.height = '42px';

  // 隐藏欢迎语
  const welcome = document.querySelector('.chat-welcome');
  if (welcome) welcome.classList.add('hidden');

  const messagesList = document.getElementById('chat-messages');

  // 1. 添加用户消息卡片
  const userMsg = document.createElement('div');
  userMsg.className = 'message user';
  userMsg.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-bubble">${escapeHTML(question)}</div>
  `;
  messagesList.appendChild(userMsg);
  messagesList.scrollTop = messagesList.scrollHeight;

  // 2. 创建并添加 AI 流式卡片占位
  const aiMsg = document.createElement('div');
  aiMsg.className = 'message assistant';
  aiMsg.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble loading-stream">
      <div class="spinner-wave" style="justify-content: flex-start;">
        <span></span><span></span><span></span><span></span>
      </div>
    </div>
  `;
  messagesList.appendChild(aiMsg);
  messagesList.scrollTop = messagesList.scrollHeight;

  const bubble = aiMsg.querySelector('.msg-bubble');
  let responseText = '';

  // 3. 启动流式响应
  await window.apiClient.chatStream(
    notebookId,
    question,
    activeConversationId,
    // onChunk
    (chunk) => {
      // 去除等待加载状态
      if (bubble.classList.contains('loading-stream')) {
        bubble.classList.remove('loading-stream');
        bubble.innerHTML = '';
      }
      responseText += chunk;
      bubble.innerHTML = window.renderMarkdown(responseText);
      messagesList.scrollTop = messagesList.scrollHeight;
    },
    // onDone
    (result) => {
      if (bubble.classList.contains('loading-stream')) {
        bubble.classList.remove('loading-stream');
        bubble.innerHTML = 'AI 对话响应为空。';
      }
      if (result && result.conversation_id) {
        activeConversationId = result.conversation_id;
      }
      if (result && result.references && result.references.length > 0) {
        renderReferences(bubble, result.references);
      }

      // 添加操作工具条：保存到笔记、复制文本等
      const actionBar = document.createElement('div');
      actionBar.className = 'msg-action-bar';
      actionBar.style = 'display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted);';
      
      const saveBtn = document.createElement('button');
      saveBtn.className = 'btn-msg-action';
      saveBtn.style = 'background: none; border: none; color: var(--neon-blue); cursor: pointer; display: flex; align-items: center; gap: 0.2rem; font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 4px; transition: background 0.2s;';
      saveBtn.innerHTML = '📌 <span>保存到笔记</span>';
      saveBtn.onmouseover = () => saveBtn.style.background = 'rgba(255,255,255,0.05)';
      saveBtn.onmouseout = () => saveBtn.style.background = 'none';
      
      saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true;
        saveBtn.querySelector('span').textContent = '正在保存...';
        try {
          const noteTitle = question.substring(0, 30) || result.answer.substring(0, 20);
          await window.apiClient.saveChatToNote(notebookId, result.answer, result.references || [], noteTitle);
          window.showToast('成功保存到笔记！', 'success');
          saveBtn.querySelector('span').textContent = '已保存';
          
          const activeTab = document.querySelector('.sidebar-menu-item.active');
          if (activeTab && activeTab.getAttribute('data-tab') === 'notes') {
            const notesModule = await import('./notes.js');
            notesModule.renderNotesTab();
          }
        } catch (err) {
          window.showToast(`保存失败: ${err.message}`, 'error');
          saveBtn.querySelector('span').textContent = '保存到笔记';
          saveBtn.disabled = false;
        }
      });

      const copyBtn = document.createElement('button');
      copyBtn.className = 'btn-msg-action';
      copyBtn.style = 'background: none; border: none; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; gap: 0.2rem; font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 4px; transition: background 0.2s;';
      copyBtn.innerHTML = '📋 <span>复制</span>';
      copyBtn.onmouseover = () => copyBtn.style.background = 'rgba(255,255,255,0.05)';
      copyBtn.onmouseout = () => copyBtn.style.background = 'none';
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(result.answer);
        window.showToast('已复制到剪贴板', 'success');
      });

      actionBar.appendChild(saveBtn);
      actionBar.appendChild(copyBtn);
      bubble.appendChild(actionBar);
    },
    // onError
    (err) => {
      if (bubble.classList.contains('loading-stream')) {
        bubble.classList.remove('loading-stream');
      }
      bubble.innerHTML = `<span style="color:var(--neon-red);">错误: ${err.message}</span>`;
      messagesList.scrollTop = messagesList.scrollHeight;
    }
  );
}

function renderReferences(messageEl, references) {
  const refContainer = document.createElement('div');
  refContainer.className = 'message-references';
  refContainer.innerHTML = '<div class="ref-label">🔍 引用来源 (点击查看引用原文):</div><div class="ref-list"></div>';
  
  const refList = refContainer.querySelector('.ref-list');
  references.forEach((ref, idx) => {
    const src = window.state.sources ? window.state.sources.find(s => s.id === ref.source_id) : null;
    const sourceTitle = src ? src.title : '参考文档';

    const chip = document.createElement('span');
    chip.className = 'ref-chip';
    chip.textContent = `${idx + 1}. ${sourceTitle}`;
    
    // 点击小卡片，弹窗展示精确引用的原文文本
    chip.addEventListener('click', () => {
      alert(`引用自《${sourceTitle}》的原文片段：\n\n${ref.cited_text || '暂无原文片段'}`);
    });
    refList.appendChild(chip);
  });
  
  messageEl.appendChild(refContainer);
}

function escapeHTML(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
