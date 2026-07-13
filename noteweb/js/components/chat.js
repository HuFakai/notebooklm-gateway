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

// 渲染对话界面（加载引导词）
export async function renderChatTab() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;

  const suggestionsContainer = document.getElementById('chat-suggestions');
  const chipsContainer = document.getElementById('suggestions-chips');

  try {
    const suggestions = await window.apiClient.getSuggestedPrompts(notebookId);
    if (suggestions && suggestions.length > 0) {
      suggestionsContainer.classList.remove('hidden');
      chipsContainer.innerHTML = suggestions.map(s => `
        <div class="suggestion-chip" data-prompt="${encodeURIComponent(s.prompt)}">${s.title}</div>
      `).join('');

      // 绑定芯片点击
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
    () => {
      if (bubble.classList.contains('loading-stream')) {
        bubble.classList.remove('loading-stream');
        bubble.innerHTML = 'AI 对话响应为空。';
      }
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

function escapeHTML(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
