/**
 * NoteWeb - Main Application Orchestrator
 * 全局状态管理、事件分发与组件初始化
 */

import { APIClient } from './api.js';
import { initNotebooks, renderNotebooksList } from './components/notebooks.js';
import { initSources } from './components/sources.js';
import { initNotes, renderNotesGrid } from './components/notes.js';
import { initChat, renderChatTab } from './components/chat.js';
import { initResearch, renderResearchTab } from './components/research.js';
import { initArtifacts, renderArtifactsTab } from './components/artifacts.js';
import { initShare, renderShareTab } from './components/share.js';

// 1. 初始化全局状态与客户端
window.state = {
  currentNotebookId: null,
  currentNotebookTitle: '',
  activeTab: 'notes',
  notebooks: [],
  sources: [],
  notes: [],
  artifacts: [],
  collaborators: [],
  publicAccess: 'disabled'
};

window.apiClient = new APIClient();

// 2. 全局 UI 辅助方法
window.showToast = function(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = '🔔';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '❌';
  if (type === 'warning') icon = '⚠️';

  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};

window.showModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
};

window.showSlideover = function(slideoverId) {
  const drawer = document.getElementById(slideoverId);
  if (drawer) drawer.classList.add('active');
};

window.closeSlideover = function(slideoverId) {
  const drawer = document.getElementById(slideoverId);
  if (drawer) drawer.classList.remove('active');
};

// 极简 Markdown 转换 HTML 引擎，确保报告及对话高格式化可读性
window.renderMarkdown = function(text) {
  if (!text) return '';
  
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  
  // 标题处理
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
  
  // 粗体
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // 换行/段落
  html = html.replace(/\n\n/g, '</p><p>');
  
  // 行内代码
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');
  
  // 代码块
  html = html.replace(/```([\s\S]*?)```/g, '<pre class="json-code"><code>$1</code></pre>');
  
  // 列表处理
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*?<\/li>)/g, '<ul>$1</ul>');
  html = html.replace(/<\/ul>\s*<ul>/g, ''); // 拼接相连的列表
  
  return '<p>' + html.replace(/\n/g, '<br>') + '</p>';
};

// 3. Tab 标签切换路由控制
window.switchTab = function(tabName) {
  window.state.activeTab = tabName;
  
  // 更新导航激活状态
  document.querySelectorAll('.tab-btn').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // 更新内容卡面板显示
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.remove('active');
  });
  const activePane = document.getElementById(`tab-content-${tabName}`);
  if (activePane) activePane.classList.add('active');

  // 根据当前激活 Tab 渲染相应的数据
  if (window.state.currentNotebookId) {
    if (tabName === 'notes') renderNotesGrid();
    else if (tabName === 'chat') renderChatTab();
    else if (tabName === 'research') renderResearchTab();
    else if (tabName === 'studio') renderArtifactsTab();
    else if (tabName === 'share') renderShareTab();
  }
};

// 4. 加载当前笔记本详情
window.loadActiveNotebook = async function(notebookId, forceRefreshTab = true) {
  try {
    const notebooksSection = document.getElementById('sources-section');
    const btnAddSource = document.getElementById('btn-add-source');
    
    if (!notebookId) {
      window.state.currentNotebookId = null;
      window.state.currentNotebookTitle = '';
      notebooksSection.classList.add('disabled');
      btnAddSource.disabled = true;
      document.getElementById('main-workspace-view').classList.add('hidden');
      document.getElementById('main-empty-view').classList.remove('hidden');
      return;
    }

    // 激活工作区视图
    document.getElementById('main-empty-view').classList.add('hidden');
    document.getElementById('main-workspace-view').classList.remove('hidden');
    notebooksSection.classList.remove('disabled');
    btnAddSource.removeAttribute('disabled');

    // 渲染笔记本标题
    const nb = window.state.notebooks.find(n => n.id === notebookId);
    window.state.currentNotebookId = notebookId;
    window.state.currentNotebookTitle = nb ? nb.title : '未命名笔记本';
    document.getElementById('active-notebook-title').textContent = window.state.currentNotebookTitle;

    // 笔记本项的激活态样式更新
    document.querySelectorAll('.notebook-item').forEach(el => {
      if (el.getAttribute('data-id') === notebookId) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    // 异步加载此笔记本下的参考来源文档列表
    await initSources(notebookId);

    // 默认展示或更新当前 Tab 面板
    if (forceRefreshTab) {
      window.switchTab(window.state.activeTab);
    }
  } catch (err) {
    window.showToast(`加载笔记本失败: ${err.message}`, 'error');
  }
};

// 5. 连接配置测试与保存
async function testAndSaveSettings(url, key, isInitial = false) {
  const statusIndicator = document.querySelector('.status-indicator');
  const statusText = document.getElementById('settings-status-text');
  const btnSave = document.getElementById('btn-save-settings');

  statusIndicator.className = 'status-indicator testing';
  statusText.textContent = '正在测试连通性...';
  btnSave.disabled = true;

  try {
    const testClient = new APIClient(url, key);
    const info = await testClient.getServerInfo();

    statusIndicator.className = 'status-indicator verified';
    statusText.textContent = `验证成功 (${info.account?.email || '已认证'})`;
    btnSave.removeAttribute('disabled');

    if (isInitial) {
      // 首次加载如果成功，直接保存配置并渲染界面
      saveCredentials(url, key, info);
    }
  } catch (err) {
    statusIndicator.className = 'status-indicator failed';
    statusText.textContent = `连接失败: ${err.message}`;
    btnSave.disabled = true;
    if (isInitial) {
      // 首次自动测试失败，弹出配置框
      window.showModal('modal-settings');
    }
  }
}

function saveCredentials(url, key, serverInfo) {
  localStorage.setItem('noteweb_url', url);
  localStorage.setItem('noteweb_key', key);
  
  window.apiClient.setCredentials(url, key);
  
  // 更新主界面账户 Badge
  const badge = document.getElementById('account-badge');
  const badgeEmail = document.getElementById('badge-email');
  badge.className = 'account-badge configured';
  badgeEmail.textContent = serverInfo.account?.email || '已连接';

  window.closeModal('modal-settings');
  window.showToast('API 配置保存成功！', 'success');

  // 重新加载笔记本列表
  initNotebooks();
}

// 6. DOM 初始化与全局绑定
document.addEventListener('DOMContentLoaded', async () => {
  // 读取本地存储配置并加载
  const savedURL = localStorage.getItem('noteweb_url') || 'http://127.0.0.1:8000';
  const savedKey = localStorage.getItem('noteweb_key') || '';

  document.getElementById('settings-url').value = savedURL;
  document.getElementById('settings-key').value = savedKey;

  if (savedKey) {
    // 异步测试验证，不阻碍首屏渲染
    testAndSaveSettings(savedURL, savedKey, true);
  } else {
    // 无配置则要求弹窗
    window.showModal('modal-settings');
  }

  // 绑定全局设置弹窗动作
  document.getElementById('btn-settings').addEventListener('click', () => {
    window.showModal('modal-settings');
  });

  document.getElementById('btn-empty-start').addEventListener('click', () => {
    window.showModal('modal-settings');
  });

  // 测试连接按钮
  document.getElementById('btn-test-connection').addEventListener('click', async () => {
    const url = document.getElementById('settings-url').value;
    const key = document.getElementById('settings-key').value;
    await testAndSaveSettings(url, key, false);
  });

  // 保存连接配置
  document.getElementById('btn-save-settings').addEventListener('click', async () => {
    const url = document.getElementById('settings-url').value;
    const key = document.getElementById('settings-key').value;
    try {
      const testClient = new APIClient(url, key);
      const info = await testClient.getServerInfo();
      saveCredentials(url, key, info);
    } catch (e) {
      window.showToast('无法保存未通过验证的设置', 'error');
    }
  });

  // 监听 Tab 导航按钮
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      window.switchTab(tabName);
    });
  });

  // 注册全局 Modal 关闭逻辑
  document.querySelectorAll('.modal-close, .slideover-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modal = e.target.closest('.modal-overlay');
      if (modal) {
        modal.classList.remove('active');
      }
      const slideover = e.target.closest('.slideover-overlay');
      if (slideover) {
        slideover.classList.remove('active');
      }
    });
  });

  // 双击背景或遮罩关闭
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('active');
      }
    });
  });

  // 初始化笔记本子模块交互
  initNotebooks();
  initNotes();
  initChat();
  initResearch();
  initArtifacts();
  initShare();
});
