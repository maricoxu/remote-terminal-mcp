# Remote Terminal MCP

> Ultra minimal MCP server for remote terminal management

![NPM Version](https://img.shields.io/npm/v/@xuyehua/remote-terminal-mcp)
![License](https://img.shields.io/npm/l/@xuyehua/remote-terminal-mcp)

## 🚀 Quick Start

```bash
# Use with npx (recommended)
npx @xuyehua/remote-terminal-mcp

# Or install globally
npm install -g @xuyehua/remote-terminal-mcp
remote-terminal-mcp
```

## 📱 Use with Cursor

Add to your `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["-y", "@xuyehua/remote-terminal-mcp"],
      "disabled": false
    }
  }
}
```

## 🛠️ Requirements

- **Node.js** >= 14.0.0
- **Python** >= 3.7.0

## 🧪 Test

```bash
npx @xuyehua/remote-terminal-mcp --test
```

## 🔧 Current Features (v0.2.0)

This version includes **real terminal management tools**:

- ✅ **System Information** - Get current system status and environment
- ✅ **Command Execution** - Run local commands with timeout control
- ✅ **Tmux Session Management** - List and create tmux sessions
- ✅ **Directory Listing** - Browse filesystem content
- ✅ **MCP Protocol Compliance** - Full JSON-RPC 2.0 support

### Available Tools

1. **`system_info`** - Get system information and current status
2. **`run_command`** - Execute local commands with working directory support
3. **`list_tmux_sessions`** - List current tmux sessions
4. **`create_tmux_session`** - Create new tmux sessions with custom working directory
5. **`list_directory`** - List directory contents with hidden file support

## 📝 Usage Examples

```python
# Get system information
{"tool": "system_info", "arguments": {}}

# Run a command
{"tool": "run_command", "arguments": {"command": "ls -la", "working_directory": "/tmp"}}

# List tmux sessions
{"tool": "list_tmux_sessions", "arguments": {}}

# Create new tmux session
{"tool": "create_tmux_session", "arguments": {"session_name": "dev", "working_directory": "/workspace"}}

# List directory
{"tool": "list_directory", "arguments": {"path": "/home", "show_hidden": true}}
```

## 🚀 Next Steps

Foundation for upcoming features:

1. **Remote SSH Management** - Connect to remote servers
2. **Connection Templates** - Pre-configured server connections  
3. **Session Persistence** - Maintain connections across restarts
4. **File Synchronization** - Sync files between local and remote

## 📄 License

MIT License

---

**Keep it simple, make it work** ✨