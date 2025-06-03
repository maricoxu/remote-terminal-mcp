# 🚀 Remote Terminal MCP 快速使用指南

## 🎯 基本使用流程

### 1. 连接到本地tmux会话
```bash
# 连接到自动创建的开发会话
tmux attach -t dev-session

# 查看所有可用会话
tmux list-sessions
```

### 2. tmux会话内的基本操作

#### 🎹 快捷键组合 (前缀键: Ctrl+B)
| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `Ctrl+B, D` | 退出会话 | 会话保持运行，可重新连接 |
| `Ctrl+B, C` | 创建新窗口 | 在同一会话中开新窗口 |
| `Ctrl+B, N` | 下一个窗口 | 切换窗口 |
| `Ctrl+B, P` | 上一个窗口 | 切换窗口 |
| `Ctrl+B, 0-9` | 跳转到窗口 | 直接跳转到指定编号窗口 |
| `Ctrl+B, %` | 垂直分屏 | 左右分屏 |
| `Ctrl+B, "` | 水平分屏 | 上下分屏 |

#### 📝 基本工作流程
```bash
# 1. 连接会话
tmux attach -t dev-session

# 2. 在会话中正常工作
cd /path/to/your/project
vim file.py
python script.py

# 3. 需要离开时按 Ctrl+B, D (会话继续运行)

# 4. 稍后重新连接
tmux attach -t dev-session  # 所有工作状态都保留
```

## 🔧 通过MCP工具管理

### 使用Claude与MCP工具交互

当MCP服务器运行时，你可以通过Claude使用这些工具：

#### 会话管理
```
"请列出当前的tmux会话"          → list_tmux_sessions
"创建一个名为'test'的新会话"     → create_tmux_session
```

#### 命令执行
```
"在当前目录执行 ls -la"         → run_command
"查看系统信息"                 → system_info
"列出项目目录内容"             → list_directory
```

#### 远程服务器管理
```
"列出所有远程服务器"           → list_remote_servers
"测试服务器连接"               → test_server_connection
"在远程服务器执行命令"         → execute_remote_command
```

## 🌟 使用场景示例

### 场景1：本地开发
```bash
# 连接到开发会话
tmux attach -t dev-session

# 开始编码工作
cd ~/Code/my-project
code .  # 打开VSCode
npm start  # 启动开发服务器

# 临时离开（Ctrl+B, D），稍后回来一切还在运行
```

### 场景2：通过Claude使用MCP
```
用户: "帮我检查一下当前有哪些tmux会话"
Claude: 使用 list_tmux_sessions 工具...

用户: "在dev-session中执行 git status"
Claude: 使用 run_command 工具...
```

### 场景3：多任务管理
```bash
# 在tmux会话中创建多个窗口
Ctrl+B, C  # 新窗口1: 运行服务器
Ctrl+B, C  # 新窗口2: 编辑代码  
Ctrl+B, C  # 新窗口3: 查看日志

# 使用 Ctrl+B, 0/1/2 快速切换
```

## 🆘 常见问题

### Q: tmux会话意外断开了怎么办？
**A:** 使用 `tmux attach -t dev-session` 重新连接，所有工作状态都会保留。

### Q: 忘记了在哪个会话中工作？
**A:** 使用 `tmux list-sessions` 查看所有会话，或通过MCP工具询问Claude。

### Q: 如何同时使用MCP工具和直接tmux操作？
**A:** 
- **直接操作**: 适合交互式工作、编辑文件
- **MCP工具**: 适合自动化任务、状态查询、远程管理

### Q: 会话崩溃了怎么办？
**A:** MCP服务器会在下次启动时自动重新创建会话（如果不存在的话）。

## 💡 最佳实践

1. **保持会话运行**: 使用 `Ctrl+B, D` 而不是直接关闭终端
2. **合理命名**: 为不同项目创建不同名称的会话
3. **利用窗口**: 一个会话中使用多个窗口管理不同任务
4. **结合使用**: 直接tmux操作 + MCP工具各有优势 