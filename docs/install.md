# 安装 / 访问

[English](./install.en.md)

Visual Feedback Studio 可以作为 Chrome Manifest V3 扩展本地加载，并配合本仓库里的本地工作流脚本使用。

## 一行安装

在你要审稿的本地项目根目录运行：

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | bash
```

这条命令会先检查 `python3`、`git` 和 `node`，然后拉取/更新公开仓、安装本地 workflow、启动 receiver，并输出 Chrome 扩展加载路径。命令会用 `[vfs]` 前缀打印每一步进度。

如果 setup 失败，看最后 JSON 里的：

- `error`：失败类型。
- `next_step`：下一步处理建议。
- `receiver.log_tail`：receiver 启动日志末尾，端口占用或本地权限阻止会直接出现在这里。

如果 `3456` 端口已被其他本地 receiver 占用，可以换端口：

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_PORT=3463 bash
```

如果仓库已经安装过，只想复用/更新 receiver：

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_INSTALL_MODE=none VFS_PORT=3463 bash
```

如果远程 preview URL 需要写入本地 receiver，显式允许一个 origin：

```bash
curl -fsSL https://raw.githubusercontent.com/Niurougan1/visual-feedback-studio/main/scripts/install.sh | VFS_ALLOWED_ORIGIN=https://your-preview-origin VFS_PORT=3463 bash
```

已经 clone 本仓库时，也可以直接运行：

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

## 加载 Chrome 扩展

打开 Chrome 扩展管理页：

```text
chrome://extensions/
```

开启 Developer mode，选择 “Load unpacked”，然后选择本仓库的 `chrome-extension/` 目录。

同一时间只保留一个 Visual Feedback Studio unpacked 扩展。如果你之前加载过打包版本或旧的本地副本，测试前先移除重复入口。

## 第一轮审稿闭环

如果你只想先验证工具是否能跑，可以打开 `examples/basic-static-preview/index.html`，或用任意静态文件服务器预览 `examples/basic-static-preview/`。

1. 打开你有权限审稿的页面。
2. 点击 Visual Feedback Studio 扩展。
3. 当 Chrome 请求当前站点访问权限时，确认授权。
4. 采集文案、样式或备注反馈。
5. 保存反馈。
6. 预览源码解析结果：

```bash
python3 scripts/vfs.py plan /path/to/your-project
```

## 本地文件页面

Chrome 会单独管理 `file://` 页面的扩展访问权限。如果你要审稿本地 HTML 文件，请打开扩展详情页并启用 file URL access。

## 公开 / 私有边界

这个公开仓库包含核心本地审稿闭环和公开文档。内部计划、商业材料、私有发布流程和敏感审稿记录单独维护。
