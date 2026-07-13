/**
 * NoteWeb - Artifacts & Studio Component
 * 管理智能生成工作室：多媒体/总结生成配置、后台任务轮询、媒体播放与二进制下载交互
 */

let activePolls = {}; // 记录轮询任务

const OPTION_TEMPLATES = {
  audio: `
    <div class="form-row">
      <div class="form-group flex-1">
        <label for="art-opt-audio-format">音频格式</label>
        <select id="art-opt-audio-format">
          <option value="deep-dive">深度双人对话 (Deep Dive)</option>
          <option value="brief">精简播报 (Brief)</option>
          <option value="critique">犀利评论 (Critique)</option>
          <option value="debate">正反辩论 (Debate)</option>
        </select>
      </div>
      <div class="form-group flex-1">
        <label for="art-opt-audio-length">音频时长</label>
        <select id="art-opt-audio-length">
          <option value="default">默认长度</option>
          <option value="short">精简版 (Short)</option>
          <option value="long">详尽版 (Long)</option>
        </select>
      </div>
    </div>
  `,
  report: `
    <div class="form-group">
      <label for="art-opt-report-format">报告格式</label>
      <select id="art-opt-report-format">
        <option value="briefing-doc">研究简报 (Briefing)</option>
        <option value="study-guide">学习指南 (Study Guide)</option>
        <option value="blog-post">博文总结 (Blog Post)</option>
        <option value="custom">完全自定义 (Custom)</option>
      </select>
    </div>
  `,
  quiz: `
    <div class="form-row">
      <div class="form-group flex-1">
        <label for="art-opt-quantity">试题数量</label>
        <select id="art-opt-quantity">
          <option value="standard">标准量 (Standard)</option>
          <option value="fewer">较少 (Fewer)</option>
          <option value="more">较多 (More)</option>
        </select>
      </div>
      <div class="form-group flex-1">
        <label for="art-opt-difficulty">测试难度</label>
        <select id="art-opt-difficulty">
          <option value="medium">中等 (Medium)</option>
          <option value="easy">简单 (Easy)</option>
          <option value="hard">硬核 (Hard)</option>
        </select>
      </div>
    </div>
  `,
  flashcards: `
    <div class="form-row">
      <div class="form-group flex-1">
        <label for="art-opt-quantity">闪卡数量</label>
        <select id="art-opt-quantity">
          <option value="standard">标准量 (Standard)</option>
          <option value="fewer">较少 (Fewer)</option>
          <option value="more">较多 (More)</option>
        </select>
      </div>
      <div class="form-group flex-1">
        <label for="art-opt-difficulty">闪卡难度</label>
        <select id="art-opt-difficulty">
          <option value="medium">中等 (Medium)</option>
          <option value="easy">简单 (Easy)</option>
          <option value="hard">硬核 (Hard)</option>
        </select>
      </div>
    </div>
  `,
  'mind-map': `
    <div class="form-group">
      <label for="art-opt-map-kind">导图类型</label>
      <select id="art-opt-map-kind">
        <option value="interactive">交互导图 (Interactive)</option>
        <option value="note-backed">富文本卡片附带 (Note-backed)</option>
      </select>
    </div>
  `,
  'slide-deck': `
    <div class="form-row">
      <div class="form-group flex-1">
        <label for="art-opt-deck-format">幻灯片格式</label>
        <select id="art-opt-deck-format">
          <option value="detailed">图文详尽 (Detailed)</option>
          <option value="presenter">演讲提纲 (Presenter)</option>
        </select>
      </div>
      <div class="form-group flex-1">
        <label for="art-opt-deck-length">幻灯片长度</label>
        <select id="art-opt-deck-length">
          <option value="default">默认长度</option>
          <option value="short">精炼短篇 (Short)</option>
        </select>
      </div>
    </div>
  `,
  video: `
    <div class="form-row">
      <div class="form-group flex-1">
        <label for="art-opt-video-format">视频格式</label>
        <select id="art-opt-video-format">
          <option value="explainer">概念讲解 (Explainer)</option>
          <option value="brief">简短演示 (Brief)</option>
          <option value="cinematic">电影级 (Cinematic)</option>
          <option value="short">短视频 (Short)</option>
        </select>
      </div>
      <div class="form-group flex-1">
        <label for="art-opt-video-style">视觉风格</label>
        <select id="art-opt-video-style">
          <option value="auto">自动 (Auto)</option>
          <option value="watercolor">水彩画 (Watercolor)</option>
          <option value="anime">动漫风 (Anime)</option>
          <option value="custom">自定义 (Custom)</option>
        </select>
      </div>
    </div>
  `,
  infographic: `
    <div class="form-row">
      <div class="form-group flex-1">
        <label for="art-opt-info-orientation">排版方向</label>
        <select id="art-opt-info-orientation">
          <option value="portrait">竖屏 (Portrait)</option>
          <option value="landscape">横屏 (Landscape)</option>
          <option value="square">正方形 (Square)</option>
        </select>
      </div>
      <div class="form-group flex-1">
        <label for="art-opt-info-detail">精细程度</label>
        <select id="art-opt-info-detail">
          <option value="standard">标准 (Standard)</option>
          <option value="concise">精简 (Concise)</option>
          <option value="detailed">详尽 (Detailed)</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label for="art-opt-info-style">风格描述</label>
      <input type="text" id="art-opt-info-style" class="form-control" placeholder="例如：极简扁平化，深色科技风" value="auto" style="width: 100%; padding: 0.6rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius-sm); color: var(--text-primary);">
    </div>
  `,
  'data-table': `
    <div class="form-group">
      <label>数据表格构建说明</label>
      <p class="subtitle" style="margin-top: 0.2rem; color: var(--text-muted); font-size: 0.75rem;">请在底部的自定义指令中输入您想生成表格的数据提取和汇总需求（例如：“整理一份核心技术指标与对比表格”）。</p>
    </div>
  `
};

export function initArtifacts() {
  const typeBtns = document.querySelectorAll('.artifact-type-btn');
  const btnGenerate = document.getElementById('btn-generate-artifact');

  // 选择生成物类别切换表单项
  typeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      typeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const type = btn.getAttribute('data-type');
      renderOptionForm(type);
    });
  });

  // 默认渲染第一个 (audio)
  renderOptionForm('audio');

  // 发起生成物异步构建
  btnGenerate.addEventListener('click', generateArtifactSubmit);

  // 清理可能遗留的定时器
  window.addEventListener('beforeunload', () => {
    Object.values(activePolls).forEach(interval => clearInterval(interval));
  });
}

function renderOptionForm(type) {
  const formContainer = document.getElementById('artifact-options-form');
  formContainer.innerHTML = OPTION_TEMPLATES[type] || '';
}

export async function renderArtifactsTab() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;

  const listContainer = document.getElementById('artifacts-list');

  // 初始化并从 LocalStorage 加载当前笔记本的 pending 任务列表
  if (!window.state.pendingTasks) {
    try {
      window.state.pendingTasks = JSON.parse(localStorage.getItem(`pending_tasks_${notebookId}`)) || [];
    } catch (_) {
      window.state.pendingTasks = [];
    }
  }

  try {
    const list = await window.apiClient.listArtifacts(notebookId);
    window.state.artifacts = list;

    // 清理：如果某个 pending 任务已经在已完成的服务器列表中，就从 pendingTasks 中移除
    window.state.pendingTasks = window.state.pendingTasks.filter(pt => {
      return !list.some(art => art.id === pt.id);
    });
    localStorage.setItem(`pending_tasks_${notebookId}`, JSON.stringify(window.state.pendingTasks));

    // 合并 pending 任务与服务器返回 of 已完成任务
    const mergedList = [...window.state.pendingTasks, ...list];

    if (mergedList.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">尚未创建任何智能生成物</div>';
      return;
    }

    listContainer.innerHTML = mergedList.map(art => {
      // 区分类型表情符号
      let emoji = '📦';
      if (art.type === 'audio') emoji = '🎙️';
      else if (art.type === 'report') emoji = '📄';
      else if (art.type === 'quiz') emoji = '📝';
      else if (art.type === 'flashcards') emoji = '🎴';
      else if (art.type === 'mind-map') emoji = '🧠';
      else if (art.type === 'slide-deck') emoji = '📊';
      else if (art.type === 'video') emoji = '🎬';
      else if (art.type === 'infographic') emoji = '🎨';
      else if (art.type === 'data-table') emoji = '📅';

      // 状态 Badge 颜色
      const status = art.status ? art.status.toLowerCase() : 'completed';
      let badgeClass = `badge-${status}`;
      let stateLabel = status;
      let spinnerHtml = '';
      
      if (status === 'completed') {
        stateLabel = '已完成';
      } else if (status === 'pending') {
        stateLabel = '等待中';
        spinnerHtml = `<div class="spinner-wave spinner-sm" style="display:inline-flex; margin-right:0.4rem;"><span></span><span></span><span></span></div>`;
      } else if (status === 'in_progress' || status === 'processing') {
        stateLabel = '生成中';
        badgeClass = 'badge-in_progress';
        spinnerHtml = `<div class="spinner-wave spinner-sm" style="display:inline-flex; margin-right:0.4rem;"><span></span><span></span><span></span></div>`;
      } else if (status === 'failed') {
        stateLabel = '失败';
      }

      // 构建动作栏
      let actionsHtml = '';
      if (status === 'completed') {
        actionsHtml = `<button class="btn btn-sm btn-primary view-art-btn" data-id="${art.id}" data-type="${art.type}">查看/播放</button>`;
      } else if (status === 'failed') {
        actionsHtml = `<button class="btn btn-sm btn-purple retry-art-btn" data-id="${art.id}">重试</button>`;
      } else {
        // 等待或生成中展示排队文本
        actionsHtml = `<span style="font-size:0.75rem; color:var(--text-muted);">正在排队构建...</span>`;
      }

      return `
        <div class="artifact-item ${status === 'in_progress' || status === 'pending' ? 'task-running' : ''}">
          <div class="artifact-item-info">
            <div class="artifact-avatar">${emoji}</div>
            <div class="artifact-title-box">
              <div class="artifact-title" title="${art.title}">${art.title}</div>
              <div class="artifact-meta-text">ID: ${art.id.slice(0, 8)}... | 类型: ${art.type}</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:0.6rem;">
            ${spinnerHtml}
            <span class="artifact-badge-status ${badgeClass}">${stateLabel}</span>
            ${actionsHtml}
            <button class="section-action-btn delete-art-btn" data-id="${art.id}" title="删除生成物" ${status === 'in_progress' || status === 'pending' ? 'disabled' : ''}>
              <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      `;
    }).join('');

    // 绑定查看事件
    listContainer.querySelectorAll('.view-art-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const artId = btn.getAttribute('data-id');
        const artType = btn.getAttribute('data-type');
        viewArtifact(artId, artType);
      });
    });

    // 绑定重试事件
    listContainer.querySelectorAll('.retry-art-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const artId = btn.getAttribute('data-id');
        try {
          const res = await window.apiClient.retryArtifact(notebookId, artId);
          window.showToast('生成任务已重新排队', 'success');
          // 重新拉取并轮询
          await renderArtifactsTab();
          startPollingArtifact(notebookId, res.task_id || artId);
        } catch (err) {
          window.showToast(`重试失败: ${err.message}`, 'error');
        }
      });
    });

    // 绑定删除事件
    listContainer.querySelectorAll('.delete-art-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const artId = btn.getAttribute('data-id');
        const confirmed = confirm('确定要永久删除该智能生成物吗？');
        if (!confirmed) return;
        try {
          await window.apiClient.deleteArtifact(notebookId, artId);
          window.showToast('生成物已删除');
          await renderArtifactsTab();
        } catch (err) {
          window.showToast(`删除失败: ${err.message}`, 'error');
        }
      });
    });

    // 检测并拉起正在生成中的任务轮询
    mergedList.forEach(art => {
      const status = art.status ? art.status.toLowerCase() : 'completed';
      if ((status === 'pending' || status === 'in_progress' || status === 'processing') && !activePolls[art.id]) {
        startPollingArtifact(notebookId, art.id);
      }
    });

  } catch (err) {
    console.error('获取生成物列表失败:', err);
    listContainer.innerHTML = '<div class="empty-state">加载工作室历史失败</div>';
  }
}

async function generateArtifactSubmit() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;

  const type = document.querySelector('.artifact-type-btn.active').getAttribute('data-type');
  const instructions = document.getElementById('artifact-instructions').value.trim();

  // 根据类型组装专属参数
  const payload = { type };
  if (instructions) {
    payload.instructions = instructions;
  }

  if (type === 'audio') {
    payload.audio_format = document.getElementById('art-opt-audio-format').value;
    payload.audio_length = document.getElementById('art-opt-audio-length').value;
  } else if (type === 'report') {
    payload.report_format = document.getElementById('art-opt-report-format').value;
  } else if (type === 'quiz' || type === 'flashcards') {
    payload.quantity = document.getElementById('art-opt-quantity').value;
    payload.difficulty = document.getElementById('art-opt-difficulty').value;
  } else if (type === 'mind-map') {
    payload.map_kind = document.getElementById('art-opt-map-kind').value;
  } else if (type === 'slide-deck') {
    payload.deck_format = document.getElementById('art-opt-deck-format').value;
    payload.deck_length = document.getElementById('art-opt-deck-length').value;
  } else if (type === 'video') {
    payload.video_format = document.getElementById('art-opt-video-format').value;
    payload.style = document.getElementById('art-opt-video-style').value;
  } else if (type === 'infographic') {
    payload.orientation = document.getElementById('art-opt-info-orientation').value;
    payload.detail = document.getElementById('art-opt-info-detail').value;
    payload.style = document.getElementById('art-opt-info-style').value.trim() || 'auto';
  }

  const btnGen = document.getElementById('btn-generate-artifact');
  btnGen.disabled = true;
  btnGen.querySelector('span').textContent = '正在提交异步构建任务...';

  try {
    const res = await window.apiClient.createArtifact(notebookId, payload);
    window.showToast('异步构建任务已发送至 Google Studio，正在后台生成中...', 'success');
    
    // 清空指令输入框
    document.getElementById('artifact-instructions').value = '';

    // 写入本地 pending 任务并持久化
    if (res.task_id) {
      if (!window.state.pendingTasks) window.state.pendingTasks = [];
      
      const typeNames = {
        audio: '音频播客 (Podcast)',
        report: '研究简报 (Report)',
        quiz: '智能测验 (Quiz)',
        flashcards: '互动闪卡 (Flashcards)',
        'mind-map': '思维导图 (Mindmap)',
        'slide-deck': '幻灯片 (Slides)',
        video: '智能视频 (Video)',
        infographic: '信息图 (Infographic)',
        'data-table': '数据表格 (Table)'
      };
      const typeName = typeNames[payload.type] || payload.type;
      
      window.state.pendingTasks.unshift({
        id: res.task_id,
        title: `正在生成: ${typeName}`,
        type: payload.type,
        status: 'in_progress',
        created_at: new Date().toISOString()
      });
      localStorage.setItem(`pending_tasks_${notebookId}`, JSON.stringify(window.state.pendingTasks));
      
      startPollingArtifact(notebookId, res.task_id);
    }

    // 重新刷新列表显示进度
    await renderArtifactsTab();
  } catch (err) {
    window.showToast(`任务创建失败: ${err.message}`, 'error');
  } finally {
    btnGen.removeAttribute('disabled');
    btnGen.querySelector('span').textContent = '立即发起异步构建任务';
  }
}

// 轮询单个生成物状态
function startPollingArtifact(notebookId, taskId) {
  if (activePolls[taskId]) return; // 避免重复创建

  activePolls[taskId] = setInterval(async () => {
    try {
      const res = await window.apiClient.getArtifactStatus(notebookId, taskId);
      const status = res.status ? res.status.toLowerCase() : '';
      
      // 更新本地 pendingTasks 中的状态并写入 localStorage
      if (window.state.pendingTasks) {
        const pt = window.state.pendingTasks.find(t => t.id === taskId);
        if (pt && status && pt.status !== status) {
          pt.status = status;
          localStorage.setItem(`pending_tasks_${notebookId}`, JSON.stringify(window.state.pendingTasks));
          await renderArtifactsTab();
        }
      }

      if (status === 'completed') {
        clearInterval(activePolls[taskId]);
        delete activePolls[taskId];
        
        // 从本地 pending 任务中删除
        if (window.state.pendingTasks) {
          window.state.pendingTasks = window.state.pendingTasks.filter(t => t.id !== taskId);
          localStorage.setItem(`pending_tasks_${notebookId}`, JSON.stringify(window.state.pendingTasks));
        }

        window.showToast(`智能生成物构建就绪！`, 'success');
        await renderArtifactsTab();
      } else if (status === 'failed') {
        clearInterval(activePolls[taskId]);
        delete activePolls[taskId];

        // 从本地 pending 任务中删除
        if (window.state.pendingTasks) {
          window.state.pendingTasks = window.state.pendingTasks.filter(t => t.id !== taskId);
          localStorage.setItem(`pending_tasks_${notebookId}`, JSON.stringify(window.state.pendingTasks));
        }

        window.showToast(`生成物任务构建失败。`, 'error');
        await renderArtifactsTab();
      }
    } catch (e) {
      console.warn('轮询生成物状态出错，继续拉取:', e);
    }
  }, 3000);
}

// 查看生成物详情 (播放音频/渲染测试卷/展示 markdown 简报)
async function viewArtifact(artifactId, type) {
  const modal = document.getElementById('modal-artifact-view');
  const titleEl = document.getElementById('artifact-view-title');
  const btnDownload = document.getElementById('btn-download-artifact');

  const art = window.state.artifacts.find(a => a.id === artifactId);
  titleEl.textContent = art ? art.title : '生成物详情';

  // 隐藏所有预览子容器
  document.querySelectorAll('.artifact-subview').forEach(el => el.classList.add('hidden'));
  
  // 设置下载按钮点击绑定
  btnDownload.onclick = () => downloadFile(window.state.currentNotebookId, type, art ? art.title : `artifact-${type}`);

  window.showModal('modal-artifact-view');

  try {
    window.showToast('正在从网关缓存下载生成物数据...', 'warning');
    const blob = await window.apiClient.downloadArtifact(window.state.currentNotebookId, type);
    
    if (type === 'audio') {
      const audioContainer = document.getElementById('artifact-audio-container');
      const audioPlayer = document.getElementById('artifact-audio-player');
      const discWrapper = audioContainer.querySelector('.audio-disc-wrapper');
      
      const audioUrl = URL.createObjectURL(blob);
      audioPlayer.src = audioUrl;
      audioContainer.classList.remove('hidden');

      // 绑定黑胶光盘旋转效果
      audioPlayer.onplay = () => discWrapper.classList.add('playing');
      audioPlayer.onpause = () => discWrapper.classList.remove('playing');
      audioPlayer.onended = () => discWrapper.classList.remove('playing');

    } else if (type === 'video') {
      const videoContainer = document.getElementById('artifact-video-container');
      const videoPlayer = document.getElementById('artifact-video-player');
      
      const videoUrl = URL.createObjectURL(blob);
      videoPlayer.src = videoUrl;
      videoContainer.classList.remove('hidden');

    } else if (type === 'infographic') {
      const imageContainer = document.getElementById('artifact-image-container');
      const imagePreview = document.getElementById('artifact-image-preview');
      
      const imageUrl = URL.createObjectURL(blob);
      imagePreview.src = imageUrl;
      imageContainer.classList.remove('hidden');

    } else if (type === 'report' || type === 'quiz' || type === 'flashcards' || type === 'mind-map' || type === 'slide-deck' || type === 'data-table') {
      const text = await blob.text();
      
      if (type === 'report' || type === 'slide-deck') {
        // 直接渲染 Markdown
        const reportContainer = document.getElementById('artifact-report-container');
        const reportText = document.getElementById('artifact-report-text');
        reportText.innerHTML = window.renderMarkdown(text || "生成物文本内容为空。");
        reportContainer.classList.remove('hidden');

      } else if (type === 'data-table') {
        // 将 CSV 数据转换为漂亮的 Markdown 表格渲染
        const reportContainer = document.getElementById('artifact-report-container');
        const reportText = document.getElementById('artifact-report-text');
        const lines = (text || "").split('\n').map(l => l.trim()).filter(l => l.length > 0);
        if (lines.length > 0) {
          const headers = lines[0].split(',');
          const mdRows = lines.slice(1).map(l => {
            return '| ' + l.split(',').join(' | ') + ' |';
          });
          const mdTable = `| ${headers.join(' | ')} |\n| ${headers.map(() => '---').join(' | ')} |\n${mdRows.join('\n')}`;
          reportText.innerHTML = window.renderMarkdown(mdTable);
        } else {
          reportText.innerHTML = "数据表格内容为空。";
        }
        reportContainer.classList.remove('hidden');

      } else if (type === 'quiz') {
        const quizContainer = document.getElementById('artifact-quiz-container');
        const quizContent = document.getElementById('artifact-quiz-content');
        
        try {
          // 如果后端返回的是 JSON 结构，我们做个选择题互动界面
          const quizData = JSON.parse(text);
          renderInteractiveQuiz(quizContent, quizData);
        } catch (_) {
          // 如果解析失败，说明是 Markdown 或普通纯文本，直接文本展示
          quizContent.innerHTML = window.renderMarkdown(text);
        }
        quizContainer.classList.remove('hidden');

      } else {
        // 其他类型 (如 mind-map JSON)，普通代码框展示
        const defaultContainer = document.getElementById('artifact-default-container');
        const rawJson = document.getElementById('artifact-raw-json');
        
        try {
          const jsonVal = JSON.parse(text);
          rawJson.textContent = JSON.stringify(jsonVal, null, 2);
        } catch (_) {
          rawJson.textContent = text;
        }
        defaultContainer.classList.remove('hidden');
      }
    }
    
    window.showToast('数据下载与解析就绪！', 'success');

  } catch (err) {
    window.showToast(`获取生成物内容失败: ${err.message}`, 'error');
  }
}

// 互动选择题测验渲染引擎
function renderInteractiveQuiz(container, quiz) {
  let questions = [];
  if (Array.isArray(quiz)) {
    questions = quiz;
  } else if (quiz.questions && Array.isArray(quiz.questions)) {
    questions = quiz.questions;
  } else {
    // 降级文本显示
    container.innerHTML = `<pre class="json-code">${JSON.stringify(quiz, null, 2)}</pre>`;
    return;
  }

  container.innerHTML = `
    <h4 style="margin-bottom:1rem; color:var(--neon-purple);">🎓 AI 互动测验（共 ${questions.length} 题）</h4>
    <div style="display:flex; flex-direction:column; gap:1.2rem;">
      ${questions.map((q, idx) => {
        const options = q.options || [];
        return `
          <div class="quiz-question-item" style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); padding:1rem; border-radius:8px;">
            <div style="font-weight:600; margin-bottom:0.6rem;">${idx + 1}. ${q.question || q.title || '问题'}</div>
            <div style="display:flex; flex-direction:column; gap:0.4rem;">
              ${options.map((opt, oidx) => {
                const optLetter = String.fromCharCode(65 + oidx); // A, B, C, D
                return `
                  <label style="display:flex; align-items:center; gap:0.5rem; cursor:pointer; font-size:0.85rem; color:var(--text-secondary);">
                    <input type="radio" name="question-${idx}" value="${optLetter}" style="width:auto;">
                    <span>${optLetter}. ${opt}</span>
                  </label>
                `;
              }).join('')}
            </div>
            <div class="quiz-answer-feedback hidden" style="margin-top:0.6rem; font-size:0.8rem; font-family:var(--font-mono); color:var(--neon-green);">
              正确答案: ${q.answer || q.correct_answer || 'A'} | 解析: ${q.explanation || q.reason || '无'}
            </div>
          </div>
        `;
      }).join('')}
      <button id="btn-submit-quiz-answers" class="btn btn-purple btn-sm">提交问卷查看答案</button>
    </div>
  `;

  // 绑定答案校验点击事件
  container.querySelector('#btn-submit-quiz-answers').addEventListener('click', (e) => {
    e.target.classList.add('hidden');
    container.querySelectorAll('.quiz-answer-feedback').forEach(el => el.classList.remove('hidden'));
    window.showToast('已核对试卷答案，解析面板已展开！', 'success');
  });
}

// 物理媒体下载到磁盘
async function downloadFile(notebookId, type, filename) {
  try {
    const blob = await window.apiClient.downloadArtifact(notebookId, type);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    
    // 根据类型判定扩展名
    let ext = '.txt';
    if (type === 'audio') ext = '.mp3';
    else if (type === 'video') ext = '.mp4';
    else if (type === 'infographic') ext = '.png';
    else if (type === 'slide-deck') ext = '.pdf';
    else if (type === 'quiz' || type === 'mind-map' || type === 'flashcards') ext = '.json';
    else if (type === 'report') ext = '.md';
    else if (type === 'data-table') ext = '.csv';

    link.download = `${filename}${ext}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.showToast('文件已成功下载到您的磁盘！', 'success');
  } catch (err) {
    window.showToast(`文件下载失败: ${err.message}`, 'error');
  }
}
