/**
 * NoteWeb - Notebooks Component
 * 管理笔记本列表展示、创建、双击重命名与删除
 */

export async function initNotebooks() {
  try {
    const notebooks = await window.apiClient.listNotebooks();
    window.state.notebooks = notebooks;
    renderNotebooksList();
    
    // 如果没有激活的笔记本，默认激活第一个（如果存在）
    if (notebooks.length > 0 && !window.state.currentNotebookId) {
      window.loadActiveNotebook(notebooks[0].id);
    } else if (notebooks.length === 0) {
      window.loadActiveNotebook(null);
    }
  } catch (err) {
    console.error('获取笔记本列表失败:', err);
    window.showToast('加载笔记本列表失败', 'error');
  }
}

export function renderNotebooksList() {
  const listContainer = document.getElementById('notebooks-list');
  if (!listContainer) return;

  if (window.state.notebooks.length === 0) {
    listContainer.innerHTML = '<div class="empty-state">暂无笔记本</div>';
    return;
  }

  listContainer.innerHTML = window.state.notebooks.map(nb => {
    const isActive = nb.id === window.state.currentNotebookId ? 'active' : '';
    const sourcesCount = nb.sources_count !== undefined ? nb.sources_count : 0;
    return `
      <div class="list-item notebook-item ${isActive}" data-id="${nb.id}">
        <div class="item-info">
          <svg class="item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          </svg>
          <span class="item-name" title="${nb.title}">${nb.title}</span>
        </div>
        <span class="item-count">${sourcesCount} 源</span>
      </div>
    `;
  }).join('');

  // 绑定笔记本项的点击切换事件
  listContainer.querySelectorAll('.notebook-item').forEach(el => {
    el.addEventListener('click', () => {
      const nbId = el.getAttribute('data-id');
      window.loadActiveNotebook(nbId);
    });
  });
}

// 绑定笔记本相关控制按钮
document.addEventListener('DOMContentLoaded', () => {
  const btnNewNotebook = document.getElementById('btn-new-notebook');
  const btnDeleteNotebook = document.getElementById('btn-delete-notebook');
  const titleDisplay = document.getElementById('active-notebook-title');
  const renameInput = document.getElementById('input-notebook-rename');
  const btnSaveRename = document.getElementById('btn-save-rename');

  // 新建笔记本
  btnNewNotebook.addEventListener('click', async (e) => {
    e.stopPropagation();
    const title = prompt('请输入新笔记本名称：');
    if (!title || !title.trim()) return;

    try {
      const newNb = await window.apiClient.createNotebook(title.trim());
      window.showToast(`已创建笔记本 "${title}"`, 'success');
      
      // 重新加载列表，并默认切换至新创建的笔记本
      await initNotebooks();
      window.loadActiveNotebook(newNb.id);
    } catch (err) {
      window.showToast(`创建笔记本失败: ${err.message}`, 'error');
    }
  });

  // 删除笔记本
  btnDeleteNotebook.addEventListener('click', async () => {
    const nbId = window.state.currentNotebookId;
    if (!nbId) return;

    const confirmed = confirm(`警告：您正在彻底删除笔记本 "${window.state.currentNotebookTitle}"。\n删除后将无法恢复，其中所有的参考来源、笔记和生成物都将一同被销毁！确定要删除吗？`);
    if (!confirmed) return;

    try {
      await window.apiClient.deleteNotebook(nbId);
      window.showToast('笔记本已成功删除', 'success');
      
      // 清空激活状态并重新刷新列表
      window.state.currentNotebookId = null;
      await initNotebooks();
    } catch (err) {
      window.showToast(`删除笔记本失败: ${err.message}`, 'error');
    }
  });

  // 双击标题开启重命名编辑
  titleDisplay.addEventListener('dblclick', () => {
    titleDisplay.classList.add('hidden');
    renameInput.classList.remove('hidden');
    btnSaveRename.classList.remove('hidden');
    renameInput.value = window.state.currentNotebookTitle;
    renameInput.focus();
    renameInput.select();
  });

  // 保存重命名方法
  const saveRename = async () => {
    const newTitle = renameInput.value.trim();
    if (!newTitle || newTitle === window.state.currentNotebookTitle) {
      closeRename();
      return;
    }

    try {
      await window.apiClient.renameNotebook(window.state.currentNotebookId, newTitle);
      window.state.currentNotebookTitle = newTitle;
      titleDisplay.textContent = newTitle;
      
      // 刷新列表使得侧边栏同步改名
      const nb = window.state.notebooks.find(n => n.id === window.state.currentNotebookId);
      if (nb) nb.title = newTitle;
      renderNotebooksList();
      
      window.showToast('重命名成功', 'success');
      closeRename();
    } catch (err) {
      window.showToast(`重命名失败: ${err.message}`, 'error');
    }
  };

  const closeRename = () => {
    titleDisplay.classList.remove('hidden');
    renameInput.classList.add('hidden');
    btnSaveRename.classList.add('hidden');
  };

  btnSaveRename.addEventListener('click', saveRename);
  
  renameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') saveRename();
    if (e.key === 'Escape') closeRename();
  });
});
