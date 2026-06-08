const DEFAULT_PORT = 3456;
const LANG_KEY = 'vfsLang';
const THEME_KEY = 'vfsTheme';
const AGENT_KEY = 'vfsAgent';
const TOKEN_KEY = 'vfsToken';

const btn = document.getElementById('activate');
const langEn = document.getElementById('lang-en');
const langZh = document.getElementById('lang-zh');
const agentDefault = document.getElementById('agent-default');
const agentCodex = document.getElementById('agent-codex');
const agentClaude = document.getElementById('agent-claude');
const themeToggle = document.getElementById('theme-toggle');
const pageRow = document.getElementById('page-row');
const workspaceRow = document.getElementById('workspace-row');
const permissionRow = document.getElementById('permission-row');
const receiverRow = document.getElementById('receiver-row');
const pageStatus = document.getElementById('page-status');
const workspaceStatus = document.getElementById('workspace-status');
const permissionStatus = document.getElementById('permission-status');
const receiverStatus = document.getElementById('receiver-status');
const footerLeft = document.getElementById('footer-left');
const permissionActions = document.getElementById('permission-actions');
const permissionAction = document.getElementById('permission-action');
const receiverActions = document.getElementById('receiver-actions');
const receiverAction = document.getElementById('receiver-action');
const reviewRow = document.getElementById('review-row');
const reviewStatus = document.getElementById('review-status');

let activeTabId = null;
let activeTabUrl = '';
let activeTabScriptable = false;
let toolActive = false;
let receiverOnline = false;
let busy = true;
let permissionBusy = false;
let permissionOrigin = '';
let permissionState = 'unknown';
let permissionMessage = '';
let lang = 'zh';
let theme = 'dark';
let agentOverride = '';
let receiverToken = '';
let receiverTokenRequired = false;
let receiverHealth = null;

const SETUP_COMMAND = 'python3 scripts/setup.py . --channel beta';

const copy = {
  en: {
    title: 'Visual Feedback Studio',
    subtitle: 'Browser edits, source-ready feedback',
    pageLabel: 'Page',
    workspaceLabel: 'Workspace',
    permissionLabel: 'Permission',
    receiverLabel: 'Receiver',
    loading: 'Checking this page',
    noTab: 'Current page is unavailable',
    pageReady: 'Ready for visual review.',
    pageUnsupported: 'This page cannot be reviewed by Chrome extensions.',
    ready: 'Workspace can start on this page.',
    active: 'Visual workspace is active on this page.',
    activated: 'Active. Return to the page to edit.',
    exited: 'Review mode exited.',
    permissionChecking: 'Checking current-site access',
    permissionGranted: 'Current site is authorized for repeat review.',
    permissionActiveTab: 'This click can start review now. Grant the current site for repeat/reload use.',
    permissionUnsupported: 'Chrome does not allow extension injection on this page.',
    permissionGranting: 'Requesting',
    permissionGrantedNow: 'Authorized',
    permissionDenied: 'Not authorized. Start still works for this active tab click.',
    grantCurrentSite: 'Grant site',
    fileDetails: 'Copy details URL',
    receiverChecking: 'Checking 127.0.0.1:3456',
    receiverOnline: 'Online. Save writes feedback locally.',
    receiverTokenMissing: 'Online. Refresh config before saving.',
    receiverOffline: 'Offline. Review now, copy setup into this thread before saving.',
    receiverOptional: 'Receiver can wait until save',
    reviewLabel: 'Review',
    reviewEmpty: 'No saved feedback yet.',
    reviewSaved: '{count} saved feedback item(s). Say "feedback done" in the agent.',
    reviewPreview: '{count} saved item(s). Preview is ready.',
    reviewVerified: '{count} saved item(s). Verification is ready.',
    copySetup: 'Copy setup',
    refreshConfig: 'Refresh config',
    copied: 'Copied',
    fileAccess: 'Enable "Allow access to file URLs" in extension details.',
    injectionFailed: 'Injection failed: ',
    start: 'Start review',
    exit: 'Exit review',
    starting: 'Starting',
    closing: 'Closing',
    footerRight: 'v4.0 beta workspace',
    agentDefault: 'Default',
    darkTheme: 'Dark theme',
    lightTheme: 'Light theme'
  },
  zh: {
    title: '视觉反馈工作室',
    subtitle: '浏览器改稿，源码可读反馈',
    pageLabel: '页面',
    workspaceLabel: '工作台',
    permissionLabel: '授权',
    receiverLabel: '接收端',
    loading: '正在检查页面',
    noTab: '无法获取当前页面',
    pageReady: '可以开始视觉审稿。',
    pageUnsupported: 'Chrome 插件无法审稿这个页面。',
    ready: '工作台可在当前页面启动。',
    active: '当前页面已开启视觉工作台。',
    activated: '已激活，回到页面即可编辑。',
    exited: '已退出审稿模式。',
    permissionChecking: '正在检查当前站点授权',
    permissionGranted: '当前站点已授权，可重复审稿。',
    permissionActiveTab: '本次点击可直接开始审稿。授权当前站点后，刷新/重复使用更稳定。',
    permissionUnsupported: 'Chrome 不允许插件注入这个页面。',
    permissionGranting: '授权中',
    permissionGrantedNow: '已授权',
    permissionDenied: '尚未授权。本次 activeTab 点击仍可开始审稿。',
    grantCurrentSite: '授权站点',
    fileDetails: '复制详情页地址',
    receiverChecking: '正在检查 127.0.0.1:3456',
    receiverOnline: '在线。保存会写入本地反馈文件。',
    receiverTokenMissing: '在线。保存前请刷新配置。',
    receiverOffline: '离线。可先审稿，保存前复制 setup到当前线程。',
    receiverOptional: '接收端可等保存前再开',
    reviewLabel: '审稿',
    reviewEmpty: '还没有保存反馈。',
    reviewSaved: '已保存 {count} 条反馈。回到 agent 说“反馈好了”。',
    reviewPreview: '已保存 {count} 条反馈，回贴预览已生成。',
    reviewVerified: '已保存 {count} 条反馈，验证结果已生成。',
    copySetup: '复制 setup',
    refreshConfig: '刷新配置',
    copied: '已复制',
    fileAccess: '请在插件详情里开启“允许访问文件网址”。',
    injectionFailed: '注入失败：',
    start: '开始审稿',
    exit: '退出审稿',
    starting: '正在启动',
    closing: '正在退出',
    footerRight: 'v4.0 beta 工作台',
    agentDefault: '默认',
    darkTheme: '深色主题',
    lightTheme: '浅色主题'
  }
};

function t(key) {
  return copy[lang][key] || copy.en[key] || key;
}

function format(key, values = {}) {
  return t(key).replace(/\{(\w+)\}/g, (_match, name) => String(values[name] ?? ''));
}

function icon(name) {
  return window.VFSHugeicons ? window.VFSHugeicons.renderIcon(name) : '';
}

function renderIconTargets() {
  document.querySelectorAll('[data-icon]').forEach(node => {
    const name = node.dataset.icon;
    if (window.VFSHugeicons && name) window.VFSHugeicons.mountIcon(node, name);
  });
}

async function getStoredPrefs() {
  try {
    const data = await chrome.storage.local.get({ [LANG_KEY]: 'zh', [THEME_KEY]: 'dark', [AGENT_KEY]: '', [TOKEN_KEY]: '' });
    return {
      lang: data[LANG_KEY] === 'en' ? 'en' : 'zh',
      theme: data[THEME_KEY] === 'light' ? 'light' : 'dark',
      agent: data[AGENT_KEY] === 'codex' || data[AGENT_KEY] === 'claude' ? data[AGENT_KEY] : '',
      token: /^[A-Za-z0-9._:-]{12,256}$/.test(data[TOKEN_KEY] || '') ? data[TOKEN_KEY] : ''
    };
  } catch {
    return { lang: 'zh', theme: 'dark', agent: '', token: '' };
  }
}

async function setStoredPrefs(next = {}) {
  if (next.lang) lang = next.lang === 'zh' ? 'zh' : 'en';
  if (next.theme) theme = next.theme === 'light' ? 'light' : 'dark';
  if (Object.prototype.hasOwnProperty.call(next, 'agent')) {
    agentOverride = next.agent === 'codex' || next.agent === 'claude' ? next.agent : '';
  }
  if (Object.prototype.hasOwnProperty.call(next, 'token')) {
    receiverToken = /^[A-Za-z0-9._:-]{12,256}$/.test(next.token || '') ? next.token : '';
  }
  try {
    await chrome.storage.local.set({ [LANG_KEY]: lang, [THEME_KEY]: theme, [AGENT_KEY]: agentOverride, [TOKEN_KEY]: receiverToken });
  } catch {
    // Storage may be unavailable on restricted pages.
  }
  render();
  syncPrefsToPage();
}

function render() {
  document.body.classList.toggle('theme-light', theme === 'light');
  document.body.classList.toggle('theme-dark', theme !== 'light');
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });

  langEn.classList.toggle('active', lang === 'en');
  langZh.classList.toggle('active', lang === 'zh');
  agentDefault.classList.toggle('active', agentOverride === '');
  agentCodex.classList.toggle('active', agentOverride === 'codex');
  agentClaude.classList.toggle('active', agentOverride === 'claude');
  themeToggle.classList.toggle('active', theme === 'light');
  themeToggle.dataset.icon = theme === 'light' ? 'light' : 'dark';
  themeToggle.title = theme === 'light' ? t('lightTheme') : t('darkTheme');
  themeToggle.setAttribute('aria-label', themeToggle.title);

  const pageOk = Boolean(activeTabId && activeTabScriptable);
  pageRow.className = `status-row ${pageOk ? 'ok' : 'err'}`;
  workspaceRow.className = `status-row ${toolActive ? 'ok' : ''}`;
  permissionRow.className = `status-row ${permissionState === 'granted' ? 'ok' : (permissionState === 'unsupported' ? 'err' : 'warn')}`;
  receiverRow.className = `status-row ${receiverOnline ? 'ok' : 'warn'}`;
  const savedCount = Number(receiverHealth?.feedback_summary?.change_count || receiverHealth?.last_change_count || 0);
  const previewReady = Boolean(receiverHealth?.preview_summary?.exists || receiverHealth?.last_preview_file);
  const verifyReady = Boolean(receiverHealth?.verify_summary?.exists || receiverHealth?.last_verify_file);
  reviewRow.className = `status-row ${savedCount > 0 ? 'ok' : 'warn'}`;
  document.getElementById('receiver-icon').dataset.icon = receiverOnline ? 'receiverOn' : 'receiverOff';

  pageStatus.textContent = activeTabId ? (activeTabScriptable ? t('pageReady') : t('pageUnsupported')) : t('noTab');
  workspaceStatus.textContent = toolActive ? t('active') : t('ready');
  if (permissionMessage) {
    permissionStatus.textContent = permissionMessage;
  } else if (permissionState === 'granted') {
    permissionStatus.textContent = t('permissionGranted');
  } else if (permissionState === 'file') {
    permissionStatus.textContent = t('fileAccess');
  } else if (permissionState === 'unsupported') {
    permissionStatus.textContent = t('permissionUnsupported');
  } else if (permissionBusy) {
    permissionStatus.textContent = t('permissionGranting');
  } else {
    permissionStatus.textContent = t('permissionActiveTab');
  }
  permissionActions.classList.toggle('visible', permissionState === 'requestable' || permissionState === 'file');
  permissionAction.textContent = permissionBusy ? t('permissionGranting') : (permissionState === 'file' ? t('fileDetails') : t('grantCurrentSite'));
  receiverStatus.textContent = receiverOnline
    ? (receiverTokenRequired && !receiverToken ? t('receiverTokenMissing') : t('receiverOnline'))
    : t('receiverOffline');
  if (!receiverOnline) {
    reviewStatus.textContent = t('reviewEmpty');
  } else if (verifyReady) {
    reviewStatus.textContent = format('reviewVerified', { count: savedCount });
  } else if (previewReady) {
    reviewStatus.textContent = format('reviewPreview', { count: savedCount });
  } else if (savedCount > 0) {
    reviewStatus.textContent = format('reviewSaved', { count: savedCount });
  } else {
    reviewStatus.textContent = t('reviewEmpty');
  }
  footerLeft.textContent = receiverOnline ? '127.0.0.1:3456' : t('receiverOptional');
  const needsConfig = receiverOnline && receiverTokenRequired && !receiverToken;
  receiverActions.classList.toggle('visible', !receiverOnline || needsConfig);
  receiverAction.textContent = needsConfig ? t('refreshConfig') : t('copySetup');

  btn.disabled = busy || !activeTabId || !activeTabScriptable || permissionState === 'file';
  btn.classList.toggle('exit', toolActive);
  btn.querySelector('[data-i18n]').textContent = busy
    ? (toolActive ? t('closing') : t('starting'))
    : (toolActive ? t('exit') : t('start'));
  btn.querySelector('[data-icon]').dataset.icon = toolActive ? 'exitReview' : 'start';

  renderIconTargets();
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab || null;
}

function permissionPatternForUrl(rawUrl) {
  try {
    const url = new URL(rawUrl || '');
    if (url.protocol === 'http:' || url.protocol === 'https:') return `${url.protocol}//${url.host}/*`;
    if (url.protocol === 'file:') return 'file:///*';
  } catch {
    return '';
  }
  return '';
}

function isScriptableUrl(rawUrl) {
  try {
    const url = new URL(rawUrl || '');
    return url.protocol === 'http:' || url.protocol === 'https:' || url.protocol === 'file:';
  } catch {
    return false;
  }
}

async function hasOptionalPermission(origin) {
  if (!origin || !chrome.permissions?.contains) return false;
  try {
    return await chrome.permissions.contains({ origins: [origin] });
  } catch {
    return false;
  }
}

async function checkCurrentSitePermission() {
  permissionOrigin = permissionPatternForUrl(activeTabUrl);
  if (!activeTabId || !activeTabScriptable || !permissionOrigin) {
    permissionState = 'unsupported';
    return;
  }
  const granted = await hasOptionalPermission(permissionOrigin);
  if (granted) {
    permissionState = 'granted';
    return;
  }
  permissionState = permissionOrigin === 'file:///*' ? 'file' : 'requestable';
}

async function isToolActive(tabId) {
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => !!window.__vf__
    });
    return result;
  } catch {
    return false;
  }
}

async function getPagePrefs(tabId) {
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        const prefs = {};
        if (window.__vf__) {
          if (typeof window.__vf__.getLang === 'function') prefs.lang = window.__vf__.getLang();
          if (typeof window.__vf__.getTheme === 'function') prefs.theme = window.__vf__.getTheme();
          if (typeof window.__vf__.getAgentOverride === 'function') {
            prefs.agent = window.__vf__.getAgentOverride();
            prefs.hasAgent = true;
          }
        }
        try {
          prefs.lang = prefs.lang || (window.localStorage && window.localStorage.getItem('__vfs_lang'));
          prefs.theme = prefs.theme || (window.localStorage && window.localStorage.getItem('__vfs_theme'));
          if (!prefs.hasAgent && window.localStorage) {
            const storedAgent = window.localStorage.getItem('__vfs_agent');
            if (storedAgent === 'codex' || storedAgent === 'claude') {
              prefs.agent = storedAgent;
              prefs.hasAgent = true;
            }
          }
        } catch {
          // localStorage may be unavailable on restricted pages.
        }
        return prefs;
      }
    });
    return {
      lang: result?.lang === 'zh' ? 'zh' : result?.lang === 'en' ? 'en' : null,
      theme: result?.theme === 'light' ? 'light' : result?.theme === 'dark' ? 'dark' : null,
      agent: result?.hasAgent ? (result.agent === 'codex' || result.agent === 'claude' ? result.agent : '') : null
    };
  } catch {
    return { lang: null, theme: null, agent: null };
  }
}

async function syncPrefsToPage() {
  if (!activeTabId) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId: activeTabId },
      args: [lang, theme, agentOverride, receiverToken],
      func: (nextLang, nextTheme, nextAgent, nextToken) => {
        try {
          if (window.localStorage) {
            window.localStorage.setItem('__vfs_lang', nextLang);
            window.localStorage.setItem('__vfs_theme', nextTheme);
            if (nextAgent === 'codex' || nextAgent === 'claude') window.localStorage.setItem('__vfs_agent', nextAgent);
            else window.localStorage.removeItem('__vfs_agent');
            if (nextToken) window.localStorage.setItem('__vfs_token', nextToken);
            else window.localStorage.removeItem('__vfs_token');
          }
        } catch {
          // localStorage may be unavailable on restricted pages.
        }
        if (window.__vf__) {
          if (typeof window.__vf__.setLang === 'function') window.__vf__.setLang(nextLang);
          if (typeof window.__vf__.setTheme === 'function') window.__vf__.setTheme(nextTheme);
          if (typeof window.__vf__.setAgent === 'function') window.__vf__.setAgent(nextAgent);
          if (typeof window.__vf__.setToken === 'function') window.__vf__.setToken(nextToken);
        }
      }
    });
  } catch {
    // The page may not have the review layer injected yet.
  }
}

async function checkReceiver() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 900);
  try {
    const response = await fetch(`http://127.0.0.1:${DEFAULT_PORT}/health`, {
      signal: controller.signal,
      cache: 'no-store'
    });
    const payload = response.ok ? await response.json() : null;
    receiverOnline = Boolean(payload && payload.ok);
    receiverTokenRequired = Boolean(payload && payload.token_required);
    receiverHealth = receiverOnline ? payload : null;
    if (receiverOnline) {
      await syncReceiverConfig();
    }
  } catch {
    receiverOnline = false;
    receiverTokenRequired = false;
    receiverHealth = null;
  } finally {
    clearTimeout(timer);
  }
}

async function copySetupCommand() {
  try {
    await navigator.clipboard.writeText(SETUP_COMMAND);
    receiverAction.textContent = t('copied');
    setTimeout(() => { receiverAction.textContent = t('copySetup'); }, 1100);
  } catch {
    receiverAction.textContent = t('copySetup');
  }
}

async function syncReceiverConfig() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 900);
  try {
    const response = await fetch(`http://127.0.0.1:${DEFAULT_PORT}/config`, {
      signal: controller.signal,
      cache: 'no-store'
    });
    const payload = response.ok ? await response.json() : null;
    if (payload && payload.ok && typeof payload.token === 'string') {
      receiverToken = payload.token;
      await chrome.storage.local.set({ [TOKEN_KEY]: receiverToken });
    }
  } catch {
    // Older receivers do not expose /config; saving can still use manual export.
  } finally {
    clearTimeout(timer);
  }
}

async function init() {
  renderIconTargets();
  const prefs = await getStoredPrefs();
  lang = prefs.lang;
  theme = prefs.theme;
  agentOverride = prefs.agent;
  receiverToken = prefs.token;
  const activeTab = await getActiveTab();
  activeTabId = activeTab?.id ?? null;
  activeTabUrl = activeTab?.url || '';
  activeTabScriptable = isScriptableUrl(activeTabUrl);
  if (activeTabId) {
    await checkCurrentSitePermission();
    toolActive = await isToolActive(activeTabId);
    const pagePrefs = await getPagePrefs(activeTabId);
    if (pagePrefs.lang) lang = pagePrefs.lang;
    if (pagePrefs.theme) theme = pagePrefs.theme;
    if (pagePrefs.agent !== null) agentOverride = pagePrefs.agent;
    try {
      await chrome.storage.local.set({ [LANG_KEY]: lang, [THEME_KEY]: theme, [AGENT_KEY]: agentOverride, [TOKEN_KEY]: receiverToken });
    } catch {
      // Keep rendering even if storage is unavailable.
    }
  }
  await checkReceiver();
  busy = false;
  render();
}

async function requestCurrentSitePermission() {
  if (permissionBusy || !permissionOrigin) return;
  permissionBusy = true;
  render();
  if (permissionState === 'file') {
    try {
      await navigator.clipboard.writeText(`chrome://extensions/?id=${chrome.runtime.id}`);
      permissionMessage = t('copied');
    } catch {
      permissionMessage = t('fileAccess');
    }
    permissionBusy = false;
    render();
    setTimeout(() => { permissionMessage = ''; render(); }, 1400);
    return;
  }
  try {
    const granted = await chrome.permissions.request({ origins: [permissionOrigin] });
    permissionState = granted ? 'granted' : 'requestable';
    permissionMessage = granted ? t('permissionGrantedNow') : t('permissionDenied');
  } catch {
    permissionState = 'requestable';
    permissionMessage = t('permissionDenied');
  } finally {
    permissionBusy = false;
    render();
    setTimeout(() => { permissionMessage = ''; render(); }, 1400);
  }
}

async function activate(tabId) {
  busy = true;
  render();
  try {
    await syncPrefsToPage();
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ['hugeicons.js', 'vfs-helpers.js', 'inject.js']
    });
    await syncPrefsToPage();
    toolActive = true;
    busy = false;
    render();
    workspaceStatus.textContent = t('activated');
    workspaceRow.className = 'status-row ok';
    setTimeout(() => window.close(), 820);
  } catch (e) {
    busy = false;
    workspaceStatus.textContent = e.message.includes('file')
      ? t('fileAccess')
      : t('injectionFailed') + e.message;
    workspaceRow.className = 'status-row err';
    renderIconTargets();
  }
}

async function deactivate(tabId) {
  busy = true;
  render();
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: () => { if (window.__vf__) window.__vf__.exit(); }
    });
  } catch {
    // The tab may have navigated.
  }
  toolActive = false;
  busy = false;
  render();
  workspaceStatus.textContent = t('exited');
  workspaceRow.className = 'status-row ok';
  setTimeout(() => window.close(), 620);
}

btn.addEventListener('click', () => {
  if (!activeTabId || busy) return;
  if (toolActive) deactivate(activeTabId);
  else activate(activeTabId);
});

langEn.addEventListener('click', () => setStoredPrefs({ lang: 'en' }));
langZh.addEventListener('click', () => setStoredPrefs({ lang: 'zh' }));
agentDefault.addEventListener('click', () => setStoredPrefs({ agent: '' }));
agentCodex.addEventListener('click', () => setStoredPrefs({ agent: 'codex' }));
agentClaude.addEventListener('click', () => setStoredPrefs({ agent: 'claude' }));
themeToggle.addEventListener('click', () => setStoredPrefs({ theme: theme === 'light' ? 'dark' : 'light' }));
permissionAction.addEventListener('click', requestCurrentSitePermission);
receiverAction.addEventListener('click', async () => {
  if (receiverOnline && receiverTokenRequired && !receiverToken) {
    await syncReceiverConfig();
    await syncPrefsToPage();
    render();
  } else {
    await copySetupCommand();
  }
});

init();
