<p align="center">
  <img src="./Logo.svg" width="88" alt="Visual Feedback Studio 标志" />
</p>

<h1 align="center">Visual Feedback Studio</h1>

<p align="center">
  <strong>在浏览器里收集视觉反馈，把反馈带回源码工作流。</strong>
</p>

<p align="center">
  <code>local-first</code> · <code>Chrome MV3</code> · <code>Codex / Claude</code> · <code>可视化审稿</code>
</p>

<p align="center">
  <a href="./README.en.md">English</a>
</p>

---

## 快速开始

在你要审稿的本地项目根目录运行：

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | bash
```

在 Chrome 中加载扩展：

```text
chrome://extensions/ -> Developer mode -> Load unpacked
```

选择本仓库的 `chrome-extension/` 目录。然后打开你有权限审稿的页面，启动 Visual Feedback Studio，采集反馈并保存。

如果 `3456` 端口已被其他本地 receiver 占用，可以换端口：

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_PORT=3463 bash
```

预览当前反馈能安全解析到哪些源码位置：

```bash
python3 scripts/vfs.py plan /path/to/your-project
```

更多说明见 [安装 / 访问](./docs/install.md)。

想先试一圈，可以打开 `examples/basic-static-preview/index.html`，或用任意静态文件服务器预览这个目录。审稿本地 `file://` 页面时，需要在 Chrome 扩展详情页开启 file URL access。

## 它是什么

Visual Feedback Studio 是一个面向前端产品审稿的 local-first 工作流工具。它让你直接在运行中的页面上改文案、调样式、贴备注，并把这些操作保存成结构化反馈，交给 AI 辅助开发流程继续预览、应用和验证。

它想解决的不是“再做一个截图批注工具”，而是产品审稿里最耗时的那段翻译工作：把“这里怪怪的”变成“应该改哪个文件、哪个组件、哪段文案、哪条样式”。

```text
打开页面 -> 标记反馈 -> 保存结构化 JSON -> 预览源码修改 -> 应用 -> 验证
```

## 它适合什么场景

- 产品、设计和开发一起审前端页面。
- 你希望少写截图说明，直接在页面上表达修改意图。
- 你正在用 Codex、Claude 或类似 AI coding agent 辅助改代码。
- 你希望反馈默认留在本地项目里，而不是先上传到云端。
- 你需要一个保守的 apply / verify 流程，避免 AI 猜错源码位置。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 页面内反馈 | 在真实页面上记录文案、样式和备注反馈。 |
| 本地结构化保存 | 将反馈写入项目本地文件，方便 agent 读取和处理。 |
| 源码预览 | 在修改前先判断哪些反馈能安全映射到源码。 |
| 保守应用 | 只有目标可证明时才自动修改，模糊反馈保留给人工判断。 |
| 验证闭环 | 对已应用的反馈做 source / browser 侧验证。 |
| Agent handoff | 提供 Codex / Claude 风格的工作流元数据。 |

## 仓库内容

| 路径 | 用途 |
| --- | --- |
| `chrome-extension/` | Chrome Manifest V3 扩展源码。 |
| `scripts/` | 本地 receiver、计划、应用、验证、打包和安装辅助脚本。 |
| `agents/` | 面向 Codex / Claude 类工作流的 agent 元数据。 |
| `docs/` | 安装、隐私、权限、架构、公开路线和安全说明。 |
| `examples/basic-static-preview/` | 用于体验基础反馈闭环的静态示例页面。 |

## 设计原则

- **Local-first**：默认把反馈、预览和验证产物留在被审稿项目中。
- **先预览再修改**：不把浏览器反馈直接等同于源码修改。
- **不猜测模糊目标**：重复文案、缺少源码线索或定位不唯一时，明确降级为人工复核。
- **尊重项目结构**：样式反馈优先作为结构化建议，由当前项目的组件、样式和 token 体系决定落点。
- **面向 agent 协作**：让 AI coding agent 读到更接近源码语义的反馈，而不是只读截图描述。

## 未来演进方向

公开版本会优先围绕几个方向继续打磨：

- 更顺滑的首次安装和诊断体验。
- 更清晰的 preview / apply / verify 报告。
- 更多静态页面和常见前端框架示例。
- 更稳定的反馈 schema，方便不同 agent 和工具消费。
- 更好的设计系统适配，让样式反馈能靠近组件、变量和 token。
- 在明确授权和配置的前提下，探索团队协作与托管工作流。

这些方向会保持一个底线：默认不上传项目源码和审稿反馈，不把不确定的反馈伪装成确定的修改。

## 公开边界

这个公开仓库包含浏览器扩展、本地工作流脚本、agent 元数据、基础示例和公开文档。内部计划、私有发布流程、商业路线、提交材料、设计策略和敏感审稿材料单独维护。

## 相关文档

- [安装 / 访问](./docs/install.md)
- [隐私说明](./docs/privacy.md)
- [权限说明](./docs/permissions.md)
- [架构概览](./docs/architecture.md)
- [公开路线](./docs/public-roadmap.md)
- [安全说明](./docs/security.md)
- [常见问题](./docs/faq.md)

## 版权

Copyright © 2026 Visual Feedback Studio. All rights reserved.

除非未来版本加入明确的 license 文件，否则本仓库不授予开源许可。
