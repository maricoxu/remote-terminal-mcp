# Cursor MCP 集成修复文档

## 问题描述

在尝试将 remote-terminal-mcp 服务器集成到 Cursor 编辑器时，遇到了以下问题：

- Cursor 中显示 `remote-terminal` 状态为红色 🔴
- 显示 `0 tools enabled`
- MCP Logs 中出现 `No server info found` 错误

## 根本原因分析

通过系统性调试，发现了三个关键问题：

### 1. SSH Manager 方法兼容性问题
- **问题**: `mcp_server.py` 中调用了不存在的方法如 `list_tools()`, `execute_tool()`
- **根因**: SSH Manager 实际方法为 `list_servers()`, `execute_command()` 等
- **影响**: 导致 AttributeError 崩溃

### 2. MCP 协议版本不匹配
- **问题**: Cursor 请求协议版本 `2025-03-26`，服务器返回 `2024-11-05`
- **根因**: 硬编码的协议版本与 Cursor 期望不符
- **影响**: 协议握手失败

### 3. 通知处理错误
- **问题**: `notifications/initialized` 被错误地返回错误响应
- **根因**: 通知应该不返回响应，但服务器将其作为未知方法处理
- **影响**: 干扰 MCP 协议通信

## 解决方案

### 1. 修复 SSH Manager 方法调用

**修改前**:
```python
# 错误的方法调用
manager.list_tools()
manager.execute_tool()
```

**修改后**:
```python
# 使用实际存在的方法
manager.list_servers()
manager.execute_command(server_name, command)
manager.simple_connect(server_name)
manager.get_server_status(server_name)
```

### 2. 实现动态协议版本匹配

**修改前**:
```python
"protocolVersion": "2024-11-05"  # 硬编码版本
```

**修改后**:
```python
# 动态使用客户端请求的版本
client_protocol_version = request.get('params', {}).get('protocolVersion', '2024-11-05')
"protocolVersion": client_protocol_version
```

### 3. 正确处理通知

**修改前**:
```python
# 将通知作为错误处理
else:
    return {"error": {"code": -1, "message": f"未知方法: {method}"}}
```

**修改后**:
```python
elif method == 'notifications/initialized':
    logger.info("处理notifications/initialized通知")
    return None  # 通知不需要响应
```

### 4. 优化大数据响应处理

为避免 SSH Manager 返回的大量服务器配置数据导致通信阻塞：

```python
# 只返回关键信息，避免大数据量
simple_servers = []
for server in servers:
    simple_servers.append({
        'name': server.get('name', ''),
        'description': server.get('description', ''),
        'connected': server.get('connected', False),
        'type': server.get('type', '')
    })
```

## 测试验证

### 1. 单元测试
创建了多个测试脚本验证修复效果：

- `test_cursor_compatible_v2.py`: 流式读取兼容性测试
- `test_cursor_real_protocol.py`: 完整 Cursor 协议模拟测试

### 2. 协议测试结果

```
🚀 测试真实的Cursor MCP协议...

=== 1. Cursor初始化请求 ===
✅ 初始化成功
   服务器: remote-terminal-mcp v1.0.0-debug
   协议版本: 2025-03-26

=== 2. Cursor初始化完成通知 ===
✅ 通知处理成功

=== 3. Cursor工具列表请求 ===
✅ 获取到 5 个工具
```

### 3. Cursor 集成测试
- ✅ Cursor 中显示绿色状态 🟢
- ✅ 显示 `5 tools enabled`
- ✅ 所有工具正常可用

## 调试工具

### mcp_server_debug.py
创建了带详细日志的调试版本，特性包括：

- 详细的请求/响应日志记录
- 文件和控制台双重日志输出
- 完整的错误堆栈跟踪
- 协议版本信息记录

### 日志分析
通过日志文件 `/tmp/mcp_server_debug.log` 可以详细追踪：

- 每个请求的处理过程
- 协议版本协商过程
- 工具调用的参数和结果
- 错误发生的具体位置

## 文件结构

```
python/
├── mcp_server.py          # 主要 MCP 服务器（修复版）
├── mcp_server_debug.py    # 调试版本（带详细日志）
└── ssh_manager.py         # SSH 管理器（未修改）

tests/
├── test_cursor_compatible_v2.py    # 兼容性测试
└── test_cursor_real_protocol.py    # 协议测试

docs/
├── NPM_DEBUGGING_LOG.md           # NPM 调试记录
└── CURSOR_INTEGRATION_FIX.md      # 本文档
```

## 使用方法

### 1. 在 Cursor 中配置

修改 `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "python3",
      "args": [
        "/Users/你的用户名/Code/remote-terminal-mcp/python/mcp_server.py"
      ],
      "env": {
        "FORCE_COLOR": "true"
      }
    }
  }
}
```

### 2. 调试模式

如需调试，可使用调试版本：

```json
"args": [
  "/Users/你的用户名/Code/remote-terminal-mcp/python/mcp_server_debug.py"
]
```

### 3. 验证安装

重启 Cursor 后，在 Tools & Integrations 中应该看到：
- `remote-terminal` 显示绿色状态 🟢
- 显示 `5 tools enabled`

## 技术要点

### MCP 协议版本兼容性
- Cursor 使用较新的协议版本 `2025-03-26`
- 服务器应该动态适配客户端版本
- 版本不匹配会导致整个连接失败

### 通知 vs 请求的区别
- 请求 (Request): 需要返回响应
- 通知 (Notification): 不需要返回响应
- 错误处理通知会干扰协议通信

### 大数据响应优化
- SSH Manager 返回的完整服务器配置数据量巨大
- 需要提取关键信息避免通信阻塞
- 使用流式读取处理大响应

## 后续维护

1. **定期测试**: 使用提供的测试脚本验证功能
2. **日志监控**: 定期查看调试日志发现潜在问题
3. **协议更新**: 关注 MCP 协议版本更新
4. **错误处理**: 继续完善边界条件处理

## 贡献者

此次修复通过系统性调试方法完成，展示了：
- 问题分解与根因分析
- 协议兼容性调试
- 结构化测试验证
- 完整的文档记录

---

*最后更新: 2025-06-12*
*状态: ✅ 修复完成，Cursor 集成正常工作* 