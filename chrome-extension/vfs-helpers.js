(function (root) {
  'use strict';

  function attr(el, name) {
    return el && typeof el.getAttribute === 'function' ? (el.getAttribute(name) || '') : '';
  }

  function cleanText(value, limit = 80) {
    return String(value || '').replace(/\s+/g, ' ').trim().slice(0, limit);
  }

  function isStableId(id) {
    const value = String(id || '').trim();
    if (!value || value.length > 80) return false;
    if (/^\d+$/.test(value)) return false;
    if (/^(?:r|react-select|headlessui|radix|mui|chakra|ember|rc|ant)[-_:]?\d+/i.test(value)) return false;
    if (/[a-f0-9]{10,}/i.test(value) && /[-_][a-f0-9]{6,}/i.test(value)) return false;
    return true;
  }

  function normalizeSourceLoc(value) {
    if (!value) return null;
    if (typeof value === 'object') {
      const file = String(value.file || value.fileName || value.filename || '').trim();
      const line = Number(value.line || value.lineNumber || 0);
      const column = Number(value.column || value.columnNumber || 0);
      if (!file) return null;
      return {
        file,
        line: Number.isFinite(line) && line > 0 ? Math.round(line) : 0,
        column: Number.isFinite(column) && column >= 0 ? Math.round(column) : 0
      };
    }
    const raw = String(value || '').trim();
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      const normalized = normalizeSourceLoc(parsed);
      if (normalized) return normalized;
    } catch {
      // Most dev source hints are compact strings, not JSON.
    }
    const match = raw.match(/^(.+?)(?::(\d+))(?::(\d+))?$/);
    if (!match) return { file: raw, line: 0, column: 0 };
    return {
      file: match[1],
      line: Number(match[2] || 0),
      column: Number(match[3] || 0)
    };
  }

  function readElementSourceLoc(el) {
    const direct = normalizeSourceLoc(attr(el, 'data-source') || attr(el, 'data-source-loc') || attr(el, 'data-loc'));
    if (direct) return direct;
    const file = attr(el, 'data-source-file') || attr(el, 'data-file') || attr(el, 'data-vite-dev-id');
    if (!file) return null;
    return normalizeSourceLoc({
      file,
      line: attr(el, 'data-source-line') || attr(el, 'data-line'),
      column: attr(el, 'data-source-column') || attr(el, 'data-column')
    });
  }

  function readAncestorElementSourceLoc(el) {
    let cur = el;
    let guard = 0;
    while (cur && guard < 8) {
      const direct = readElementSourceLoc(cur);
      if (direct) return direct;
      cur = cur.parentElement;
      guard += 1;
    }
    return null;
  }

  function readReactFiber(el) {
    if (!el) return null;
    try {
      const key = Object.keys(el).find(name => name.startsWith('__reactFiber$') || name.startsWith('__reactInternalInstance$'));
      return key ? el[key] : null;
    } catch {
      return null;
    }
  }

  function fiberName(fiber) {
    const type = fiber && (fiber.elementType || fiber.type);
    if (!type) return '';
    return cleanText(type.displayName || type.name || (typeof type === 'string' ? type : ''), 80);
  }

  function readReactFiberInfo(el) {
    const chain = [];
    let fiber = readReactFiber(el);
    let guard = 0;
    let previous = '';
    let debugSource = null;
    let componentName = '';

    while (fiber && guard < 25) {
      const name = fiberName(fiber);
      const sourceLoc = normalizeSourceLoc(fiber._debugSource);
      if (!debugSource && sourceLoc) debugSource = sourceLoc;
      if (name && !/^[a-z]+$/.test(name)) {
        if (!componentName) componentName = name;
        if (name !== previous) {
          chain.push({ name, framework: 'react', sourceLoc });
          previous = name;
        }
      }
      fiber = fiber.return;
      guard += 1;
    }

    return { debugSource, componentName, componentChain: chain.slice(0, 12) };
  }

  function readReactDebugSource(el) {
    return readReactFiberInfo(el).debugSource;
  }

  function readDevSource(el) {
    return readAncestorElementSourceLoc(el) || readReactDebugSource(el);
  }

  function readDirectComponentName(el) {
    return cleanText(
      attr(el, 'data-component') ||
      attr(el, 'data-component-name') ||
      attr(el, 'data-source-component') ||
      attr(el, 'data-vfs-component'),
      80
    );
  }

  function readVueComponentName(el) {
    const vue = el && (el.__vueParentComponent || el.__vue__);
    const vueType = vue ? (vue.type || vue.$options || {}) : {};
    return cleanText(vueType.name || vueType.__name || '', 80);
  }

  function readComponentName(el) {
    const direct = readDirectComponentName(el);
    if (direct) return direct;

    const vueName = readVueComponentName(el);
    if (vueName) return vueName;

    return readReactFiberInfo(el).componentName;
  }

  function reactComponentChain(el) {
    return readReactFiberInfo(el).componentChain;
  }

  function vueComponentChain(el) {
    const chain = [];
    let cur = el && (el.__vueParentComponent || el.__vue__);
    let guard = 0;
    let previous = '';
    while (cur && guard < 12) {
      const type = cur.type || cur.$options || {};
      const name = cleanText(type.name || type.__name || '', 80);
      const file = cleanText(type.__file || '', 180);
      if ((name || file) && `${name}|${file}` !== previous) {
        chain.push({
          name,
          framework: 'vue',
          sourceLoc: file ? { file, line: 0, column: 0 } : null
        });
        previous = `${name}|${file}`;
      }
      cur = cur.parent;
      guard += 1;
    }
    return chain;
  }

  function detectFramework(el) {
    if (readReactFiber(el)) return 'react';
    if (el && (el.__vueParentComponent || el.__vue__)) return 'vue';
    let cur = el;
    let guard = 0;
    while (cur && guard < 8) {
      if (attr(cur, 'data-svelte-h')) return 'svelte';
      if (attr(cur, 'data-astro-cid') || attr(cur, 'data-astro-source-file')) return 'astro';
      cur = cur.parentElement;
      guard += 1;
    }
    return 'unknown';
  }

  function componentChain(el) {
    const react = reactComponentChain(el);
    if (react.length) return react;
    const vue = vueComponentChain(el);
    if (vue.length) return vue;
    const direct = readComponentName(el);
    return direct ? [{ name: direct, framework: 'unknown', sourceLoc: null }] : [];
  }

  function domPath(el) {
    const path = [];
    let cur = el;
    let guard = 0;
    const docElement = typeof document !== 'undefined' ? document.documentElement : null;
    while (cur && cur.nodeType === 1 && guard < 8 && cur !== docElement) {
      path.push({
        tag: cur.tagName ? cur.tagName.toLowerCase() : '',
        testId: attr(cur, 'data-testid') || attr(cur, 'data-test') || attr(cur, 'data-cy'),
        stableId: isStableId(cur.id) ? cur.id : '',
        role: attr(cur, 'role'),
        ariaLabel: attr(cur, 'aria-label'),
        classes: Array.from(cur.classList || []).filter(name => !name.startsWith('vf-') && !name.startsWith('__vf')).slice(0, 4),
        text: cleanText(cur.textContent, 80)
      });
      cur = cur.parentElement;
      guard += 1;
    }
    return path;
  }

  function confidenceReasons(anchors = {}, chain = []) {
    const reasons = [];
    if (anchors.testId) reasons.push('testId');
    if (anchors.sourceLoc) reasons.push('sourceLoc');
    if (anchors.stableId) reasons.push('stableId');
    if (anchors.componentName) reasons.push('componentName');
    if (chain.length) reasons.push('componentChain');
    if (anchors.role) reasons.push('role');
    if (anchors.ariaLabel) reasons.push('ariaLabel');
    if (!reasons.length && anchors.textFingerprint) reasons.push('textFingerprint');
    if (!reasons.length) reasons.push('selectorFallback');
    return reasons;
  }

  function detectDomFramework(el, reactInfo, vueName, vueChain) {
    if (reactInfo && (reactInfo.debugSource || reactInfo.componentName || (reactInfo.componentChain || []).length)) return 'react';
    if (vueName || (vueChain || []).length || (el && (el.__vueParentComponent || el.__vue__))) return 'vue';
    let cur = el;
    let guard = 0;
    while (cur && guard < 8) {
      if (attr(cur, 'data-svelte-h')) return 'svelte';
      if (attr(cur, 'data-astro-cid') || attr(cur, 'data-astro-source-file')) return 'astro';
      cur = cur.parentElement;
      guard += 1;
    }
    return 'unknown';
  }

  function normalizeAnchors(anchors = {}) {
    return {
      testId: anchors.testId || '',
      stableId: anchors.stableId || '',
      sourceLoc: anchors.sourceLoc || null,
      textFingerprint: anchors.textFingerprint || '',
      role: anchors.role || '',
      ariaLabel: anchors.ariaLabel || '',
      componentName: anchors.componentName || ''
    };
  }

  function getSourceAnchors(el) {
    try {
      const testId = attr(el, 'data-testid') || attr(el, 'data-test') || attr(el, 'data-cy');
      return normalizeAnchors({
        testId,
        stableId: isStableId(el && el.id) ? el.id : '',
        sourceLoc: readDevSource(el),
        textFingerprint: cleanText(el && el.textContent, 80),
        role: attr(el, 'role'),
        ariaLabel: attr(el, 'aria-label'),
        componentName: readComponentName(el)
      });
    } catch {
      return normalizeAnchors({
        testId: '',
        stableId: isStableId(el && el.id) ? el.id : '',
        sourceLoc: null,
        textFingerprint: cleanText(el && el.textContent, 80),
        role: attr(el, 'role'),
        ariaLabel: attr(el, 'aria-label'),
        componentName: ''
      });
    }
  }

  function locateConfidence(anchors = {}) {
    if (anchors.testId || anchors.sourceLoc) return 'high';
    if (anchors.stableId || anchors.componentName) return 'medium';
    return 'low';
  }

  function getSourceHint(el, anchors = getSourceAnchors(el)) {
    const chain = componentChain(el);
    const framework = detectFramework(el);
    const reasons = confidenceReasons(anchors, chain);
    return {
      anchors,
      framework: framework === 'unknown' && chain.length ? chain[0].framework || 'unknown' : framework,
      component_chain: chain,
      dom_path: domPath(el),
      confidence_reasons: reasons
    };
  }

  function getSourcePayload(el) {
    try {
      const reactInfo = readReactFiberInfo(el);
      const directName = readDirectComponentName(el);
      const vueName = readVueComponentName(el);
      const vueChain = reactInfo.componentChain.length ? [] : vueComponentChain(el);
      const componentName = directName || vueName || reactInfo.componentName;
      const sourceLoc = readAncestorElementSourceLoc(el) || reactInfo.debugSource;
      const chain = reactInfo.componentChain.length
        ? reactInfo.componentChain
        : vueChain.length
          ? vueChain
          : componentName
            ? [{ name: componentName, framework: 'unknown', sourceLoc: null }]
            : [];
      const anchors = normalizeAnchors({
        testId: attr(el, 'data-testid') || attr(el, 'data-test') || attr(el, 'data-cy'),
        stableId: isStableId(el && el.id) ? el.id : '',
        sourceLoc,
        textFingerprint: cleanText(el && el.textContent, 80),
        role: attr(el, 'role'),
        ariaLabel: attr(el, 'aria-label'),
        componentName
      });
      const detected = detectDomFramework(el, reactInfo, vueName, vueChain);
      const framework = detected === 'unknown' && chain.length ? chain[0].framework || 'unknown' : detected;
      const hint = {
        anchors,
        framework,
        component_chain: chain,
        dom_path: domPath(el),
        confidence_reasons: confidenceReasons(anchors, chain)
      };
      return {
        source_anchors: anchors,
        source_hint: hint,
        locate_confidence: locateConfidence(anchors)
      };
    } catch {
      const anchors = normalizeAnchors({
        testId: '',
        stableId: isStableId(el && el.id) ? el.id : '',
        sourceLoc: null,
        textFingerprint: cleanText(el && el.textContent, 80),
        role: attr(el, 'role'),
        ariaLabel: attr(el, 'aria-label'),
        componentName: ''
      });
      return {
        source_anchors: anchors,
        source_hint: {
          anchors,
          framework: 'unknown',
          component_chain: [],
          dom_path: domPath(el),
          confidence_reasons: confidenceReasons(anchors, [])
        },
        locate_confidence: locateConfidence(anchors)
      };
    }
  }

  function parseControlNumber(raw) {
    const normalized = String(raw || '')
      .trim()
      .replace(',', '.')
      .replace(/\s*(px|rem|em|%)$/i, '');
    if (!normalized) return null;
    if (!/^-?\d+(\.\d+)?$/.test(normalized)) return null;
    const number = Number(normalized);
    return Number.isFinite(number) ? number : null;
  }

  function clampControlNumber(control, value) {
    let next = value;
    if (typeof control.min === 'number') next = Math.max(control.min, next);
    if (typeof control.max === 'number') next = Math.min(control.max, next);
    return next;
  }

  function rgbToHex(value) {
    const match = String(value).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!match) {
      if (/^#[0-9a-f]{6}$/i.test(String(value))) return value;
      return '';
    }
    return '#' + [match[1], match[2], match[3]].map(part => Number(part).toString(16).padStart(2, '0')).join('');
  }

  root.__VFS_HELPERS__ = {
    attr,
    cleanText,
    isStableId,
    normalizeSourceLoc,
    readElementSourceLoc,
    readReactFiber,
    readReactFiberInfo,
    readDevSource,
    readComponentName,
    reactComponentChain,
    getSourceAnchors,
    getSourceHint,
    getSourcePayload,
    locateConfidence,
    parseControlNumber,
    clampControlNumber,
    rgbToHex
  };
})(typeof window !== 'undefined' ? window : globalThis);
