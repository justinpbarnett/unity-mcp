# Unity MCP ✨

**Connect your Unity Editor to LLMs using the Model Context Protocol.**

Unity MCP acts as a bridge, allowing AI assistants (like Claude, Cursor) to interact directly with your Unity Editor via a local **MCP (Model Context Protocol) Client**. Give your LLM tools to manage assets, control scenes, edit scripts, and automate tasks within Unity.

---

## <picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/justinpbarnett/unity-mcp/assets/11047284/c279675a-dd58-406b-9613-5b16b5c6bb63"><source media="(prefers-color-scheme: light)" srcset="https://github.com/justinpbarnett/unity-mcp/assets/11047284/b54f891d-961b-4048-a9c4-3af46e2a52fc"><img alt="UnityMCP Workflow" width="100%" style="max-width: 600px; display: block; margin-left: auto; margin-right: auto;"></picture>

## Key Features 🚀

*   **🗣️ Natural Language Control:** Instruct your LLM to perform Unity tasks.
*   **🛠️ Powerful Tools:** Manage assets, scenes, materials, scripts, and editor functions.
*   **🤖 Automation:** Automate repetitive Unity workflows.
*   **🧩 Extensible:** Designed to work with various MCP Clients.

<details>
  <summary><strong>Expand for Available Tools...</strong></summary>

  Your LLM can use functions like:

  *   `read_console`: Gets messages from or clears the console.
  *   `manage_script`: Manages C# scripts (create, read, update, delete).
  *   `manage_editor`: Controls and queries the editor's state and settings.
  *   `manage_scene`: Manages scenes (load, save, create, get hierarchy, etc.).
  *   `manage_asset`: Performs asset operations (import, create, modify, delete, etc.).
  *   `manage_gameobject`: Manages GameObjects: create, modify, delete, find, and component operations.
  *   `execute_menu_item`: Executes a menu item via its path (e.g., "File/Save Project").
</details>

---

## How It Works 🤔

Unity MCP connects your tools using two components:

1.  **Unity MCP Bridge:** A Unity package running inside the Editor. (Installed via Package Manager).
2.  **Unity MCP Server:** A Python server that runs locally, communicating between the Unity Bridge and your MCP Client. (Installed manually).

**Flow:** `[Your LLM via MCP Client] <-> [Unity MCP Server (Python)] <-> [Unity MCP Bridge (Unity Editor)]`

---

## Installation ⚙️

> **Note:** The setup is constantly improving as we update the package. Check back if you randomly start to run into issues.

### Prerequisites

<details>
  <summary><strong>Click to view required software...</strong></summary>

  *   **Git CLI:** For cloning the server code. [Download Git](https://git-scm.com/downloads)
  *   **Python:** Version 3.12 or newer. [Download Python](https://www.python.org/downloads/)
  *   **Unity Hub & Editor:** Version 2020.3 LTS or newer. [Download Unity](https://unity.com/download)
  *   **uv (Python package manager):**
      ```bash
      pip install uv
      # Or see: https://docs.astral.sh/uv/getting-started/installation/
      ```
  *   **An MCP Client:**
      *   [Claude Desktop](https://claude.ai/download)
      *   [Cursor](https://www.cursor.com/en/downloads)
      *   *(Others may work with manual config)*
</details>

### Step 1: Install the Unity Package (Bridge)

1.  Open your Unity project.
2.  Go to `Window > Package Manager`.
3.  Click `+` -> `Add package from git URL...`.
4.  Enter:
    ```
    https://github.com/justinpbarnett/unity-mcp.git?path=/UnityMcpBridge
    ```
5.  Click `Add`.
6. The MCP Server should automatically be installed onto your machine as a result of this process.

### Step 2: Configure Your MCP Client

Connect your MCP Client (Claude, Cursor, etc.) to the Python server you installed in Step 1.

**Option A: Auto-Configure (Recommended for Claude/Cursor)**

1.  In Unity, go to `Window > Unity MCP`.
2.  Click `Auto Configure Claude` or `Auto Configure Cursor`.
3.  Look for a green status indicator 🟢 and "Connected". *(This attempts to modify the MCP Client's config file automatically)*.

**Option B: Manual Configuration**

If Auto-Configure fails or you use a different client:

1.  **Find your MCP Client's configuration file.** (Check client documentation).
    *   *Claude Example (macOS):* `~/Library/Application Support/Claude/claude_desktop_config.json`
    *   *Claude Example (Windows):* `%APPDATA%\Claude\claude_desktop_config.json`
2.  **Edit the file** to add/update the `mcpServers` section, using the *exact* paths from Step 1.

<details>
<summary><strong>Click for OS-Specific JSON Configuration Snippets...</strong></summary>

**Windows:**

  ```json
  {
    "mcpServers": {
      "UnityMCP": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\UnityMCP\\UnityMcpServer\\src",
          "server.py"
        ]
      }
      // ... other servers might be here ...
    }
  }
``` 

(Remember to replace YOUR_USERNAME and use double backslashes \\)

**macOS:**

```json
{
  "mcpServers": {
    "UnityMCP": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/usr/local/bin/UnityMCP/UnityMcpServer/src",
        "server.py"
      ]
    }
    // ... other servers might be here ...
  }
}
```
(Replace YOUR_USERNAME if using ~/bin)

**Linux:**

```json
{
  "mcpServers": {
    "UnityMCP": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/YOUR_USERNAME/bin/UnityMCP/UnityMcpServer/src",
        "server.py"
      ]
    }
    // ... other servers might be here ...
  }
}
```

(Replace YOUR_USERNAME)

</details>

---

## Usage ▶️

1. **Open your Unity Project.** The Unity MCP Bridge (package) should connect automatically. Check status via Window > Unity MCP.
    
2. **Start your MCP Client** (Claude, Cursor, etc.). It should automatically launch the Unity MCP Server (Python) using the configuration from Installation Step 3.
    
3. **Interact!** Unity tools should now be available in your MCP Client.
    
    Example Prompt: `Create a 3D player controller.`
    

---

## Contributing 🤝

Help make Unity MCP better!

1. **Fork** the main repository.
    
2. **Create a branch** (`feature/your-idea` or `bugfix/your-fix`).
    
3. **Make changes.**
    
4. **Commit** (feat: Add cool new feature).
    
5. **Push** your branch.
    
6. **Open a Pull Request** against the master branch.
    

---

## Troubleshooting ❓

<details>  
<summary><strong>Click to view common issues and fixes...</strong></summary>  

- **Unity Bridge Not Running/Connecting:**
    
    - Ensure Unity Editor is open.
        
    - Check the status window: Window > Unity MCP.
        
    - Restart Unity.
        
- **MCP Client Not Connecting / Server Not Starting:**
    
    - **Verify Server Path:** Double-check the --directory path in your MCP Client's JSON config. It must exactly match the location where you cloned the UnityMCP repository in Installation Step 1 (e.g., .../Programs/UnityMCP/UnityMcpServer/src).
        
    - **Verify uv:** Make sure uv is installed and working (pip show uv).
        
    - **Run Manually:** Try running the server directly from the terminal to see errors: `# Navigate to the src directory first! cd /path/to/your/UnityMCP/UnityMcpServer/src uv run server.py`
        
    - **Permissions (macOS/Linux):** If you installed the server in a system location like /usr/local/bin, ensure the user running the MCP client has permission to execute uv and access files there. Installing in ~/bin might be easier.
        
- **Auto-Configure Failed:**
    
    - Use the Manual Configuration steps. Auto-configure might lack permissions to write to the MCP client's config file.
        

</details>  

Still stuck? [Open an Issue](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2Fjustinpbarnett%2Funity-mcp%2Fissues).

---

## Resources 

<details>
<summary><b>Open MCP Marketplace API Support</b></summary>

![MCP Marketplace User Review Rating Badge](http://www.deepnlp.org/api/marketplace/svg?justinpbarnett/unity-mcp)|[Reviews](http://www.deepnlp.org/store/ai-agent/mcp-server/pub-justinpbarnett/unity-mcp)|[GitHub](https://github.com/AI-Agent-Hub/mcp-marketplace)|[Doc](http://www.deepnlp.org/doc/mcp_marketplace)|[MCP Marketplace](http://www.deepnlp.org/store/ai-agent/mcp-server)

Allow AI/Agent/LLM to find this MCP Server via common python/typescript API, search and explore relevant servers and tools

***Example: Search Server and Tools***
```python
import anthropic
import mcp_marketplace as mcpm

result_q = mcpm.search(query="unity mcp", mode="list", page_id=0, count_per_page=100, config_name="deepnlp") # search server by category choose various endpoint
result_id = mcpm.search(id="justinpbarnett/unity-mcp", mode="list", page_id=0, count_per_page=100, config_name="deepnlp")      # search server by id choose various endpoint 
tools = mcpm.list_tools(id="justinpbarnett/unity-mcp", config_name="deepnlp_tool")
# Call Claude to Choose Tools Function Calls 
# client = anthropic.Anthropic()
# response = client.messages.create(model="claude-opus-4-20250514", max_tokens=1024, tools=tools, messages=[])
```

</details>


## License 📜

MIT License. See [LICENSE](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2Fjustinpbarnett%2Funity-mcp%2Fblob%2Fmaster%2FLICENSE) file.

---

## Contact 👋

- **X/Twitter:** [@justinpbarnett](https://www.google.com/url?sa=E&q=https%3A%2F%2Fx.com%2Fjustinpbarnett)
    

---

## Acknowledgments 🙏

Thanks to the contributors and the Unity team.
