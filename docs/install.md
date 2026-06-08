# 安装 / 访问

[English](./install.en.md)

Visual Feedback Studio 可以作为 Chrome Manifest V3 扩展本地加载，并配合本仓库里的本地工作流脚本使用。

## 本地 setup

对你要审稿的项目运行 setup：

```bash
python3 scripts/setup.py /path/to/your-project --channel beta
```

setup 输出会包含扩展加载路径和本地工作流状态。

## 加载 Chrome 扩展

打开 Chrome 扩展管理页：

```text
chrome://extensions/
```

开启 Developer mode，选择 “Load unpacked”，然后选择本仓库的 `chrome-extension/` 目录。

同一时间只保留一个 Visual Feedback Studio unpacked 扩展。如果你之前加载过打包版本或旧的本地副本，测试前先移除重复入口。

## 第一轮审稿闭环

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
