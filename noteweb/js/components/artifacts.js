/** Studio generation UI aligned with notebooklm-py 0.7.3 public API. */

const activePolls = new Map();
let previewUrl = null;

const TYPE_META = {
  audio: ['🎙️', '音频概览'],
  video: ['🎬', '视频概览'],
  cinematic_video: ['🎞️', '电影视频'],
  report: ['📄', '报告'],
  quiz: ['📝', '测验'],
  flashcards: ['🎴', '闪卡'],
  infographic: ['🖼️', '信息图'],
  slide_deck: ['📊', '幻灯片'],
  data_table: ['🧮', '数据表'],
  mind_map: ['🧠', '思维导图']
};

const OPTION_TEMPLATES = {
  audio: `
    <div class="form-row">
      <div class="form-group flex-1"><label for="art-opt-audio-format">节目形式</label>
        <select id="art-opt-audio-format"><option value="deep_dive">深度对谈</option><option value="brief">简明播报</option><option value="critique">内容评论</option><option value="debate">观点辩论</option></select>
      </div>
      <div class="form-group flex-1"><label for="art-opt-audio-length">节目长度</label>
        <select id="art-opt-audio-length"><option value="default">默认</option><option value="short">较短</option><option value="long">较长</option></select>
      </div>
    </div>`,
  video: `
    <div class="form-row">
      <div class="form-group flex-1"><label for="art-opt-video-format">视频形式</label>
        <select id="art-opt-video-format"><option value="explainer">讲解视频</option><option value="brief">简明视频</option><option value="cinematic">电影视频</option></select>
      </div>
      <div class="form-group flex-1"><label for="art-opt-video-style">视觉风格</label>
        <select id="art-opt-video-style"><option value="auto_select">自动选择</option><option value="custom">自定义</option><option value="classic">经典</option><option value="whiteboard">白板</option><option value="kawaii">可爱</option><option value="anime">动漫</option><option value="watercolor">水彩</option><option value="retro_print">复古印刷</option><option value="heritage">文化遗产</option><option value="paper_craft">纸艺</option></select>
      </div>
    </div>
    <div id="art-video-style-prompt-wrap" class="form-group hidden"><label for="art-opt-style-prompt">自定义视觉风格</label><textarea id="art-opt-style-prompt" maxlength="10000" rows="2" placeholder="描述色彩、材质、镜头与构图风格"></textarea></div>`,
  cinematic_video: `<div class="parameter-note">电影视频使用独立生成管线，仅支持来源、语言与内容指令。</div>`,
  report: `
    <div class="form-group"><label for="art-opt-report-format">报告格式</label>
      <select id="art-opt-report-format"><option value="briefing_doc">研究简报</option><option value="study_guide">学习指南</option><option value="blog_post">博客文章</option><option value="custom">自定义报告</option></select>
    </div>
    <div id="art-report-custom-wrap" class="form-group hidden"><label for="art-opt-custom-prompt">自定义报告结构</label><textarea id="art-opt-custom-prompt" maxlength="20000" rows="3" placeholder="说明报告标题、结构和写作要求"></textarea></div>`,
  quiz: quizOptions('题目'),
  flashcards: quizOptions('卡片'),
  infographic: `
    <div class="form-row">
      <div class="form-group flex-1"><label for="art-opt-orientation">版式</label><select id="art-opt-orientation"><option value="landscape">横向</option><option value="portrait">纵向</option><option value="square">方形</option></select></div>
      <div class="form-group flex-1"><label for="art-opt-detail">信息密度</label><select id="art-opt-detail"><option value="standard">标准</option><option value="concise">精简</option><option value="detailed">详细</option></select></div>
    </div>
    <div class="form-group"><label for="art-opt-infographic-style">设计风格</label><select id="art-opt-infographic-style"><option value="auto_select">自动选择</option><option value="sketch_note">手绘笔记</option><option value="professional">专业商务</option><option value="bento_grid">便当网格</option><option value="editorial">编辑设计</option><option value="instructional">教学图解</option><option value="bricks">积木</option><option value="clay">黏土</option><option value="anime">动漫</option><option value="kawaii">可爱</option><option value="scientific">科学图谱</option></select></div>`,
  slide_deck: `
    <div class="form-row">
      <div class="form-group flex-1"><label for="art-opt-slide-format">幻灯片用途</label><select id="art-opt-slide-format"><option value="detailed_deck">详细阅读稿</option><option value="presenter_slides">演讲展示稿</option></select></div>
      <div class="form-group flex-1"><label for="art-opt-slide-length">篇幅</label><select id="art-opt-slide-length"><option value="default">默认</option><option value="short">精简</option></select></div>
    </div>`,
  data_table: `<div class="parameter-note">数据表会以 CSV 生成并下载，内容指令可描述所需字段和排序方式。</div>`,
  mind_map: `<div class="parameter-note">思维导图同步生成并保存到笔记本笔记系统，可下载为 JSON。</div>`
};

function quizOptions(noun) {
  return `<div class="form-row">
    <div class="form-group flex-1"><label for="art-opt-quantity">${noun}数量</label><select id="art-opt-quantity"><option value="standard">标准</option><option value="fewer">较少</option><option value="more">较多（SDK 与标准量等价）</option></select></div>
    <div class="form-group flex-1"><label for="art-opt-difficulty">难度</label><select id="art-opt-difficulty"><option value="medium">中等</option><option value="easy">简单</option><option value="hard">困难</option></select></div>
  </div>`;
}

export function initArtifacts() {
  document.querySelectorAll('.artifact-type-btn').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.artifact-type-btn').forEach(item => item.classList.remove('active'));
      button.classList.add('active');
      renderOptionForm(button.dataset.type);
    });
  });
  document.getElementById('btn-generate-artifact').addEventListener('click', generateArtifact);
  document.getElementById('btn-toggle-artifact-sources').addEventListener('click', () => {
    document.getElementById('artifact-source-options').classList.toggle('hidden');
  });
  const instructions = document.getElementById('artifact-instructions');
  instructions.addEventListener('input', () => {
    document.getElementById('artifact-instructions-count').textContent = instructions.value.length;
  });
  window.addEventListener('beforeunload', stopAllPolls);
  renderOptionForm('audio');
}

function renderOptionForm(type) {
  const container = document.getElementById('artifact-options-form');
  container.innerHTML = OPTION_TEMPLATES[type] || '';
  document.getElementById('art-opt-video-style')?.addEventListener('change', event => {
    document.getElementById('art-video-style-prompt-wrap').classList.toggle('hidden', event.target.value !== 'custom');
  });
  document.getElementById('art-opt-report-format')?.addEventListener('change', event => {
    document.getElementById('art-report-custom-wrap').classList.toggle('hidden', event.target.value !== 'custom');
  });
}

function renderSourcePicker(notebookId) {
  const container = document.getElementById('artifact-source-options');
  const signature = (window.state.sources || []).map(source => source.id).join('|');
  if (
    container.dataset.notebookId === notebookId &&
    container.dataset.sourceSignature === signature &&
    container.childElementCount
  ) return;
  container.dataset.notebookId = notebookId;
  container.dataset.sourceSignature = signature;
  container.replaceChildren();
  const sources = window.state.sources || [];
  if (!sources.length) {
    const empty = document.createElement('span');
    empty.className = 'field-hint';
    empty.textContent = '当前笔记本没有可选来源';
    container.appendChild(empty);
    return;
  }
  sources.forEach(source => {
    const label = document.createElement('label');
    label.className = 'source-choice';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = source.id;
    input.checked = true;
    input.addEventListener('change', updateSourceSummary);
    const text = document.createElement('span');
    text.textContent = source.title || '未命名来源';
    label.append(input, text);
    container.appendChild(label);
  });
  updateSourceSummary();
}

function updateSourceSummary() {
  const all = [...document.querySelectorAll('#artifact-source-options input')];
  const selected = all.filter(item => item.checked).length;
  document.getElementById('artifact-source-summary').textContent =
    selected === all.length ? `全部 ${all.length} 个来源` : `已选择 ${selected} / ${all.length} 个来源`;
}

export async function renderArtifactsTab() {
  const notebookId = window.state.currentNotebookId;
  if (!notebookId) return;
  renderSourcePicker(notebookId);
  const container = document.getElementById('artifacts-list');
  try {
    const artifacts = await window.apiClient.listArtifacts(notebookId);
    if (window.state.currentNotebookId !== notebookId) return;
    window.state.artifacts = artifacts;
    renderArtifactList(container, artifacts, notebookId);
    artifacts.forEach(artifact => {
      if (['pending', 'in_progress', 'processing'].includes(artifact.status)) {
        startPolling(notebookId, artifact.id);
      }
    });
  } catch (error) {
    container.replaceChildren(emptyState(`加载失败：${error.message}`));
  }
}

function emptyState(message) {
  const node = document.createElement('div');
  node.className = 'empty-state';
  node.textContent = message;
  return node;
}

function renderArtifactList(container, artifacts, notebookId) {
  container.replaceChildren();
  if (!artifacts.length) {
    container.appendChild(emptyState('尚未创建任何智能生成物'));
    return;
  }
  artifacts.forEach(artifact => container.appendChild(createArtifactCard(artifact, notebookId)));
}

function createArtifactCard(artifact, notebookId) {
  const meta = TYPE_META[artifact.type] || ['📦', artifact.type || '未知类型'];
  const status = artifact.status || 'completed';
  const labels = { completed: '已完成', pending: '等待中', in_progress: '生成中', processing: '生成中', failed: '失败', not_found: '等待同步' };
  const card = document.createElement('article');
  card.className = `artifact-item ${['pending', 'in_progress', 'processing'].includes(status) ? 'task-running' : ''}`;

  const info = document.createElement('div');
  info.className = 'artifact-item-info';
  const avatar = document.createElement('div');
  avatar.className = 'artifact-avatar';
  avatar.textContent = meta[0];
  const textBox = document.createElement('div');
  textBox.className = 'artifact-title-box';
  const title = document.createElement('div');
  title.className = 'artifact-title';
  title.textContent = artifact.title || `正在生成：${meta[1]}`;
  const detail = document.createElement('div');
  detail.className = 'artifact-meta-text';
  detail.textContent = `${meta[1]} · ${String(artifact.id || '').slice(0, 8)}`;
  textBox.append(title, detail);
  info.append(avatar, textBox);

  const actions = document.createElement('div');
  actions.className = 'artifact-actions';
  const badge = document.createElement('span');
  badge.className = `artifact-badge-status badge-${status === 'processing' ? 'in_progress' : status}`;
  badge.textContent = labels[status] || status;
  actions.appendChild(badge);

  if (status === 'completed') {
    actions.appendChild(actionButton('查看', 'btn btn-sm btn-primary', () => viewArtifact(artifact)));
  } else if (status === 'failed') {
    actions.appendChild(actionButton('重试', 'btn btn-sm btn-purple', async () => {
      const result = await window.apiClient.retryArtifact(notebookId, artifact.id);
      window.showToast('任务已重新排队');
      startPolling(notebookId, result.task_id || artifact.id);
      await renderArtifactsTab();
    }));
  }
  const remove = actionButton('删除', 'section-action-btn', async () => {
    if (!confirm('确定永久删除该生成物吗？')) return;
    await window.apiClient.deleteArtifact(notebookId, artifact.id);
    window.showToast('生成物已删除');
    await renderArtifactsTab();
  });
  remove.disabled = ['pending', 'in_progress', 'processing'].includes(status);
  actions.appendChild(remove);
  card.append(info, actions);
  return card;
}

function actionButton(label, className, handler) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = className;
  button.textContent = label;
  button.addEventListener('click', async () => {
    button.disabled = true;
    try { await handler(); } catch (error) { window.showToast(error.message, 'error'); }
    finally { button.disabled = false; }
  });
  return button;
}

function selectedSourceIds() {
  const all = [...document.querySelectorAll('#artifact-source-options input')];
  if (!all.length || all.every(item => item.checked)) return null;
  return all.filter(item => item.checked).map(item => item.value);
}

async function generateArtifact() {
  const notebookId = window.state.currentNotebookId;
  const selectedType = document.querySelector('.artifact-type-btn.active');
  if (!notebookId || !selectedType) return;
  const sourceIds = selectedSourceIds();
  if (sourceIds && !sourceIds.length) {
    window.showToast('请至少选择一个参考来源', 'warning');
    return;
  }
  const type = selectedType.dataset.type;
  const instructions = document.getElementById('artifact-instructions').value.trim();
  const payload = { type, language: document.getElementById('artifact-language').value };
  if (sourceIds) payload.source_ids = sourceIds;
  if (instructions) payload.instructions = instructions;

  if (type === 'audio') {
    payload.audio_format = valueOf('art-opt-audio-format');
    payload.audio_length = valueOf('art-opt-audio-length');
  } else if (type === 'video') {
    payload.video_format = valueOf('art-opt-video-format');
    payload.video_style = valueOf('art-opt-video-style');
    if (payload.video_style === 'custom') payload.style_prompt = valueOf('art-opt-style-prompt').trim();
  } else if (type === 'report') {
    payload.report_format = valueOf('art-opt-report-format');
    payload.extra_instructions = instructions || undefined;
    delete payload.instructions;
    if (payload.report_format === 'custom') payload.custom_prompt = valueOf('art-opt-custom-prompt').trim();
  } else if (type === 'quiz' || type === 'flashcards') {
    payload.quantity = valueOf('art-opt-quantity');
    payload.difficulty = valueOf('art-opt-difficulty');
  } else if (type === 'infographic') {
    payload.orientation = valueOf('art-opt-orientation');
    payload.detail_level = valueOf('art-opt-detail');
    payload.infographic_style = valueOf('art-opt-infographic-style');
  } else if (type === 'slide_deck') {
    payload.slide_format = valueOf('art-opt-slide-format');
    payload.slide_length = valueOf('art-opt-slide-length');
  }

  if (type === 'video' && payload.video_style === 'custom' && !payload.style_prompt) {
    window.showToast('自定义视觉风格不能为空', 'warning');
    return;
  }
  if (type === 'report' && payload.report_format === 'custom' && !payload.custom_prompt) {
    window.showToast('自定义报告结构不能为空', 'warning');
    return;
  }

  const button = document.getElementById('btn-generate-artifact');
  button.disabled = true;
  button.querySelector('span').textContent = '正在提交…';
  try {
    const result = await window.apiClient.createArtifact(notebookId, payload);
    document.getElementById('artifact-instructions').value = '';
    document.getElementById('artifact-instructions-count').textContent = '0';
    window.showToast(result.status === 'completed' ? '生成物已完成' : '任务已进入生成队列');
    if (result.task_id && result.status !== 'completed') startPolling(notebookId, result.task_id);
    await renderArtifactsTab();
  } catch (error) {
    window.showToast(`创建失败：${error.message}`, 'error');
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = '立即发起异步构建任务';
  }
}

function valueOf(id) { return document.getElementById(id)?.value || ''; }

function startPolling(notebookId, taskId) {
  const key = `${notebookId}:${taskId}`;
  if (activePolls.has(key)) return;
  let misses = 0;
  const poll = async () => {
    if (window.state.currentNotebookId !== notebookId) {
      activePolls.delete(key);
      return;
    }
    try {
      const result = await window.apiClient.getArtifactStatus(notebookId, taskId);
      misses = 0;
      if (['completed', 'failed', 'removed'].includes(result.status)) {
        activePolls.delete(key);
        window.showToast(result.status === 'completed' ? '智能生成物已就绪' : `生成失败：${result.error || '上游未返回原因'}`, result.status === 'completed' ? 'success' : 'error');
        await renderArtifactsTab();
        return;
      }
      await renderArtifactsTab();
    } catch (error) {
      misses += 1;
      if (misses >= 5) {
        activePolls.delete(key);
        window.showToast(`任务状态同步暂停：${error.message}`, 'warning');
        return;
      }
    }
    const timer = window.setTimeout(poll, 4000);
    activePolls.set(key, timer);
  };
  activePolls.set(key, window.setTimeout(poll, 1200));
}

function stopAllPolls() {
  activePolls.forEach(timer => clearTimeout(timer));
  activePolls.clear();
}

async function viewArtifact(artifact) {
  document.querySelectorAll('.artifact-subview').forEach(node => node.classList.add('hidden'));
  document.getElementById('artifact-view-title').textContent = artifact.title || TYPE_META[artifact.type]?.[1] || '生成物详情';
  const download = document.getElementById('btn-download-artifact');
  download.onclick = () => downloadFile(artifact);
  window.showModal('modal-artifact-view');
  try {
    const blob = await window.apiClient.downloadArtifact(window.state.currentNotebookId, artifact.type, artifact.id);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (artifact.type === 'audio') {
      previewUrl = URL.createObjectURL(blob);
      const player = document.getElementById('artifact-audio-player');
      player.src = previewUrl;
      document.getElementById('artifact-audio-container').classList.remove('hidden');
    } else if (['video', 'cinematic_video', 'infographic', 'slide_deck'].includes(artifact.type)) {
      previewUrl = URL.createObjectURL(blob);
      const container = document.getElementById('artifact-default-container');
      const output = document.getElementById('artifact-raw-json');
      output.replaceChildren();
      const media = artifact.type === 'infographic' ? document.createElement('img') :
        artifact.type === 'slide_deck' ? document.createElement('iframe') : document.createElement('video');
      media.src = previewUrl;
      media.className = 'artifact-media-preview';
      if (media.tagName === 'VIDEO') media.controls = true;
      if (media.tagName === 'IMG') media.alt = artifact.title || '信息图预览';
      output.appendChild(media);
      container.classList.remove('hidden');
    } else {
      const text = await blob.text();
      if (artifact.type === 'report') {
        document.getElementById('artifact-report-text').innerHTML = window.renderMarkdown(text || '内容为空');
        document.getElementById('artifact-report-container').classList.remove('hidden');
      } else {
        const output = document.getElementById('artifact-raw-json');
        try { output.textContent = JSON.stringify(JSON.parse(text), null, 2); }
        catch { output.textContent = text; }
        document.getElementById('artifact-default-container').classList.remove('hidden');
      }
    }
  } catch (error) {
    window.showToast(`预览失败：${error.message}`, 'error');
  }
}

async function downloadFile(artifact) {
  try {
    const blob = await window.apiClient.downloadArtifact(window.state.currentNotebookId, artifact.type, artifact.id);
    const extensions = { audio: 'mp3', video: 'mp4', cinematic_video: 'mp4', report: 'md', quiz: 'json', flashcards: 'json', infographic: 'png', slide_deck: 'pdf', data_table: 'csv', mind_map: 'json' };
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = `${safeFilename(artifact.title || artifact.type)}.${extensions[artifact.type] || 'bin'}`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    window.showToast(`下载失败：${error.message}`, 'error');
  }
}

function safeFilename(value) {
  return value.replace(/[\\/:*?"<>|]/g, '_').slice(0, 120);
}
