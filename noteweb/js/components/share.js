/**
 * NoteWeb - Share Component
 * 管理笔记本共享状态（公开分享链接）、协作者添加、读写角色更新及移除操作
 */

export function initShare() {
  const publicToggle = document.getElementById('share-public-toggle');
  const btnAdd = document.getElementById('btn-add-collaborator');
  const btnCopy = document.getElementById('btn-copy-share-link');

  // 公开开关切换
  publicToggle.addEventListener('change', async () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId) return;

    const enable = publicToggle.checked;
    try {
      const res = await window.apiClient.togglePublicShare(notebookId, enable);
      window.state.publicAccess = res.public_access;
      renderPublicLink(notebookId);
      window.showToast(enable ? '公开共享链接已开启' : '公开共享链接已关闭');
    } catch (err) {
      window.showToast(`切换公开共享失败: ${err.message}`, 'error');
      // 还原开关状态
      publicToggle.checked = !enable;
    }
  });

  // 复制共享链接
  btnCopy.addEventListener('click', () => {
    const linkInput = document.getElementById('public-share-link');
    linkInput.select();
    document.execCommand('copy');
    window.showToast('已复制共享链接至剪贴板');
  });

  // 添加协作者
  btnAdd.addEventListener('click', async () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId) return;

    const email = document.getElementById('share-user-email').value.trim();
    const permission = document.getElementById('share-user-permission').value;

    if (!email) {
      window.showToast('请输入受邀人的邮箱地址', 'warning');
      return;
    }

    try {
      await window.apiClient.addCollaborator(notebookId, email, permission, false);
      window.showToast(`已邀请协协作人 ${email}`, 'success');
      document.getElementById('share-user-email').value = '';
      
      // 刷新列表
      await renderShareTab();
    } catch (err) {
      window.showToast(`添加协作者失败: ${err.message}`, 'error');
    }
  });
}

export async function renderShareTab() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;

  const publicToggle = document.getElementById('share-public-toggle');
  const collabList = document.getElementById('collaborators-list');

  try {
    const shareInfo = await window.apiClient.getShareStatus(notebookId);
    
    // 更新公开链接开关状态
    window.state.publicAccess = shareInfo.public_access;
    const isPublic = shareInfo.public_access === 'enabled';
    publicToggle.checked = isPublic;
    
    renderPublicLink(notebookId);

    // 渲染协作者列表
    const users = shareInfo.shared_users || [];
    window.state.collaborators = users;

    if (users.length === 0) {
      collabList.innerHTML = `
        <tr>
          <td colspan="3" class="table-empty">暂无受邀协作者</td>
        </tr>
      `;
      return;
    }

    collabList.innerHTML = users.map(user => {
      const isViewer = user.permission === 'viewer' ? 'selected' : '';
      const isEditor = user.permission === 'editor' ? 'selected' : '';

      return `
        <tr>
          <td class="collab-email">${user.email}</td>
          <td>
            <select class="collab-select" data-email="${user.email}">
              <option value="viewer" ${isViewer}>查看者 (Viewer)</option>
              <option value="editor" ${isEditor}>编辑者 (Editor)</option>
            </select>
          </td>
          <td style="text-align: center;">
            <button class="icon-btn danger delete-collab-btn" data-email="${user.email}" title="移除协作者">
              <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // 绑定更新角色改变事件
    collabList.querySelectorAll('.collab-select').forEach(select => {
      select.addEventListener('change', async () => {
        const email = select.getAttribute('data-email');
        const newPermission = select.value;
        try {
          await window.apiClient.updateCollaborator(notebookId, email, newPermission);
          window.showToast(`已成功修改 ${email} 的权限为 ${newPermission}`);
        } catch (err) {
          window.showToast(`修改权限失败: ${err.message}`, 'error');
          // 还原
          await renderShareTab();
        }
      });
    });

    // 绑定删除成员事件
    collabList.querySelectorAll('.delete-collab-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const email = btn.getAttribute('data-email');
        const confirmed = confirm(`确定要移除协作者 ${email} 的所有访问权限吗？`);
        if (!confirmed) return;

        try {
          await window.apiClient.removeCollaborator(notebookId, email);
          window.showToast('协作者移除成功');
          await renderShareTab();
        } catch (err) {
          window.showToast(`移除失败: ${err.message}`, 'error');
        }
      });
    });

  } catch (err) {
    console.error('获取共享状态失败:', err);
    collabList.innerHTML = `
      <tr>
        <td colspan="3" class="table-empty" style="color:var(--neon-red);">获取共享列表失败: ${err.message}</td>
      </tr>
    `;
  }
}

function renderPublicLink(notebookId) {
  const container = document.getElementById('public-link-container');
  const linkInput = document.getElementById('public-share-link');
  const isPublic = window.state.publicAccess === 'enabled';

  if (isPublic) {
    container.classList.remove('hidden');
    // 构建以网关为域名的直接公开访问接口
    linkInput.value = `${window.apiClient.baseURL}/v1/notebooks/${notebookId}`;
  } else {
    container.classList.add('hidden');
    linkInput.value = '';
  }
}
