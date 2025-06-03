# Remote Terminal MCP

🚀 **简单易用的远程终端管理MCP服务器**

## 📦 快速安装

### 方式一：NPM安装（推荐）

```bash
# 安装包
npm install -g remote-terminal-mcp

# 直接启动（自动创建配置）
npm start
```

### 方式二：本地开发

```bash
# 克隆项目
git clone https://github.com/your-username/remote-terminal-mcp.git
cd remote-terminal-mcp

# 安装依赖
pip install -r requirements.txt

# 直接启动（自动创建配置）
python3 python/mcp_server.py
```

## 🎯 功能特点

✨ **开箱即用** - 默认配置本地tmux会话管理  
🔧 **简单配置** - 一个YAML文件搞定所有设置  
🏠 **用户友好** - 配置文件自动存储在 `~/.remote-terminal-mcp/`  
🖥️ **本地优先** - 先支持本地终端，再扩展远程连接  

## 📋 基础工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| `system_info` | 获取系统信息 | "显示系统信息" |
| `run_command` | 执行本地命令 | "运行命令: ls -la" |
| `list_tmux_sessions` | 列出tmux会话 | "列出所有tmux会话" |
| `create_tmux_session` | 创建tmux会话 | "创建名为test的tmux会话" |
| `list_directory` | 列出目录内容 | "显示当前目录内容" |

## 🔌 在Cursor中使用

1. **安装并启动服务器**
2. **在Cursor设置中添加MCP服务器配置**
3. **直接对话测试：**
   - "列出所有tmux会话"
   - "在dev-session中执行 pwd"
   - "显示系统信息"

## ⚙️ 配置说明

配置文件位置：`~/.remote-terminal-mcp/config.yaml`

### 默认配置示例：

```yaml
servers:
  local-dev:
    type: "local_tmux"
    description: "本地开发会话"
    session:
      name: "dev-session"           # 📍 修改会话名
      working_directory: "~/Code"   # 📍 修改工作目录
      shell: "/bin/zsh"            # 📍 修改shell类型

global_settings:
  default_server: "local-dev"
  connection_timeout: 30
```

### 添加远程服务器（可选）：

```yaml
servers:
  # ... 保留local-dev配置
  
  remote-gpu:
    type: "direct_ssh"
    description: "GPU服务器"
    host: "gpu.example.com"
    username: "your-username"
    private_key_path: "~/.ssh/id_rsa"
```

## 🛠️ 开发命令

```bash
npm run start      # 启动服务器
npm run dev        # 调试模式启动
npm run test       # 运行测试
npm run lint       # 代码检查
```

## 📂 目录结构

```
~/.remote-terminal-mcp/
├── config.yaml          # 用户配置文件
└── logs/                # 日志文件（自动创建）

项目目录/
├── python/              # Python MCP服务器
├── scripts/             # 安装和管理脚本
├── config/              # 配置模板
└── package.json         # NPM配置
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

💡 **设计理念：简化优先，开箱即用，逐步扩展**