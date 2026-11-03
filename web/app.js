const $ = (id) => document.getElementById(id);
const effortLabels = { none: '关闭思考', low: '轻量思考', high: '深入思考', max: '极高思考' };
const effortHints = { none: '直接输出译文，适合简单、日常的表达。', low: '轻量思考，兼顾翻译速度与准确性。', high: '更充分地理解原文，适合复杂句子与专业内容。', max: '投入最多思考，等待时间和用量可能增加。' };
const state = { direction: 'zh-en', has_api_key: false, model: 'deepseek-flash', thinking: 'low', draftEffort: 'low', ready: false, busy: false, saving: false, requestId: null, result: '', resultValid: false };

function status(text) { $('statusText').textContent = text; }
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('toast').hidden = true, 2800); }
function error(message = '') { $('errorBanner').textContent = message; $('errorBanner').hidden = !message; }
function count() { $('sourceCount').textContent = `${[...$('sourceText').value].length.toLocaleString()} / 20,000`; $('translateButton').disabled = !state.ready || state.busy || !$('sourceText').value.trim(); }
function summary() { $('modelSummary').textContent = state.model; $('thinkingSummary').textContent = effortLabels[state.thinking]; }
function setResult(text, valid = false) {
  state.result = text; state.resultValid = valid;
  const pane = $('resultText');
  const nearBottom = pane.scrollHeight - pane.scrollTop - pane.clientHeight < 70;
  pane.textContent = text; pane.hidden = !text; $('resultPlaceholder').hidden = !!text;
  if (nearBottom) pane.scrollTop = pane.scrollHeight;
  $('copyButton').disabled = !text;
  $('resultCount').textContent = text ? `${[...text].length.toLocaleString()} 字符${valid ? '' : ' · 未完成'}` : '等待翻译';
}
function busy(value) {
  state.busy = value;
  document.body.classList.toggle('busy', value);
  $('sourceText').readOnly = value;
  for (const id of ['swapButton', 'clearButton', 'modelButton', 'thinkingButton', 'settingsButton']) $(id).disabled = value;
  $('translateLabel').textContent = value ? '翻译中' : '翻译';
  $('translateArrow').hidden = value; $('translateSpinner').hidden = !value; $('stopButton').hidden = !value;
  count();
}
function direction() {
  const zh = state.direction === 'zh-en';
  $('sourceLabel').textContent = zh ? '中文' : 'English'; $('resultLabel').textContent = zh ? 'English' : '中文';
  $('sourceBadge').textContent = zh ? '中' : 'A'; $('targetBadge').textContent = zh ? 'A' : '中';
  $('sourceText').placeholder = zh ? '写下或粘贴一段中文…' : 'Write or paste something in English…';
}
function chooseEffort(effort) {
  state.draftEffort = effort;
  document.querySelectorAll('[data-effort]').forEach(b => { b.classList.toggle('selected', b.dataset.effort === effort); b.setAttribute('aria-pressed', String(b.dataset.effort === effort)); });
  $('effortHint').textContent = effortHints[effort];
}
function openSettings() {
  if (state.busy || !state.ready) return;
  const first = !state.has_api_key;
  $('dialogTitle').textContent = first ? '你好，欢迎来到译间。' : '让翻译，更合你意。';
  $('dialogDescription').textContent = first ? '连接 DeepSeek，开始你的第一段翻译。' : '调整模型与思考强度，下次翻译即刻生效。';
  $('saveLabel').textContent = first ? '保存并开始' : '保存设置';
  $('keyStatus').textContent = first ? '' : '已保存';
  $('savedKey').hidden = first;
  $('keyInput').hidden = !first;
  $('keyHint').hidden = !first;
  $('apiKey').value = ''; $('apiKey').type = 'password';
  $('toggleKeyButton').title = '显示密钥'; $('toggleKeyButton').setAttribute('aria-label', '显示密钥');
  $('apiKey').placeholder = first ? '粘贴你的 API Key' : '留空，保留当前密钥';
  $('keyHint').textContent = first ? '只需填写并保存一次，以后启动会自动使用。' : '填写新密钥并保存即可更换，留空则继续使用已保存的密钥。';
  $('modelId').value = state.model; chooseEffort(state.thinking); $('settingsError').hidden = true;
  $('settingsDialog').showModal();
  (first ? $('apiKey') : $('modelId')).focus();
}
async function saveSettings(event) {
  event.preventDefault(); if (state.saving) return;
  state.saving = true; $('saveButton').disabled = true; $('settingsError').hidden = true;
  try {
    const result = await window.pywebview.api.save_settings({ api_key: $('apiKey').value.trim(), model: $('modelId').value.trim(), thinking: state.draftEffort });
    if (!result.ok) throw new Error(result.error);
    Object.assign(state, { has_api_key: result.has_api_key, model: result.model, thinking: result.thinking });
    summary(); $('settingsDialog').close(); status('准备就绪'); toast('设置已保存'); $('sourceText').focus();
  } catch (e) { $('settingsError').textContent = e.message || '设置未能保存，请重试。'; $('settingsError').hidden = false; }
  finally { state.saving = false; $('saveButton').disabled = false; }
}
window.receiveTranslation = (event) => {
  if (event.request_id !== state.requestId || !state.busy) return;
  if (event.phase === 'thinking') { status('正在理解原文…'); $('placeholderTitle').textContent = '正在理解原文…'; $('placeholderDescription').textContent = '译文生成后会逐步显示'; }
  if (typeof event.text === 'string') { setResult(event.text); status('正在翻译…'); }
  if (event.phase === 'done') {
    const result = event.result;
    if (result.ok) { setResult(result.text, true); status(`翻译完成 · ${result.elapsed} 秒`); }
    else if (result.cancelled) { status('已停止'); }
    else { if (result.partial) setResult(result.partial); error(result.error || '翻译失败，请重试。'); status('未完成'); }
    state.requestId = null; busy(false); resetPlaceholder();
  }
};
async function translate() {
  if (!state.ready || state.busy || !$('sourceText').value.trim()) return;
  if (!state.has_api_key) { openSettings(); return; }
  const id = crypto.randomUUID(); state.requestId = id;
  error(); busy(true); setResult('');
  $('placeholderTitle').textContent = '正在连接 DeepSeek…'; $('placeholderDescription').textContent = '可以随时停止，已生成的译文会保留'; status('正在连接…');
  try {
    const result = await window.pywebview.api.translate({ text: $('sourceText').value, direction: state.direction, request_id: id });
    if (state.requestId !== id) return;
    if (!result.ok) throw new Error(result.error);
  } catch (e) { if (state.requestId === id) { error(e.message || '翻译失败，请重试。'); status('未完成'); state.requestId = null; busy(false); resetPlaceholder(); } }
}
function resetPlaceholder() { $('placeholderTitle').textContent = '另一种语言，同样的意思'; $('placeholderDescription').textContent = '译文会在这里逐步呈现'; }
async function stop() {
  const id = state.requestId; if (!id) return;
  state.requestId = null;
  try { await window.pywebview.api.cancel_translation(id); } catch { error('停止请求未送达，请稍后重试。'); }
  finally { busy(false); resetPlaceholder(); status('已停止'); }
}
async function copy() {
  if (!state.result) return;
  try {
    try { await navigator.clipboard.writeText(state.result); }
    catch {
      const helper = document.createElement('textarea'); helper.value = state.result; document.body.appendChild(helper); helper.select();
      let copied; try { copied = document.execCommand('copy'); } finally { helper.remove(); }
      if (!copied) throw new Error();
    }
    toast('译文已复制');
  } catch { toast('复制失败，请选中译文后按 Ctrl+C。'); }
}
function swap() {
  if (state.busy) return;
  const oldSource = $('sourceText').value;
  state.direction = state.direction === 'zh-en' ? 'en-zh' : 'zh-en';
  if (state.result && state.resultValid) { $('sourceText').value = state.result; setResult(oldSource, true); }
  else { setResult(''); }
  direction(); count(); error(); status('已交换语言');
}
async function windowAction(action) { try { const result = await window.pywebview.api[action](); if (result?.ok === false) toast(result.error); } catch { toast('窗口操作未完成，请重试。'); } }

$('sourceText').addEventListener('input', () => { state.resultValid = false; count(); });
$('translateButton').addEventListener('click', translate); $('stopButton').addEventListener('click', stop);
$('copyButton').addEventListener('click', copy); $('swapButton').addEventListener('click', swap);
$('clearButton').addEventListener('click', () => { $('sourceText').value = ''; setResult(''); error(); count(); status('准备就绪'); $('sourceText').focus(); });
for (const id of ['settingsButton', 'modelButton', 'thinkingButton']) $(id).addEventListener('click', openSettings);
$('settingsForm').addEventListener('submit', saveSettings);
$('changeKeyButton').addEventListener('click', () => { $('savedKey').hidden = true; $('keyInput').hidden = false; $('keyHint').hidden = false; $('apiKey').focus(); });
$('dialogCloseButton').addEventListener('click', () => { if (!state.saving) $('settingsDialog').close(); });
$('settingsDialog').addEventListener('cancel', (e) => { if (state.saving) e.preventDefault(); });
$('settingsDialog').addEventListener('close', () => { $('apiKey').value = ''; });
$('toggleKeyButton').addEventListener('click', () => { const show = $('apiKey').type === 'password'; $('apiKey').type = show ? 'text' : 'password'; $('toggleKeyButton').title = show ? '隐藏密钥' : '显示密钥'; $('toggleKeyButton').setAttribute('aria-label', $('toggleKeyButton').title); });
document.querySelectorAll('[data-effort]').forEach(b => b.addEventListener('click', () => chooseEffort(b.dataset.effort)));
$('minimizeButton').addEventListener('click', () => windowAction('minimize'));
$('maximizeButton').addEventListener('click', () => windowAction('toggle_maximize'));
$('closeButton').addEventListener('click', () => windowAction('hide_window'));
document.querySelectorAll('.window-drag').forEach(el => el.addEventListener('dblclick', () => windowAction('toggle_maximize')));
document.addEventListener('keydown', e => { if (e.ctrlKey && e.key === 'Enter' && !$('settingsDialog').open) { e.preventDefault(); translate(); } });
async function init() {
  if (state.ready) return;
  try { const initial = await window.pywebview.api.get_state(); Object.assign(state, initial, { ready: true }); summary(); count(); status(state.has_api_key ? '准备就绪' : '等待连接 DeepSeek'); if (!state.has_api_key) openSettings(); if (initial.notice) error(initial.notice); }
  catch { error('应用连接未就绪，请从托盘退出后重新打开。'); }
}
window.addEventListener('pywebviewready', init);
if (window.pywebview?.api) init();
