# 🖥️ Remote Terminal MCP

统一远程终端管理工具 - 基于Model Context Protocol (MCP)

## 🌟 功能特色

- 🎯 **零安装使用** - 只需编辑mcp.json，npx自动处理一切依赖和配置
- 🚀 **智能连接管理** - 支持relay-cli、跳板机、直连多种模式
- 🐳 **Docker容器支持** - 自动检测、创建、管理Docker开发环境
- 🔄 **会话持久化** - 基于tmux的会话管理，断线重连无压力
- 🛠️ **环境自动配置** - 云存储同步、SSH密钥、zsh环境一键设置
- 📊 **统一管理界面** - 在Cursor中通过AI对话管理所有远程服务器

## 🎯 快速开始

### 1. 零安装配置（推荐）

**只需编辑一个文件，无需任何安装！**

在 `~/.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["-y", "@xuyehua/remote-terminal-mcp"],
      "disabled": false,
      "autoApprove": true,
      "description": "🖥️ Remote Terminal MCP"
    }
  }
}
```

重启Cursor即可使用！首次运行时npx会自动下载和配置。

### 2. 其他安装方式

#### 方式一：NPM全局安装

```bash
# 全局安装
npm install -g @xuyehua/remote-terminal-mcp

# 初始化配置
remote-terminal-mcp init

# 环境检查
remote-terminal-mcp doctor
```

#### 方式二：源码安装（开发者）

```bash
# 克隆项目
git clone https://github.com/maricoxu/remote-terminal-mcp.git
cd remote-terminal-mcp

# 安装Node.js依赖
npm install

# 安装Python依赖
pip install -r requirements.txt

# 确保系统已安装 tmux
# macOS: brew install tmux
# Ubuntu: sudo apt install tmux
```

然后在mcp.json中使用本地路径：

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "node",
      "args": ["/path/to/remote-terminal-mcp/index.js"],
      "disabled": false,
      "autoApprove": true,
      "description": "🖥️ Remote Terminal MCP"
    }
  }
}
```

### 3. 开始使用

配置完成后，在Cursor中直接与AI对话：

```
"列出所有远程服务器"
"连接到my-server"  
"在服务器上执行 nvidia-smi"
```

#### 高级配置（可选）

如果使用npm全局安装，可以使用CLI工具：

```bash
# 初始化配置
remote-terminal-mcp init

# 配置服务器
remote-terminal-mcp config

# 环境诊断
remote-terminal-mcp doctor
```

## 🔧 服务器配置

### 基础配置文件结构

配置文件位置：`~/.remote-terminal-mcp/config.yaml`

```yaml
servers:
  my-server:
    type: "script_based"           # 服务器类型
    description: "我的开发服务器"    # 描述信息
    connection:                    # 连接配置
      tool: "ssh"                 # 连接工具: ssh/relay-cli
      mode: "direct"              # 连接模式
      target:
        host: "server.example.com" # 目标主机地址
        user: "root"              # 用户名
    docker:                       # Docker配置(可选)
      container_name: "dev_env"   # 容器名
      image: "ubuntu:20.04"       # 镜像名
      auto_create: true           # 自动创建
    session:                      # 会话配置
      name: "my_dev"              # tmux会话名
      working_directory: "/workspace" # 工作目录
      shell: "/bin/zsh"          # Shell类型
    bos:                          # 云存储配置(可选)
      access_key: "your_key"      # 访问密钥
      secret_key: "your_secret"   # 密钥
      bucket: "your-bucket/path"  # 存储桶路径
```

### 支持的连接模式

#### 1. 直连模式 (Direct)
```yaml
connection:
  tool: "ssh"
  mode: "direct"
  target:
    host: "your-server.com"
    user: "root"
```

#### 2. 跳板机模式 (Jump Host)
```yaml
connection:
  tool: "ssh"
  mode: "jump_host"
  jump_host:
    host: "user@jump-server.com"
    password: "your_password"  # 建议使用密钥
  target:
    host: "target-server"
    user: "root"
```

#### 3. 双层跳板机模式
```yaml
connection:
  tool: "relay-cli"
  mode: "double_jump_host"
  first_jump:
    host: "user@first-jump.com"
    password: "password1"
  second_jump:
    host: "10.0.0.100"
    user: "root"
```

## 🚀 使用方法

### 在Cursor中使用

启动Cursor后，在对话中直接使用自然语言：

```
# 基础操作
"列出所有远程服务器"
"连接到my-server"
"检查server-01的状态"

# 命令执行
"在server-01上执行 nvidia-smi"
"查看my-server的Docker容器"
"在所有服务器上检查磁盘空间"

# 环境管理
"启动server-02的开发环境"
"重启my-server的Docker容器"
```

### 直接使用tmux

```bash
# 查看活动会话
tmux list-sessions

# 连接到特定服务器会话
tmux attach -t server01_dev

# 从会话中分离 (Ctrl+b d)
```

### 使用Python脚本

```bash
# 直接连接服务器
python3 connect_server.py my-server

# 列出所有服务器
python3 connect_server.py --list

# 强制重新连接
python3 connect_server.py my-server --force-recreate
```

## 🐳 Docker集成

### 自动容器管理

系统会自动：
1. 检测Docker服务是否可用
2. 查找指定名称的容器
3. 如果容器存在且运行中，直接进入
4. 如果容器存在但停止，重新启动并进入
5. 如果容器不存在，自动创建并进入

### Docker配置示例

```yaml
docker:
  container_name: "my_dev_env"
  image: "ubuntu:20.04"
  auto_create: true
  working_directory: "/workspace"
  run_options: "--privileged -v /data:/data"
```

## 📊 管理功能

### 添加新服务器

1. **编辑配置文件**：
```bash
nano ~/.remote-terminal-mcp/config.yaml
```

2. **添加服务器配置**到 `servers` 段

3. **重启Cursor MCP服务**或重新加载

### 服务器类型说明

- **`local_tmux`** - 本地tmux会话
- **`script_based`** - 远程服务器（支持Docker、云存储等高级功能）
- **`direct_ssh`** - 简单SSH连接

### 常用操作

```bash
# 检查配置
python3 debug_config.py

# 测试连接
python3 connect_server.py server-name --test

# 诊断问题
python3 connect_server.py server-name --diagnose
```

## 🛠️ 高级功能

### 云存储集成

支持自动配置云存储服务：

```yaml
bos:
  access_key: "your_access_key"
  secret_key: "your_secret_key"
  bucket: "your-bucket/path"
```

### 环境自动化

```yaml
environment_setup:
  auto_setup: true
  quick_connect_mode: true
```

### 会话管理

```yaml
session:
  environment:
    PROJECT_ROOT: "/workspace"
    PYTHONPATH: "/workspace:/workspace/src"
    TERM: "xterm-256color"
  shell: "/bin/zsh"
```

## 🐛 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 确认服务器地址正确
   - 验证SSH密钥或密码

2. **Docker容器问题**
   - 确认Docker服务运行
   - 检查镜像是否存在
   - 验证容器权限设置

3. **tmux会话问题**
   - 检查tmux是否安装
   - 确认会话名称唯一
   - 验证会话状态

### 调试命令

```bash
# 显示详细配置信息
python3 debug_config.py

# 测试特定服务器连接
python3 connect_server.py server-name --test

# 显示连接诊断信息
python3 connect_server.py server-name --diagnose

# 强制重新创建会话
python3 connect_server.py server-name --force-recreate
```

## 📝 配置模板

### 基础服务器模板

```yaml
my-server:
  type: "script_based"
  description: "我的开发服务器"
  connection:
    tool: "ssh"
    mode: "direct"
    target:
      host: "server.example.com"
      user: "root"
  session:
    name: "my_dev"
    working_directory: "/workspace"
    shell: "/bin/zsh"
```

### GPU服务器模板

```yaml
gpu-server:
  type: "script_based"
  description: "GPU训练服务器"
  connection:
    tool: "ssh"
    mode: "direct"
    target:
      host: "gpu.example.com"
      user: "root"
  docker:
    container_name: "pytorch_env"
    image: "pytorch/pytorch:latest"
    auto_create: true
    working_directory: "/workspace"
  session:
    name: "gpu_dev"
    working_directory: "/workspace"
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Model Context Protocol](https://github.com/modelcontextprotocol) - 强大的AI工具集成协议
- [tmux](https://github.com/tmux/tmux) - 终端多路复用器
- [Cursor](https://cursor.sh/) - AI代码编辑器