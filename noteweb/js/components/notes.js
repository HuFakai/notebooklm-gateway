/**
 * NoteWeb - Notes Component
 * 管理笔记卡片列表渲染 (Bento Grid)、创建、编辑与删除
 */

let activeNoteId = null; // 当前编辑中的笔记 ID (null 表示新建)

export function initNotes() {
  const btnAddCard = document.getElementById('btn-add-note-card');
  const btnSaveNote = document.getElementById('btn-save-note');
  const btnDeleteActiveNote = document.getElementById('btn-delete-active-note');

  // 点击“写新笔记”卡片
  btnAddCard.addEventListener('click', () => {
    activeNoteId = null;
    document.getElementById('note-edit-title').value = '';
    document.getElementById('note-edit-content').value = '';
    document.getElementById('note-save-time').textContent = '新笔记';
    btnDeleteActiveNote.classList.add('hidden'); // 新建笔记隐藏删除按钮
    
    window.showModal('modal-note-edit');
  });

  // 保存笔记按钮
  btnSaveNote.addEventListener('click', async () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId) return;

    const title = document.getElementById('note-edit-title').value.trim();
    const content = document.getElementById('note-edit-content').value.trim();

    if (!title && !content) {
      window.showToast('标题与正文不能均为空', 'warning');
      return;
    }

    try {
      const finalTitle = title || '无标题笔记';
      if (activeNoteId === null) {
        // 创建笔记
        await window.apiClient.createNote(notebookId, finalTitle, content);
        window.showToast('已创建笔记', 'success');
      } else {
        // 编辑修改
        await window.apiClient.updateNote(notebookId, activeNoteId, finalTitle, content);
        window.showToast('已保存笔记', 'success');
      }
      
      window.closeModal('modal-note-edit');
      renderNotesGrid();
    } catch (err) {
      window.showToast(`保存笔记失败: ${err.message}`, 'error');
    }
  });

  // 删除当前笔记按钮
  btnDeleteActiveNote.addEventListener('click', async () => {
    const notebookId = window.state.currentNotebookId;
    if (!notebookId || !activeNoteId) return;

    const confirmed = confirm('确定要彻底删除此篇笔记卡片吗？');
    if (!confirmed) return;

    try {
      await window.apiClient.deleteNote(notebookId, activeNoteId);
      window.showToast('已删除笔记卡片');
      window.closeModal('modal-note-edit');
      renderNotesGrid();
    } catch (err) {
      window.showToast(`删除笔记失败: ${err.message}`, 'error');
    }
  });
}

export async function renderNotesGrid() {
  const grid = document.getElementById('notes-grid');
  if (!grid) return;

  // 保留 statically-placed 新建笔记卡片
  const addCardHtml = `
    <div id="btn-add-note-card" class="note-card add-card">
      <svg class="icon-lg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
      <span>写新笔记</span>
    </div>
  `;

  try {
    const notes = await window.apiClient.listNotes(window.state.currentNotebookId);
    window.state.notes = notes;

    if (notes.length === 0) {
      grid.innerHTML = addCardHtml;
      // 重新绑定新建卡片点击事件
      document.getElementById('btn-add-note-card').addEventListener('click', () => {
        activeNoteId = null;
        document.getElementById('note-edit-title').value = '';
        document.getElementById('note-edit-content').value = '';
        document.getElementById('note-save-time').textContent = '新笔记';
        document.getElementById('btn-delete-active-note').classList.add('hidden');
        window.showModal('modal-note-edit');
      });
      return;
    }

    const cardsHtml = notes.map(note => {
      // 制作纯文本摘要
      let excerpt = note.content || '无内容';
      // 简易过滤 Markdown 标记以供摘要显示
      excerpt = excerpt.replace(/[#*`_-]/g, '').slice(0, 100);
      if (note.content && note.content.length > 100) excerpt += '...';

      return `
        <div class="note-card note-item" data-id="${window.escapeHTML(note.id)}">
          <div class="note-card-title">${window.escapeHTML(note.title)}</div>
          <div class="note-card-excerpt">${window.escapeHTML(excerpt)}</div>
          <div class="note-card-date">📝 卡片</div>
        </div>
      `;
    }).join('');

    grid.innerHTML = addCardHtml + cardsHtml;

    // 重新绑定新建卡片点击事件
    document.getElementById('btn-add-note-card').addEventListener('click', () => {
      activeNoteId = null;
      document.getElementById('note-edit-title').value = '';
      document.getElementById('note-edit-content').value = '';
      document.getElementById('note-save-time').textContent = '新笔记';
      document.getElementById('btn-delete-active-note').classList.add('hidden');
      window.showModal('modal-note-edit');
    });

    // 绑定笔记项点击卡片进行编辑
    grid.querySelectorAll('.note-item').forEach(el => {
      el.addEventListener('click', () => {
        const noteId = el.getAttribute('data-id');
        openNoteForEdit(noteId);
      });
    });

  } catch (err) {
    console.error('获取笔记列表失败:', err);
    grid.innerHTML = addCardHtml;
    window.showToast('加载笔记卡片失败', 'error');
  }
}

function openNoteForEdit(noteId) {
  const note = window.state.notes.find(n => n.id === noteId);
  if (!note) return;

  activeNoteId = noteId;
  document.getElementById('note-edit-title').value = note.title;
  document.getElementById('note-edit-content').value = note.content || '';
  document.getElementById('note-save-time').textContent = '修改历史笔记';
  
  // 显示删除按钮
  document.getElementById('btn-delete-active-note').classList.remove('hidden');

  window.showModal('modal-note-edit');
}
