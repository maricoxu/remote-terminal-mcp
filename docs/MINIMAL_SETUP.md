# 🚀 Remote Terminal MCP - 最小配置快速开始

> 15分钟内让你的MCP服务跑起来！

## ✅ 当前状态

你的Remote Terminal MCP服务已经配置完成并可以正常使用！

### 📋 已完成配置

- ✅ **MCP服务器**: 已在 `~/.cursor/mcp.json` 中配置
- ✅ **本地测试环境**: 3个本地服务器配置
- ✅ **tmux会话**: 已创建测试会话
- ✅ **功能验证**: 基本功能测试通过

## 🛠️ 可用功能

### 1. 列出服务器
在Cursor中询问：
```
"列出所有服务器"
```

### 2. 查看tmux会话  
```
"显示所有tmux会话"
```

### 3. 执行命令
```
"在default会话中执行 ls -la"
"在dev会话中运行 python --version"
```

### 4. 获取服务器信息
```
"获取local_default服务器的详细信息"
```

## 🔧 当前配置

### 本地服务器列表
- `local_default`: 本地默认会话
- `local_dev`: 本地开发会话  
- `local_test`: 本地测试会话

### 可用tmux会话
- `default`: 默认会话
- `dev`: 开发会话
- `test`: 测试会话

## 🚀 扩展配置

### 添加真实远程服务器

编辑 `~/.cursor-bridge/servers.yaml`，添加你的服务器：

```yaml
servers:
  # 保留现有本地配置...
  
  # 添加你的远程服务器
  my_gpu_server:
    name: 我的GPU服务器
    host: your-server.com
    jump_host: jumphost.com  # 如果需要跳板机
    container_name: your_container
    gpu_type: Tesla A100
    gpu_count: 8
    series: GPU
    location: 数据中心
    status: active
```

### 修改默认设置

编辑 `~/.cursor-bridge/config.yaml`：

```yaml
settings:
  default_tmux_session: default
  auto_create_session: true
  debug_mode: true  # 开启调试信息
```

## 🧪 测试步骤

1. **重启Cursor编辑器**
2. **测试基本功能**：
   - "列出所有服务器"
   - "显示tmux会话"
   - "在default会话中执行date"

3. **验证输出**：
   - 应该看到3台本地服务器
   - 应该看到已创建的tmux会话
   - 命令应该正常执行

## 🔍 故障排除

### 如果MCP服务无法启动
```bash
# 手动测试
cd /Users/xuyehua/Code/remote-terminal-mcp
MCP_DEBUG=1 node index.js --test
```

### 如果找不到tmux会话
```bash
# 重新创建会话
tmux new-session -d -s default
tmux new-session -d -s dev  
tmux new-session -d -s test
```

### 查看调试信息
MCP服务已启用调试模式，在Cursor的开发者工具中可以看到详细日志。

## 📈 进阶使用

### 1. 批量操作
```
"在所有LOCAL系列服务器上执行system info命令"
```

### 2. 会话管理
```
"创建新的tmux会话名为ml-training"
"切换到dev会话"
```

### 3. 监控功能
```
"监控所有服务器状态"
"显示服务器资源使用情况"
```

## 🎯 下一步计划

1. **添加真实服务器配置**
2. **集成SSH密钥管理**  
3. **添加GPU监控功能**
4. **实现自动化脚本生成**
5. **集成日志管理**

---

🎉 **恭喜！你的Remote Terminal MCP服务已经可以使用了！**

开始在Cursor中用自然语言操作服务器吧！ 