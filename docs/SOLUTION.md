# Remote Terminal MCP 问题解决方案

## 问题现象
Cursor显示"remote-terminal: 0 tools enabled"，但其他MCP服务器工作正常。

## 根本原因
MCP协议要求纯JSON通信，中文字符输出干扰了JSON-RPC协议解析。

## 解决步骤

### 1. 强制清理缓存
```bash
# 清理npm缓存
npm cache clean --force

# 清理npx缓存
npx clear-npx-cache

# 删除npx缓存目录
rm -rf ~/.npm/_npx
```

### 2. 重启Cursor
完全退出Cursor应用，然后重新启动。

### 3. 验证配置
确认 `~/.cursor/mcp.json` 配置正确：
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

### 4. 测试MCP服务器
运行以下命令验证服务器工作：
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | npx -y @xuyehua/remote-terminal-mcp@latest
```

应该返回JSON响应，不应该有任何中文输出。

### 5. 检查工具列表
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | npx -y @xuyehua/remote-terminal-mcp@latest
```

应该返回包含11个工具的JSON响应。

## 预期结果
- Cursor MCP工具面板显示"remote-terminal: 11 tools enabled"
- 可以使用以下工具：
  1. system_info
  2. run_command
  3. list_tmux_sessions
  4. create_tmux_session
  5. list_directory
  6. list_remote_servers
  7. test_server_connection
  8. execute_remote_command
  9. get_server_status
  10. refresh_server_connections
  11. establish_connection

## 故障排除

### 如果仍显示0个工具：
1. 检查Cursor MCP日志是否有错误
2. 确认网络连接正常
3. 尝试手动安装：`npm install -g @xuyehua/remote-terminal-mcp@latest`

### 如果看到中文输出：
说明NPX仍在使用缓存版本，请：
1. 等待5-10分钟让NPM传播
2. 重复清理缓存步骤
3. 重启Cursor

## 技术说明
- 最新版本：v0.2.11
- 修复内容：移除所有中文输出，确保MCP协议兼容性
- 依赖：chalk v4.1.2（已包含）

## 联系支持
如果问题仍然存在，请提供：
1. Cursor版本
2. 操作系统版本
3. MCP日志输出
4. 测试命令的完整输出 