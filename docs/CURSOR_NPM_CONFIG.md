# Cursor NPM包配置指南

## 方法1: 本地下载配置（推荐）

1. 下载NPM包：
```bash
cd ~/Downloads
npm pack @xuyehua/remote-terminal-mcp@0.5.8
tar -xzf xuyehua-remote-terminal-mcp-0.5.8.tgz
```

2. 在Cursor的MCP配置中添加：
```json
{
  "mcpServers": {
    "remote-terminal-mcp-npm": {
      "command": "node",
      "args": ["/Users/你的用户名/Downloads/package/bin/cli.js"],
      "description": "🖥️ Remote Terminal MCP (NPM Package)"
    }
  }
}
```

## 方法2: 全局安装配置

1. 全局安装包：
```bash
npm install -g @xuyehua/remote-terminal-mcp@0.5.8
```

2. 找到全局安装路径：
```bash
npm root -g
# 通常是 /usr/local/lib/node_modules 或 ~/.npm-global/lib/node_modules
```

3. 在Cursor配置中使用：
```json
{
  "mcpServers": {
    "remote-terminal-mcp-npm": {
      "command": "node",
      "args": ["/usr/local/lib/node_modules/@xuyehua/remote-terminal-mcp/bin/cli.js"],
      "description": "🖥️ Remote Terminal MCP (NPM Package)"
    }
  }
}
```

## 验证配置

配置完成后，重启Cursor，你应该能看到：
- ✅ 绿色状态指示器
- 🖥️ 5个可用工具：
  - `list_servers` - 列出服务器
  - `connect_server` - 连接服务器  
  - `execute_command` - 执行命令
  - `get_server_status` - 获取状态
  - `run_local_command` - 本地命令

## 优势

- ✅ **版本控制**：可以指定具体版本
- ✅ **自动更新**：通过npm更新到最新版本
- ✅ **依赖管理**：NPM自动处理依赖
- ✅ **跨平台**：在任何支持Node.js的系统上工作 