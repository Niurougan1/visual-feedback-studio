#!/usr/bin/env node
const http = require('http');
const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');

const PORT = Number(process.env.VFS_PORT || 3456);
const HOST = process.env.VFS_HOST || '127.0.0.1';
const FEEDBACK_FILE = path.resolve(
  process.env.VFS_FEEDBACK_FILE || path.join(process.cwd(), '.visual_feedback_studio.json')
);
const TOKENS_FILE = path.resolve(
  process.env.VFS_TOKENS_FILE || path.join(process.cwd(), '.visual_feedback_studio_tokens.json')
);
const PREVIEW_FILE = path.resolve(
  process.env.VFS_PREVIEW_FILE || path.join(process.cwd(), '.visual_feedback_studio_preview.json')
);
const VERIFY_FILE = path.resolve(
  process.env.VFS_VERIFY_FILE || path.join(process.cwd(), '.visual_feedback_studio_verify.json')
);
const STATE_FILE = process.env.VFS_STATE_FILE ? path.resolve(process.env.VFS_STATE_FILE) : '';
const SCRIPT_DIR = __dirname;
const MAX_BODY_BYTES = Number(process.env.VFS_MAX_BODY_BYTES || 5_000_000);
const TOKEN = String(process.env.VFS_TOKEN || '').trim();
const EXTRA_ALLOWED_ORIGINS = String(process.env.VFS_ALLOWED_ORIGINS || '')
  .split(',')
  .map(item => item.trim())
  .filter(Boolean);
const KNOWN_AGENTS = new Set(['codex', 'claude']);
const RAW_AGENT = String(process.env.VFS_AGENT || 'codex').toLowerCase();
const DEFAULT_AGENT = KNOWN_AGENTS.has(RAW_AGENT) ? RAW_AGENT : 'codex';

if (!Number.isInteger(PORT) || PORT < 1 || PORT > 65535) {
  console.error(`Invalid VFS_PORT: ${process.env.VFS_PORT}`);
  process.exit(2);
}

if (!KNOWN_AGENTS.has(RAW_AGENT)) {
  console.warn(`Invalid VFS_AGENT: ${process.env.VFS_AGENT}. Falling back to codex.`);
}

function sendJson(res, status, payload) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(payload));
}

function readJsonFile(file, fallback = null) {
  try {
    if (!fs.existsSync(file)) return fallback;
    const raw = fs.readFileSync(file, 'utf8').trim();
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJsonFile(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmpFile = `${file}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmpFile, JSON.stringify(payload, null, 2));
  fs.renameSync(tmpFile, file);
}

function updateState(patch) {
  if (!STATE_FILE) return;
  const existing = readJsonFile(STATE_FILE, {}) || {};
  writeJsonFile(STATE_FILE, { ...existing, ...patch });
}

function runPython(scriptName, args, callback) {
  const script = path.join(SCRIPT_DIR, scriptName);
  childProcess.execFile(
    'python3',
    [script, ...args],
    { cwd: process.cwd(), timeout: 15000, maxBuffer: 5 * 1024 * 1024 },
    (error, stdout, stderr) => {
      let payload = null;
      try {
        payload = stdout ? JSON.parse(stdout) : null;
      } catch (parseError) {
        callback(parseError, { ok: false, error: parseError.message, stdout, stderr });
        return;
      }
      if (error || !payload || payload.ok === false) {
        callback(error || new Error((payload && payload.error) || stderr || 'script failed'), payload || { ok: false, stderr });
        return;
      }
      callback(null, payload);
    }
  );
}

function summarizeFeedbackFile(file) {
  const payload = readJsonFile(file, null);
  const sessions = payload && Array.isArray(payload.sessions) ? payload.sessions : [];
  let changeCount = 0;
  let latestTimestamp = '';
  const lifecycleCounts = {};
  const typeCounts = {};
  sessions.forEach(session => {
    if (session && typeof session === 'object') {
      const timestamp = String(session.timestamp || '');
      if (timestamp > latestTimestamp) latestTimestamp = timestamp;
      const changes = Array.isArray(session.changes) ? session.changes : [];
      changeCount += changes.length;
      changes.forEach(change => {
        if (!change || typeof change !== 'object') return;
        const lifecycle = String(change.lifecycle_status || change.status || 'captured');
        lifecycleCounts[lifecycle] = (lifecycleCounts[lifecycle] || 0) + 1;
        const type = String(change.type || 'unknown');
        typeCounts[type] = (typeCounts[type] || 0) + 1;
      });
    }
  });
  return {
    session_count: sessions.length,
    change_count: changeCount,
    latest_timestamp: latestTimestamp,
    lifecycle_counts: lifecycleCounts,
    type_counts: typeCounts,
  };
}

function summarizePreviewFile(file) {
  const preview = readJsonFile(file, null);
  return preview && preview.ok ? {
    exists: true,
    counts: preview.counts || {},
    latest_timestamp: preview.latest_timestamp || '',
  } : { exists: false, counts: {}, latest_timestamp: '' };
}

function summarizeVerifyFile(file) {
  const verify = readJsonFile(file, null);
  return verify && verify.ok ? {
    exists: true,
    counts: verify.counts || {},
    verification_mode: verify.verification_mode || '',
    report_schema: verify.report_schema || '',
    rollback_available: Boolean(verify.rollback_command),
    evidence_counts: verify.evidence_counts || {},
  } : { exists: false, counts: {}, verification_mode: '' };
}

function isLoopbackHost(hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1' || hostname === '[::1]';
}

function isAllowedOrigin(origin, options = {}) {
  if (!origin) return true;
  if (origin === 'null') return true;
  if (EXTRA_ALLOWED_ORIGINS.includes(origin)) return true;
  try {
    const parsed = new URL(origin);
    if (options.allowExtension && parsed.protocol === 'chrome-extension:') return true;
    if (parsed.protocol === 'file:') return true;
    if ((parsed.protocol === 'http:' || parsed.protocol === 'https:') && isLoopbackHost(parsed.hostname)) return true;
  } catch {
    return false;
  }
  return false;
}

function isExtensionOrigin(origin) {
  if (!origin) return false;
  try {
    return new URL(origin).protocol === 'chrome-extension:';
  } catch {
    return false;
  }
}

function setCors(req, res, options = {}) {
  const origin = req.headers.origin || '';
  if (isAllowedOrigin(origin, options)) {
    if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-VFS-Token');
    res.setHeader('Access-Control-Max-Age', '600');
    return true;
  }
  return false;
}

function verifyToken(req) {
  if (!TOKEN) return true;
  return String(req.headers['x-vfs-token'] || '') === TOKEN;
}

function normalizeChange(change) {
  const allowedLifecycle = new Set(['captured', 'planned', 'applied', 'verified', 'needs_review', 'unresolved']);
  const rawLifecycle = String(change.lifecycle_status || '').trim();
  const lifecycle = allowedLifecycle.has(rawLifecycle) ? rawLifecycle : 'captured';
  return {
    ...change,
    status: change.status || lifecycle,
    lifecycle_status: lifecycle,
  };
}

function readExisting() {
  if (!fs.existsSync(FEEDBACK_FILE)) return { sessions: [] };
  const raw = fs.readFileSync(FEEDBACK_FILE, 'utf8').trim();
  if (!raw) return { sessions: [] };
  const parsed = JSON.parse(raw);
  if (!parsed || !Array.isArray(parsed.sessions)) return { sessions: [] };
  return parsed;
}

function normalizeSession(session) {
  if (!session || typeof session !== 'object') {
    throw new Error('request body must be a JSON object');
  }
  const changes = Array.isArray(session.changes)
    ? session.changes.filter(change => change && typeof change === 'object')
    : [];
  const sessionAgent = String(session.agent || '').toLowerCase();
  return {
    version: session.version || '4.0-beta',
    timestamp: session.timestamp || new Date().toISOString(),
    agent: KNOWN_AGENTS.has(sessionAgent) ? sessionAgent : DEFAULT_AGENT,
    source_url: session.source_url || '',
    page_title: session.page_title || '',
    viewport: session.viewport || null,
    changes: changes.map(normalizeChange)
  };
}

function writeFeedback(data) {
  fs.mkdirSync(path.dirname(FEEDBACK_FILE), { recursive: true });
  const tmpFile = `${FEEDBACK_FILE}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmpFile, JSON.stringify(data, null, 2));
  fs.renameSync(tmpFile, FEEDBACK_FILE);
}

const server = http.createServer((req, res) => {
  const allowExtension = [
    '/config',
    '/feedback',
    '/health',
    '/',
    '/tokens',
    '/tokens/rescan',
    '/preview',
    '/verify-result',
    '/apply-preview',
    '/verify',
  ].includes(req.url);
  const corsAllowed = setCors(req, res, { allowExtension });

  if (req.method === 'OPTIONS') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method === 'GET' && (req.url === '/' || req.url === '/health')) {
    const state = readJsonFile(STATE_FILE, {}) || {};
    sendJson(res, 200, {
      ok: true,
      host: HOST,
      port: PORT,
      feedback_file: FEEDBACK_FILE,
      tokens_file: TOKENS_FILE,
      preview_file: PREVIEW_FILE,
      verify_file: VERIFY_FILE,
      agent: DEFAULT_AGENT,
      token_required: Boolean(TOKEN),
      last_saved_at: state.last_saved_at || '',
      last_feedback_file: state.last_feedback_file || '',
      last_change_count: state.last_change_count || 0,
      last_preview_at: state.last_preview_at || '',
      last_preview_file: state.last_preview_file || '',
      last_verify_at: state.last_verify_at || '',
      last_verify_file: state.last_verify_file || '',
      feedback_summary: summarizeFeedbackFile(FEEDBACK_FILE),
      preview_summary: summarizePreviewFile(PREVIEW_FILE),
      verify_summary: summarizeVerifyFile(VERIFY_FILE),
    });
    return;
  }

  if (req.method === 'GET' && req.url === '/config') {
    if (!corsAllowed || !isExtensionOrigin(req.headers.origin || '')) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    sendJson(res, 200, { ok: true, host: HOST, port: PORT, agent: DEFAULT_AGENT, token_required: Boolean(TOKEN), token: TOKEN });
    return;
  }

  if (req.method === 'GET' && req.url === '/tokens') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    const payload = readJsonFile(TOKENS_FILE, { ok: true, token_count: 0, tokens: [] });
    sendJson(res, 200, { ok: true, tokens_file: TOKENS_FILE, ...(payload || {}), token_required: undefined });
    return;
  }

  if (req.method === 'POST' && req.url === '/tokens/rescan') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    runPython('scan_design_tokens.py', [process.cwd(), '--output', TOKENS_FILE], (error, payload) => {
      if (error) {
        sendJson(res, 500, payload || { ok: false, error: error.message });
        return;
      }
      updateState({ last_tokens_rescan_at: new Date().toISOString(), last_tokens_file: TOKENS_FILE });
      sendJson(res, 200, { ok: true, tokens_file: TOKENS_FILE, ...(payload || {}), token_required: undefined });
    });
    return;
  }

  if (req.method === 'GET' && req.url === '/preview') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    const preview = readJsonFile(PREVIEW_FILE, null);
    sendJson(res, preview ? 200 : 404, preview ? { ok: true, preview_file: PREVIEW_FILE, preview } : { ok: false, error: 'preview not found', preview_file: PREVIEW_FILE });
    return;
  }

  if (req.method === 'GET' && req.url === '/verify-result') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    const verify = readJsonFile(VERIFY_FILE, null);
    sendJson(res, verify ? 200 : 404, verify ? { ok: true, verify_file: VERIFY_FILE, verify } : { ok: false, error: 'verify result not found', verify_file: VERIFY_FILE });
    return;
  }

  if (req.method === 'POST' && req.url === '/apply-preview') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    runPython('plan_feedback_apply.py', [process.cwd(), '--feedback-file', FEEDBACK_FILE], (error, payload) => {
      if (error) {
        sendJson(res, 500, payload || { ok: false, error: error.message });
        return;
      }
      writeJsonFile(PREVIEW_FILE, payload);
      updateState({ last_preview_at: new Date().toISOString(), last_preview_file: PREVIEW_FILE });
      sendJson(res, 200, { ok: true, preview_file: PREVIEW_FILE, preview: payload });
    });
    return;
  }

  if (req.method === 'POST' && req.url === '/verify') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    const args = [process.cwd(), '--feedback-file', FEEDBACK_FILE, '--output', VERIFY_FILE];
    if (fs.existsSync(PREVIEW_FILE)) args.push('--preview-file', PREVIEW_FILE);
    runPython('verify_feedback_apply.py', args, (error, payload) => {
      if (error) {
        sendJson(res, 500, payload || { ok: false, error: error.message });
        return;
      }
      updateState({ last_verify_at: new Date().toISOString(), last_verify_file: VERIFY_FILE });
      sendJson(res, 200, { ok: true, verify_file: VERIFY_FILE, verify: payload });
    });
    return;
  }

  if (req.method === 'POST' && req.url === '/feedback') {
    if (!corsAllowed) {
      sendJson(res, 403, { ok: false, error: 'origin not allowed' });
      return;
    }
    if (!verifyToken(req)) {
      sendJson(res, 401, { ok: false, error: 'invalid or missing token' });
      return;
    }
    let body = '';
    let tooLarge = false;
    req.on('data', chunk => {
      body += chunk;
      if (body.length > MAX_BODY_BYTES) {
        tooLarge = true;
        req.destroy();
      }
    });
    req.on('error', () => {
      if (!res.headersSent) sendJson(res, tooLarge ? 413 : 400, { ok: false, error: tooLarge ? 'request body too large' : 'request aborted' });
    });
    req.on('end', () => {
      try {
        if (tooLarge) {
          sendJson(res, 413, { ok: false, error: 'request body too large' });
          return;
        }
        const session = normalizeSession(JSON.parse(body));
        const existing = readExisting();
        existing.sessions.push(session);
        writeFeedback(existing);
        const count = session.changes.length;
        updateState({ last_saved_at: new Date().toISOString(), last_feedback_file: FEEDBACK_FILE, last_change_count: count });
        console.log(`[${new Date().toLocaleTimeString()}] saved ${count} change(s) -> ${FEEDBACK_FILE}`);
        sendJson(res, 200, { ok: true, feedback_file: FEEDBACK_FILE, changes: count, agent: session.agent });
      } catch (error) {
        sendJson(res, 400, { ok: false, error: error.message });
      }
    });
    return;
  }

  sendJson(res, 404, { ok: false, error: 'not found' });
});

server.on('error', error => {
  if (error.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use. Try VFS_PORT=<free-port>.`);
  } else {
    console.error(error.message);
  }
  process.exit(1);
});

server.listen(PORT, HOST, () => {
  console.log(`Visual Feedback Studio receiver on http://${HOST}:${PORT}`);
  console.log(`Writing feedback to: ${FEEDBACK_FILE}`);
  console.log(`Default agent: ${DEFAULT_AGENT}`);
});
