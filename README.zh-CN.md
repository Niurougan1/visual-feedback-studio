<p align="center">
  <img src="./Logo.svg" width="88" alt="Visual Feedback Studio 标志" />
</p>

<h1 align="center">Visual Feedback Studio</h1>

<p align="center">
  <strong>浏览器里收反馈，源码里做修改。</strong>
</p>

<p align="center">
  <code>local-first</code> · <code>Chrome MV3</code> · <code>Codex / Claude</code> · <code>可视化审稿工作流</code>
</p>

<p align="center">
  <a href="./README.md">English</a>
</p>

---

Visual Feedback Studio 是一个 local-first 的浏览器可视化审稿工作流。审稿者可以直接在运行中的页面上标记文案、样式和备注反馈，工具会保存结构化反馈，让 AI 辅助开发流程继续预览、应用并验证源码修改。

这个公开仓库包含浏览器扩展、本地工作流脚本、agent 集成元数据、基础示例和公开文档。

内部计划、私有发布流程、商业路线图、提交材料、设计策略和敏感审稿材料单独维护。

## 为什么需要它

可视化审稿变慢，通常是因为反馈要经过截图、聊天、issue 长文和记忆转述。Visual Feedback Studio 把这条链路缩短为：

```text
打开页面 -> 标记反馈 -> 保存结构化 JSON -> 预览源码修改 -> 应用 -> 验证
```

工作流默认保持保守：只有源码目标可证明时才自动应用文案修改；样式修改默认作为带源码线索的结构化建议处理，除非目标可以安全解析。

## 仓库内容

| 路径 | 用途 |
| --- | --- |
| `chrome-extension/` | Chrome Manifest V3 扩展源码。 |
| `scripts/` | 本地 receiver、计划、应用、验证、打包和安装辅助脚本。 |
| `agents/` | Codex 和 Claude 类工作流的 agent 集成元数据。 |
| `docs/` | 公开安装、隐私、权限、架构、路线和安全说明。 |
| `examples/basic-static-preview/` | 用于尝试浏览器反馈闭环的基础静态示例。 |

## 快速开始

1. 为本地项目运行 setup：

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

2. 加载 Chrome 扩展：

```text
chrome://extensions/ -> Developer mode -> Load unpacked
```

选择本仓库的 `chrome-extension/` 目录。

3. 打开你有权限审稿的页面，启动 Visual Feedback Studio，采集反馈并保存。

4. 预览工作流能安全解析的修改：

```bash
python3 scripts/vfs.py plan /path/to/your-project
```

更多说明见 [安装 / 访问](./docs/install.md)。

## 隐私模型

默认工作流是 local-first。反馈、预览状态和验证产物默认保存在被审稿项目中，除非你明确配置托管或团队工作流。

详见 [隐私说明](./docs/privacy.md) 和 [权限说明](./docs/permissions.md)。

## 状态

这是一个公开项目分发仓库。部分计划文档、私有发布流程、高级内部实验和商业材料不会发布在这里。

## 版权

Copyright © 2026 Visual Feedback Studio. All rights reserved.

除非未来版本加入明确的 license 文件，否则本仓库不授予开源许可。
