# 🖥️ Remote Terminal MCP

统一远程终端管理工具 - 基于Model Context Protocol (MCP)

## 🌟 功能特色

- 🚀 **智能连接管理** - 支持relay-cli、跳板机、直连多种模式
- 🐳 **Docker容器支持** - 自动检测、创建、管理Docker开发环境
- 🔄 **会话持久化** - 基于tmux的会话管理，断线重连无压力
- 🛠️ **环境自动配置** - BOS云存储同步、SSH密钥、zsh环境一键设置
- 📊 **统一管理界面** - 在Cursor中通过AI对话管理所有远程服务器

## 🎯 快速开始

### 1. 配置Cursor

在 `~/.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "node",
      "args": ["/Users/xuyehua/Code/remote-terminal-mcp/index.js"],
      "disabled": false,
      "autoApprove": true,
      "description": "🖥️ Remote Terminal MCP"
    }
  }
}
```

> 💡 **提示**：将路径改为你的实际项目路径

### 2. 对话配置服务器

重启Cursor后，直接说：

```
"帮我配置一台服务器，地址是 gpu.company.com"
```

AI会引导你完成配置，无需手动编辑文件！

### 3. 开始使用

```
"列出所有远程服务器"
"连接到gpu-server"  
"在服务器上执行 nvidia-smi"
```

## 🔧 服务器配置指南

### 配置文件结构

```yaml
servers:
  my-server:
    type: "script_based"           # 服务器类型
    description: "我的服务器"       # 描述信息
    connection:                    # 连接配置
      tool: "relay-cli"           # 连接工具: relay-cli/ssh
      mode: "direct"              # 连接模式: direct/jump_host
      target:
        host: "server.domain.com"  # 目标主机地址
        user: "root"              # 用户名
    docker:                       # Docker配置(可选)
      container_name: "dev_env"   # 容器名
      image: "ubuntu:20.04"       # 镜像名
      auto_create: true           # 自动创建
    session:                      # 会话配置
      name: "my_dev"              # tmux会话名
      working_directory: "/work"  # 工作目录
      shell: "/bin/zsh"          # Shell类型
    bos:                          # BOS配置(可选)
      access_key: "your_key"      # 访问密钥
      secret_key: "your_secret"   # 密钥
      bucket: "bos://bucket/path" # 存储桶路径
```

### 支持的连接模式

#### 1. 直连模式 (Direct)
```yaml
connection:
  tool: "ssh"  # 或 "relay-cli"
  mode: "direct"
  target:
    host: "your-server.com"
    user: "root"
```

#### 2. 跳板机模式 (Jump Host)
```yaml
connection:
  tool: "relay-cli"
  mode: "jump_host"
  jump_host:
    host: "jump@jump-server.com"
    password: "your_password"  # 建议使用密钥
  target:
    host: "target-server"
    user: "root"
```

#### 3. Relay-CLI模式 (百度内网)
```yaml
connection:
  tool: "relay-cli"
  mode: "direct"
  target:
    host: "internal-server.domain"
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
"同步BOS配置到server-03"
```

### 直接使用tmux

```bash
# 查看活动会话
tmux list-sessions

# 连接到特定服务器会话
tmux attach -t server01_dev

# 从会话中分离
# Ctrl+b d
```

## 📊 服务器管理

### 添加新服务器

1. **编辑配置文件**：
```bash
nano ~/.remote-terminal-mcp/config.yaml
```

2. **添加服务器配置**：
```yaml
servers:
  new-server:
    type: "script_based"
    description: "新服务器"
    connection:
      tool: "ssh"
      mode: "direct"
      target:
        host: "new-server.com"
        user: "root"
    session:
      name: "new_dev"
      working_directory: "/workspace"
```

3. **重启MCP服务器**或重新加载Cursor

### 服务器类型说明

- **`local_tmux`** - 本地tmux会话
- **`script_based`** - 远程服务器（支持Docker、BOS等高级功能）
- **`direct_ssh`** - 简单SSH连接

## 🐳 Docker集成

### 自动容器管理

```yaml
docker:
  container_name: "my_dev_env"
  image: "ubuntu:20.04"
  auto_create: true
  run_options: "--privileged -v /data:/data"
```

### 容器操作流程

1. **检查容器** - 自动检测容器是否存在
2. **创建/启动** - 不存在则创建，已停止则启动
3. **进入容器** - 使用配置的shell进入开发环境
4. **环境配置** - 可选的BOS同步、SSH密钥设置

## ☁️ BOS云存储同步

### 配置BOS

```yaml
bos:
  access_key: "your_access_key"
  secret_key: "your_secret_key"
  bucket: "bos://your-bucket/config-path"
```

### 同步的文件

- `.zshrc` - Zsh配置
- `.p10k.zsh` - Powerlevel10k主题
- `.zsh_history` - 命令历史
- SSH密钥和其他开发配置

## 🔒 安全配置

### 命令限制

```yaml
security:
  allowed_commands:
    - "ls.*"
    - "ps.*"
    - "nvidia-smi"
  forbidden_commands:
    - "rm -rf /"
    - "format.*"
  require_confirmation:
    - "rm -rf"
    - "shutdown"
    - "reboot"
```

### 认证建议

- 使用SSH密钥而非密码
- 定期轮换访问凭证
- 限制网络访问权限
- 启用审计日志

## ⚙️ 高级配置

### 智能预连接

```yaml
global_settings:
  auto_preconnect: true
  preconnect_servers:
    - "local-dev"
    - "main-server"
    - "gpu-cluster"
  preconnect_timeout: 60
  preconnect_parallel: 3
```

### 环境变量

```yaml
session:
  environment:
    PYTHONPATH: "/workspace:/workspace/src"
    CUDA_VISIBLE_DEVICES: "0,1"
    PROJECT_ROOT: "/workspace"
```

## 🛠️ 故障排除

### 常见问题

#### 1. relay-cli认证失败
```bash
# 检查relay-cli是否正确安装
which relay-cli

# 手动测试连接
relay-cli
```

#### 2. Docker容器无法创建
```bash
# 检查Docker服务状态
sudo systemctl status docker

# 验证镜像是否存在
docker images | grep your-image
```

#### 3. tmux会话连接失败
```bash
# 检查tmux服务
tmux list-sessions

# 重启tmux服务器
tmux kill-server
```

### 调试模式

启用详细日志：
```json
{
  "env": {
    "MCP_DEBUG": "1"
  }
}
```

## 📈 性能优化

### 连接池管理
- 复用已建立的连接
- 智能超时机制
- 自动重连机制

### 并发控制
- 限制同时连接数
- 优先级队列
- 资源分配策略

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🔗 相关资源

- [MCP协议文档](https://modelcontextprotocol.io/)
- [tmux用户指南](https://github.com/tmux/tmux/wiki)
- [Docker官方文档](https://docs.docker.com/)
- [relay-cli使用指南](https://apigo.baidu.com/d/TgXlCxmm)

---

## 📞 支持

如有问题或建议，请：
- 提交Issue
- 发起Discussion
- 联系维护者

**让远程开发变得简单高效！** 🚀