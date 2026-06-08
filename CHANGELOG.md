# CHANGELOG

Visual Feedback Studio 版本记录。默认使用中文，保持简洁、产品化，只记录真正影响使用和集成的变化。

## v4.0.0-beta - 2026-06-07

### 重点更新

- Chrome 扩展升级为 v4.0.0 beta，商店版 `manifest.json` 默认只保留 `activeTab`、`scripting`、`storage`。
- 默认 host 权限改为 optional host permissions：`http://*/*`、`https://*/*`、`file:///*` 只在用户授权当前站点后获得持久访问。
- 开发 / 分发权限配置分离，避免误把宽权限带入分发包。
- popup 新增当前页面权限状态、授权当前站点按钮和 file URL 详情页指引。
- `setup.py` 输出新增 `first_loop`、权限模型、token 状态和 receiver/token/permission 失败处理建议。
- `scripts/vfs.py doctor` 升级为一屏可读状态：receiver、token、feedback count、preview、verify、permission model 和下一步。
- 浏览器保存失败时区分 receiver token mismatch，提示刷新配置或重启 receiver。
- 新 session 版本更新为 `4.0-beta`，继续兼容 v2.1、v3.0、v3.1 和 v3.2 beta payload。

### 分发与文档

- 打包输出更新为 `dist/visual-feedback-studio-v4.0.0-beta-extension.zip`。
- `scripts/package_extension.py` 会拒绝带默认 `host_permissions` 的商店 manifest，并验证 zip 中不包含 runtime JSON、AppleDouble 文件或本地缓存。
- 中英文 README / SKILL 同步 v4.0 安装路径、5-minute first loop、权限说明和 FAQ。
- 新增 v4.0 商店、隐私、演示和发布材料清单，便于后续 Chrome Web Store、GitHub Release 或 unpacked fallback 使用。

### 安全与边界

- v4.0 仍保持 local-first：反馈、preview、verify、receiver 状态和 rollback snapshot 默认写入项目本地文件。
- 不启用 hosted dashboard，不默认上传反馈或源码。
- 真实 Chrome Web Store 审核、P50 首轮时间和 file URL 授权后保存仍需要外部/人工验证；当前版本提供本地 release candidate 与验证脚本证据。

## v3.2.0-beta - 2026-06-04

### 重点更新

- 新增源码感知的 apply preview，并统一输出 `lifecycle_status`：`captured`、`planned`、`applied`、`verified`、`needs_review`、`unresolved`。
- 新增 `action_candidates[]`，让 agent 区分可自动执行、需要复核和无法定位的反馈。
- 新增 token-aware 样式建议：扫描 `.visual_feedback_studio_tokens.json`，在样式面板显示 nearest token，并在 CSS preview 中优先使用 `var(--token)`。
- 新增 source/browser 验证：`verify_feedback_apply.py` 支持源码验证，也可通过本地 URL 做 DOM/computed style 验证。
- 新增统一 CLI：`scripts/vfs.py plan|apply|verify|doctor|tokens rescan`。
- 新增高置信 `sourceLoc` 行级消歧：重复文案只有在目标源码行唯一可证明时才自动应用。
- 新增 Phase 3 验证闭环：`vfs apply --verify` 输出统一机器可读报告，包含 apply、verify、证据计数、snapshot 和 rollback command。
- 新增 apply 前 rollback snapshot：自动写源码前保存 `.visual_feedback_studio_snapshots/`，并提供 `vfs rollback --snapshot <file>`。
- 新增浏览器验证 artifact：Playwright 可用时保存页面或目标元素截图到 `.visual_feedback_studio_artifacts/`。

### 体验

- Chrome popup 新增 receiver 状态、已保存反馈数、preview 状态、verify 状态和 agent handoff 提示。
- Receiver `/health` 新增 feedback、preview、verify 摘要，方便扩展和 agent 判断当前闭环状态。
- 新增受 token 保护的 `POST /tokens/rescan`，浏览器工作台可重新扫描 token 缓存。
- Setup 默认走 beta-safe 安装，并补齐 restore、package 和浏览器安装辅助流程。

### 安全

- `/tokens`、`/preview`、`/verify-result`、`/tokens/rescan` 在启用 token 时都要求 `X-VFS-Token`。
- Preview 与 apply 共用 `scripts/apply_policy.py`，避免判定口径分裂。
- 新增源码映射基准覆盖，涵盖静态 HTML/CSS、React sourceLoc、Vue 中置信、生产降级和 token 样式建议。
- Rollback 默认校验当前文件是否仍等于 snapshot 记录的 post-apply hash，避免覆盖后续手工修改。

## v3.1.0 - 2026-06-03

- 新增 `source_anchors` 和 `locate_confidence`，提升源码定位稳定性。
- 新增源码感知样式建议，输出 `computed_diff`、`batch_hint` 和 CSS preview。
- 新增备注意图 chips，并为常见设计备注生成确定性 `intent_guess`。
- Receiver 写入新增 Origin 校验和 `X-VFS-Token`。
- Inspector 合并逻辑升级为稳定 fingerprint：优先 test id、sourceLoc、组件线索、语义信息，最后回退 selector。

## v3.0.0 - 2026-06-03

- 新增 Codex 与 Claude / Cowork 双 agent 支持。
- Chrome popup 新增 `Default`、`Codex`、`Claude` agent 选择。
- Receiver 新增 `VFS_AGENT` 和 `receiver_control.py --agent`。
- 新增 `agents/anthropic.yaml`，保留 `agents/openai.yaml`。
- 继续兼容 v2.1 反馈 payload 和既有工作流。

## v2.1.0 - 2026-06-03

- 优化浏览器审稿工作台，样式面板拆分为常用与高级控制。
- 新增 Figma 式数值输入：聚焦选中、方向键微调、修饰键加速、标签拖拽调参。
- 新增属性已改标记、单项 reset、盒模型分组和面板折叠。
- 新增审稿任务板，支持数量统计、保存状态、定位、删除和撤销。
- 源码线索面板支持复制 selector、元素 metadata、inline style 和 computed style 快照。

## v2.0.0 - 2026-06-02

- 引入完整视觉编辑工作台：样式、文案、备注、反馈和源码线索。
- 新增结构化 `style_edit`，记录 CSS 属性、computed-before 和 computed-after。
- 新增反馈列表管理、定位、删除、导出和导入。
- 新增相似元素批量样式 metadata：`batch`、`similar_selector`、`batch_count`。
- 文案修改继续保持保守策略：只有精确唯一匹配才自动应用。

## v1.0.0 - 2026-06-02

- 初始 Chrome extension，用于浏览器内视觉反馈采集。
- 支持页面内文案修改和元素备注。
- 支持通过本地 receiver 保存 `.visual_feedback_studio.json`。
- 提供 `feedback_inspector.py`、`apply_text_edits.py`、`receiver_control.py` 和 `self_check.py`。
- 建立基础闭环：浏览器采集反馈，保存 JSON，再映射回源码。
