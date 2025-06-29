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
我想新增一个远程服务器
```

AI会启动**交互式配置向导**，引导你完成服务器配置：
- 🎯 **智能向导**：根据你的需求选择最适合的配置方式
- 🔧 **多种模式**：支持SSH直连、跳板机中继、Docker容器等
- 📝 **逐步指导**：清晰的步骤说明，向导会询问所需的配置信息
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
我想新增一个远程服务器
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

跳板机中继支持一级跳板和二级跳板两种模式，适用于复杂的网络环境。

##### 一级跳板机配置
通过单个跳板机连接目标服务器：

```yaml
servers:
  relay-server:
    type: relay
    host: target-server.com
    user: ubuntu
    jumphost: jumphost.com
    jumphost_user: admin
    # 可选配置
    port: 22
    jumphost_port: 22
    auth_method: key  # 或 password
```

##### 二级跳板机配置
通过两级跳板机连接目标服务器（跳板机→二级跳板机→目标服务器）：

```yaml
servers:
  relay-server:
    type: relay
    host: target-server.com
    user: ubuntu
    # 一级跳板机配置
    jumphost: jumphost.com
    jumphost_user: admin
    # 二级跳板机配置
    specs:
      connection:
        jump_host:
          host: jumphost.com
          username: admin
          port: 22
        secondary_jump:
          host: secondary-jumphost.com
          username: root
          port: 22
        target:
          host: target-server.com
          username: ubuntu
          port: 22
        tool: relay-cli
```

##### 配置说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `jumphost` | 一级跳板机地址 | `jumphost.com` |
| `jumphost_user` | 一级跳板机用户名 | `admin` |
| `secondary_jump.host` | 二级跳板机地址 | `secondary-jumphost.com` |
| `secondary_jump.username` | 二级跳板机用户名 | `root` |
| `target.host` | 最终目标服务器地址 | `target-server.com` |
| `target.username` | 目标服务器用户名 | `ubuntu` |
| `tool` | 连接工具类型 | `relay-cli` |

##### 跳板机连接原理

跳板机连接通过建立多级SSH隧道来实现安全的远程访问：

```
本地 → 一级跳板机 → 二级跳板机 → 目标服务器
```

**连接流程：**
1. 首先连接到一级跳板机（jumphost）
2. 在一级跳板机上建立到二级跳板机的连接（如果配置了二级跳板）
3. 最后从二级跳板机连接到目标服务器
4. 所有数据通过这个安全隧道传输

**适用场景：**
- 🏢 **企业内网访问**：通过公司跳板机访问内网服务器
- 🔒 **安全隔离环境**：生产环境需要多层安全验证
- 🌐 **跨网络访问**：不同网络段之间的服务器访问
- 🛡️ **合规要求**：满足安全审计和访问控制要求

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

## 🔧 MCP工具详细说明

本工具提供11个专业的MCP工具，通过Cursor的AI助手，你可以用自然语言轻松管理远程服务器。

### 🔍 服务器查询与状态工具

| 工具名称 | 功能描述 | Cursor使用示例 |
|---------|---------|---------------|
| `list_servers` | 列出所有配置的服务器 | "显示所有远程服务器列表" |
| `get_server_info` | 获取特定服务器的详细信息 | "查看production服务器的详细配置" |
| `get_server_status` | 检查服务器连接状态 | "检查所有服务器的连接状态" |

### 🔗 连接与命令执行工具

| 工具名称 | 功能描述 | Cursor使用示例 |
|---------|---------|---------------|
| `connect_server` | 连接到指定服务器 | "连接到production服务器" |
| `disconnect_server` | 断开服务器连接并清理资源 | "断开production服务器的连接" |
| `execute_command` | 在远程服务器执行命令 | "在服务器上运行docker ps命令" |
| `run_local_command` | 在本地系统执行命令 | "在本地运行ls -la命令" |

### ⚙️ 服务器配置管理工具

| 工具名称 | 功能描述 | Cursor使用示例 |
|---------|---------|---------------|
| `create_server_config` | 创建新的服务器配置（交互式） | "我想新增一个远程服务器" |
| `update_server_config` | 更新现有服务器配置（交互式） | "我想修改production服务器的配置" |
| `delete_server_config` | 删除服务器配置 | "删除名为test-server的配置" |

### 🔧 诊断与故障排除工具

| 工具名称 | 功能描述 | Cursor使用示例 |
|---------|---------|---------------|
| `diagnose_connection` | 诊断连接问题并提供解决方案 | "诊断production服务器的连接问题" |

### 🎯 智能交互特性

#### 1. **自动工具选择**
你无需记住具体的工具名称，只需用自然语言描述需求：

```
✅ "我想看看有哪些服务器" → AI自动使用 list_servers
✅ "连接到我的开发服务器" → AI自动使用 connect_server  
✅ "检查服务器是否在线" → AI自动使用 get_server_status
✅ "在服务器上查看进程" → AI自动使用 execute_command
✅ "添加一台新服务器" → AI自动使用 create_server_config
```

#### 2. **交互式配置体验**
配置管理工具提供两种交互模式：

**🖥️ 终端交互模式（默认）**
- 自动弹出Terminal窗口
- 彩色表单界面
- 实时输入验证
- 智能默认值推荐

**💬 聊天界面模式（可选）**
- 直接在Cursor聊天界面配置
- 分步骤引导配置
- 无需切换窗口

#### 3. **预填充参数支持**
你可以在请求中提供部分参数，工具会自动预填充：

```
"我想添加一个名为production的服务器，IP是192.168.1.100"
→ AI会预填充这些信息到配置表单中
```

#### 4. **Docker配置自动化**
支持完整的Docker容器管理：

```yaml
# 自动生成的Docker配置示例
specs:
  docker:
    enabled: true
    image: "ubuntu:20.04"
    container: "my-dev-container"
    ports: ["8080:8080", "8888:8888"]
    volumes: ["/home:/home", "/data:/data"]
    shell: "bash"
    auto_create: true
```

#### 5. **智能错误处理**
工具提供详细的错误诊断和解决建议：

```
❌ 连接失败 → 自动运行 diagnose_connection
❌ 配置错误 → 提供具体的修复建议  
❌ 权限问题 → 给出权限设置指导
```

## 📝 使用场景示例

### 场景1：开发环境管理

```
用户：我想新增一个开发服务器
AI：我来启动配置向导帮你设置...
    [启动交互式配置向导]
    - 请输入服务器名称...
    - 请输入服务器IP地址...
    - 请输入用户名...
    - 选择认证方式：SSH密钥 / 密码
    - 是否需要Docker支持？
    [配置完成，自动测试连接]
```

### 场景2：跳板机配置

```
用户：我想新增一个通过跳板机连接的服务器
AI：我来启动配置向导帮你设置跳板机连接...
    [启动交互式配置向导]
    - 请输入服务器名称：production-server
    - 选择连接方式：Relay跳板机连接
    - 请输入目标服务器地址：target-server.com
    - 请输入目标服务器用户名：ubuntu
    - 请输入跳板机地址：jumphost.com
    - 请输入跳板机用户名：admin
    - 是否需要二级跳板机？选择：是
    [二级跳板机配置]
    - 请输入二级跳板机地址：secondary-jumphost.com
    - 请输入二级跳板机用户名：root
    [配置完成，自动测试连接]
```

### 场景3：Docker容器配置

```
用户：我想新增一个GPU训练服务器
AI：启动配置向导...
    [配置向导询问]
    - 请输入服务器信息...
    - 是否需要Docker支持？选择：是
    [Docker环境配置向导]
    - 选择基础镜像：Ubuntu 20.04 / PyTorch官方镜像
    - GPU支持：是否启用NVIDIA GPU
    - 端口映射：Jupyter (8888), TensorBoard (6006)
    - 挂载目录：代码目录、数据目录
    [创建并启动容器]
```

### 场景4：多服务器监控

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
ls -la ~/.remote-terminal/

# 重置配置（在Cursor中说）
"请帮我重置远程服务器配置"
# 或者手动重置
rm -rf ~/.remote-terminal/
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

### v0.15.0 (最新) - 2024年12月22日
- 🎯 **重大功能升级**：完整的11个MCP工具集成
- ✨ **交互式配置体验**：支持Terminal和聊天界面两种配置模式
- 🐳 **Docker配置自动化**：完整的Docker容器管理和自动创建
- 🔧 **智能参数预填充**：配置时支持参数预填充和智能默认值
- 🛠️ **强化错误处理**：完善的连接诊断和故障排除机制
- 📝 **全面测试覆盖**：39项回归测试确保稳定性
- 🔄 **配置同步机制**：update_server_config与create保持一致的交互体验

### v0.8.3
- 🐛 修复服务器删除功能的逻辑问题
- ✨ 改进配置备份机制
- 📝 完善文档和使用指南

### v0.8.2
- ✨ 增强配置管理功能
- 🐳 完善Docker支持
- 🔧 优化连接稳定性

---

💡 **提示**：这个工具专为Cursor设计，通过AI助手的自然语言交互，让远程服务器管理变得简单直观。开始使用时，只需要告诉AI你想做什么，它会自动选择合适的工具来完成任务！