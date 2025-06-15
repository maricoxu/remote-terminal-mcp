# Remote Terminal MCP for Cursor

🚀 **一个专为Cursor设计的远程终端MCP工具**，让你在Cursor中轻松管理和连接远程服务器，支持SSH直连、跳板机中继、Docker容器等多种连接方式。

## ✨ 主要特性

- 🎯 **专为Cursor优化**：完美集成Cursor的MCP架构
- 🔗 **多种连接方式**：SSH直连、跳板机中继、Docker容器
- 🛠️ **智能配置管理**：交互式配置向导，支持模板和自定义
- 📦 **一键安装**：NPM包管理，开箱即用
- 🔧 **强大的服务器管理**：增删改查服务器配置
- 💻 **远程命令执行**：在Cursor中直接执行远程命令
- 🐳 **Docker支持**：完整的Docker容器管理
- 🔄 **会话管理**：基于tmux的持久化会话

## 🚀 快速开始

### 1. 在Cursor中配置MCP

在Cursor中，打开设置并编辑MCP配置文件（`.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["@xuyehua/remote-terminal-mcp"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

> 💡 **提示**：使用`npx`会自动下载最新版本，无需手动安装NPM包。如果你偏好手动管理，也可以先运行 `npm install -g @xuyehua/remote-terminal-mcp` 然后将`command`改为包的绝对路径。

### 2. 启用MCP服务

配置完成后，你需要让MCP服务生效：
- **方式1**：在Cursor中刷新MCP服务（推荐）
- **方式2**：重启Cursor应用

配置生效后，你就可以开始使用了！

## 🎯 在Cursor中使用

### 📋 查看可用服务器

在Cursor中询问AI：

```
请帮我查看当前配置的远程服务器列表
```

AI会使用`list_servers`工具显示所有配置的服务器。

### ⚙️ 配置新服务器

在Cursor中说：

```
我想配置一个新的远程服务器，服务器IP是192.168.1.100，用户名是ubuntu，使用SSH密钥认证
```

AI会启动**交互式配置向导**，引导你完成服务器配置：
- 🎯 **智能向导**：根据你的需求选择最适合的配置方式
- 🔧 **多种模式**：支持SSH直连、跳板机中继、Docker容器等
- 📝 **逐步指导**：清晰的步骤说明，无需复杂的手动配置
- ✅ **即时验证**：配置完成后自动测试连接

### 🔗 连接服务器

在Cursor中请求：

```
请帮我连接到服务器 my-server
```

AI会使用`connect_server`工具建立连接。

### 💻 执行远程命令

连接后，你可以说：

```
在服务器上执行 ls -la 命令
```

AI会使用`execute_command`工具执行命令并返回结果。

### 🗑️ 删除服务器配置

```
请删除名为 old-server 的服务器配置
```

AI会使用管理工具安全删除服务器配置。

## 🛠️ 配置管理

### 交互式配置向导

在Cursor中直接说：
```
我要配置一个新的远程服务器
```

AI会自动启动配置向导，无需手动运行命令。向导包括：
- 🚀 **快速配置**：适合常见场景的一键配置
- 🎯 **向导配置**：详细的分步指导
- 📋 **模板配置**：基于预设模板快速创建
- ⚙️ **高级配置**：完全自定义的配置选项

### 支持的连接类型

#### 1. SSH直连
```yaml
servers:
  my-server:
    type: ssh
    host: 192.168.1.100
    user: ubuntu
    port: 22
    auth_method: key  # 或 password
```

#### 2. 跳板机中继
```yaml
servers:
  relay-server:
    type: relay
    host: target-server.com
    user: ubuntu
    jumphost: jumphost.com
    jumphost_user: admin
```

#### 3. Docker容器
```yaml
servers:
  docker-server:
    type: ssh
    host: 192.168.1.100
    user: ubuntu
    docker:
      container_name: my-container
      image: ubuntu:20.04
      ports: ["8080:80"]
```

## 🔧 MCP工具说明

### 核心工具

| 工具名称 | 功能描述 | Cursor使用示例 |
|---------|---------|---------------|
| `list_servers` | 列出所有服务器 | "显示所有远程服务器" |
| `connect_server` | 连接到服务器 | "连接到production服务器" |
| `execute_command` | 执行远程命令 | "在服务器上运行docker ps" |
| `get_server_status` | 查看连接状态 | "检查服务器连接状态" |
| `run_local_command` | 执行本地命令 | "在本地运行ls命令" |

### 配置管理工具

| 工具名称 | 功能描述 | Cursor使用示例 |
|---------|---------|---------------|
| `interactive_config_wizard` | 交互式配置 | "我要配置一个新服务器" |
| `manage_server_config` | 管理服务器配置 | "删除test-server配置" |
| `create_server_config` | 创建服务器配置 | "创建一个Docker服务器配置" |
| `diagnose_connection` | 诊断连接问题 | "诊断服务器连接问题" |

## 📝 使用场景示例

### 场景1：开发环境管理

```
用户：我需要配置一个开发服务器，IP是192.168.1.100
AI：我来启动配置向导帮你设置...
    [启动交互式配置向导]
    - 检测到这是一个内网IP，推荐SSH直连方式
    - 请输入用户名...
    - 选择认证方式：SSH密钥 / 密码
    - 是否需要Docker支持？
    [配置完成，自动测试连接]
```

### 场景2：Docker容器配置

```
用户：我要配置一个带Docker的GPU训练服务器
AI：启动Docker配置向导...
    [Docker环境配置向导]
    - 选择基础镜像：Ubuntu 20.04 / PyTorch官方镜像
    - GPU支持：是否启用NVIDIA GPU
    - 端口映射：Jupyter (8888), TensorBoard (6006)
    - 挂载目录：代码目录、数据目录
    [创建并启动容器]
```

### 场景3：多服务器监控

```
用户：检查所有生产服务器的CPU使用情况
AI：我来检查所有生产服务器的系统状态...
```

## 🔍 故障排除

### 常见问题

#### 1. MCP服务器无法启动
```bash
# 如果使用npx方式，通常无需手动安装
# 如果需要检查全局安装的包
npm list -g @xuyehua/remote-terminal-mcp

# 清除缓存并重新获取（npx方式）
npx clear-npx-cache
# 或者手动重新安装
npm uninstall -g @xuyehua/remote-terminal-mcp
npm install -g @xuyehua/remote-terminal-mcp
```

#### 2. 服务器连接失败
在Cursor中说：
```
请诊断服务器连接问题
```

#### 3. 配置文件问题
```bash
# 查看配置文件位置
ls -la ~/.remote-terminal-mcp/

# 重置配置（在Cursor中说）
"请帮我重置远程服务器配置"
# 或者手动重置
rm -rf ~/.remote-terminal-mcp/
```

### 调试模式

启用详细日志：
```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["@xuyehua/remote-terminal-mcp"],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "true"
      }
    }
  }
}
```

## 🔐 安全注意事项

1. **SSH密钥管理**：建议使用SSH密钥而非密码认证
2. **配置文件权限**：确保配置文件权限设置正确（600）
3. **跳板机安全**：使用跳板机时确保跳板机的安全性
4. **网络安全**：在不安全网络中使用VPN

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置

```bash
git clone https://github.com/maricoxu/remote-terminal-mcp.git
cd remote-terminal-mcp
npm install
```

### 测试

```bash
npm test
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [GitHub仓库](https://github.com/maricoxu/remote-terminal-mcp)
- [NPM包](https://www.npmjs.com/package/@xuyehua/remote-terminal-mcp)
- [问题反馈](https://github.com/maricoxu/remote-terminal-mcp/issues)

## 📊 版本历史

### v0.8.3 (最新)
- 🐛 修复服务器删除功能的逻辑问题
- ✨ 改进配置备份机制
- 📝 完善文档和使用指南

### v0.8.2
- ✨ 增强配置管理功能
- 🐳 完善Docker支持
- 🔧 优化连接稳定性

---

💡 **提示**：这个工具专为Cursor设计，通过AI助手的自然语言交互，让远程服务器管理变得简单直观。开始使用时，只需要告诉AI你想做什么，它会自动选择合适的工具来完成任务！