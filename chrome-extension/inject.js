(function () {
  'use strict';

  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  const DEFAULT_PORT = 3456;
  const LANG_KEY = '__vfs_lang';
  const THEME_KEY = '__vfs_theme';
  const PORT_KEY = '__vfs_port';
  const AGENT_KEY = '__vfs_agent';
  const TOKEN_KEY = '__vfs_token';
  const DEFAULT_AGENT = 'codex';
  const AGENT_PROFILES = {
    codex: { id: 'codex', label: 'Codex' },
    claude: { id: 'claude', label: 'Claude' }
  };
  const SESSION_VERSION = '4.0-beta';
  const PANEL_WIDTH = '388px';
  const PANEL_COLLAPSED_WIDTH = '330px';
  const TOOLBAR_WIDTH = '430px';
  const VFSHelpers = window.__VFS_HELPERS__ || {};
  const parseControlNumber = VFSHelpers.parseControlNumber || fallbackParseControlNumber;
  const clampControlNumber = VFSHelpers.clampControlNumber || fallbackClampControlNumber;
  const rgbToHex = VFSHelpers.rgbToHex || fallbackRgbToHex;
  const ANNOTATION_INTENTS = ['spacing', 'contrast', 'hierarchy', 'typography', 'copy-tone', 'interaction', 'other'];

  if (window.__vf__) {
    window.__vf__.toggle();
    return;
  }

  const state = {
    mode: 'style',
    tab: 'style',
    lang: readStoredLang(),
    theme: readStoredTheme(),
    agent: readStoredAgent() || DEFAULT_AGENT,
    receiverAgent: '',
    receiverToken: readStoredToken(),
    selectedEl: null,
    selectedSelector: '',
    selectedBefore: null,
    selectedSimilarSelector: '',
    selectedSourceAnchors: null,
    selectedSourceHint: null,
    selectedLocateConfidence: 'low',
    tokenCatalog: [],
    tokenLoaded: false,
    tokenError: false,
    previewStatus: null,
    verifyStatus: null,
    selectedBatchCount: 1,
    hoveredEl: null,
    activeEditEl: null,
    textEdits: [],
    styleEdits: [],
    annotations: [],
    annIdCounter: 0,
    saveAbortController: null,
    feedbackSaved: false,
    batch: false,
    advancedStyle: false,
    panelCollapsed: false,
    batchConfirmArmed: false,
    lastDeleted: null,
    lastSavedAt: '',
    saveError: false
  };

  const copy = {
    en: {
      title: 'Visual Feedback Studio',
      style: 'Style',
      text: 'Text',
      note: 'Note',
      feedback: 'Feedback',
      code: 'Source clues',
      select: 'Select an element',
      emptySelect: 'Click any page element to edit its visual style.',
      similar: 'similar',
      batch: 'Batch',
      batchOff: 'Batch off',
      batchOn: 'Batch on',
      batchDisabled: 'No similar elements',
      batchAffects: 'Affects',
      batchConfirm: 'Click again to apply batch editing',
      batchReady: 'Batch editing is available for this selection.',
      batchNone: 'No similar elements can be edited together.',
      batchWillAffect: 'Will affect',
      currentElement: 'Current element',
      common: 'Common',
      advanced: 'Advanced',
      showAdvanced: 'Show advanced',
      hideAdvanced: 'Hide advanced',
      modified: 'Changed',
      resetProperty: 'Reset property',
      unsaved: 'Unsaved',
      saveFailed: 'Save failed',
      savedAt: 'Saved at',
      saveFile: '.visual_feedback_studio.json',
      changesSummary: 'review items',
      copySelector: 'Copy selector',
      copySnapshot: 'Copy snapshot',
      tokenMatch: 'Token',
      noTokens: 'No design tokens detected yet',
      rescanTokens: 'Rescan tokens',
      tokensRescanned: 'Tokens rescanned',
      tokenRescanFailed: 'Could not rescan tokens',
      previewPlan: 'Preview plan',
      verifyResult: 'Verify',
      refreshPreview: 'Refresh preview',
      runVerify: 'Run verify',
      exportPreview: 'Export preview',
      previewEmpty: 'Save feedback first, then refresh the apply preview.',
      verifyEmpty: 'Verification has not run yet.',
      copied: 'Copied',
      dragToAdjust: 'Drag label to adjust. Arrow keys nudge, Shift speeds up, Option slows down.',
      sourceIntro: 'These clues help {agent} map browser feedback back to source code. You usually do not need to edit them.',
      sourceSummary: 'Source',
      selectorLabel: 'Selector',
      elementText: 'Element text',
      elementMeta: 'Element',
      feedbackBoard: 'Review board',
      nextTellAgent: 'Back in {agent}, say: feedback done',
      feedbackSavedMeta: 'Feedback saved to',
      deleted: 'Feedback deleted',
      undo: 'Undo',
      collapsePanel: 'Collapse panel',
      expandPanel: 'Expand panel',
      resetConfirm: 'Clear all feedback in this round?',
      padding: 'Padding',
      margin: 'Margin',
      top: 'Top',
      right: 'Right',
      bottom: 'Bottom',
      left: 'Left',
      save: 'Save',
      saved: 'Saved',
      exit: 'Exit',
      export: 'Export',
      import: 'Import',
      delete: 'Delete',
      locate: 'Locate',
      textEdits: 'Text',
      styleEdits: 'Style',
      notes: 'Notes',
      dimensions: 'Size',
      typography: 'Typography',
      spacing: 'Spacing',
      appearance: 'Appearance',
      border: 'Border',
      width: 'W',
      height: 'H',
      fontSize: 'Size',
      fontWeight: 'Weight',
      lineHeight: 'Line',
      letterSpacing: 'Track',
      color: 'Color',
      backgroundColor: 'Fill',
      textAlign: 'Align',
      paddingTop: 'PT',
      paddingRight: 'PR',
      paddingBottom: 'PB',
      paddingLeft: 'PL',
      marginTop: 'MT',
      marginRight: 'MR',
      marginBottom: 'MB',
      marginLeft: 'ML',
      borderRadius: 'Radius',
      borderWidth: 'Stroke',
      borderStyle: 'Line',
      borderColor: 'Stroke',
      boxShadow: 'Shadow',
      opacity: 'Opacity',
      inlineStyle: 'Inline Style',
      computedStyle: 'Computed Style',
      noInline: 'no inline overrides',
      noSelection: 'No element selected',
      noFeedback: 'No feedback yet',
      notePlaceholder: 'Write a note...',
      noteConfirm: 'Confirm',
      noteIntent: 'Intent',
      intentSpacing: 'Spacing',
      intentContrast: 'Contrast',
      intentHierarchy: 'Hierarchy',
      intentTypography: 'Type',
      intentCopyTone: 'Copy',
      intentInteraction: 'Action',
      intentOther: 'Other',
      savedToast: 'Feedback saved. Tell {agent}: "反馈好了"',
      timeoutToast: 'Save timed out. Check receiver on 127.0.0.1:',
      receiverMissing: 'Receiver is not running. Start the visual feedback receiver from the project root.',
      tokenMismatch: 'Receiver rejected the token. Open the extension popup and click Refresh config, or restart the receiver.',
      imported: 'Feedback imported',
      importFailed: 'Import failed',
      exported: 'Feedback exported',
      resetToast: 'New feedback round started',
      activeToast: 'Visual editing workspace is active',
      styleEmpty: 'Click an element. Common style controls appear here first.',
      textEmpty: 'Click live text, edit in place, then leave focus to record it.',
      noteEmpty: 'Click any element, choose an intent if useful, then leave a note for {agent}.',
      feedbackEmpty: 'Captured text, style, and note feedback will appear here before you save.',
      styleCommonIntro: 'Start with the controls people reach for most. Advanced controls stay folded until needed.',
      exitTip: 'Exit review',
      styleTip: 'Style editor',
      textTip: 'Text edit',
      noteTip: 'Add note',
      feedbackTip: 'Feedback list',
      importTip: 'Import JSON',
      exportTip: 'Export JSON',
      saveTip: 'Save feedback',
      savingTip: 'Saving',
      savedTip: 'Saved',
      themeTip: 'Theme',
      darkTheme: 'Dark theme',
      lightTheme: 'Light theme',
      languageTip: 'Language',
      resetTip: 'Reset round'
    },
    zh: {
      title: '视觉反馈工作室',
      style: '样式',
      text: '文案',
      note: '备注',
      feedback: '反馈',
      code: '源码线索',
      select: '选择元素',
      emptySelect: '点击页面元素，即可编辑视觉样式。',
      similar: '同类',
      batch: '批量',
      batchOff: '批量关闭',
      batchOn: '批量开启',
      batchDisabled: '没有可批量应用的同类元素',
      batchAffects: '将影响',
      batchConfirm: '再次点击确认批量编辑',
      batchReady: '当前选择可以批量编辑同类元素。',
      batchNone: '没有可一起批量应用的同类元素。',
      batchWillAffect: '将影响',
      currentElement: '当前元素',
      common: '常用',
      advanced: '高级',
      showAdvanced: '展开高级',
      hideAdvanced: '收起高级',
      modified: '已改',
      resetProperty: '恢复属性',
      unsaved: '未保存',
      saveFailed: '保存失败',
      savedAt: '保存于',
      saveFile: '.visual_feedback_studio.json',
      changesSummary: '条审稿项',
      copySelector: '复制 selector',
      copySnapshot: '复制样式快照',
      tokenMatch: 'Token',
      noTokens: '尚未检测到设计 token',
      rescanTokens: '重新扫描 token',
      tokensRescanned: 'token 已重新扫描',
      tokenRescanFailed: '无法重新扫描 token',
      previewPlan: '回贴预览',
      verifyResult: '验证',
      refreshPreview: '刷新预览',
      runVerify: '运行验证',
      exportPreview: '导出预览',
      previewEmpty: '先保存反馈，再刷新回贴预览。',
      verifyEmpty: '尚未运行验证。',
      copied: '已复制',
      dragToAdjust: '拖拽标签可调数值。方向键微调，Shift 加速，Option 精调。',
      sourceIntro: '这些线索用于帮助 {agent} 回到源码定位，你通常不需要手动处理。',
      sourceSummary: '源码线索',
      selectorLabel: 'Selector',
      elementText: '元素文本',
      elementMeta: '元素',
      feedbackBoard: '审稿任务板',
      nextTellAgent: '回到 {agent} 说：反馈好了',
      feedbackSavedMeta: '反馈已保存到',
      deleted: '反馈已删除',
      undo: '撤销',
      collapsePanel: '折叠面板',
      expandPanel: '展开面板',
      resetConfirm: '清空本轮所有反馈吗？',
      padding: '内边距',
      margin: '外边距',
      top: '上',
      right: '右',
      bottom: '下',
      left: '左',
      save: '保存',
      saved: '已保存',
      exit: '退出',
      export: '导出',
      import: '导入',
      delete: '删除',
      locate: '定位',
      textEdits: '文案',
      styleEdits: '样式',
      notes: '备注',
      dimensions: '尺寸',
      typography: '字体',
      spacing: '间距',
      appearance: '外观',
      border: '边框',
      width: '宽',
      height: '高',
      fontSize: '字号',
      fontWeight: '字重',
      lineHeight: '行高',
      letterSpacing: '字距',
      color: '文字',
      backgroundColor: '背景',
      textAlign: '对齐',
      paddingTop: '上内',
      paddingRight: '右内',
      paddingBottom: '下内',
      paddingLeft: '左内',
      marginTop: '上外',
      marginRight: '右外',
      marginBottom: '下外',
      marginLeft: '左外',
      borderRadius: '圆角',
      borderWidth: '线宽',
      borderStyle: '线型',
      borderColor: '线色',
      boxShadow: '阴影',
      opacity: '透明',
      inlineStyle: 'Inline Style',
      computedStyle: 'Computed Style',
      noInline: '无内联覆盖',
      noSelection: '尚未选择元素',
      noFeedback: '还没有反馈',
      notePlaceholder: '写下你的意见...',
      noteConfirm: '确认',
      noteIntent: '意图',
      intentSpacing: '间距',
      intentContrast: '对比',
      intentHierarchy: '层级',
      intentTypography: '字号',
      intentCopyTone: '文案',
      intentInteraction: '交互',
      intentOther: '其它',
      savedToast: '反馈已保存。告诉 {agent}：「反馈好了」',
      timeoutToast: '保存超时，请检查接收端 127.0.0.1:',
      receiverMissing: '接收端未运行，请先在项目根目录开启视觉反馈接收端。',
      tokenMismatch: '接收端拒绝了 token。请打开插件弹窗点击“刷新配置”，或重启 receiver。',
      imported: '反馈已导入',
      importFailed: '导入失败',
      exported: '反馈已导出',
      resetToast: '已开始新一轮反馈',
      activeToast: '视觉编辑工作台已开启',
      styleEmpty: '点击元素后，常用样式控件会优先出现在这里。',
      textEmpty: '点击页面文字直接修改，失焦后会记录为文案反馈。',
      noteEmpty: '点击任意元素，可选择意图并为 {agent} 留下备注。',
      feedbackEmpty: '捕获到的文案、样式和备注反馈会先汇总在这里，再保存。',
      styleCommonIntro: '先处理最常用的视觉属性；需要精细调整时再展开高级。',
      exitTip: '退出审稿',
      styleTip: '样式编辑',
      textTip: '文案修改',
      noteTip: '添加备注',
      feedbackTip: '反馈列表',
      importTip: '导入 JSON',
      exportTip: '导出 JSON',
      saveTip: '保存反馈',
      savingTip: '正在保存',
      savedTip: '已保存',
      themeTip: '主题',
      darkTheme: '深色主题',
      lightTheme: '浅色主题',
      languageTip: '语言',
      resetTip: '重置本轮'
    }
  };

  const styleControls = [
    { tier: 'common', section: 'typography', items: [
      { key: 'fontSize', prop: 'font-size', kind: 'px', min: 1 },
      { key: 'fontWeight', prop: 'font-weight', kind: 'number', min: 100, max: 900, step: 50 },
      { key: 'lineHeight', prop: 'line-height', kind: 'px', min: 0 },
      { key: 'color', prop: 'color', kind: 'color' }
    ] },
    { tier: 'common', section: 'appearance', items: [
      { key: 'backgroundColor', prop: 'background-color', kind: 'color' },
      { key: 'borderRadius', prop: 'border-radius', kind: 'px', min: 0 },
      { key: 'boxShadow', prop: 'box-shadow', kind: 'text' },
      { key: 'opacity', prop: 'opacity', kind: 'number', min: 0, max: 1, step: 0.05 }
    ] },
    { tier: 'common', section: 'spacing', layout: 'box', items: [
      { key: 'paddingTop', prop: 'padding-top', kind: 'px', min: 0, box: 'padding' },
      { key: 'paddingRight', prop: 'padding-right', kind: 'px', min: 0, box: 'padding' },
      { key: 'paddingBottom', prop: 'padding-bottom', kind: 'px', min: 0, box: 'padding' },
      { key: 'paddingLeft', prop: 'padding-left', kind: 'px', min: 0, box: 'padding' },
      { key: 'marginTop', prop: 'margin-top', kind: 'px', box: 'margin' },
      { key: 'marginRight', prop: 'margin-right', kind: 'px', box: 'margin' },
      { key: 'marginBottom', prop: 'margin-bottom', kind: 'px', box: 'margin' },
      { key: 'marginLeft', prop: 'margin-left', kind: 'px', box: 'margin' }
    ] },
    { tier: 'advanced', section: 'dimensions', items: [
      { key: 'width', prop: 'width', kind: 'px', min: 0 },
      { key: 'height', prop: 'height', kind: 'px', min: 0 }
    ] },
    { tier: 'advanced', section: 'typography', items: [
      { key: 'letterSpacing', prop: 'letter-spacing', kind: 'px', min: -20 },
      { key: 'textAlign', prop: 'text-align', kind: 'select', options: ['', 'left', 'center', 'right', 'justify'] }
    ] },
    { tier: 'advanced', section: 'border', items: [
      { key: 'borderWidth', prop: 'border-width', kind: 'px', min: 0 },
      { key: 'borderStyle', prop: 'border-style', kind: 'select', options: ['', 'solid', 'dashed', 'dotted', 'none'] },
      { key: 'borderColor', prop: 'border-color', kind: 'color' }
    ] }
  ];

  const flatStyleControls = styleControls.flatMap(section => section.items);

  const snapshotProps = [
    'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'color',
    'backgroundColor', 'padding', 'paddingTop', 'paddingRight', 'paddingBottom',
    'paddingLeft', 'margin', 'marginTop', 'marginRight', 'marginBottom',
    'marginLeft', 'borderRadius', 'borderWidth', 'borderStyle', 'borderColor',
    'boxShadow', 'display', 'width', 'height', 'opacity', 'textAlign'
  ];

  function t(key) {
    const value = (copy[state.lang] && copy[state.lang][key]) || copy.en[key] || key;
    return String(value).replace(/\{agent\}/g, agentLabel());
  }

  function intentLabel(intent) {
    const labels = {
      spacing: t('intentSpacing'),
      contrast: t('intentContrast'),
      hierarchy: t('intentHierarchy'),
      typography: t('intentTypography'),
      'copy-tone': t('intentCopyTone'),
      interaction: t('intentInteraction'),
      other: t('intentOther')
    };
    return labels[intent] || intent;
  }

  function icon(name) {
    return window.VFSHugeicons ? window.VFSHugeicons.renderIcon(name) : '<span class="vf-icon-missing" aria-hidden="true"></span>';
  }

  function readStoredLang() {
    try {
      const stored = window.localStorage && window.localStorage.getItem(LANG_KEY);
      return stored === 'en' ? 'en' : 'zh';
    } catch {
      return 'zh';
    }
  }

  function storeLang(nextLang) {
    try {
      if (window.localStorage) window.localStorage.setItem(LANG_KEY, nextLang);
    } catch {
      // Some protected pages block localStorage.
    }
  }

  function readStoredTheme() {
    try {
      const stored = window.localStorage && window.localStorage.getItem(THEME_KEY);
      return stored === 'light' ? 'light' : 'dark';
    } catch {
      return 'dark';
    }
  }

  function storeTheme(nextTheme) {
    try {
      if (window.localStorage) window.localStorage.setItem(THEME_KEY, nextTheme);
    } catch {
      // Some protected pages block localStorage.
    }
  }

  function readStoredAgent() {
    try {
      const stored = window.localStorage && window.localStorage.getItem(AGENT_KEY);
      return AGENT_PROFILES[stored] ? stored : '';
    } catch {
      return '';
    }
  }

  function storeAgent(nextAgent) {
    try {
      if (window.localStorage) window.localStorage.setItem(AGENT_KEY, nextAgent);
    } catch {
      // Some protected pages block localStorage.
    }
  }

  function clearStoredAgent() {
    try {
      if (window.localStorage) window.localStorage.removeItem(AGENT_KEY);
    } catch {
      // Some protected pages block localStorage.
    }
  }

  function readStoredToken() {
    try {
      const stored = window.localStorage && window.localStorage.getItem(TOKEN_KEY);
      return /^[A-Za-z0-9._:-]{12,256}$/.test(stored || '') ? stored : '';
    } catch {
      return '';
    }
  }

  function storeToken(nextToken) {
    try {
      if (!window.localStorage) return;
      if (nextToken) window.localStorage.setItem(TOKEN_KEY, nextToken);
      else window.localStorage.removeItem(TOKEN_KEY);
    } catch {
      // Some protected pages block localStorage.
    }
  }

  function resolveAgent() {
    const override = readStoredAgent();
    if (override) return override;
    if (AGENT_PROFILES[state.receiverAgent]) return state.receiverAgent;
    return DEFAULT_AGENT;
  }

  function agentLabel() {
    const profile = AGENT_PROFILES[state.agent] || AGENT_PROFILES[DEFAULT_AGENT];
    return profile.label;
  }

  const styleNode = document.createElement('style');
  styleNode.id = '__vf_style__';
  styleNode.textContent = `
    [data-vf-hover] {
      outline: 1.5px solid #7D9E20 !important;
      outline-offset: 3px !important;
      cursor: crosshair !important;
    }
    [data-vf-selected] {
      outline: 2px solid #8fad29 !important;
      outline-offset: 4px !important;
    }
    [data-vf-editing] {
      outline: 2px solid #B9D9EA !important;
      outline-offset: 4px !important;
      background: rgba(185, 217, 234, .12) !important;
    }
    [data-vf-batch-preview] {
      outline: 1.5px dashed rgba(125, 158, 32, .82) !important;
      outline-offset: 5px !important;
    }
    :host {
      --vf-bg: #090908;
      --vf-elevated: #100f0e;
      --vf-field: rgba(244, 244, 244, .055);
      --vf-field-strong: rgba(244, 244, 244, .095);
      --vf-line: rgba(244, 244, 244, .16);
      --vf-line-soft: rgba(244, 244, 244, .105);
      --vf-text: #F4F4F4;
      --vf-muted: rgba(244, 244, 244, .64);
      --vf-heading: rgba(244, 244, 244, .88);
      --vf-control: rgba(244, 244, 244, .74);
      --vf-control-border: rgba(244, 244, 244, .16);
      --vf-control-hover: rgba(125, 158, 32, .48);
      --vf-code: #B9D9EA;
      --vf-accent: #7D9E20;
      --vf-accent-hover: #8fad29;
      --vf-accent-soft: rgba(125, 158, 32, .16);
      --vf-accent-strong: #DDE9A0;
      --vf-regent: #B9D9EA;
      --vf-regent-soft: rgba(185, 217, 234, .12);
      --vf-logo-bg: rgba(125, 158, 32, .12);
      --vf-logo-color: #DDE9A0;
      --vf-logo-line: rgba(125, 158, 32, .54);
      --vf-logo-shine: rgba(244, 244, 244, .11);
      --vf-logo-shadow: 0 8px 18px rgba(0,0,0,.24);
      --vf-success: oklch(74% .12 158);
      --vf-warning: oklch(78% .13 78);
      --vf-error: oklch(70% .13 25);
      --vf-tooltip-bg: #100f0e;
      --vf-tooltip-text: #F4F4F4;
      --vf-shadow: 0 16px 34px rgba(0,0,0,.36), inset 0 1px 0 rgba(255,255,255,.035);
      --vf-float-shadow: 0 14px 30px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.035);
      color-scheme: dark;
    }
    :host([data-vfs-theme="light"]) {
      --vf-bg: #F4F4F4;
      --vf-elevated: #FAFAF4;
      --vf-field: rgba(28, 28, 28, .055);
      --vf-field-strong: rgba(28, 28, 28, .092);
      --vf-line: rgba(28, 28, 28, .18);
      --vf-line-soft: rgba(28, 28, 28, .115);
      --vf-text: #1C1C1C;
      --vf-muted: rgba(28, 28, 28, .62);
      --vf-heading: rgba(28, 28, 28, .84);
      --vf-control: rgba(28, 28, 28, .7);
      --vf-control-border: rgba(28, 28, 28, .16);
      --vf-control-hover: rgba(111, 140, 25, .42);
      --vf-code: #5B8191;
      --vf-accent: #6F8C19;
      --vf-accent-hover: #7D9E20;
      --vf-accent-soft: rgba(111, 140, 25, .13);
      --vf-accent-strong: #4E6612;
      --vf-regent: #5B8191;
      --vf-regent-soft: rgba(91, 129, 145, .10);
      --vf-logo-bg: rgba(111, 140, 25, .105);
      --vf-logo-color: #4E6612;
      --vf-logo-line: rgba(111, 140, 25, .42);
      --vf-logo-shine: rgba(255,255,250,.72);
      --vf-logo-shadow: 0 8px 18px rgba(72,91,20,.12);
      --vf-success: oklch(56% .13 158);
      --vf-warning: oklch(58% .13 78);
      --vf-error: oklch(54% .14 25);
      --vf-tooltip-bg: #1C1C1C;
      --vf-tooltip-text: #FAFAF4;
      --vf-shadow: 0 14px 32px rgba(28,28,28,.12), inset 0 1px 0 rgba(255,255,255,.7);
      --vf-float-shadow: 0 14px 30px rgba(28,28,28,.12), inset 0 1px 0 rgba(255,255,255,.7);
      color-scheme: light;
    }
    #__vf_panel__, #__vf_panel__ *, #__vf_toolbar__, #__vf_toolbar__ *, .vf-beacon, .vf-beacon-tip, .vf-beacon-label, .__vf_toast__ {
      box-sizing: border-box;
    }
    .vfs-hugeicon,
    .vf-icon-missing {
      width: 17px;
      height: 17px;
      display: block;
      flex: none;
    }
    .vf-icon-missing {
      border: 1.5px solid currentColor;
      border-radius: 0;
      opacity: .54;
    }
    #__vf_panel__ {
      all: initial;
      display: block !important;
      position: fixed !important;
      top: 12px !important;
      right: 12px !important;
      left: auto !important;
      z-index: 2147483647 !important;
      width: 388px !important;
      min-width: 388px !important;
      max-width: 388px !important;
      max-height: calc(100vh - 24px);
      color: var(--vf-text);
      background-color: var(--vf-bg);
      background-image: repeating-linear-gradient(45deg, var(--vf-field) 0, transparent 1px, transparent 0, transparent 50%);
      background-size: 10px 10px;
      border: 1px solid var(--vf-line);
      border-radius: 0;
      box-shadow: var(--vf-shadow);
      font: 13px/1.42 Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      overflow: hidden;
      user-select: none;
      -webkit-font-smoothing: antialiased;
      pointer-events: auto;
    }
    #__vf_panel__[data-collapsed="true"] {
      width: 330px !important;
      min-width: 330px !important;
      max-width: 330px !important;
    }
    #__vf_panel__ button,
    #__vf_panel__ input,
    #__vf_panel__ select {
      font: inherit;
    }
    #__vf_panel__ .vf-grip {
      width: 74px;
      height: 3px;
      border-radius: 0;
      margin: 7px auto 3px;
      background: var(--vf-line);
      opacity: .62;
    }
    #__vf_panel__ .vf-top {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 8px 12px 11px;
      align-items: center;
      border-bottom: 1px solid var(--vf-line-soft);
      background: var(--vf-elevated);
    }
    #__vf_panel__ .vf-brand-strip {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    #__vf_panel__ .vf-brand-mark {
      position: relative;
      width: 28px;
      height: 28px;
      border: 1px solid var(--vf-logo-line);
      border-radius: 0;
      background: var(--vf-logo-bg);
      color: var(--vf-logo-color);
      box-shadow: var(--vf-logo-shadow);
      display: grid;
      place-items: center;
      flex: none;
      overflow: hidden;
    }
    #__vf_panel__ .vf-brand-mark::before {
      content: "";
      position: absolute;
      inset: 1px;
      border-radius: 0;
      background: linear-gradient(145deg, var(--vf-logo-shine), transparent 48%);
      pointer-events: none;
    }
    #__vf_panel__ .vf-brand-mark .vfs-hugeicon {
      position: relative;
      width: 22px;
      height: 22px;
    }
    #__vf_panel__ .vf-tabs {
      display: flex;
      gap: 3px;
      align-items: center;
      min-width: 0;
      padding: 3px;
      border: 1px solid var(--vf-line-soft);
      border-radius: 0;
      background: var(--vf-field);
    }
    #__vf_panel__ .vf-tab {
      border: 0;
      background: transparent;
      color: var(--vf-muted);
      padding: 6px 8px;
      border-radius: 0;
      cursor: pointer;
      font-size: 13px;
      font-weight: 720;
      letter-spacing: 0;
      transition: color .16s ease, background .16s ease, box-shadow .16s ease;
    }
    #__vf_panel__ .vf-tab:hover {
      color: var(--vf-text);
      background: var(--vf-field-strong);
    }
    #__vf_panel__ .vf-tab.on {
      color: var(--vf-text);
      background: var(--vf-accent-soft);
      box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--vf-accent) 46%, transparent);
    }
    #__vf_panel__ .vf-actions {
      display: flex;
      align-items: center;
      gap: 7px;
    }
    #__vf_panel__ .vf-icon-btn,
    #__vf_toolbar__ .vf-tool {
      border: 1px solid var(--vf-control-border);
      background: var(--vf-field);
      color: var(--vf-control);
      cursor: pointer;
      display: grid;
      place-items: center;
      transition: color .16s ease, background .16s ease, border-color .16s ease, transform .16s ease;
    }
    #__vf_panel__ .vf-icon-btn {
      width: 32px;
      height: 32px;
      border-radius: 0;
      font-size: 16px;
    }
    #__vf_panel__ .vf-icon-btn:hover,
    #__vf_toolbar__ .vf-tool:hover {
      color: var(--vf-text);
      border-color: var(--vf-control-hover);
      background: var(--vf-field-strong);
    }
    #__vf_toolbar__ .vf-tool:disabled {
      cursor: not-allowed;
      opacity: .48;
    }
    #__vf_toolbar__ .vf-tool:disabled:hover {
      color: var(--vf-control);
      border-color: var(--vf-control-border);
      background: var(--vf-field);
    }
    #__vf_panel__ .vf-switch {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 32px;
      padding: 3px 5px 3px 10px;
      border-radius: 0;
      background: var(--vf-field);
      color: var(--vf-control);
      border: 1px solid var(--vf-line-soft);
      font-size: 12px;
      font-weight: 650;
      cursor: pointer;
    }
    #__vf_panel__ .vf-switch:disabled {
      cursor: not-allowed;
      opacity: .5;
    }
    #__vf_panel__ .vf-switch span:last-child {
      width: 24px;
      height: 24px;
      border-radius: 0;
      background: var(--vf-control);
      box-shadow: inset 0 0 0 1px rgba(0,0,0,.16);
      transition: transform .16s ease, background .16s ease;
    }
    #__vf_panel__ .vf-switch.on span:last-child {
      transform: translateX(6px);
      background: var(--vf-accent);
    }
    #__vf_panel__ .vf-content {
      padding: 14px 14px 74px;
      overflow: auto;
      max-height: calc(100vh - 148px);
      background: var(--vf-bg);
    }
    #__vf_panel__ .vf-mini {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 12px;
      background: var(--vf-elevated);
    }
    #__vf_panel__ .vf-mini-title {
      min-width: 0;
      color: var(--vf-text);
      font-size: 13px;
      font-weight: 820;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-mini-meta {
      margin-top: 4px;
      color: var(--vf-muted);
      font-size: 11px;
      font-weight: 680;
    }
    #__vf_panel__ .vf-selection {
      display: grid;
      gap: 7px;
      margin-bottom: 14px;
    }
    #__vf_panel__ .vf-selector {
      color: var(--vf-muted);
      font-size: 12px;
      font-weight: 720;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-element-title {
      color: var(--vf-text);
      font-size: 22px;
      font-weight: 800;
      line-height: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-muted {
      color: var(--vf-muted);
      font-size: 12px;
    }
    #__vf_panel__ .vf-context {
      display: grid;
      gap: 10px;
      margin-bottom: 14px;
      padding: 12px;
      border: 1px solid var(--vf-line-soft);
      border-radius: 0;
      background: var(--vf-elevated);
    }
    #__vf_panel__ .vf-context-head {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: start;
    }
    #__vf_panel__ .vf-context-title {
      color: var(--vf-text);
      font-size: 17px;
      font-weight: 820;
      line-height: 1.15;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-context-text {
      margin-top: 5px;
      color: var(--vf-muted);
      font-size: 12px;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    #__vf_panel__ .vf-chip-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      min-width: 0;
    }
    #__vf_panel__ .vf-chip {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      max-width: 100%;
      padding: 0 8px;
      border-radius: 0;
      border: 1px solid var(--vf-line-soft);
      background: var(--vf-field);
      color: var(--vf-muted);
      font-size: 11px;
      font-weight: 740;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-batch-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      padding-top: 2px;
    }
    #__vf_panel__ .vf-batch-copy {
      color: var(--vf-muted);
      font-size: 11.5px;
      line-height: 1.35;
    }
    #__vf_panel__ .vf-batch-copy strong {
      color: var(--vf-heading);
      font-weight: 820;
    }
    #__vf_panel__ .vf-section {
      margin-top: 18px;
    }
    #__vf_panel__ .vf-section:first-child {
      margin-top: 0;
    }
    #__vf_panel__ .vf-section h4 {
      margin: 0 0 10px;
      color: var(--vf-heading);
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0;
    }
    #__vf_panel__ .vf-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    #__vf_panel__ .vf-field {
      min-height: 50px;
      border-radius: 0;
      background: var(--vf-field);
      border: 1px solid var(--vf-line-soft);
      padding: 8px 10px;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 9px;
      align-items: center;
      position: relative;
    }
    #__vf_panel__ .vf-field.changed {
      border-color: color-mix(in srgb, var(--vf-accent) 56%, transparent);
      background: linear-gradient(180deg, var(--vf-field-strong), var(--vf-field));
    }
    #__vf_panel__ .vf-field.scrubbing {
      border-color: var(--vf-accent);
      box-shadow: 0 0 0 2px var(--vf-accent-soft);
    }
    #__vf_panel__ .vf-field.wide {
      grid-column: 1 / -1;
    }
    #__vf_panel__ .vf-field.compact {
      min-height: 42px;
    }
    #__vf_panel__ .vf-field label {
      color: var(--vf-muted);
      font-size: 12px;
      font-weight: 780;
      min-width: 34px;
    }
    #__vf_panel__ .vf-field[data-scrubbable="true"] label {
      cursor: ew-resize;
      user-select: none;
    }
    #__vf_panel__ .vf-field[data-scrubbable="true"] label:hover {
      color: var(--vf-accent-strong);
    }
    #__vf_panel__ .vf-field input,
    #__vf_panel__ .vf-field select {
      width: 100%;
      min-width: 0;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--vf-text);
      font-size: 14px;
      font-weight: 620;
      padding: 4px 0;
      font-variant-numeric: tabular-nums;
      caret-color: var(--vf-accent);
    }
    #__vf_panel__ .vf-field:focus-within {
      border-color: var(--vf-accent);
      box-shadow: 0 0 0 2px var(--vf-accent-soft);
    }
    #__vf_panel__ .vf-field input[type="number"]::-webkit-outer-spin-button,
    #__vf_panel__ .vf-field input[type="number"]::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    #__vf_panel__ .vf-field input[type="number"] {
      appearance: textfield;
    }
    #__vf_panel__ .vf-field input[type="color"] {
      height: 30px;
      padding: 0;
      border-radius: 0;
      overflow: hidden;
      cursor: pointer;
    }
    #__vf_panel__ .vf-color-wrap {
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 8px;
      align-items: center;
      min-width: 0;
    }
    #__vf_panel__ .vf-color-wrap input[type="color"] {
      width: 38px;
    }
    #__vf_panel__ .vf-color-text {
      color: var(--vf-text);
      font-size: 12px;
      font-weight: 720;
      font-variant-numeric: tabular-nums;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-modified {
      position: absolute;
      right: 8px;
      top: 6px;
      min-height: 17px;
      padding: 0 5px;
      border-radius: 0;
      background: var(--vf-accent-soft);
      color: var(--vf-accent-strong);
      font-size: 9.5px;
      font-weight: 840;
      line-height: 17px;
      pointer-events: none;
    }
    #__vf_panel__ .vf-property-reset {
      position: absolute;
      right: 7px;
      bottom: 6px;
      min-width: 21px;
      height: 21px;
      padding: 0;
      border-radius: 0;
      border: 1px solid var(--vf-line-soft);
      background: var(--vf-bg);
      color: var(--vf-muted);
      cursor: pointer;
      font-size: 11px;
      font-weight: 820;
    }
    #__vf_panel__ .vf-unit {
      position: absolute;
      right: 10px;
      bottom: 8px;
      color: var(--vf-muted);
      font-size: 10px;
      font-weight: 760;
      pointer-events: none;
    }
    #__vf_panel__ .vf-token-chip {
      grid-column: 1 / -1;
      justify-self: start;
      max-width: 100%;
      min-height: 20px;
      margin-top: -4px;
      padding: 0 7px;
      border-radius: 0;
      border: 1px solid color-mix(in srgb, var(--vf-accent) 38%, transparent);
      background: var(--vf-accent-soft);
      color: var(--vf-accent-strong);
      font-size: 10px;
      font-weight: 820;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-box-model {
      display: grid;
      gap: 10px;
    }
    #__vf_panel__ .vf-box-row {
      display: grid;
      grid-template-columns: 58px repeat(4, 1fr);
      gap: 8px;
      align-items: center;
    }
    #__vf_panel__ .vf-box-label {
      color: var(--vf-muted);
      font-size: 12px;
      font-weight: 820;
    }
    #__vf_panel__ .vf-box-row .vf-field {
      min-height: 42px;
      grid-template-columns: 1fr;
      padding: 7px 8px;
    }
    #__vf_panel__ .vf-box-row .vf-field label {
      min-width: 0;
      font-size: 10px;
    }
    #__vf_panel__ .vf-box-row .vf-field[data-scrubbable="true"] label {
      cursor: ew-resize;
    }
    #__vf_panel__ .vf-advanced-toggle {
      width: 100%;
      min-height: 36px;
      margin-top: 16px;
      border: 1px solid var(--vf-line-soft);
      border-radius: 0;
      background: var(--vf-field);
      color: var(--vf-heading);
      cursor: pointer;
      font-size: 12px;
      font-weight: 780;
    }
    #__vf_panel__ .vf-advanced-toggle:hover {
      border-color: var(--vf-control-hover);
      background: var(--vf-field-strong);
      color: var(--vf-text);
    }
    #__vf_panel__ .vf-code-card {
      border: 1px solid var(--vf-line-soft);
      background: linear-gradient(180deg, var(--vf-elevated), var(--vf-field));
      border-radius: 0;
      padding: 14px;
      margin-top: 14px;
      overflow: hidden;
    }
    #__vf_panel__ .vf-code-card h4 {
      margin: 0 0 12px;
      color: var(--vf-regent);
      font-size: 13px;
      font-weight: 780;
    }
    #__vf_panel__ .vf-code-card .vf-code-actions {
      display: flex;
      gap: 8px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }
    #__vf_panel__ pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--vf-code);
      font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    #__vf_panel__ .vf-feedback-list {
      display: grid;
      gap: 10px;
    }
    #__vf_panel__ .vf-review-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 12px;
    }
    #__vf_panel__ .vf-review-card {
      display: grid;
      gap: 8px;
      min-width: 0;
      padding: 10px;
      border: 1px solid var(--vf-line-soft);
      border-radius: 0;
      background: var(--vf-field);
    }
    #__vf_panel__ .vf-review-card h4 {
      margin: 0;
      color: var(--vf-heading);
      font-size: 12px;
      font-weight: 820;
    }
    #__vf_panel__ .vf-review-card .vf-chip-row {
      gap: 5px;
    }
    #__vf_panel__ .vf-feedback-summary {
      display: grid;
      gap: 8px;
      margin-bottom: 12px;
      padding: 12px;
      border: 1px solid var(--vf-line-soft);
      border-radius: 0;
      background: var(--vf-elevated);
    }
    #__vf_panel__ .vf-feedback-summary strong {
      color: var(--vf-text);
      font-size: 14px;
      font-weight: 820;
    }
    #__vf_panel__ .vf-feedback-meta {
      color: var(--vf-muted);
      font-size: 11.5px;
      line-height: 1.4;
    }
    #__vf_panel__ .vf-feedback-item {
      border: 1px solid var(--vf-line-soft);
      background: var(--vf-field);
      border-radius: 0;
      padding: 12px;
      display: grid;
      gap: 9px;
    }
    #__vf_panel__ .vf-feedback-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
    }
    #__vf_panel__ .vf-pill {
      display: inline-flex;
      align-items: center;
      min-height: 23px;
      padding: 0 8px;
      border-radius: 0;
      background: var(--vf-accent-soft);
      color: var(--vf-accent-strong);
      font-size: 11px;
      font-weight: 800;
    }
    #__vf_panel__ .vf-pill.neutral {
      background: var(--vf-field-strong);
      color: var(--vf-muted);
      border: 1px solid var(--vf-line-soft);
    }
    #__vf_panel__ .vf-feedback-copy {
      color: var(--vf-heading);
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    #__vf_panel__ .vf-feedback-source {
      color: var(--vf-muted);
      font-size: 11.5px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    #__vf_panel__ .vf-feedback-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    #__vf_panel__ .vf-small-btn {
      border: 1px solid var(--vf-line);
      background: transparent;
      color: var(--vf-control);
      min-height: 27px;
      border-radius: 0;
      padding: 0 9px;
      cursor: pointer;
      font-size: 11px;
      font-weight: 700;
    }
    #__vf_panel__ .vf-small-btn:hover {
      color: var(--vf-text);
      border-color: var(--vf-control-hover);
      background: var(--vf-field-strong);
    }
    #__vf_panel__ .vf-small-btn:disabled {
      cursor: not-allowed;
      opacity: .46;
    }
    #__vf_panel__ .vf-undo-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      margin-bottom: 10px;
      padding: 10px;
      border-radius: 0;
      border: 1px solid var(--vf-line-soft);
      background: var(--vf-field);
    }
    #__vf_panel__ .vf-statusbar {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
      border-top: 1px solid var(--vf-line-soft);
      background: var(--vf-elevated);
    }
    #__vf_panel__ .vf-status-count {
      min-width: 0;
      color: var(--vf-heading);
      font-size: 11.5px;
      font-weight: 760;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__vf_panel__ .vf-status-state {
      color: var(--vf-muted);
      font-size: 11px;
      font-weight: 780;
    }
    #__vf_panel__ .vf-status-state.saved {
      color: var(--vf-success);
    }
    #__vf_panel__ .vf-status-state.unsaved {
      color: var(--vf-warning);
    }
    #__vf_panel__ .vf-status-state.error {
      color: var(--vf-error);
    }
    #__vf_toolbar__ {
      all: initial;
      position: fixed !important;
      left: 50% !important;
      bottom: 18px !important;
      transform: translateX(-50%);
      z-index: 2147483647 !important;
      width: 430px !important;
      min-width: 430px !important;
      max-width: 430px !important;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px;
      border-radius: 0;
      background: var(--vf-bg);
      border: 1px solid var(--vf-line);
      box-shadow: var(--vf-float-shadow);
      font: 13px/1 Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      user-select: none;
      pointer-events: auto;
      overflow: visible;
    }
    #__vf_toolbar__ .vf-tool {
      position: relative;
      width: 38px;
      height: 38px;
      border-radius: 0;
      font-size: 16px;
      font-weight: 780;
    }
    #__vf_toolbar__ .vf-tool::after {
      content: attr(data-tip);
      position: absolute;
      left: 50%;
      bottom: calc(100% + 10px);
      max-width: 180px;
      white-space: nowrap;
      padding: 7px 9px;
      border-radius: 0;
      background: var(--vf-tooltip-bg);
      color: var(--vf-tooltip-text);
      border: 1px solid var(--vf-line);
      box-shadow: var(--vf-float-shadow);
      font: 11px/1.1 Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-weight: 720;
      opacity: 0;
      transform: translate(-50%, 4px);
      pointer-events: none;
      transition: opacity .18s ease, transform .18s ease;
      z-index: 2147483647;
    }
    #__vf_toolbar__ .vf-tool:hover::after,
    #__vf_toolbar__ .vf-tool:focus-visible::after {
      opacity: 1;
      transform: translate(-50%, 0);
    }
    #__vf_toolbar__ .vf-tool:focus-visible,
    #__vf_panel__ .vf-icon-btn:focus-visible,
    #__vf_panel__ .vf-tab:focus-visible,
    #__vf_panel__ .vf-small-btn:focus-visible,
    #__vf_panel__ .vf-switch:focus-visible {
      outline: 2px solid var(--vf-accent);
      outline-offset: 2px;
    }
    #__vf_toolbar__ .vf-tool.on {
      background: var(--vf-accent-soft);
      border-color: color-mix(in srgb, var(--vf-accent) 60%, transparent);
      color: var(--vf-accent-strong);
    }
    #__vf_toolbar__ .vf-divider {
      width: 1px;
      height: 28px;
      background: var(--vf-line);
      margin: 0 2px;
    }
    #__vf_toolbar__ .vf-count {
      min-width: 42px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 0;
      border: 1px solid var(--vf-line-soft);
      background: var(--vf-field);
      color: var(--vf-text);
      font-weight: 800;
      font-size: 14px;
    }
    .vf-beacon,
    .vf-beacon-tip {
      pointer-events: auto;
    }
    .vf-beacon {
      position: fixed !important;
      z-index: 2147483646 !important;
      width: 14px;
      height: 14px;
      border-radius: 0;
      background: var(--vf-accent);
      border: 2px solid var(--vf-bg);
      box-shadow: 0 0 0 1px color-mix(in srgb, var(--vf-accent) 38%, transparent), 0 8px 18px rgba(0,0,0,.34);
      transform: translate(-50%, -50%);
      cursor: pointer;
    }
    .vf-beacon:hover {
      transform: translate(-50%, -50%) scale(1.35);
    }
    .vf-beacon-tip {
      position: fixed !important;
      z-index: 2147483647 !important;
      min-width: 270px;
      max-width: 340px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 9px;
      padding: 10px;
      border-radius: 0;
      border: 1px solid var(--vf-line);
      background: var(--vf-elevated);
      box-shadow: var(--vf-float-shadow);
      font: 13px/1.42 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .vf-beacon-tip input {
      min-width: 0;
      border: 0;
      outline: 0;
      border-bottom: 1px solid var(--vf-line);
      background: transparent;
      color: var(--vf-text);
      padding: 5px 0;
    }
    .vf-beacon-tip .vf-note-ok {
      width: 30px;
      height: 30px;
      border-radius: 0;
      border: 1px solid var(--vf-line);
      background: var(--vf-accent-soft);
      color: var(--vf-text);
      cursor: pointer;
    }
    .vf-beacon-tip .vf-note-ok:hover {
      border-color: var(--vf-control-hover);
      background: var(--vf-field-strong);
    }
    .vf-note-intents {
      grid-column: 1 / -1;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      align-items: center;
      color: var(--vf-muted);
      font-size: 10.5px;
      font-weight: 780;
    }
    .vf-note-intent {
      min-height: 22px;
      padding: 0 7px;
      border-radius: 0;
      border: 1px solid var(--vf-line-soft);
      background: var(--vf-field);
      color: var(--vf-muted);
      cursor: pointer;
      font: inherit;
      font-size: 10.5px;
      font-weight: 780;
    }
    .vf-note-intent:hover {
      border-color: var(--vf-control-hover);
      background: var(--vf-field-strong);
      color: var(--vf-text);
    }
    .vf-note-intent.active {
      border-color: var(--vf-accent);
      background: var(--vf-accent-soft);
      color: var(--vf-accent-strong);
    }
    .vf-beacon-label {
      position: fixed !important;
      z-index: 2147483647 !important;
      display: none;
      max-width: 260px;
      padding: 9px 11px;
      color: var(--vf-text);
      background: var(--vf-elevated);
      border: 1px solid var(--vf-line);
      border-radius: 0;
      box-shadow: var(--vf-float-shadow);
      font: 12px/1.48 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      white-space: pre-wrap;
      pointer-events: none;
    }
    .__vf_toast__ {
      position: fixed !important;
      right: 26px !important;
      bottom: 26px !important;
      z-index: 2147483647 !important;
      width: 420px !important;
      min-width: 420px !important;
      max-width: 420px !important;
      padding: 11px 14px;
      color: var(--vf-text);
      background: var(--vf-elevated);
      border: 1px solid var(--vf-line);
      border-radius: 0;
      box-shadow: var(--vf-float-shadow);
      font: 12.5px/1.42 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: opacity .3s ease, transform .3s ease;
      pointer-events: none;
    }
    @media (max-width: 760px) {
      #__vf_panel__ {
        left: auto !important;
        right: 10px !important;
        top: 10px !important;
        width: 388px !important;
        min-width: 388px !important;
        max-width: 388px !important;
      }
      #__vf_panel__[data-collapsed="true"] {
        width: 330px !important;
        min-width: 330px !important;
        max-width: 330px !important;
      }
      #__vf_toolbar__ {
        bottom: 12px !important;
        width: 430px !important;
        min-width: 430px !important;
        max-width: 430px !important;
        overflow-x: visible;
      }
    }
  `;
  document.head.appendChild(styleNode);

  const shadowHost = document.createElement('div');
  shadowHost.id = '__vf_root__';
  shadowHost.dataset.vfsTheme = state.theme;
  shadowHost.style.cssText = [
    'all: initial !important',
    'position: fixed !important',
    'inset: 0 !important',
    'z-index: 2147483647 !important',
    'pointer-events: none !important'
  ].join(';');
  const shadowRoot = shadowHost.attachShadow({ mode: 'closed' });
  const shadowStyleNode = document.createElement('style');
  shadowStyleNode.textContent = styleNode.textContent;
  shadowRoot.appendChild(shadowStyleNode);
  document.body.appendChild(shadowHost);

  const panel = document.createElement('aside');
  panel.id = '__vf_panel__';
  shadowRoot.appendChild(panel);

  const toolbar = document.createElement('div');
  toolbar.id = '__vf_toolbar__';
  shadowRoot.appendChild(toolbar);

  const importInput = document.createElement('input');
  importInput.type = 'file';
  importInput.accept = 'application/json,.json';
  importInput.style.display = 'none';
  shadowRoot.appendChild(importInput);

  const handlers = {
    mouseover: event => {
      const target = event.target;
      if (isIgnoredTarget(target)) return;
      if (state.mode === 'text' && !isEditableTarget(target)) return;
      setHover(target);
    },
    mouseout: event => {
      if (event.target === state.hoveredEl) clearHover();
    },
    click: event => {
      const target = event.target;
      if (isIgnoredTarget(target)) return;
      if (state.mode === 'text' && !isEditableTarget(target)) return;
      event.preventDefault();
      event.stopPropagation();
      if (state.mode === 'text') startEdit(target);
      else if (state.mode === 'note') addSticky(target, event);
      else selectElement(target);
    },
    keydown: event => {
      if (event.key === 'Escape' && state.activeEditEl) commitEdit();
      else if (event.key === 'Escape') clearSelection();
    },
    blur: event => {
      if (event.target === state.activeEditEl) setTimeout(commitEdit, 50);
    },
    scroll: () => updateOverlayPositions(),
    resize: () => {
      updateOverlayPositions();
      enforcePanelGeometry();
      enforceToolbarGeometry();
    }
  };

  document.addEventListener('mouseover', handlers.mouseover, true);
  document.addEventListener('mouseout', handlers.mouseout, true);
  document.addEventListener('click', handlers.click, true);
  document.addEventListener('keydown', handlers.keydown);
  document.addEventListener('blur', handlers.blur, true);
  window.addEventListener('scroll', handlers.scroll, true);
  window.addEventListener('resize', handlers.resize);
  importInput.addEventListener('change', handleImportFile);

  function enforcePanelGeometry() {
    const width = state.panelCollapsed ? PANEL_COLLAPSED_WIDTH : PANEL_WIDTH;
    panel.style.setProperty('display', 'block', 'important');
    panel.style.setProperty('position', 'fixed', 'important');
    panel.style.setProperty('top', window.innerWidth <= 760 ? '10px' : '12px', 'important');
    panel.style.setProperty('right', window.innerWidth <= 760 ? '10px' : '12px', 'important');
    panel.style.setProperty('left', 'auto', 'important');
    panel.style.setProperty('width', width, 'important');
    panel.style.setProperty('min-width', width, 'important');
    panel.style.setProperty('max-width', width, 'important');
    panel.style.setProperty('box-sizing', 'border-box', 'important');
    panel.style.setProperty('overflow', 'hidden', 'important');
    panel.style.setProperty('pointer-events', 'auto', 'important');
  }

  function enforceToolbarGeometry() {
    toolbar.style.setProperty('display', 'flex', 'important');
    toolbar.style.setProperty('position', 'fixed', 'important');
    toolbar.style.setProperty('left', '50%', 'important');
    toolbar.style.setProperty('bottom', window.innerWidth <= 760 ? '12px' : '18px', 'important');
    toolbar.style.setProperty('width', TOOLBAR_WIDTH, 'important');
    toolbar.style.setProperty('min-width', TOOLBAR_WIDTH, 'important');
    toolbar.style.setProperty('max-width', TOOLBAR_WIDTH, 'important');
    toolbar.style.setProperty('box-sizing', 'border-box', 'important');
    toolbar.style.setProperty('overflow', 'visible', 'important');
    toolbar.style.setProperty('pointer-events', 'auto', 'important');
  }

  function isIgnoredTarget(el) {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) return true;
    if (
      el === shadowHost ||
      el.closest('#__vf_root__') ||
      el.closest('#__vf_panel__') ||
      el.closest('#__vf_toolbar__') ||
      el.closest('.vf-beacon') ||
      el.closest('.vf-beacon-tip')
    ) return true;
    const tag = el.tagName.toLowerCase();
    return ['html', 'head', 'body', 'script', 'style', 'noscript', 'meta', 'link', 'title', 'svg', 'path'].includes(tag);
  }

  function isEditableTarget(el) {
    if (isIgnoredTarget(el)) return false;
    const tag = el.tagName.toLowerCase();
    if (['input', 'textarea', 'select', 'option'].includes(tag)) return false;
    return (el.textContent || '').trim().length > 0;
  }

  function receiverPort() {
    let raw = null;
    try {
      raw = window.localStorage && window.localStorage.getItem(PORT_KEY);
    } catch {
      raw = null;
    }
    const port = Number(raw || DEFAULT_PORT);
    return Number.isInteger(port) && port > 0 && port <= 65535 ? port : DEFAULT_PORT;
  }

  function currentSourceAnchors(el) {
    const anchors = VFSHelpers.getSourceAnchors ? VFSHelpers.getSourceAnchors(el) : {};
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

  function currentSourceHint(el, anchors = currentSourceAnchors(el)) {
    const hint = VFSHelpers.getSourceHint ? VFSHelpers.getSourceHint(el, anchors) : {};
    return {
      anchors,
      framework: hint.framework || 'unknown',
      component_chain: Array.isArray(hint.component_chain) ? hint.component_chain : [],
      dom_path: Array.isArray(hint.dom_path) ? hint.dom_path : [],
      confidence_reasons: Array.isArray(hint.confidence_reasons) ? hint.confidence_reasons : []
    };
  }

  function confidenceForAnchors(anchors) {
    return VFSHelpers.locateConfidence ? VFSHelpers.locateConfidence(anchors) : 'low';
  }

  function sourcePayload(el) {
    if (VFSHelpers.getSourcePayload) {
      const payload = VFSHelpers.getSourcePayload(el) || {};
      const anchors = payload.source_anchors || {};
      const hint = payload.source_hint || {};
      const normalizedAnchors = {
        testId: anchors.testId || '',
        stableId: anchors.stableId || '',
        sourceLoc: anchors.sourceLoc || null,
        textFingerprint: anchors.textFingerprint || '',
        role: anchors.role || '',
        ariaLabel: anchors.ariaLabel || '',
        componentName: anchors.componentName || ''
      };
      return {
        source_anchors: normalizedAnchors,
        source_hint: {
          anchors: hint.anchors || normalizedAnchors,
          framework: hint.framework || 'unknown',
          component_chain: Array.isArray(hint.component_chain) ? hint.component_chain : [],
          dom_path: Array.isArray(hint.dom_path) ? hint.dom_path : [],
          confidence_reasons: Array.isArray(hint.confidence_reasons) ? hint.confidence_reasons : []
        },
        locate_confidence: payload.locate_confidence || confidenceForAnchors(normalizedAnchors)
      };
    }
    const anchors = currentSourceAnchors(el);
    const hint = currentSourceHint(el, anchors);
    return {
      source_anchors: anchors,
      source_hint: hint,
      locate_confidence: confidenceForAnchors(anchors)
    };
  }

  function receiverHeaders() {
    const token = state.receiverToken || readStoredToken();
    const headers = {};
    if (token) headers['X-VFS-Token'] = token;
    return headers;
  }

  async function fetchReceiverJson(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeout || 1200);
    try {
      const response = await fetch(`http://127.0.0.1:${receiverPort()}${path}`, {
        method: options.method || 'GET',
        headers: { ...receiverHeaders(), ...(options.headers || {}) },
        body: options.body,
        signal: controller.signal,
        cache: 'no-store'
      });
      return response.ok ? await response.json() : null;
    } catch {
      return null;
    } finally {
      clearTimeout(timer);
    }
  }

  async function syncReceiverAgent() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 900);
    try {
      const response = await fetch(`http://127.0.0.1:${receiverPort()}/health`, {
        signal: controller.signal,
        cache: 'no-store'
      });
      const payload = response.ok ? await response.json() : null;
      const nextAgent = payload && AGENT_PROFILES[payload.agent] ? payload.agent : '';
      if (nextAgent && nextAgent !== state.receiverAgent) {
        state.receiverAgent = nextAgent;
        state.agent = resolveAgent();
        render();
      }
    } catch {
      // Receiver is optional until saving.
    } finally {
      clearTimeout(timer);
    }
  }

  async function syncTokenCatalog() {
    const payload = await fetchReceiverJson('/tokens');
    if (payload && payload.ok && Array.isArray(payload.tokens)) {
      state.tokenCatalog = payload.tokens;
      state.tokenLoaded = true;
      state.tokenError = false;
      renderPanel();
      return;
    }
    state.tokenCatalog = [];
    state.tokenLoaded = true;
    state.tokenError = true;
  }

  async function rescanTokenCatalog(options = {}) {
    const payload = await fetchReceiverJson('/tokens/rescan', { method: 'POST', timeout: 12000 });
    if (payload && payload.ok && Array.isArray(payload.tokens)) {
      state.tokenCatalog = payload.tokens;
      state.tokenLoaded = true;
      state.tokenError = false;
      if (!options.silent) toast(t('tokensRescanned'));
    } else if (!options.silent) {
      toast(t('tokenRescanFailed'));
    }
    renderPanel();
    return payload;
  }

  async function syncReviewArtifacts() {
    const [preview, verify] = await Promise.all([
      fetchReceiverJson('/preview'),
      fetchReceiverJson('/verify-result')
    ]);
    state.previewStatus = preview && preview.ok ? preview.preview || preview : state.previewStatus;
    state.verifyStatus = verify && verify.ok ? verify.verify || verify : state.verifyStatus;
    if (state.tab === 'feedback') renderPanel();
  }

  async function refreshPreview(options = {}) {
    const payload = await fetchReceiverJson('/apply-preview', { method: 'POST', timeout: 9000 });
    if (payload && payload.ok) {
      state.previewStatus = payload.preview || payload;
      if (!options.silent) toast(t('previewPlan'));
    } else if (!options.silent) {
      toast(t('receiverMissing'));
    }
    if (state.tab === 'feedback') renderPanel();
    return payload;
  }

  async function runVerify(options = {}) {
    const payload = await fetchReceiverJson('/verify', { method: 'POST', timeout: 12000 });
    if (payload && payload.ok) {
      state.verifyStatus = payload.verify || payload;
      if (!options.silent) toast(t('verifyResult'));
    } else if (!options.silent) {
      toast(t('receiverMissing'));
    }
    if (state.tab === 'feedback') renderPanel();
    return payload;
  }

  function getSelector(el) {
    if (el.id) return '#' + CSS.escape(el.id);
    const parts = [];
    let cur = el;
    while (cur && cur !== document.documentElement && cur !== document.body) {
      let seg = cur.tagName.toLowerCase();
      const classes = Array.from(cur.classList).filter(name => !name.startsWith('vf-') && !name.startsWith('__vf')).slice(0, 2);
      if (classes.length) seg += '.' + classes.map(name => CSS.escape(name)).join('.');
      const siblings = cur.parentElement ? Array.from(cur.parentElement.children).filter(node => node.tagName === cur.tagName) : [];
      if (siblings.length > 1) seg += `:nth-of-type(${siblings.indexOf(cur) + 1})`;
      parts.unshift(seg);
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  }

  function getSimilarSelector(el) {
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role');
    if (role) return `${tag}[role="${CSS.escape(role)}"]`;
    const dataAttr = Array.from(el.attributes).find(attr => attr.name.startsWith('data-') && !attr.name.startsWith('data-vf'));
    if (dataAttr) return `${tag}[${CSS.escape(dataAttr.name)}="${CSS.escape(dataAttr.value)}"]`;
    const classes = Array.from(el.classList).filter(name => !name.startsWith('vf-') && !name.startsWith('__vf')).slice(0, 2);
    if (classes.length) return `${tag}.${classes.map(name => CSS.escape(name)).join('.')}`;
    return tag;
  }

  function querySimilar(selector) {
    try {
      return Array.from(document.querySelectorAll(selector)).filter(el => !isIgnoredTarget(el));
    } catch {
      return [];
    }
  }

  function elementMeta(el) {
    const rect = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      classes: Array.from(el.classList).filter(name => !name.startsWith('vf-') && !name.startsWith('__vf')).slice(0, 12),
      text: (el.textContent || '').trim().slice(0, 220),
      rect: {
        x: Math.round(rect.left + window.scrollX),
        y: Math.round(rect.top + window.scrollY),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      }
    };
  }

  function styleSnapshot(el) {
    const cs = window.getComputedStyle(el);
    const snapshot = {};
    snapshotProps.forEach(prop => {
      snapshot[prop] = cs[prop] || '';
    });
    return snapshot;
  }

  function inlineStyleText(el) {
    const text = (el.getAttribute('style') || '').trim();
    return text || `/* ${t('noInline')} */`;
  }

  function propertyOriginal(prop) {
    if (!state.selectedBefore) return '';
    const camel = prop.replace(/-([a-z])/g, (_, char) => char.toUpperCase());
    return state.selectedBefore[camel] || '';
  }

  function cssValueForControl(control, raw) {
    const value = String(raw || '').trim();
    if (!value) return '';
    if (control.kind === 'px') {
      const parsed = parseControlNumber(value);
      if (parsed === null) return null;
      return `${formatControlNumber(clampControlNumber(control, parsed))}px`;
    }
    if (control.kind === 'number') {
      const parsed = parseControlNumber(value);
      if (parsed === null) return null;
      return formatControlNumber(clampControlNumber(control, parsed));
    }
    return value;
  }

  function displayValueForControl(control, computed) {
    const prop = control.prop.replace(/-([a-z])/g, (_, char) => char.toUpperCase());
    const value = computed[prop] || '';
    if (control.kind === 'px' && value.endsWith('px')) return String(parseFloat(value));
    if (control.kind === 'color') return rgbToHex(value) || '#f1f2f4';
    return value;
  }

  function fallbackParseControlNumber(raw) {
    const normalized = String(raw || '')
      .trim()
      .replace(',', '.')
      .replace(/\s*(px|rem|em|%)$/i, '');
    if (!normalized) return null;
    if (!/^-?\d+(\.\d+)?$/.test(normalized)) return null;
    const number = Number(normalized);
    return Number.isFinite(number) ? number : null;
  }

  function fallbackClampControlNumber(control, value) {
    let next = value;
    if (typeof control.min === 'number') next = Math.max(control.min, next);
    if (typeof control.max === 'number') next = Math.min(control.max, next);
    return next;
  }

  function formatControlNumber(value) {
    if (!Number.isFinite(value)) return '';
    return String(Number(value.toFixed(3)));
  }

  function controlStep(control, event = {}) {
    const base = Number(control.step || (control.kind === 'number' ? 1 : 1));
    const multiplier = event.shiftKey ? 10 : event.altKey ? 0.1 : 1;
    return base * multiplier;
  }

  function inputNumberValue(input, control) {
    const parsed = parseControlNumber(input.value);
    if (parsed !== null) return parsed;
    const current = state.selectedEl ? displayValueForControl(control, styleSnapshot(state.selectedEl)) : '';
    return parseControlNumber(current) ?? 0;
  }

  function setNumericInputValue(input, control, value) {
    input.value = formatControlNumber(clampControlNumber(control, value));
  }

  function fallbackRgbToHex(value) {
    const match = String(value).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!match) {
      if (/^#[0-9a-f]{6}$/i.test(String(value))) return value;
      return '';
    }
    return '#' + [match[1], match[2], match[3]].map(part => Number(part).toString(16).padStart(2, '0')).join('');
  }

  function tokenTypeForControl(control) {
    const prop = String(control?.prop || '').toLowerCase();
    if (!prop) return '';
    if (prop.includes('color')) return 'color';
    if (prop.includes('radius')) return 'radius';
    if (prop.includes('shadow')) return 'shadow';
    if (prop.includes('font') || prop.includes('line-height') || prop.includes('letter-spacing')) return 'typography';
    if (prop.includes('padding') || prop.includes('margin') || prop === 'gap' || prop === 'width' || prop === 'height') return 'spacing';
    return '';
  }

  function normalizeHexColor(value) {
    const raw = String(value || '').trim().toLowerCase();
    if (!raw) return '';
    const fromRgb = rgbToHex(raw);
    if (fromRgb) return fromRgb.toLowerCase();
    const short = raw.match(/^#([0-9a-f])([0-9a-f])([0-9a-f])$/i);
    if (short) return `#${short[1]}${short[1]}${short[2]}${short[2]}${short[3]}${short[3]}`.toLowerCase();
    return /^#[0-9a-f]{6}$/i.test(raw) ? raw : '';
  }

  function hexDistance(a, b) {
    const left = normalizeHexColor(a);
    const right = normalizeHexColor(b);
    if (!left || !right) return Number.POSITIVE_INFINITY;
    const parts = value => [1, 3, 5].map(index => parseInt(value.slice(index, index + 2), 16));
    const [lr, lg, lb] = parts(left);
    const [rr, rg, rb] = parts(right);
    return Math.sqrt((lr - rr) ** 2 + (lg - rg) ** 2 + (lb - rb) ** 2);
  }

  function cssLengthPx(value) {
    const raw = String(value || '').trim().toLowerCase();
    const match = raw.match(/^(-?\d*\.?\d+)\s*(px|rem|em)?$/);
    if (!match) return null;
    const number = Number(match[1]);
    if (!Number.isFinite(number)) return null;
    const unit = match[2] || 'px';
    if (unit === 'px') return number;
    if (unit === 'rem' || unit === 'em') return number * 16;
    return null;
  }

  function tokenDistance(control, token, value) {
    const type = tokenTypeForControl(control);
    const tokenType = String(token?.type || '').toLowerCase();
    const tokenValue = String(token?.value || '').trim();
    if (!type || !tokenValue) return Number.POSITIVE_INFINITY;
    if (type === 'color') {
      if (tokenType !== 'color') return Number.POSITIVE_INFINITY;
      return hexDistance(value, tokenValue);
    }
    if (type === 'shadow') {
      if (tokenType !== 'shadow') return Number.POSITIVE_INFINITY;
      return String(value).trim() === tokenValue ? 0 : Number.POSITIVE_INFINITY;
    }
    if (type === 'radius' && tokenType !== 'radius' && tokenType !== 'spacing') return Number.POSITIVE_INFINITY;
    if (type === 'spacing' && tokenType !== 'spacing' && tokenType !== 'radius') return Number.POSITIVE_INFINITY;
    if (type === 'typography' && tokenType !== 'typography' && tokenType !== 'spacing') return Number.POSITIVE_INFINITY;
    const left = cssLengthPx(value);
    const right = cssLengthPx(tokenValue);
    if (left === null || right === null) return Number.POSITIVE_INFINITY;
    return Math.abs(left - right);
  }

  function tokenThreshold(control) {
    const type = tokenTypeForControl(control);
    const prop = String(control?.prop || '');
    if (type === 'color') return 18;
    if (type === 'radius') return 4;
    if (type === 'typography') return prop === 'letter-spacing' ? 1 : 3;
    if (type === 'spacing') return 4;
    if (type === 'shadow') return 0;
    return 0;
  }

  function cleanTokenPayload(token, distance) {
    if (!token || !token.name) return null;
    const name = String(token.name || '').trim();
    const value = String(token.value || '').trim();
    const type = String(token.type || '').trim();
    const source = String(token.source || '').trim();
    const applied = String(token.applied_as || (name.startsWith('--') ? `var(${name})` : value)).trim();
    return {
      name,
      value,
      type,
      source,
      distance: Number.isFinite(distance) ? Number(distance.toFixed(3)) : 0,
      applied_as: applied
    };
  }

  function findTokenMatch(control, value) {
    if (!Array.isArray(state.tokenCatalog) || state.tokenCatalog.length === 0) return null;
    const type = tokenTypeForControl(control);
    if (!type) return null;
    const threshold = tokenThreshold(control);
    let best = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    state.tokenCatalog.forEach(token => {
      const distance = tokenDistance(control, token, value);
      if (distance < bestDistance) {
        best = token;
        bestDistance = distance;
      }
    });
    if (!best || bestDistance > threshold) return null;
    return cleanTokenPayload(best, bestDistance);
  }

  function tokenForControl(control, value) {
    const saved = selectedStyleEdit()?.properties?.[control.prop]?.token;
    if (saved && saved.name) return cleanTokenPayload(saved, Number(saved.distance || 0));
    const cssValue = cssValueForControl(control, value);
    return cssValue ? findTokenMatch(control, cssValue) : null;
  }

  function setHover(el) {
    if (state.hoveredEl === el) return;
    clearHover();
    state.hoveredEl = el;
    el.setAttribute('data-vf-hover', '');
  }

  function clearHover() {
    if (state.hoveredEl) {
      state.hoveredEl.removeAttribute('data-vf-hover');
      state.hoveredEl = null;
    }
  }

  function clearBatchPreview() {
    document.querySelectorAll('[data-vf-batch-preview]').forEach(el => {
      el.removeAttribute('data-vf-batch-preview');
    });
  }

  function syncBatchPreview() {
    clearBatchPreview();
    if (!state.selectedEl || (!state.batch && !state.batchConfirmArmed)) return;
    if (state.selectedBatchCount <= 1) return;
    querySimilar(state.selectedSimilarSelector).forEach(el => {
      if (el !== state.selectedEl) el.setAttribute('data-vf-batch-preview', '');
    });
  }

  function selectElement(el) {
    if (state.selectedEl) state.selectedEl.removeAttribute('data-vf-selected');
    state.selectedEl = el;
    state.selectedSelector = getSelector(el);
    state.selectedSimilarSelector = getSimilarSelector(el);
    const source = sourcePayload(el);
    state.selectedSourceAnchors = source.source_anchors;
    state.selectedSourceHint = source.source_hint;
    state.selectedLocateConfidence = source.locate_confidence;
    state.selectedBatchCount = Math.max(1, querySimilar(state.selectedSimilarSelector).length);
    state.selectedBefore = styleSnapshot(el);
    el.setAttribute('data-vf-selected', '');
    state.batch = false;
    state.batchConfirmArmed = false;
    clearBatchPreview();
    if (state.mode === 'feedback') state.tab = 'feedback';
    else if (state.mode === 'note') state.tab = 'feedback';
    else state.tab = 'style';
    render();
  }

  function clearSelection() {
    if (state.selectedEl) state.selectedEl.removeAttribute('data-vf-selected');
    state.selectedEl = null;
    state.selectedSelector = '';
    state.selectedSimilarSelector = '';
    state.selectedSourceAnchors = null;
    state.selectedSourceHint = null;
    state.selectedLocateConfidence = 'low';
    state.selectedBatchCount = 1;
    state.selectedBefore = null;
    state.batch = false;
    state.batchConfirmArmed = false;
    clearBatchPreview();
    render();
  }

  function setMode(nextMode) {
    if (state.activeEditEl) commitEdit();
    state.mode = nextMode;
    if (nextMode === 'feedback') state.tab = 'feedback';
    if (nextMode === 'style') state.tab = 'style';
    clearHover();
    render();
  }

  function setTab(nextTab) {
    state.tab = nextTab;
    if (nextTab === 'feedback') state.mode = 'feedback';
    if (nextTab === 'style' || nextTab === 'code') state.mode = 'style';
    render();
  }

  function setLang(nextLang) {
    state.lang = nextLang === 'zh' ? 'zh' : 'en';
    storeLang(state.lang);
    render();
  }

  function setTheme(nextTheme) {
    state.theme = nextTheme === 'light' ? 'light' : 'dark';
    shadowHost.dataset.vfsTheme = state.theme;
    storeTheme(state.theme);
    render();
  }

  function setAgent(nextAgent) {
    if (AGENT_PROFILES[nextAgent]) {
      storeAgent(nextAgent);
    } else {
      clearStoredAgent();
    }
    state.agent = resolveAgent();
    render();
    return state.agent;
  }

  function setToken(nextToken) {
    state.receiverToken = /^[A-Za-z0-9._:-]{12,256}$/.test(nextToken || '') ? nextToken : '';
    storeToken(state.receiverToken);
    return state.receiverToken;
  }

  function markDirty() {
    state.feedbackSaved = false;
    state.saveError = false;
    renderToolbar();
  }

  function selectedStyleEdit() {
    if (!state.selectedSelector) return null;
    return state.styleEdits.find(item => item.selector === state.selectedSelector) || null;
  }

  function currentStyleEdit() {
    if (!state.selectedEl || !state.selectedSelector) return null;
    let edit = state.styleEdits.find(item => item.selector === state.selectedSelector);
    const source = sourcePayload(state.selectedEl);
    if (!edit) {
      edit = {
        type: 'style_edit',
        selector: state.selectedSelector,
        similar_selector: state.selectedSimilarSelector,
        batch: state.batch,
        batch_count: state.batch ? state.selectedBatchCount : 1,
        properties: {},
        computed_before: state.selectedBefore || styleSnapshot(state.selectedEl),
        computed_after: {},
        element: elementMeta(state.selectedEl),
        ...source
      };
      state.styleEdits.push(edit);
    }
    edit.similar_selector = state.selectedSimilarSelector;
    edit.batch = state.batch;
    edit.batch_count = state.batch ? state.selectedBatchCount : 1;
    edit.element = elementMeta(state.selectedEl);
    edit.source_anchors = source.source_anchors;
    edit.source_hint = source.source_hint;
    edit.locate_confidence = source.locate_confidence;
    return edit;
  }

  function applyStyle(control, raw, options = {}) {
    if (!state.selectedEl) return;
    const value = cssValueForControl(control, raw);
    if (value === null) return;
    const edit = currentStyleEdit();
    if (!edit) return;
    const original = edit.properties[control.prop]?.original || propertyOriginal(control.prop);
    const targets = state.batch ? querySimilar(state.selectedSimilarSelector) : [state.selectedEl];
    if (!value) {
      targets.forEach(el => el.style.removeProperty(control.prop));
      delete edit.properties[control.prop];
    } else {
      targets.forEach(el => el.style.setProperty(control.prop, value));
      const token = findTokenMatch(control, value);
      edit.properties[control.prop] = {
        original,
        modified: value,
        ...(token ? { token } : {})
      };
    }
    edit.computed_after = styleSnapshot(state.selectedEl);
    if (Object.keys(edit.properties).length === 0) {
      state.styleEdits = state.styleEdits.filter(item => item !== edit);
    }
    markDirty();
    if (options.renderPanel) renderPanel();
    else refreshStatusUi();
  }

  function resetStyleProperty(prop) {
    if (!state.selectedEl) return;
    const edit = selectedStyleEdit();
    const original = edit?.properties?.[prop]?.original || propertyOriginal(prop);
    const targets = edit?.batch ? querySimilar(edit.similar_selector || state.selectedSimilarSelector) : [state.selectedEl];
    targets.forEach(el => {
      if (original) el.style.setProperty(prop, original);
      else el.style.removeProperty(prop);
    });
    if (edit) {
      delete edit.properties[prop];
      edit.computed_after = styleSnapshot(state.selectedEl);
      if (Object.keys(edit.properties || {}).length === 0) {
        state.styleEdits = state.styleEdits.filter(item => item !== edit);
      }
    }
    markDirty();
    render();
  }

  function toggleBatch() {
    if (!state.selectedEl || state.selectedBatchCount <= 1) return;
    if (!state.batch && !state.batchConfirmArmed) {
      state.batchConfirmArmed = true;
      syncBatchPreview();
      toast(t('batchConfirm'));
      render();
      return;
    }
    if (!state.batch && state.batchConfirmArmed) {
      state.batch = true;
      state.batchConfirmArmed = false;
      syncSelectedBatchState();
      syncBatchPreview();
      markDirty();
      render();
      return;
    }
    state.batch = false;
    state.batchConfirmArmed = false;
    syncSelectedBatchState();
    clearBatchPreview();
    markDirty();
    render();
  }

  function startEdit(el) {
    if (state.activeEditEl) commitEdit();
    if (!isEditableTarget(el)) return;
    selectElement(el);
    state.activeEditEl = el;
    el.dataset.vfOriginal = el.textContent;
    el.dataset.vfSelector = getSelector(el);
    el.setAttribute('contenteditable', 'true');
    el.setAttribute('data-vf-editing', '');
    el.focus();
  }

  function commitEdit() {
    if (!state.activeEditEl) return;
    const el = state.activeEditEl;
    state.activeEditEl = null;
    const original = el.dataset.vfOriginal;
    const modified = el.textContent;
    const selector = el.dataset.vfSelector;
    el.removeAttribute('contenteditable');
    el.removeAttribute('data-vf-editing');
    delete el.dataset.vfOriginal;
    delete el.dataset.vfSelector;
    if (modified === original || !selector) return;
    const source = sourcePayload(el);
    const idx = state.textEdits.findIndex(item => item.selector === selector);
    if (idx > -1) {
      const firstOriginal = state.textEdits[idx].original;
      if (modified === firstOriginal) state.textEdits.splice(idx, 1);
      else state.textEdits[idx] = { ...state.textEdits[idx], original: firstOriginal, modified, element: elementMeta(el), ...source };
    } else {
      state.textEdits.push({ type: 'text_edit', selector, original, modified, element: elementMeta(el), ...source });
    }
    markDirty();
    render();
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(value, max));
  }

  function viewportPoint(docX, docY) {
    return {
      x: Math.round(docX - window.scrollX),
      y: Math.round(docY - window.scrollY)
    };
  }

  function positionBeacon(node, docX, docY) {
    const point = viewportPoint(docX, docY);
    node.dataset.vfX = String(docX);
    node.dataset.vfY = String(docY);
    node.style.left = point.x + 'px';
    node.style.top = point.y + 'px';
  }

  function positionFloatingNote(node, docX, docY, maxWidth) {
    const point = viewportPoint(docX, docY);
    node.dataset.vfX = String(docX);
    node.dataset.vfY = String(docY);
    node.style.left = clamp(point.x + 16, 12, Math.max(12, window.innerWidth - maxWidth - 12)) + 'px';
    node.style.top = clamp(point.y - 18, 12, Math.max(12, window.innerHeight - 60)) + 'px';
  }

  function updateOverlayPositions() {
    shadowRoot.querySelectorAll('.vf-beacon').forEach(node => {
      positionBeacon(node, Number(node.dataset.vfX || 0), Number(node.dataset.vfY || 0));
    });
    shadowRoot.querySelectorAll('.vf-beacon-label').forEach(node => {
      positionFloatingNote(node, Number(node.dataset.vfX || 0), Number(node.dataset.vfY || 0), 280);
    });
    shadowRoot.querySelectorAll('.vf-beacon-tip').forEach(node => {
      positionFloatingNote(node, Number(node.dataset.vfX || 0), Number(node.dataset.vfY || 0), 310);
    });
  }

  function addSticky(el, event) {
    if (isIgnoredTarget(el)) return;
    selectElement(el);
    const id = ++state.annIdCounter;
    const selector = getSelector(el);
    const source = sourcePayload(el);
    const x = (event ? event.clientX : el.getBoundingClientRect().left) + window.scrollX;
    const y = (event ? event.clientY : el.getBoundingClientRect().top) + window.scrollY;
    const beacon = document.createElement('div');
    beacon.className = 'vf-beacon';
    beacon.dataset.vfId = String(id);
    beacon.dataset.vfSelector = selector;
    beacon.dataset.vfNote = '';
    positionBeacon(beacon, x, y);
    shadowRoot.appendChild(beacon);

    const tip = document.createElement('div');
    tip.className = 'vf-beacon-tip';
    positionFloatingNote(tip, x, y, 310);
    tip.innerHTML = `
      <input type="text">
      <button class="vf-note-ok" type="button">OK</button>
      <div class="vf-note-intents" role="group" aria-label="${escapeHtml(t('noteIntent'))}">
        <span>${escapeHtml(t('noteIntent'))}</span>
        ${ANNOTATION_INTENTS.map(intent => `<button class="vf-note-intent" type="button" data-intent="${escapeHtml(intent)}">${escapeHtml(intentLabel(intent))}</button>`).join('')}
      </div>
    `;
    shadowRoot.appendChild(tip);

    const input = tip.querySelector('input');
    const button = tip.querySelector('.vf-note-ok');
    const intentButtons = Array.from(tip.querySelectorAll('[data-intent]'));
    let intentHint = '';
    input.placeholder = t('notePlaceholder');
    button.title = t('noteConfirm');
    input.focus();

    let label = null;
    const removeAnnotation = () => {
      if (label) label.remove();
      beacon.remove();
      state.annotations = state.annotations.filter(item => item.id !== id);
      markDirty();
      render();
    };

    const commit = () => {
      const note = input.value.trim();
      tip.remove();
      if (!note) {
        beacon.remove();
        return;
      }
      beacon.dataset.vfNote = note;
      const annotation = {
        id,
        type: 'annotation',
        selector,
        note,
        ...(intentHint ? { intent_hint: intentHint } : {}),
        element: elementMeta(el),
        computed_snapshot: styleSnapshot(el),
        ...source
      };
      state.annotations.push(annotation);
      label = document.createElement('div');
      label.className = 'vf-beacon-label';
      label.dataset.vfId = String(id);
      label.textContent = note;
      positionFloatingNote(label, x, y, 280);
      shadowRoot.appendChild(label);
      beacon.addEventListener('mouseenter', () => { label.style.display = 'block'; });
      beacon.addEventListener('mouseleave', () => { label.style.display = 'none'; });
      beacon.addEventListener('contextmenu', event => {
        event.preventDefault();
        removeAnnotation();
      });
      markDirty();
      render();
    };

    button.addEventListener('click', commit);
    intentButtons.forEach(intentButton => {
      intentButton.addEventListener('click', () => {
        const next = intentButton.dataset.intent || '';
        intentHint = intentHint === next ? '' : next;
        intentButtons.forEach(node => node.classList.toggle('active', node.dataset.intent === intentHint));
        input.focus();
      });
    });
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        commit();
      } else if (event.key === 'Escape') {
        tip.remove();
        beacon.remove();
      }
    });
  }

  function allChanges() {
    return [
      ...state.textEdits,
      ...state.styleEdits,
      ...state.annotations.map(({ id, ...annotation }) => annotation)
    ];
  }

  function makeSession() {
    return {
      version: SESSION_VERSION,
      timestamp: new Date().toISOString(),
      agent: state.agent || DEFAULT_AGENT,
      source_url: location.href,
      page_title: document.title || '',
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      changes: allChanges()
    };
  }

  async function saveFeedback() {
    if (state.activeEditEl) commitEdit();
    const changes = allChanges();
    if (changes.length === 0) return;
    state.saveAbortController = new AbortController();
    state.saveError = false;
    render();
    const timeoutId = setTimeout(() => state.saveAbortController.abort(), 5000);
    try {
      const port = receiverPort();
      const token = state.receiverToken || readStoredToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['X-VFS-Token'] = token;
      const response = await fetch(`http://127.0.0.1:${port}/feedback`, {
        method: 'POST',
        headers,
        body: JSON.stringify(makeSession()),
        signal: state.saveAbortController.signal
      });
      if (!response.ok) {
        const error = new Error('HTTP ' + response.status);
        error.status = response.status;
        throw error;
      }
      state.feedbackSaved = true;
      state.lastSavedAt = new Date().toLocaleTimeString(state.lang === 'zh' ? 'zh-CN' : 'en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
      refreshPreview({ silent: true });
      toast(t('savedToast'));
    } catch (error) {
      state.feedbackSaved = false;
      state.saveError = true;
      let message = t('receiverMissing');
      if (error.name === 'AbortError') {
        message = `${t('timeoutToast')}${receiverPort()}`;
      } else if (error.status === 401 || error.status === 403) {
        message = t('tokenMismatch');
      }
      toast(message);
    } finally {
      clearTimeout(timeoutId);
      state.saveAbortController = null;
      render();
    }
  }

  function exportSession() {
    const blob = new Blob([JSON.stringify(makeSession(), null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'visual-feedback-studio-session.json';
    shadowRoot.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    toast(t('exported'));
  }

  function exportPreviewArtifact() {
    if (!state.previewStatus) return;
    const blob = new Blob([JSON.stringify(state.previewStatus, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'visual-feedback-studio-apply-preview.json';
    shadowRoot.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    toast(t('exported'));
  }

  async function handleImportFile() {
    const file = importInput.files && importInput.files[0];
    importInput.value = '';
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      importSession(payload);
      toast(t('imported'));
    } catch {
      toast(t('importFailed'));
    }
  }

  function importSession(payload) {
    const changes = Array.isArray(payload?.changes)
      ? payload.changes
      : Array.isArray(payload?.sessions)
        ? payload.sessions[payload.sessions.length - 1]?.changes || []
        : [];
    resetReview({ silent: true });
    changes.forEach(change => {
      if (!change || typeof change !== 'object') return;
      if (change.type === 'text_edit') {
        state.textEdits.push(change);
        const el = findElement(change.selector);
        if (el && typeof change.modified === 'string') el.textContent = change.modified;
      } else if (change.type === 'style_edit') {
        state.styleEdits.push(change);
        const targets = change.batch ? querySimilar(change.similar_selector || change.selector) : [findElement(change.selector)].filter(Boolean);
        targets.forEach(el => {
          Object.entries(change.properties || {}).forEach(([prop, pair]) => {
            if (pair && pair.modified) el.style.setProperty(prop, pair.modified);
          });
        });
      } else if (change.type === 'annotation') {
        restoreAnnotation(change);
      }
    });
    markDirty();
    render();
  }

  function restoreAnnotation(change, insertIndex = state.annotations.length) {
    const id = ++state.annIdCounter;
    const el = findElement(change.selector);
    const rect = el ? el.getBoundingClientRect() : null;
    const x = change.element?.rect?.x || (rect ? rect.left + window.scrollX : 80);
    const y = change.element?.rect?.y || (rect ? rect.top + window.scrollY : 80);
    const restored = { ...change, id };
    if (insertIndex >= 0 && insertIndex < state.annotations.length) state.annotations.splice(insertIndex, 0, restored);
    else state.annotations.push(restored);
    const beacon = document.createElement('div');
    beacon.className = 'vf-beacon';
    beacon.dataset.vfId = String(id);
    beacon.dataset.vfSelector = change.selector || '';
    beacon.dataset.vfNote = change.note || '';
    positionBeacon(beacon, x, y);
    shadowRoot.appendChild(beacon);
    const label = document.createElement('div');
    label.className = 'vf-beacon-label';
    label.dataset.vfId = String(id);
    label.textContent = change.note || '';
    positionFloatingNote(label, x, y, 280);
    shadowRoot.appendChild(label);
    beacon.addEventListener('mouseenter', () => { label.style.display = 'block'; });
    beacon.addEventListener('mouseleave', () => { label.style.display = 'none'; });
    beacon.addEventListener('contextmenu', event => {
      event.preventDefault();
      label.remove();
      beacon.remove();
      state.annotations = state.annotations.filter(item => item.id !== id);
      markDirty();
      render();
    });
  }

  function findElement(selector) {
    if (!selector) return null;
    try {
      return document.querySelector(selector);
    } catch {
      return null;
    }
  }

  function removeFeedback(kind, index) {
    const item = feedbackItem(kind, index);
    if (!item) return;
    state.lastDeleted = {
      kind,
      index,
      item: cloneFeedbackItem(item)
    };
    if (kind === 'text_edit') {
      revertTextEditPreview(item);
      state.textEdits.splice(index, 1);
    }
    if (kind === 'style_edit') {
      revertStyleEditPreview(item);
      state.styleEdits.splice(index, 1);
    }
    if (kind === 'annotation') {
      const removed = state.annotations.splice(index, 1)[0];
      if (removed) removeAnnotationNodes(removed.id);
    }
    markDirty();
    render();
  }

  function syncSelectedBatchState() {
    if (!state.selectedSelector) return;
    const edit = state.styleEdits.find(item => item.selector === state.selectedSelector);
    if (!edit) return;
    edit.similar_selector = state.selectedSimilarSelector;
    edit.batch = state.batch;
    edit.batch_count = state.batch ? state.selectedBatchCount : 1;
  }

  function locateFeedback(item) {
    const el = findElement(item.selector);
    if (!el) return;
    selectElement(el);
    el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
  }

  function resetReview(options = {}) {
    if (state.activeEditEl) commitEdit();
    if (!options.silent && allChanges().length > 0 && !window.confirm(t('resetConfirm'))) return;
    restorePreviewBeforeClear();
    state.textEdits.splice(0, state.textEdits.length);
    state.styleEdits.splice(0, state.styleEdits.length);
    state.annotations.splice(0, state.annotations.length);
    state.feedbackSaved = false;
    state.saveError = false;
    state.lastSavedAt = '';
    state.lastDeleted = null;
    state.batchConfirmArmed = false;
    state.annIdCounter = 0;
    shadowRoot.querySelectorAll('.vf-beacon,.vf-beacon-tip,.vf-beacon-label').forEach(el => el.remove());
    clearSelection();
    if (!options.silent) toast(t('resetToast'));
    render();
  }

  function cleanup() {
    if (state.saveAbortController) state.saveAbortController.abort();
    clearBatchPreview();
    document.removeEventListener('mouseover', handlers.mouseover, true);
    document.removeEventListener('mouseout', handlers.mouseout, true);
    document.removeEventListener('click', handlers.click, true);
    document.removeEventListener('keydown', handlers.keydown);
    document.removeEventListener('blur', handlers.blur, true);
    window.removeEventListener('scroll', handlers.scroll, true);
    window.removeEventListener('resize', handlers.resize);
    importInput.removeEventListener('change', handleImportFile);
    if (state.activeEditEl) {
      state.activeEditEl.removeAttribute('contenteditable');
      state.activeEditEl.removeAttribute('data-vf-editing');
    }
    clearHover();
    clearSelection();
    panel.remove();
    toolbar.remove();
    importInput.remove();
    shadowHost.remove();
    styleNode.remove();
    delete window.__vf__;
  }

  function toast(message) {
    const node = document.createElement('div');
    node.className = '__vf_toast__';
    node.textContent = message;
    shadowRoot.appendChild(node);
    setTimeout(() => {
      node.style.opacity = '0';
      node.style.transform = 'translateY(4px)';
      setTimeout(() => node.remove(), 320);
    }, 3200);
  }

  function render() {
    renderPanel();
    renderToolbar();
  }

  function refreshStatusUi() {
    const statusbar = panel.querySelector('.vf-statusbar');
    if (statusbar) statusbar.outerHTML = renderStatusBar();
    const count = toolbar.querySelector('.vf-count');
    if (count) count.textContent = String(allChanges().length);
  }

  function renderPanel() {
    panel.dataset.collapsed = state.panelCollapsed ? 'true' : 'false';
    enforcePanelGeometry();
    if (state.panelCollapsed) {
      panel.innerHTML = renderMiniPanel();
      bindPanelChrome();
      enforcePanelGeometry();
      return;
    }
    const selected = state.selectedEl;
    panel.innerHTML = `
      <div class="vf-grip"></div>
      <div class="vf-top">
        <div class="vf-brand-strip">
          <div class="vf-brand-mark" aria-hidden="true">${icon('studio')}</div>
          <div class="vf-tabs">
            <button class="vf-tab ${state.tab === 'style' ? 'on' : ''}" data-tab="style">${t('style')}</button>
            <button class="vf-tab ${state.tab === 'code' ? 'on' : ''}" data-tab="code">${t('code')}</button>
            <button class="vf-tab ${state.tab === 'feedback' ? 'on' : ''}" data-tab="feedback">${t('feedback')}</button>
          </div>
        </div>
        <div class="vf-actions">
          <button class="vf-icon-btn" id="__vf_lang__" type="button" title="${t('languageTip')}" aria-label="${t('languageTip')}">${icon('language')}</button>
          <button class="vf-icon-btn" id="__vf_theme__" type="button" title="${t('themeTip')}" aria-label="${t('themeTip')}">${icon(state.theme === 'light' ? 'light' : 'dark')}</button>
          <button class="vf-icon-btn" id="__vf_reset__" type="button" title="${t('resetTip')}" aria-label="${t('resetTip')}">${icon('reset')}</button>
          <button class="vf-icon-btn" data-collapse="true" type="button" title="${t('collapsePanel')}" aria-label="${t('collapsePanel')}">${icon('cancel')}</button>
        </div>
      </div>
      <div class="vf-content">
        ${state.tab === 'style' ? renderStyleTab(selected) : ''}
        ${state.tab === 'code' ? renderCodeTab(selected) : ''}
        ${state.tab === 'feedback' ? renderFeedbackTab() : ''}
      </div>
      ${renderStatusBar()}
    `;
    bindPanelChrome();
    bindStyleControls();
    bindFeedbackControls();
    bindSourceControls();
    enforcePanelGeometry();
  }

  function emptyMessageKey() {
    if (state.mode === 'text') return 'textEmpty';
    if (state.mode === 'note') return 'noteEmpty';
    if (state.mode === 'feedback') return 'feedbackEmpty';
    return 'styleEmpty';
  }

  function renderMiniPanel() {
    const counts = changeCounts();
    const status = statusState();
    return `
      <div class="vf-mini">
        <div class="vf-brand-mark" aria-hidden="true">${icon('studio')}</div>
        <div>
          <div class="vf-mini-title">${t('title')}</div>
          <div class="vf-mini-meta">${counts.text} ${t('textEdits')} · ${counts.style} ${t('styleEdits')} · ${counts.note} ${t('notes')} · ${status.label}</div>
        </div>
        <button class="vf-icon-btn" data-collapse="false" type="button" title="${t('expandPanel')}" aria-label="${t('expandPanel')}">${icon('feedback')}</button>
      </div>
    `;
  }

  function bindPanelChrome() {
    panel.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => setTab(button.dataset.tab)));
    panel.querySelector('#__vf_lang__')?.addEventListener('click', () => setLang(state.lang === 'zh' ? 'en' : 'zh'));
    panel.querySelector('#__vf_theme__')?.addEventListener('click', () => setTheme(state.theme === 'light' ? 'dark' : 'light'));
    panel.querySelector('#__vf_reset__')?.addEventListener('click', () => resetReview());
    panel.querySelectorAll('[data-collapse]').forEach(button => {
      button.addEventListener('click', () => {
        state.panelCollapsed = button.dataset.collapse === 'true';
        renderPanel();
      });
    });
  }

  function renderStyleTab(selected) {
    if (!selected) {
      return `<div class="vf-selection"><div class="vf-element-title">${t('select')}</div><div class="vf-muted">${t(emptyMessageKey())}</div></div>`;
    }
    const computed = styleSnapshot(selected);
    const commonSections = styleControls.filter(section => section.tier === 'common');
    const advancedSections = styleControls.filter(section => section.tier === 'advanced');
    return `
      ${renderSelectedContext(selected, true)}
      <div class="vf-muted">${t('styleCommonIntro')}</div>
      ${commonSections.map(section => renderStyleSection(section, computed)).join('')}
      <button class="vf-advanced-toggle" type="button" data-toggle-advanced="true" aria-expanded="${state.advancedStyle ? 'true' : 'false'}">
        ${state.advancedStyle ? t('hideAdvanced') : t('showAdvanced')}
      </button>
      ${state.advancedStyle ? advancedSections.map(section => renderStyleSection(section, computed)).join('') : ''}
    `;
  }

  function renderSelectedContext(selected, includeBatch) {
    const meta = elementMeta(selected);
    const text = meta.text || state.selectedSelector;
    const sourceLine = sourceSummary({
      source_anchors: state.selectedSourceAnchors || {},
      source_hint: state.selectedSourceHint || {}
    });
    const batchAvailable = state.selectedBatchCount > 1;
    const batchCopy = batchAvailable
      ? `${t('batchWillAffect')} ${state.selectedBatchCount} ${t('similar')}`
      : t('batchNone');
    return `
      <div class="vf-context">
        <div class="vf-context-head">
          <div>
            <div class="vf-context-title">${escapeHtml(meta.tag || t('currentElement'))}</div>
            <div class="vf-context-text">${escapeHtml(text)}</div>
          </div>
          <span class="vf-chip">${escapeHtml(meta.tag || '')}</span>
        </div>
        <div class="vf-chip-row">
          <span class="vf-chip">${escapeHtml(state.selectedSelector)}</span>
          <span class="vf-chip">${escapeHtml(state.selectedSimilarSelector)} · ${state.selectedBatchCount}</span>
          <span class="vf-chip">${escapeHtml(state.selectedLocateConfidence || 'low')}</span>
          ${sourceLine ? `<span class="vf-chip">${escapeHtml(sourceLine)}</span>` : ''}
        </div>
        ${includeBatch ? `
          <div class="vf-batch-row">
            <div class="vf-batch-copy">
              <strong>${t('batch')}</strong><br>
              ${escapeHtml(batchCopy)}
            </div>
            <button
              class="vf-switch ${state.batch ? 'on' : ''}"
              data-batch-toggle="true"
              type="button"
              ${batchAvailable ? '' : 'disabled'}
              aria-pressed="${state.batch ? 'true' : 'false'}"
              title="${escapeHtml(batchCopy)}"
            ><span>${state.batch ? t('batchOn') : t('batchOff')}</span><span></span></button>
          </div>
        ` : ''}
      </div>
    `;
  }

  function renderStyleSection(section, computed) {
    if (section.layout === 'box') {
      return `
        <section class="vf-section">
          <h4>${t(section.section)}</h4>
          <div class="vf-box-model">
            ${renderBoxModelRow('padding', section.items.filter(item => item.box === 'padding'), computed)}
            ${renderBoxModelRow('margin', section.items.filter(item => item.box === 'margin'), computed)}
          </div>
        </section>
      `;
    }
    return `
      <section class="vf-section">
        <h4>${t(section.section)}</h4>
        <div class="vf-grid">
          ${section.items.map(control => renderControl(control, computed)).join('')}
        </div>
      </section>
    `;
  }

  function renderBoxModelRow(kind, controls, computed) {
    return `
      <div class="vf-box-row">
        <div class="vf-box-label">${t(kind)}</div>
        ${controls.map(control => renderControl(control, computed, { compact: true, shortLabel: directionalLabel(control.key) })).join('')}
      </div>
    `;
  }

  function directionalLabel(key) {
    if (key.endsWith('Top')) return t('top');
    if (key.endsWith('Right')) return t('right');
    if (key.endsWith('Bottom')) return t('bottom');
    if (key.endsWith('Left')) return t('left');
    return t(key);
  }

  function renderControl(control, computed, options = {}) {
    const value = displayValueForControl(control, computed);
    const changed = Boolean(selectedStyleEdit()?.properties?.[control.prop]);
    const token = tokenForControl(control, value);
    const wide = !options.compact && (control.kind === 'text' || control.prop === 'box-shadow' || control.prop === 'text-align');
    const classes = ['vf-field'];
    if (wide) classes.push('wide');
    if (options.compact) classes.push('compact');
    if (changed) classes.push('changed');
    const label = options.shortLabel || t(control.key);
    const scrubbable = control.kind === 'px' || control.kind === 'number';
    const fieldAttrs = [
      `class="${classes.join(' ')}"`,
      `data-control-kind="${escapeHtml(control.kind)}"`,
      scrubbable ? 'data-scrubbable="true"' : ''
    ].filter(Boolean).join(' ');
    const commonAttrs = [
      `data-style-prop="${escapeHtml(control.prop)}"`,
      `data-style-kind="${escapeHtml(control.kind)}"`,
      control.min !== undefined ? `min="${control.min}"` : '',
      control.max !== undefined ? `max="${control.max}"` : '',
      control.step !== undefined ? `step="${control.step}"` : ''
    ].filter(Boolean).join(' ');
    let field = '';
    if (control.kind === 'select') {
      field = `
        <select ${commonAttrs}>
          ${control.options.map(option => `<option value="${escapeHtml(option)}" ${option === value ? 'selected' : ''}>${escapeHtml(option || 'auto')}</option>`).join('')}
        </select>
      `;
    } else if (control.kind === 'color') {
      field = `
        <div class="vf-color-wrap">
          <input ${commonAttrs} type="color" value="${escapeHtml(value)}">
          <span class="vf-color-text">${escapeHtml(value)}</span>
        </div>
      `;
    } else {
      const numeric = control.kind === 'number' || control.kind === 'px';
      const numericAttrs = numeric ? 'inputmode="decimal" autocomplete="off" spellcheck="false"' : '';
      field = `<input ${commonAttrs} ${numericAttrs} type="text" value="${escapeHtml(value)}">`;
    }
    return `
      <div ${fieldAttrs}>
        <label ${scrubbable ? `data-scrub-prop="${escapeHtml(control.prop)}" title="${escapeHtml(t('dragToAdjust'))}"` : ''}>${escapeHtml(label)}</label>
        ${field}
        ${control.kind === 'px' ? '<span class="vf-unit">px</span>' : ''}
        ${token ? `<span class="vf-token-chip" title="${escapeHtml(token.value)}">${escapeHtml(token.name)}</span>` : ''}
        ${!token && state.tokenLoaded && state.tokenError ? `<button class="vf-property-reset" type="button" data-rescan-tokens="true" title="${t('rescanTokens')}" aria-label="${t('rescanTokens')}">${t('rescanTokens')}</button>` : ''}
        ${changed ? `<span class="vf-modified">${t('modified')}</span><button class="vf-property-reset" type="button" data-reset-prop="${escapeHtml(control.prop)}" title="${t('resetProperty')}" aria-label="${t('resetProperty')}">reset</button>` : ''}
      </div>
    `;
  }

  function bindStyleControls() {
    panel.querySelectorAll('[data-style-prop]').forEach(input => {
      let composing = false;
      input.addEventListener('input', () => {
        if (composing) return;
        const control = flatStyleControls.find(item => item.prop === input.dataset.styleProp);
        if (control) applyStyle(control, input.value, { renderPanel: false });
        if (input.type === 'color') {
          const text = input.closest('.vf-color-wrap')?.querySelector('.vf-color-text');
          if (text) text.textContent = input.value;
        }
      });
      input.addEventListener('compositionstart', () => { composing = true; });
      input.addEventListener('compositionend', () => {
        composing = false;
        const control = flatStyleControls.find(item => item.prop === input.dataset.styleProp);
        if (control) applyStyle(control, input.value, { renderPanel: false });
      });
      input.addEventListener('change', () => {
        const control = flatStyleControls.find(item => item.prop === input.dataset.styleProp);
        if (control) applyStyle(control, input.value, { renderPanel: true });
      });
      input.addEventListener('keydown', event => {
        const control = flatStyleControls.find(item => item.prop === input.dataset.styleProp);
        if (control) handleStyleInputKeydown(event, input, control);
      });
      input.addEventListener('focus', () => {
        if (input.type === 'text') window.setTimeout(() => input.select(), 0);
      });
    });
    bindStyleScrubbers();
    panel.querySelectorAll('[data-reset-prop]').forEach(button => {
      button.addEventListener('click', () => resetStyleProperty(button.dataset.resetProp));
    });
    panel.querySelectorAll('[data-rescan-tokens]').forEach(button => {
      button.addEventListener('click', () => rescanTokenCatalog());
    });
    panel.querySelector('[data-toggle-advanced]')?.addEventListener('click', () => {
      state.advancedStyle = !state.advancedStyle;
      renderPanel();
    });
    panel.querySelector('[data-batch-toggle]')?.addEventListener('click', toggleBatch);
  }

  function handleStyleInputKeydown(event, input, control) {
    if (control.kind !== 'px' && control.kind !== 'number') return;
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      const direction = event.key === 'ArrowUp' ? 1 : -1;
      const next = inputNumberValue(input, control) + direction * controlStep(control, event);
      setNumericInputValue(input, control, next);
      applyStyle(control, input.value, { renderPanel: false });
    } else if (event.key === 'Enter') {
      event.preventDefault();
      applyStyle(control, input.value, { renderPanel: true });
      input.blur();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      input.value = displayValueForControl(control, styleSnapshot(state.selectedEl));
      input.blur();
    }
  }

  function bindStyleScrubbers() {
    panel.querySelectorAll('[data-scrub-prop]').forEach(label => {
      label.addEventListener('pointerdown', event => {
        if (event.button !== 0 || !state.selectedEl) return;
        const control = flatStyleControls.find(item => item.prop === label.dataset.scrubProp);
        const input = label.parentElement?.querySelector('[data-style-prop]');
        if (!control || !input || (control.kind !== 'px' && control.kind !== 'number')) return;
        event.preventDefault();
        label.setPointerCapture(event.pointerId);
        const field = label.closest('.vf-field');
        const startX = event.clientX;
        const startValue = inputNumberValue(input, control);
        let lastValue = startValue;
        field?.classList.add('scrubbing');

        const onMove = moveEvent => {
          const pixelsPerStep = moveEvent.altKey ? 12 : moveEvent.shiftKey ? 3 : 6;
          const deltaSteps = Math.round((moveEvent.clientX - startX) / pixelsPerStep);
          const next = startValue + deltaSteps * controlStep(control, moveEvent);
          if (next === lastValue) return;
          lastValue = next;
          setNumericInputValue(input, control, next);
          applyStyle(control, input.value, { renderPanel: false });
        };

        const onUp = upEvent => {
          label.releasePointerCapture(upEvent.pointerId);
          label.removeEventListener('pointermove', onMove);
          label.removeEventListener('pointerup', onUp);
          label.removeEventListener('pointercancel', onUp);
          field?.classList.remove('scrubbing');
          applyStyle(control, input.value, { renderPanel: true });
        };

        label.addEventListener('pointermove', onMove);
        label.addEventListener('pointerup', onUp);
        label.addEventListener('pointercancel', onUp);
      });
    });
  }

  function renderCodeTab(selected) {
    if (!selected) {
      return `<div class="vf-selection"><div class="vf-element-title">${t('noSelection')}</div><div class="vf-muted">${t(emptyMessageKey())}</div></div>`;
    }
    const computed = styleSnapshot(selected);
    const selector = state.selectedSelector;
    return `
      ${renderSelectedContext(selected, false)}
      <div class="vf-muted">${t('sourceIntro')}</div>
      <div class="vf-code-card">
        <h4>${t('selectorLabel')}</h4>
        <div class="vf-code-actions">
          <button class="vf-small-btn" type="button" data-copy="selector">${t('copySelector')}</button>
        </div>
        <pre>${escapeHtml(selector)}</pre>
      </div>
      <div class="vf-code-card">
        <h4>${t('elementMeta')}</h4>
        <pre>${escapeHtml(JSON.stringify(elementMeta(selected), null, 2))}</pre>
      </div>
      <div class="vf-code-card">
        <h4>${t('inlineStyle')}</h4>
        <pre>${escapeHtml(`${selected.tagName.toLowerCase()} {\n  ${inlineStyleText(selected)}\n}`)}</pre>
      </div>
      <div class="vf-code-card">
        <h4>${t('computedStyle')}</h4>
        <div class="vf-code-actions">
          <button class="vf-small-btn" type="button" data-copy="snapshot">${t('copySnapshot')}</button>
        </div>
        <pre>${escapeHtml(snapshotText(selected, computed))}</pre>
      </div>
    `;
  }

  function renderFeedbackTab() {
    const items = feedbackItems();
    const counts = changeCounts();
    const status = statusState();
    return `
      <div class="vf-feedback-summary">
        <strong>${t('feedbackBoard')}</strong>
        <div class="vf-chip-row">
          <span class="vf-chip">${counts.text} ${t('textEdits')}</span>
          <span class="vf-chip">${counts.style} ${t('styleEdits')}</span>
          <span class="vf-chip">${counts.note} ${t('notes')}</span>
          <span class="vf-chip">${status.label}</span>
        </div>
        <div class="vf-feedback-meta">
          ${state.lastSavedAt ? `${t('feedbackSavedMeta')} ${t('saveFile')} · ${t('savedAt')} ${escapeHtml(state.lastSavedAt)}<br>${t('nextTellAgent')}` : t('feedbackEmpty')}
        </div>
      </div>
      ${renderReviewArtifacts()}
      ${state.lastDeleted ? `
        <div class="vf-undo-row">
          <span class="vf-muted">${t('deleted')}</span>
          <button class="vf-small-btn" type="button" data-undo-delete="true">${t('undo')}</button>
        </div>
      ` : ''}
      ${items.length ? `
        <div class="vf-feedback-list">
          ${items.map(({ kind, index, item }) => renderFeedbackItem(kind, index, item)).join('')}
        </div>
      ` : `<div class="vf-selection"><div class="vf-element-title">${t('noFeedback')}</div><div class="vf-muted">${t('feedbackEmpty')}</div></div>`}
    `;
  }

  function renderReviewArtifacts() {
    const preview = state.previewStatus;
    const verify = state.verifyStatus;
    const previewCounts = preview?.counts || {};
    const verifyCounts = verify?.counts || {};
    return `
      <div class="vf-review-grid">
        <div class="vf-review-card">
          <h4>${t('previewPlan')}</h4>
          ${preview ? `
            <div class="vf-chip-row">
              <span class="vf-chip">${Number(previewCounts.total || 0)} total</span>
              <span class="vf-chip">${Number(previewCounts.auto_applicable_text || 0)} auto</span>
              <span class="vf-chip">${Number(previewCounts.manual_review || 0)} manual</span>
              <span class="vf-chip">${Number(previewCounts.unresolved || 0)} unresolved</span>
            </div>
          ` : `<div class="vf-muted">${t('previewEmpty')}</div>`}
          <div class="vf-feedback-actions">
            <button class="vf-small-btn" type="button" data-refresh-preview="true">${t('refreshPreview')}</button>
            <button class="vf-small-btn" type="button" data-export-preview="true" ${preview ? '' : 'disabled'}>${t('exportPreview')}</button>
          </div>
        </div>
        <div class="vf-review-card">
          <h4>${t('verifyResult')}</h4>
          ${verify ? `
            <div class="vf-chip-row">
              <span class="vf-chip">${escapeHtml(verify.verification_mode || 'source_only')}</span>
              <span class="vf-chip">${Number(verifyCounts.verified || 0)} verified</span>
              <span class="vf-chip">${Number(verifyCounts.drift || 0)} drift</span>
              <span class="vf-chip">${Number(verifyCounts.not_found || 0)} missing</span>
              <span class="vf-chip">${Number(verifyCounts.manual_review || 0)} manual</span>
            </div>
          ` : `<div class="vf-muted">${t('verifyEmpty')}</div>`}
          <div class="vf-feedback-actions">
            <button class="vf-small-btn" type="button" data-run-verify="true">${t('runVerify')}</button>
          </div>
        </div>
      </div>
    `;
  }

  function reviewStatusFor(kind, item) {
    const selector = item?.selector || '';
    const verifyResult = Array.isArray(state.verifyStatus?.results)
      ? state.verifyStatus.results.find(result => result.type === kind && (result.selector || '') === selector)
      : null;
    if (verifyResult?.status) return verifyResult.status;
    const previewBuckets = kind === 'text_edit'
      ? state.previewStatus?.text_edits
      : kind === 'style_edit'
        ? state.previewStatus?.style_edits
        : state.previewStatus?.annotations;
    const previewItem = Array.isArray(previewBuckets)
      ? previewBuckets.find(result => (result.selector || '') === selector)
      : null;
    return previewItem?.status || '';
  }

  function renderFeedbackItem(kind, index, item) {
    const reviewStatus = reviewStatusFor(kind, item);
    const confidence = item.locate_confidence || 'low';
    const summary = sourceSummary(item);
    return `
      <div class="vf-feedback-item">
        <div class="vf-feedback-head">
          <span class="vf-pill">${feedbackLabel(kind)}</span>
          ${reviewStatus ? `<span class="vf-pill neutral">${escapeHtml(reviewStatus)}</span>` : ''}
          <span class="vf-pill neutral">${escapeHtml(confidence)}</span>
          <span class="vf-muted">${escapeHtml(item.selector || '')}</span>
        </div>
        ${summary ? `<div class="vf-feedback-source">${escapeHtml(t('sourceSummary'))}: ${escapeHtml(summary)}</div>` : ''}
        <div class="vf-feedback-copy">${escapeHtml(feedbackSummary(kind, item))}</div>
        <div class="vf-feedback-actions">
          <button class="vf-small-btn" data-locate-kind="${kind}" data-locate-index="${index}">${t('locate')}</button>
          <button class="vf-small-btn" data-delete-kind="${kind}" data-delete-index="${index}">${t('delete')}</button>
        </div>
      </div>
    `;
  }

  function bindFeedbackControls() {
    panel.querySelector('[data-refresh-preview]')?.addEventListener('click', () => refreshPreview());
    panel.querySelector('[data-run-verify]')?.addEventListener('click', () => runVerify());
    panel.querySelector('[data-export-preview]')?.addEventListener('click', exportPreviewArtifact);
    panel.querySelectorAll('[data-locate-kind]').forEach(button => button.addEventListener('click', () => {
      const item = feedbackItem(button.dataset.locateKind, Number(button.dataset.locateIndex));
      if (item) locateFeedback(item);
    }));
    panel.querySelectorAll('[data-delete-kind]').forEach(button => button.addEventListener('click', () => {
      removeFeedback(button.dataset.deleteKind, Number(button.dataset.deleteIndex));
    }));
    panel.querySelector('[data-undo-delete]')?.addEventListener('click', undoDelete);
  }

  function bindSourceControls() {
    panel.querySelectorAll('[data-copy]').forEach(button => {
      button.addEventListener('click', async () => {
        if (!state.selectedEl) return;
        const value = button.dataset.copy === 'selector'
          ? state.selectedSelector
          : snapshotText(state.selectedEl, styleSnapshot(state.selectedEl));
        await copyText(value);
      });
    });
  }

  function feedbackItem(kind, index) {
    if (kind === 'text_edit') return state.textEdits[index];
    if (kind === 'style_edit') return state.styleEdits[index];
    if (kind === 'annotation') return state.annotations[index];
    return null;
  }

  function feedbackSummary(kind, item) {
    if (kind === 'text_edit') return `${item.original || ''}\n-> ${item.modified || ''}`;
    if (kind === 'style_edit') {
      return Object.entries(item.properties || {}).map(([prop, pair]) => `${prop}: ${pair.original || ''} -> ${pair.modified || ''}`).join('\n');
    }
    return item.note || '';
  }

  function changeCounts() {
    return {
      text: state.textEdits.length,
      style: state.styleEdits.length,
      note: state.annotations.length,
      total: allChanges().length
    };
  }

  function statusState() {
    if (state.saveAbortController) return { key: 'saving', label: t('savingTip'), className: 'unsaved' };
    if (state.saveError) return { key: 'error', label: t('saveFailed'), className: 'error' };
    if (state.feedbackSaved) return { key: 'saved', label: t('saved'), className: 'saved' };
    if (allChanges().length > 0) return { key: 'unsaved', label: t('unsaved'), className: 'unsaved' };
    return { key: 'empty', label: t('noFeedback'), className: '' };
  }

  function renderStatusBar() {
    const counts = changeCounts();
    const status = statusState();
    return `
      <div class="vf-statusbar">
        <div class="vf-status-count">${counts.text} ${t('textEdits')} · ${counts.style} ${t('styleEdits')} · ${counts.note} ${t('notes')}</div>
        <div class="vf-status-state ${status.className}">${escapeHtml(status.label)}</div>
      </div>
    `;
  }

  function feedbackItems() {
    return [
      ...state.textEdits.map((item, index) => ({ kind: 'text_edit', index, item })),
      ...state.styleEdits.map((item, index) => ({ kind: 'style_edit', index, item })),
      ...state.annotations.map((item, index) => ({ kind: 'annotation', index, item }))
    ];
  }

  function feedbackLabel(kind) {
    if (kind === 'text_edit') return t('textEdits');
    if (kind === 'style_edit') return t('styleEdits');
    return t('notes');
  }

  function compactSourceLoc(sourceLoc) {
    if (!sourceLoc || typeof sourceLoc !== 'object') return '';
    const file = String(sourceLoc.file || '').trim();
    if (!file) return '';
    const line = Number(sourceLoc.line || 0);
    const column = Number(sourceLoc.column || 0);
    return `${file}${line > 0 ? `:${line}` : ''}${column > 0 ? `:${column}` : ''}`;
  }

  function sourceSummary(item = {}) {
    const anchors = item.source_anchors && typeof item.source_anchors === 'object' ? item.source_anchors : {};
    const hint = item.source_hint && typeof item.source_hint === 'object' ? item.source_hint : {};
    const hintAnchors = hint.anchors && typeof hint.anchors === 'object' ? hint.anchors : {};
    const loc = compactSourceLoc(anchors.sourceLoc || hintAnchors.sourceLoc);
    if (loc) return loc;
    const chain = Array.isArray(hint.component_chain) ? hint.component_chain : [];
    const names = chain.map(part => part && part.name).filter(Boolean).slice(0, 3);
    if (names.length) return names.join(' > ');
    if (anchors.testId) return `testId=${anchors.testId}`;
    if (anchors.componentName) return `component=${anchors.componentName}`;
    if (anchors.stableId) return `id=${anchors.stableId}`;
    const reasons = Array.isArray(hint.confidence_reasons) ? hint.confidence_reasons.filter(Boolean).slice(0, 3) : [];
    return reasons.length ? reasons.join(', ') : '';
  }

  function snapshotText(selected, computed = styleSnapshot(selected)) {
    return [
      `selector: ${state.selectedSelector}`,
      `similar_selector: ${state.selectedSimilarSelector}`,
      '',
      JSON.stringify({
        element: elementMeta(selected),
        source_anchors: state.selectedSourceAnchors || currentSourceAnchors(selected),
        source_hint: state.selectedSourceHint || currentSourceHint(selected),
        locate_confidence: state.selectedLocateConfidence,
        inline_style: inlineStyleText(selected),
        computed_style: computed
      }, null, 2)
    ].join('\n');
  }

  async function copyText(value) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = value;
        textarea.style.cssText = 'position:fixed;left:-9999px;top:-9999px;';
        shadowRoot.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
      }
      toast(t('copied'));
    } catch {
      toast(t('copySnapshot'));
    }
  }

  function cloneFeedbackItem(item) {
    return JSON.parse(JSON.stringify(item));
  }

  function undoDelete() {
    const deleted = state.lastDeleted;
    if (!deleted) return;
    const item = cloneFeedbackItem(deleted.item);
    if (deleted.kind === 'text_edit') {
      state.textEdits.splice(Math.min(deleted.index, state.textEdits.length), 0, item);
      applyTextEditPreview(item);
    } else if (deleted.kind === 'style_edit') {
      state.styleEdits.splice(Math.min(deleted.index, state.styleEdits.length), 0, item);
      applyStyleEditPreview(item);
    } else if (deleted.kind === 'annotation') {
      restoreAnnotation(item, Math.min(deleted.index, state.annotations.length));
    }
    state.lastDeleted = null;
    markDirty();
    render();
  }

  function removeAnnotationNodes(id) {
    shadowRoot
      .querySelectorAll(`.vf-beacon[data-vf-id="${id}"],.vf-beacon-tip[data-vf-id="${id}"],.vf-beacon-label[data-vf-id="${id}"]`)
      .forEach(el => el.remove());
  }

  function applyTextEditPreview(item) {
    const el = findElement(item.selector);
    if (el && typeof item.modified === 'string') el.textContent = item.modified;
  }

  function revertTextEditPreview(item) {
    const el = findElement(item.selector);
    if (el && typeof item.original === 'string' && el.textContent === item.modified) el.textContent = item.original;
  }

  function applyStyleEditPreview(item) {
    const targets = item.batch ? querySimilar(item.similar_selector || item.selector) : [findElement(item.selector)].filter(Boolean);
    targets.forEach(el => {
      Object.entries(item.properties || {}).forEach(([prop, pair]) => {
        if (pair && pair.modified) el.style.setProperty(prop, pair.modified);
      });
    });
  }

  function revertStyleEditPreview(item) {
    const targets = item.batch ? querySimilar(item.similar_selector || item.selector) : [findElement(item.selector)].filter(Boolean);
    targets.forEach(el => {
      Object.entries(item.properties || {}).forEach(([prop, pair]) => {
        if (pair && pair.original) el.style.setProperty(prop, pair.original);
        else el.style.removeProperty(prop);
      });
    });
  }

  function restorePreviewBeforeClear() {
    [...state.styleEdits].reverse().forEach(revertStyleEditPreview);
    [...state.textEdits].reverse().forEach(revertTextEditPreview);
    clearBatchPreview();
  }

  function renderToolbar() {
    const count = allChanges().length;
    const saveTip = state.saveAbortController ? t('savingTip') : state.feedbackSaved ? t('savedTip') : t('saveTip');
    const tools = [
      { action: 'exit', icon: 'cancel', tip: t('exitTip') },
      { divider: true },
      { mode: 'style', icon: 'style', tip: t('styleTip') },
      { mode: 'text', icon: 'text', tip: t('textTip') },
      { mode: 'note', icon: 'note', tip: t('noteTip') },
      { mode: 'feedback', icon: 'feedback', tip: t('feedbackTip') },
      { divider: true },
      { action: 'import', icon: 'import', tip: t('importTip') },
      { action: 'export', icon: 'export', tip: t('exportTip') },
      { action: 'save', icon: 'save', tip: saveTip, busy: Boolean(state.saveAbortController), disabled: count === 0 || Boolean(state.saveAbortController) }
    ];
    toolbar.innerHTML = `
      ${tools.map(tool => tool.divider ? '<div class="vf-divider"></div>' : renderToolButton(tool)).join('')}
      <div class="vf-count">${count}</div>
    `;
    toolbar.querySelector('[data-action="exit"]')?.addEventListener('click', cleanup);
    toolbar.querySelector('[data-action="import"]')?.addEventListener('click', () => importInput.click());
    toolbar.querySelector('[data-action="export"]')?.addEventListener('click', exportSession);
    toolbar.querySelector('[data-action="save"]')?.addEventListener('click', saveFeedback);
    toolbar.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
    enforceToolbarGeometry();
  }

  function renderToolButton(tool) {
    const active = tool.mode && state.mode === tool.mode;
    const attrs = [
      'class="vf-tool' + (active ? ' on' : '') + (tool.busy ? ' busy' : '') + '"',
      'type="button"',
      `title="${escapeHtml(tool.tip)}"`,
      `aria-label="${escapeHtml(tool.tip)}"`,
      `data-tip="${escapeHtml(tool.tip)}"`
    ];
    if (tool.mode) attrs.push(`data-mode="${escapeHtml(tool.mode)}"`);
    if (tool.action) attrs.push(`data-action="${escapeHtml(tool.action)}"`);
    if (tool.disabled) attrs.push('disabled');
    return `<button ${attrs.join(' ')}>${icon(tool.icon)}</button>`;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  window.__vf__ = {
    exit: cleanup,
    getAgent: () => state.agent,
    getAgentOverride: () => readStoredAgent(),
    getLang: () => state.lang,
    getTheme: () => state.theme,
    getToken: () => state.receiverToken || readStoredToken(),
    reset: resetReview,
    setAgent,
    setLang,
    setToken,
    setTheme,
    toggle: () => {
      shadowHost.style.display = shadowHost.style.display === 'none' ? '' : 'none';
    }
  };

  render();
  syncReceiverAgent();
  syncTokenCatalog();
  syncReviewArtifacts();
  toast(t('activeToast'));
})();
