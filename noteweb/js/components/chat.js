/**
 * NoteWeb - Chat Component
 * 管理智能对话、推荐提问词列表、自定义 System Prompt / Goal 配置及客户端渐显渲染
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
        <div class="suggestion-chip" data-prompt="${encodeURIComponent(s.prompt)}">${window.escapeHTML(s.question || s.prompt)}</div>
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

// 发送提问并在消息框内渐显普通 JSON 响应
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
        renderReferences(aiMsg, result.references);
      }
    },
    // onError
    (err) => {
      if (bubble.classList.contains('loading-stream')) {
        bubble.classList.remove('loading-stream');
      }
      bubble.textContent = `错误: ${err.message}`;
      bubble.style.color = 'var(--neon-red)';
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
    const chip = document.createElement('span');
    chip.className = 'ref-chip';
    chip.textContent = `${idx + 1}. ${ref.source_title || ref.source_id || '未命名文档'}`;
    
    // 点击小卡片，弹窗展示精确引用的原文文本
    chip.addEventListener('click', () => {
      const passage = ref.cited_text || (Array.isArray(ref.quotes) ? ref.quotes.join('\n\n') : '上游未返回引用原文');
      alert(`引用来源：${ref.source_title || ref.source_id || '未知'}\n\n${passage}`);
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
