# 🔧 Remote Terminal MCP 配置指南

完整的远程服务器配置和管理指南

## 📖 目录

- [🚀 快速配置](#-快速配置)
- [📋 配置步骤详解](#-配置步骤详解)
- [🏗️ 服务器类型配置](#️-服务器类型配置)
- [🐳 Docker环境配置](#-docker环境配置)
- [☁️ BOS云存储配置](#️-bos云存储配置)
- [🔒 安全配置](#-安全配置)
- [⚙️ 高级配置](#️-高级配置)
- [🛠️ 故障排除](#️-故障排除)

## 🚀 快速配置

### Step 1: 安装MCP服务器

```bash
# 通过npm安装
npm install -g @xuyehua/remote-terminal-mcp

# 或本地开发模式
git clone <repo>
cd remote-terminal-mcp
npm install
```

### Step 2: 配置Cursor

编辑 `~/.cursor/mcp.json`：

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

### Step 3: 启动并初始化

1. 启动Cursor
2. 在对话中说："列出所有远程服务器"
3. 系统会自动创建配置文件 `~/.remote-terminal-mcp/config.yaml`

## 📋 配置步骤详解

### 1. 基础配置文件结构

配置文件位置：`~/.remote-terminal-mcp/config.yaml`

```yaml
# 服务器配置
servers:
  # 服务器1配置
  server-name:
    type: "script_based"
    description: "服务器描述"
    # ... 详细配置

# 全局设置
global_settings:
  default_server: "local-dev"
  connection_timeout: 30
  # ... 其他设置

# 安全配置
security:
  allowed_commands: [".*"]
  # ... 安全选项
```

### 2. 必填字段说明

| 字段 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `type` | ✅ | 服务器类型 | `"script_based"`, `"local_tmux"` |
| `description` | ✅ | 服务器描述 | `"生产环境GPU服务器"` |
| `session.name` | ✅ | tmux会话名 | `"prod_gpu_dev"` |

### 3. 可选字段说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `docker.auto_create` | 自动创建Docker容器 | `false` |
| `bos.access_key` | BOS访问密钥 | `""` |
| `environment_setup.auto_setup` | 自动环境配置 | `false` |

## 🏗️ 服务器类型配置

### 1. 本地开发环境 (`local_tmux`)

适用于本地开发和测试：

```yaml
local-dev:
  type: "local_tmux"
  description: "本地开发会话"
  session:
    name: "dev-session"
    working_directory: "~/Code"
    shell: "/bin/zsh"
    environment:
      TERM: "xterm-256color"
      PYTHONPATH: "~/Code/src"
```

### 2. 远程脚本服务器 (`script_based`)

适用于远程Linux服务器，支持完整的环境管理：

```yaml
gpu-server:
  type: "script_based"
  description: "GPU训练服务器"
  connection:
    tool: "ssh"  # 或 "relay-cli"
    mode: "direct"
    target:
      host: "gpu.example.com"
      user: "root"
  docker:
    container_name: "training_env"
    image: "pytorch/pytorch:latest"
    auto_create: true
  session:
    name: "gpu_training"
    working_directory: "/workspace"
    shell: "/bin/bash"
```

### 3. 跳板机服务器配置

通过跳板机访问的服务器：

```yaml
private-server:
  type: "script_based"
  description: "内网高性能服务器"
  connection:
    tool: "relay-cli"
    mode: "jump_host"
    jump_host:
      host: "user@jump.example.com"
      password: "your_password"  # 建议使用密钥
    target:
      host: "private-gpu-01"
      user: "root"
  docker:
    container_name: "private_dev"
    image: "custom/dev-env:latest"
    auto_create: true
```

## 🐳 Docker环境配置

### 基础Docker配置

```yaml
docker:
  container_name: "dev_env"          # 容器名称
  image: "ubuntu:20.04"              # Docker镜像
  auto_create: true                  # 自动创建容器
  run_options: "--privileged -dti"   # Docker运行参数
```

### 高级Docker配置

```yaml
docker:
  container_name: "ml_training"
  image: "pytorch/pytorch:1.12.0-cuda11.3-cudnn8-devel"
  auto_create: true
  run_options: >-
    --gpus all
    --privileged
    --ulimit core=-1
    --security-opt seccomp=unconfined
    --net=host
    --uts=host
    --ipc=host
    -v /data:/data
    -v /home:/home
    --shm-size=64g
    --restart=always
  health_check:
    enabled: true
    command: "nvidia-smi"
    interval: 30
```

### Docker操作流程

1. **容器检查** - 检测容器是否存在和运行状态
2. **自动创建** - 如果不存在且`auto_create=true`，则创建容器
3. **启动容器** - 如果容器已停止，则启动
4. **进入环境** - 使用指定shell进入容器
5. **环境配置** - 执行BOS同步等初始化任务

## ☁️ BOS云存储配置

### 基础BOS配置

```yaml
bos:
  access_key: "your_access_key"
  secret_key: "your_secret_key"
  bucket: "bos://your-bucket/config-path"
```

### 同步的文件和目录

| 文件 | 说明 | 同步方向 |
|------|------|----------|
| `.zshrc` | Zsh配置文件 | 双向 |
| `.p10k.zsh` | Powerlevel10k主题 | 双向 |
| `.zsh_history` | 命令历史 | 双向 |
| `~/.ssh/` | SSH密钥目录 | 下载 |
| `.vimrc` | Vim配置 | 双向 |

### BOS操作命令

```bash
# 配置BOS凭证（在容器内执行）
bcecmd configure set --access_key=your_key --secret_key=your_secret

# 下载配置文件
bcecmd bos cp bos://bucket/path/zshrc ~/.zshrc

# 上传配置文件
bcecmd bos cp ~/.zshrc bos://bucket/path/zshrc
```

## 🔒 安全配置

### 命令安全限制

```yaml
security:
  # 允许的命令模式（正则表达式）
  allowed_commands:
    - "ls.*"           # 所有ls命令
    - "ps.*"           # 进程查看
    - "nvidia-smi"     # GPU状态
    - "git.*"          # Git操作
    - "python.*"       # Python执行
    - "pip.*"          # 包管理
  
  # 禁止的命令
  forbidden_commands:
    - "rm -rf /"       # 危险删除
    - "format.*"       # 格式化
    - "mkfs.*"         # 文件系统创建
  
  # 需要确认的命令
  require_confirmation:
    - "rm -rf"         # 递归删除
    - "docker rm"      # 删除容器
    - "shutdown"       # 关机
    - "reboot"         # 重启
    - "passwd"         # 修改密码
```

### 认证和访问控制

#### SSH密钥认证（推荐）

```yaml
connection:
  target:
    host: "server.example.com"
    user: "deploy"
    key_file: "~/.ssh/deploy_rsa"  # 私钥路径
    # 不要设置password字段
```

#### 密码认证（不推荐）

```yaml
connection:
  target:
    host: "server.example.com"
    user: "admin"
    password: "secure_password"  # 仅用于测试环境
```

### 网络安全建议

1. **使用VPN或专网**
2. **配置防火墙规则**
3. **定期轮换密钥**
4. **启用审计日志**
5. **限制用户权限**

## ⚙️ 高级配置

### 智能预连接

启动时自动连接常用服务器：

```yaml
global_settings:
  auto_preconnect: true              # 启用预连接
  preconnect_servers:                # 预连接服务器列表
    - "local-dev"                    # 本地开发
    - "main-gpu"                     # 主GPU服务器
    - "backup-server"                # 备份服务器
  preconnect_timeout: 60             # 预连接超时（秒）
  preconnect_parallel: 3             # 并行连接数
  preconnect_retry: 2                # 重试次数
```

### 环境变量配置

```yaml
session:
  environment:
    # Python环境
    PYTHONPATH: "/workspace:/workspace/src"
    PYTHON_VERSION: "3.10"
    
    # CUDA环境
    CUDA_VISIBLE_DEVICES: "0,1,2,3"
    CUDA_HOME: "/usr/local/cuda"
    
    # 项目环境
    PROJECT_ROOT: "/workspace"
    DATA_PATH: "/data"
    MODEL_PATH: "/models"
    
    # 开发工具
    EDITOR: "vim"
    TERM: "xterm-256color"
```

### 会话管理配置

```yaml
session:
  name: "ml_training"                # 会话名称
  working_directory: "/workspace"    # 工作目录
  shell: "/bin/zsh"                 # Shell类型
  auto_attach: true                 # 自动附加到会话
  persistent: true                  # 持久化会话
  window_config:                    # 窗口配置
    - name: "code"                  # 代码窗口
      command: "cd /workspace && vim"
    - name: "monitor"               # 监控窗口
      command: "htop"
    - name: "logs"                  # 日志窗口
      command: "tail -f /var/log/app.log"
```

### 负载均衡配置

```yaml
load_balancing:
  enabled: true
  strategy: "round_robin"  # round_robin, least_connections, random
  health_check:
    enabled: true
    interval: 30          # 检查间隔（秒）
    timeout: 10           # 超时时间（秒）
    retry_count: 3        # 重试次数
  failover:
    enabled: true
    backup_servers:       # 备份服务器列表
      - "backup-gpu-01"
      - "backup-gpu-02"
```

## 🛠️ 故障排除

### 常见问题和解决方案

#### 1. 连接超时问题

**问题**：连接服务器时出现超时
```
Error: Connection timeout after 30 seconds
```

**解决方案**：
```yaml
# 增加超时时间
global_settings:
  connection_timeout: 60
  command_timeout: 300
```

#### 2. relay-cli认证失败

**问题**：relay-cli无法认证
```
Error: relay-cli authentication failed
```

**解决方案**：
```bash
# 1. 检查relay-cli安装
which relay-cli

# 2. 手动测试连接
relay-cli

# 3. 检查网络连接
ping relay-server.com

# 4. 重新配置凭证
relay-cli config
```

#### 3. Docker容器创建失败

**问题**：无法创建Docker容器
```
Error: Failed to create Docker container
```

**解决方案**：
```bash
# 1. 检查Docker服务
sudo systemctl status docker

# 2. 检查镜像是否存在
docker images | grep your-image

# 3. 手动拉取镜像
docker pull your-image:tag

# 4. 检查磁盘空间
df -h

# 5. 清理无用容器
docker system prune
```

#### 4. tmux会话问题

**问题**：tmux会话连接失败
```
Error: no sessions
```

**解决方案**：
```bash
# 1. 列出所有会话
tmux list-sessions

# 2. 创建新会话
tmux new-session -d -s test_session

# 3. 重启tmux服务器
tmux kill-server

# 4. 检查tmux配置
cat ~/.tmux.conf
```

#### 5. BOS同步失败

**问题**：BOS文件同步失败
```
Error: BOS sync failed
```

**解决方案**：
```bash
# 1. 检查BOS配置
bcecmd configure list

# 2. 测试BOS连接
bcecmd bos ls bos://bucket-name

# 3. 重新配置凭证
bcecmd configure set --access_key=key --secret_key=secret

# 4. 检查网络连接
ping bos.api.com
```

### 调试模式

启用详细日志记录：

```json
# 在mcp.json中添加环境变量
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["-y", "@xuyehua/remote-terminal-mcp"],
      "env": {
        "MCP_DEBUG": "1",
        "DEBUG_LEVEL": "verbose"
      }
    }
  }
}
```

### 日志文件位置

- **MCP服务器日志**：`~/.remote-terminal-mcp/logs/mcp.log`
- **连接日志**：`~/.remote-terminal-mcp/logs/connections.log`
- **Docker日志**：`~/.remote-terminal-mcp/logs/docker.log`
- **BOS同步日志**：`~/.remote-terminal-mcp/logs/bos.log`

## 📞 获取帮助

如果遇到问题，可以通过以下方式获取帮助：

1. **查看日志文件** - 检查详细错误信息
2. **查阅文档** - 阅读官方文档和FAQ
3. **提交Issue** - 在GitHub仓库提交问题报告
4. **社区讨论** - 参与技术讨论

## 🔗 相关资源

- [MCP协议文档](https://modelcontextprotocol.io/)
- [tmux用户手册](https://man.openbsd.org/tmux)
- [Docker官方文档](https://docs.docker.com/)
- [relay-cli使用指南](https://apigo.baidu.com/d/TgXlCxmm)
- [BOS API文档](https://cloud.baidu.com/doc/BOS/index.html)

---

🎯 **配置完成后，在Cursor中说 "列出所有远程服务器" 即可开始使用！** 