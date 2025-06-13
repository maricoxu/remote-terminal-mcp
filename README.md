# Remote Terminal MCP

一个基于 Model Context Protocol (MCP) 的远程终端管理工具，旨在简化远程服务器连接和管理流程。

## 🚀 特性

- **🔧 交互式配置**：友好的配置向导，无需手动编写YAML
- **🌐 多种连接方式**：支持SSH、跳板机、Docker等连接模式
- **⚡ 快速上手**：预设模板，一键配置常用场景
- **🛠️ 完整管理**：配置创建、编辑、测试、导入导出
- **🔒 安全可靠**：支持SSH密钥、跳板机认证等安全连接
- **📱 用户友好**：渐进式复杂度，从新手到专家

## 📦 安装

### 前置要求

- Python 3.8+
- Node.js 16+ (可选，用于NPM安装)

### 方式1: 直接使用

```bash
git clone https://github.com/your-username/remote-terminal-mcp.git
cd remote-terminal-mcp
pip install -r requirements.txt
```

### 方式2: NPM安装

```bash
npm install remote-terminal-mcp
```

## 🎯 快速开始

### 1. 快速配置向导

```bash
python3 config-helper.py --quick
```

选择您的服务器类型：
- 🖥️ 普通Linux服务器 (直接SSH)
- 🌉 内网服务器 (通过relay-cli)
- 🐳 带Docker环境的开发服务器
- 🎯 自定义配置

### 2. 完整配置管理

```bash
python3 config-helper.py
```

提供8个完整功能：
1. 📝 创建新服务器配置
2. 📋 查看现有配置
3. ✏️ 编辑服务器配置
4. 🗑️ 删除服务器配置
5. 🧪 测试服务器连接
6. 📤 导出配置
7. 📥 导入配置
8. 🚪 退出

## 📖 使用示例

### 配置SSH服务器

```bash
python3 config-helper.py --quick

# 选择: 1. 普通Linux服务器
# 输入服务器信息
服务器名称: my-server
服务器地址: 192.168.1.100
用户名: developer
```

### 配置内网服务器

```bash
python3 config-helper.py --quick

# 选择: 2. 内网服务器
# 输入跳板机信息
服务器名称: internal-dev
目标服务器地址: internal-server.company.com
用户名: developer
```

### 配置Docker环境

```bash
python3 config-helper.py --quick

# 选择: 3. Docker开发服务器
# 输入Docker信息
服务器名称: docker-dev
服务器地址: 192.168.1.200
Docker容器名: dev-container
```

## 🏗️ 项目结构

```
remote-terminal-mcp/
├── python/
│   ├── mcp_server.py              # 主MCP服务器
│   ├── ssh_manager.py             # SSH连接管理
│   ├── interactive_config.py      # 交互式配置管理器
│   └── enhanced_ssh_manager.py    # 增强SSH管理器
├── config-helper.py               # 配置助手工具
├── package.json                   # NPM配置
├── README.md                      # 项目文档
├── DEVELOPMENT_ROADMAP.md         # 开发规划
├── PROGRESS.md                    # 开发进度
└── INTERACTIVE_CONFIG_GUIDE.md    # 配置指南
```

## ⚙️ 配置文件

配置文件位置：`~/.remote-terminal-mcp/config.yaml`

### 基本配置示例

```yaml
my-server:
  description: "开发服务器"
  host: "192.168.1.100"
  username: "developer"
  port: 22

internal-server:
  description: "内网服务器"
  host: "relay.company.com"
  username: "developer"
  port: 22
  specs:
    connection:
      tool: "relay"
      target:
        host: "internal-server.company.com"

docker-server:
  description: "Docker开发环境"
  host: "192.168.1.200"
  username: "developer"
  specs:
    docker:
      container: "dev-container"
      image: "ubuntu:20.04"
```

## 🔧 高级功能

### 连接方式

1. **直接SSH连接**
   - 适用于公网或局域网服务器
   - 简单配置，稳定连接

2. **跳板机连接**
   - 支持relay-cli工具
   - 适用于内网环境
   - 自动认证处理

3. **二级跳板机**
   - 复杂网络环境
   - 多级跳转支持
   - 灵活路由配置

### Docker支持

- 自动容器管理
- 容器自动创建
- 开发环境隔离
- 工作目录配置

### 环境配置

- 存储桶同步
- 环境变量设置
- Tmux会话管理
- 自定义工作目录

## 🧪 测试连接

```bash
# 测试特定服务器
python3 config-helper.py --test my-server

# 列出所有配置
python3 config-helper.py --list
```

## 📚 文档

- [交互式配置指南](INTERACTIVE_CONFIG_GUIDE.md)
- [开发规划](DEVELOPMENT_ROADMAP.md)
- [开发进度](PROGRESS.md)

## 🛠️ 开发

### 本地开发

```bash
git clone https://github.com/your-username/remote-terminal-mcp.git
cd remote-terminal-mcp
pip install -r requirements.txt

# 运行配置工具
python3 config-helper.py

# 运行MCP服务器
python3 python/mcp_server.py
```

### 测试

```bash
# 运行测试
python3 -m pytest tests/

# 配置验证
python3 config-helper.py --test all
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 提交规范

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构
- `test:` 测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果遇到问题或有建议：

1. 查看 [配置指南](INTERACTIVE_CONFIG_GUIDE.md)
2. 使用测试功能诊断问题
3. 提交 Issue 或 Pull Request

## 🎯 路线图

- ✅ 基础MCP服务器
- ✅ 交互式配置系统
- ✅ 多种连接方式支持
- 🚧 智能默认值系统
- 📋 连接状态监控
- 📋 文件传输集成
- 📋 企业级功能

---

**⭐ 如果这个项目对您有帮助，请给我们一个星标！**