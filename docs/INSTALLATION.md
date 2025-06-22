# 🚀 Remote Terminal MCP 安装指南

## 方式一：npm一键安装（推荐）

### 📦 直接使用

```bash
# 一键启动（自动下载最新版本）
npx @xuyehua/remote-terminal-mcp

# 测试安装
npx @xuyehua/remote-terminal-mcp --test
```

### 🔧 Cursor配置

在 `~/.cursor/mcp.json` 中添加：

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

## 方式二：从源码运行

### 📥 克隆项目

```bash
git clone https://github.com/xuyehua/remote-terminal-mcp.git
cd remote-terminal-mcp
```

### 🏃 启动服务

```bash
npm start
# 或
python3 python/mcp_server.py
```

## 🎯 快速体验

### 1️⃣ 本地开发（开箱即用）

安装后立即可用：
- ✅ 自动创建 `dev-session` tmux会话
- 📁 工作目录：`~/Code`（自动检测）
- 🎮 支持所有MCP工具

### 2️⃣ 配置远程服务器（可选）

编辑配置文件：
```bash
nano ~/.remote-terminal/config.yaml
```

修改 `remote-server` 部分的 📍 标记项：
- 连接工具和目标服务器
- Docker容器配置
- 工作目录和环境变量

### 3️⃣ 使用MCP工具

在Cursor中使用Claude：
```
"列出所有tmux会话"
"在dev-session中执行 pwd"
"连接到remote-server"
"在远程服务器执行 ls -la"
```

## 💡 特性亮点

### 🎯 渐进式设计
- **本地优先**：无需配置即可使用本地tmux
- **按需扩展**：需要时再配置远程服务器
- **智能检测**：自动适应不同的环境和限制

### 🔧 Script-based连接
- ✅ 支持跳板机和代理工具（如relay-cli）
- 🐳 智能Docker容器检测和进入
- 🛠️ 自适应受限环境（如企业内网）
- 📁 自动设置工作目录

### 🚀 一键体验
```bash
# 体验完整功能
npx @xuyehua/remote-terminal-mcp --test
```

## 🔍 故障排除

### 常见问题

1. **Python3不可用**
   ```bash
   # macOS
   brew install python3
   
   # Ubuntu/Debian
   sudo apt install python3
   ```

2. **tmux不可用**
   ```bash
   # macOS
   brew install tmux
   
   # Ubuntu/Debian
   sudo apt install tmux
   ```

3. **权限问题**
   ```bash
   # 确保配置目录可写
   mkdir -p ~/.remote-terminal
chmod 755 ~/.remote-terminal
   ```

### 🐛 调试模式

```bash
# 启用调试输出
npx @xuyehua/remote-terminal-mcp --debug
```

## 📚 更多资源

- [快速指南](QUICK_GUIDE.md)
- [配置示例](../config/)
- [脚本示例](../scripts/)

---

## 🎉 开始使用

```bash
# 立即体验
npx @xuyehua/remote-terminal-mcp
```

然后在Cursor中对Claude说：**"列出所有tmux会话"** 