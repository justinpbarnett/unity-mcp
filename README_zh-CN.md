# Unity MCP Package

> 当前页面为中文版本

| [English](README.md) | [🇨🇳简体中文](README_zh-CN.md) |
|----------------------|---------------------------------|

这是一个 Unity MCP Package，通过**模型上下文协议（MCP）**实现 Unity 与大语言模型（如 Claude Desktop）之间的无缝通信。MCP 服务器作为桥梁，允许 Unity 向 MCP 兼容的工具发送命令并接收响应，使得开发者能够自动化工作流、操作资源(Assets)并自动控制 Unity 编辑器。

欢迎使用这个开源项目的初始版本！无论您是想要将 LLM 集成到 Unity 工作流程中，还是想要为这个令人兴奋的新工具做出贡献，我都感谢您花时间查看这个项目！

## 概述

Unity MCP 服务器在 Unity（C#）和 Python 服务器之间提供双向通信通道，支持：

- **资源管理**：自动创建、导入和使用 Unity 资源。
- **场景控制**：管理场景、对象及其属性。
- **材质编辑**：修改材质及其属性。
- **脚本交互**：查看、创建和修改 Unity 脚本。
- **自动化Editor**：控制 Unity 编辑器功能，如撤销、重做、播放和打包Build。

这个项目非常适合想要利用 LLM 在 Unity 项目或自动化重复任务中增加开发效率的开发者。

## 安装

要使用 Unity MCP Package，请确保安装以下内容：

- **Unity 2020.3 LTS 或更新版本**（⚠️ 目前仅适用于 URP 项目）
- **Python 3.12 或更新版本**
- **uv package manager**

### 步骤 1：安装 Python

从 [python.org](https://www.python.org/downloads/) 下载并安装 Python 3.12 或更新版本。安装时请确保将 Python 添加到系统的 PATH 中。

### 步骤 2：安装 uv

uv 是一个简化依赖管理的 Python 包管理器。根据您的操作系统使用以下命令安装：

- **Mac**：

  ```bash
  brew install uv
  ```

- **Windows**：

  ```bash
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

  然后，将 uv 包管理器添加到 PATH：

  ```bash
  set Path=%USERPROFILE%\.local\bin;%Path%
  ```

- **Linux**：

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

有关其他安装方法，请参阅 [uv 安装指南（英文）](https://docs.astral.sh/uv/getting-started/installation/)。

**重要提示**：请勿在未安装 uv 的情况下继续下文的操作。

### 步骤 3：安装 Unity 包

1. 打开 Unity 并转到 `Window > Package Manager`。
2. 点击 `+` 按钮，选择 `Add package from git URL`。
3. 输入：`https://github.com/justinpbarnett/unity-mcp.git`

安装完成后，Unity MCP Package 将可以应用在您的 Unity 项目中。当与 Claude Desktop 或 Cursor 等 MCP 客户端一起使用时，服务器将自动启动。

## 功能

- **双向通信**：在 Unity 和 LLM 之间无缝发送和接收数据。
- **资源管理**：自动创建、导入和使用 Unity 资源。
- **场景控制**：管理场景、对象及其属性。
- **材质编辑**：修改材质及其属性。
- **脚本交互**：查看、创建和修改 Unity 脚本。
- **自动化Editor**：控制 Unity 编辑器功能，如撤销、重做、播放和打包Build。

## 贡献

我很乐意得到您的帮助，让 Unity MCP 服务器变得更好！以下是贡献方式：

1. **Fork 仓库**  
   将 [github.com/justinpbarnett/unity-mcp](https://github.com/justinpbarnett/unity-mcp) Fork 到您的 GitHub 账户。

2. **创建分支**

   ```bash
   git checkout -b feature/your-feature-name
   ```

   或

   ```bash
   git checkout -b bugfix/your-bugfix-name
   ```

3. **进行更改**  
   实现您的功能或修复。

4. **提交和推送**  
   使用清晰、描述性的提交消息：

   ```bash
   git commit -m "Add feature: your feature description"
   git push origin feature/your-feature-name
   ```

5. **提交拉取请求**  
   向 `master` 分支提交Pull Requst，并描述您的更改。

## 许可证

本项目采用 **MIT 许可证**。您可以自由使用、修改和分发它。查看完整许可证[点击此处](https://github.com/justinpbarnett/unity-mcp/blob/master/LICENSE)。

## 排除故障

遇到问题？请尝试以下解决方案：

- **Unity Bridge 未运行**
  确保 Unity 编辑器已打开且 MCP 窗口处于活动状态。必要时，请重启 Unity。

- **Python 服务器未连接**
  验证 Python 和 uv 是否正确安装，以及 Unity MCP Package 是否正确设置。

- **Claude Desktop 或 Cursor 配置问题**
  确保配置了 MCP 客户端与 Unity MCP 服务器的通信。

如需更多帮助，请访问[issue tracker](https://github.com/justinpbarnett/unity-mcp/issues)或提交新 issue。

## 联系方式

有问题或想讨论项目？请联系我！

- **X**：[@justinpbarnett](https://x.com/justinpbarnett)

## 致谢

非常感谢所有支持这个项目初始发布的人。特别感谢 Unity Technologies 提供的出色的 Editor API。

祝您编码愉快，享受将 LLM 与 Unity 交互的乐趣！
