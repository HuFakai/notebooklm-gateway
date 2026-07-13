/**
 * NoteWeb - Deep Research Component
 * 管理深度探索、搜索集成、状态轮询与文献成果一键导入参考来源
 */

let researchInterval = null;
let currentRunId = null;

export function initResearch() {
  const btnStart = document.getElementById('btn-start-research');
  const btnCancel = document.getElementById('btn-cancel-research');
  const btnImport = document.getElementById('btn-import-research');

  // 启动深度研究
  btnStart.addEventListener('click', startDeepResearch);

  // 取消深度研究
  btnCancel.addEventListener('click', cancelDeepResearch);

  // 导入为参考源
  btnImport.addEventListener('click', importResearchToSource);
}

export function renderResearchTab() {
  // 保持现有状态，不做强制清空，方便用户在切换 Tab 后继续阅读已生成的报告
}

async function startDeepResearch() {
  const notebookId = window.state.currentNotebookId;
  const query = document.getElementById('research-query').value.trim();
  const source = document.getElementById('research-source').value;
  const mode = document.getElementById('research-mode').value;

  if (!notebookId || !query) {
    window.showToast('请输入研究课题或搜索关键词', 'warning');
    return;
  }

  const btnStart = document.getElementById('btn-start-research');
  const statusPanel = document.getElementById('research-status-panel');
  const statusText = document.getElementById('research-status-text');
  const reportView = document.getElementById('research-report-view');
  const btnImport = document.getElementById('btn-import-research');

  // UI 状态切换
  btnStart.disabled = true;
  statusPanel.classList.remove('hidden');
  btnImport.classList.add('hidden');
  statusText.textContent = '正在初始化研究会话与搜索管道...';
  reportView.innerHTML = '';

  try {
    const res = await window.apiClient.startResearch(notebookId, query, source, mode);
    currentRunId = res.run_id || res.task_id;

    // 开始定时轮询获取研究进度
    researchInterval = setInterval(() => pollResearchProgress(notebookId, currentRunId), 2000);
  } catch (err) {
    window.showToast(`启动探索任务失败: ${err.message}`, 'error');
    btnStart.removeAttribute('disabled');
    statusPanel.classList.add('hidden');
  }
}

async function pollResearchProgress(notebookId, runId) {
  const statusText = document.getElementById('research-status-text');
  const reportView = document.getElementById('research-report-view');
  const statusPanel = document.getElementById('research-status-panel');
  const btnStart = document.getElementById('btn-start-research');
  const btnImport = document.getElementById('btn-import-research');

  try {
    const res = await window.apiClient.getResearchStatus(notebookId, runId);
    
    if (res.status === 'completed') {
      clearInterval(researchInterval);
      statusPanel.classList.add('hidden');
      btnStart.removeAttribute('disabled');
      
      // 渲染 Markdown 格式研究报告
      const reportHtml = window.renderMarkdown(res.report || "深度研究报告生成为空。");
      
      // 渲染引用来源
      let referencesHtml = '';
      if (res.sources && res.sources.length > 0) {
        referencesHtml = `
          <div style="margin-top: 2rem; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 1rem;">
            <h4>🔍 搜集参考文献资料 (${res.sources.length} 篇)：</h4>
            <ul style="list-style-type: decimal; margin-left: 1.5rem; margin-top: 0.5rem;">
              ${res.sources.map(s => `
                <li style="margin-bottom: 0.4rem;">
                  <a href="${s.url}" target="_blank" style="color: var(--neon-blue); text-decoration: underline;">${s.title}</a>
                </li>
              `).join('')}
            </ul>
          </div>
        `;
      }

      reportView.innerHTML = reportHtml + referencesHtml;
      
      // 显示导入参考源按钮
      btnImport.classList.remove('hidden');
      window.showToast('深度探索任务已完成，报告生成成功！', 'success');

    } else if (res.status === 'failed') {
      clearInterval(researchInterval);
      statusPanel.classList.add('hidden');
      btnStart.removeAttribute('disabled');
      reportView.innerHTML = `<p style="color:var(--neon-red); text-align:center;">研究任务失败。云端服务报错。</p>`;
      window.showToast('深度探索任务失败', 'error');

    } else {
      // 处于 PENDING 或 IN_PROGRESS
      statusText.textContent = `云端 AI 正在对文献深度咀嚼中，状态：[${res.status || '执行中'}]`;
    }
  } catch (err) {
    console.error('轮询研究进度出错:', err);
    // 轮询偶发报错不清除定时器，尝试继续
  }
}

async function cancelDeepResearch() {
  if (!currentRunId) return;
  
  const notebookId = window.state.currentNotebookId;
  const statusPanel = document.getElementById('research-status-panel');
  const btnStart = document.getElementById('btn-start-research');

  try {
    clearInterval(researchInterval);
    await window.apiClient.cancelResearch(notebookId, currentRunId);
    
    statusPanel.classList.add('hidden');
    btnStart.removeAttribute('disabled');
    window.showToast('探索任务已被用户取消');
  } catch (err) {
    window.showToast(`取消探索任务失败: ${err.message}`, 'error');
  }
}

async function importResearchToSource() {
  if (!currentRunId) return;

  const notebookId = window.state.currentNotebookId;
  const btnImport = document.getElementById('btn-import-research');

  btnImport.disabled = true;
  btnImport.querySelector('span').textContent = '正在导入...';

  try {
    await window.apiClient.importResearch(notebookId, currentRunId);
    window.showToast('深度研究报告及参考资料已成功导入为左侧参考源！', 'success');
    
    // 隐藏按钮防止重复导入
    btnImport.classList.add('hidden');
    
    // 异步刷新文档来源列表
    const { initSources } = await import('./sources.js');
    await initSources(notebookId);
  } catch (err) {
    window.showToast(`导入参考源失败: ${err.message}`, 'error');
  } finally {
    btnImport.removeAttribute('disabled');
    btnImport.querySelector('span').textContent = '导入参考源';
  }
}
