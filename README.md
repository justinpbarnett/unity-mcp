# Unity MCP Package

| [English](README.md) | [🇨🇳简体中文](README_zh-CN.md) |
|----------------------|---------------------------------|

A Unity package that enables seamless communication between Unity and Large Language Models (LLMs) like Claude Desktop via the **Model Context Protocol (MCP)**. This server acts as a bridge, allowing Unity to send commands to and receive responses from MCP-compliant tools, empowering developers to automate workflows, manipulate assets, and control the Unity Editor programmatically.

Welcome to the initial release of this open-source project! Whether you're looking to integrate LLMs into your Unity workflow or contribute to an exciting new tool, I appreciate you taking the time to check it out!

## Overview

The Unity MCP Server provides a bidirectional communication channel between Unity (via C#) and a Python server, enabling:

- **Asset Management**: Create, import, and manipulate Unity assets programmatically.
- **Scene Control**: Manage scenes, objects, and their properties.
- **Material Editing**: Modify materials and their properties.
- **Script Integration**: View, create, and update Unity scripts.
- **Editor Automation**: Control Unity Editor functions like undo, redo, play, and build.

This project is perfect for developers who want to leverage LLMs to enhance their Unity projects or automate repetitive tasks.

## Installation

To use the Unity MCP Package, ensure you have the following installed:

- **Unity 2020.3 LTS or newer** (⚠️ Currently only works in URP projects)
- **Python 3.12 or newer**
- **uv package manager**

### Step 1: Install Python

Download and install Python 3.12 or newer from [python.org](https://www.python.org/downloads/). Make sure to add Python to your system’s PATH during installation.

### Step 2: Install uv

uv is a Python package manager that simplifies dependency management. Install it using the command below based on your operating system:

- **Mac**:

  ```bash
  brew install uv
  ```

- **Windows**:

  ```bash
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

  Then, add uv to your PATH:

  ```bash
  set Path=%USERPROFILE%\.local\bin;%Path%
  ```

- **Linux**:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

For alternative installation methods, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

**Important**: Do not proceed without installing uv.

### Step 3: Install the Unity Package

1. Open Unity and go to `Window > Package Manager`.
2. Click the `+` button and select `Add package from git URL`.
3. Enter: `https://github.com/justinpbarnett/unity-mcp.git`

Once installed, the Unity MCP Package will be available in your Unity project. The server will start automatically when used with an MCP client like Claude Desktop or Cursor.

## Features

- **Bidirectional Communication**: Seamlessly send and receive data between Unity and LLMs.
- **Asset Management**: Import assets, instantiate prefabs, and create new prefabs programmatically.
- **Scene Control**: Open, save, and modify scenes, plus create and manipulate game objects.
- **Material Editing**: Apply and modify materials with ease.
- **Script Integration**: Create, view, and update C# scripts within Unity.
- **Editor Automation**: Automate Unity Editor tasks like building projects or entering play mode.

## Contributing

I’d love your help to make the Unity MCP Server even better! Here’s how to contribute:

1. **Fork the Repository**  
   Fork [github.com/justinpbarnett/unity-mcp](https://github.com/justinpbarnett/unity-mcp) to your GitHub account.

2. **Create a Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

   or

   ```bash
   git checkout -b bugfix/your-bugfix-name
   ```

3. **Make Changes**  
   Implement your feature or fix.

4. **Commit and Push**  
   Use clear, descriptive commit messages:

   ```bash
   git commit -m "Add feature: your feature description"
   git push origin feature/your-feature-name
   ```

5. **Submit a Pull Request**  
   Open a pull request to the `master` branch with a description of your changes.

## License

This project is licensed under the **MIT License**. Feel free to use, modify, and distribute it as you see fit. See the full license [here](https://github.com/justinpbarnett/unity-mcp/blob/master/LICENSE).

## Troubleshooting

Encountering issues? Try these fixes:

- **Unity Bridge Not Running**  
  Ensure the Unity Editor is open and the MCP window is active. Restart Unity if needed.

- **Python Server Not Connected**  
  Verify that Python and uv are correctly installed and that the Unity MCP package is properly set up.

- **Configuration Issues with Claude Desktop or Cursor**  
  Ensure your MCP client is configured to communicate with the Unity MCP server.

For more help, visit the [issue tracker](https://github.com/justinpbarnett/unity-mcp/issues) or file a new issue.

## Contact

Have questions or want to chat about the project? Reach out!

- **X**: [@justinpbarnett](https://x.com/justinpbarnett)

## Acknowledgments

A huge thanks to everyone who’s supported this project’s initial release. Special shoutout to Unity Technologies for their excellent Editor API.

Happy coding, and enjoy integrating LLMs with Unity!
