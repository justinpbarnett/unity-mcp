### macOS: Claude CLI fails to start (dyld ICU library not loaded)

- Symptoms
  - MCP For Unity error: “Failed to start Claude CLI. dyld: Library not loaded: /usr/local/opt/icu4c/lib/libicui18n.71.dylib …”
  - Running `claude` in Terminal fails with missing `libicui18n.xx.dylib`.

- Cause
  - Homebrew Node (or the `claude` binary) was linked against an ICU version that’s no longer installed; dyld can’t find that dylib.

- Fix options (pick one)
  - Reinstall Homebrew Node (relinks to current ICU), then reinstall CLI:
    ```bash
    brew update
    brew reinstall node
    npm uninstall -g @anthropic-ai/claude-code
    npm install -g @anthropic-ai/claude-code
    ```
  - Use NVM Node (avoids Homebrew ICU churn):
    ```bash
    nvm install --lts
    nvm use --lts
    npm install -g @anthropic-ai/claude-code
    # MCP For Unity → Claude Code → Choose Claude Location → ~/.nvm/versions/node/<ver>/bin/claude
    ```
  - Use the native installer (puts claude in a stable path):
    ```bash
    # macOS/Linux
    curl -fsSL https://claude.ai/install.sh | bash
    # MCP For Unity → Claude Code → Choose Claude Location → /opt/homebrew/bin/claude or ~/.local/bin/claude
    ```

- After fixing
  - In MCP For Unity (Claude Code), click “Choose Claude Location” and select the working `claude` binary, then Register again.

- More details
  - See: Troubleshooting MCP For Unity and Claude Code

---

### FAQ (Claude Code)

- Q: Unity can’t find `claude` even though Terminal can.
  - A: macOS apps launched from Finder/Hub don’t inherit your shell PATH. In the MCP For Unity window, click “Choose Claude Location” and select the absolute path (e.g., `/opt/homebrew/bin/claude` or `~/.nvm/versions/node/<ver>/bin/claude`).

- Q: I installed via NVM; where is `claude`?
  - A: Typically `~/.nvm/versions/node/<ver>/bin/claude`. Our UI also scans NVM versions and you can browse to it via “Choose Claude Location”.

- Q: The Register button says “Claude Not Found”.
  - A: Install the CLI or set the path. Click the orange “[HELP]” link in the MCP For Unity window for step‑by‑step install instructions, then choose the binary location.


