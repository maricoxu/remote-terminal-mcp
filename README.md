# Remote Terminal MCP

一个强大的远程终端管理模块化控制协议(MCP)服务器，为Cursor提供完整的远程服务器配置、连接管理和代码同步功能。

## 🌟 主要功能

- **智能服务器配置** - 支持SSH直连、Relay跳板机、Docker容器
- **代码同步系统** - 自动同步本地和远程代码库
- **FTP服务部署** - 自动部署和管理远程FTP服务
- **Git集成** - 本地stash和远程同步
- **配置管理** - 完整的服务器配置向导

## 🚀 快速开始

### 安装

```bash
npm install @xuyehua/remote-terminal-mcp
```

### 配置

在Cursor中配置MCP服务器：

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["@xuyehua/remote-terminal-mcp"],
      "env": {}
    }
  }
}
```

## 🔄 同步工具使用指南

### 1. Git同步工具 (`git_sync`)

**功能**: 同步本地和远程代码库，确保代码一致性

**使用场景**: 
- 开发前同步远程最新代码
- 确保本地和远程代码库一致
- 备份本地修改并同步远程代码

**提示词示例**:

```markdown
# 基本同步
请帮我同步代码库，服务器名称是 "prod-server"，本地路径是 "/Users/me/projects/myapp"，远程路径是 "/home/user/myapp"，使用main分支

# 指定分支同步
请使用git_sync工具同步代码，服务器：dev-server，本地路径：/Users/me/dev/project，远程路径：/home/dev/project，分支：develop

# 强制同步
请强制同步代码库，服务器：test-server，本地路径：/Users/me/test/app，远程路径：/home/test/app，分支：feature/new-ui，强制模式

# 同步到特定提交
请同步代码到特定提交，服务器：prod-server，本地路径：/Users/me/prod/app，远程路径：/home/prod/app，提交哈希：abc123def
```

**参数说明**:
- `server_name`: 服务器名称（必需）
- `local_path`: 本地Git仓库路径（必需）
- `remote_path`: 远程Git仓库路径（必需）
- `branch`: Git分支名称（可选）
- `commit_hash`: 特定提交哈希（可选）
- `force`: 强制同步（可选，默认false）

### 2. 自动同步启用工具 (`autosync_enable`)

**功能**: 启用自动同步，部署远程FTP服务并配置本地同步

**使用场景**:
- 开发过程中自动同步本地修改到远程
- 部署远程FTP服务用于文件同步
- 配置VSCode SFTP扩展

**提示词示例**:

```markdown
# 启用自动同步
请启用自动同步功能，服务器：dev-server，本地路径：/Users/me/dev/project，远程路径：/home/dev/project

# 使用默认路径启用
请为prod-server启用自动同步，使用配置中的默认路径

# 自定义FTP配置
请启用自动同步，服务器：test-server，本地路径：/Users/me/test/app，远程路径：/home/test/app，FTP端口：8021，FTP用户：syncuser

# 完整配置启用
请启用自动同步功能，包含以下配置：
- 服务器：prod-server
- 本地路径：/Users/me/prod/app
- 远程路径：/home/prod/app
- FTP端口：8021
- FTP用户：syncuser
- FTP密码：syncpass
```

**参数说明**:
- `server_name`: 服务器名称（必需）
- `local_path`: 本地工作目录（可选，默认使用配置）
- `remote_path`: 远程工作目录（可选，默认使用配置）

### 3. 自动同步禁用工具 (`autosync_disable`)

**功能**: 禁用自动同步，停止远程FTP服务

**使用场景**:
- 开发完成后停止自动同步
- 停止远程FTP服务
- 清理同步配置

**提示词示例**:

```markdown
# 禁用自动同步
请禁用prod-server的自动同步功能

# 停止同步服务
请停止dev-server的自动同步服务

# 清理同步配置
请为test-server禁用自动同步并清理相关配置
```

**参数说明**:
- `server_name`: 服务器名称（必需）

## 📋 完整工作流程示例

### 开发工作流程

```markdown
# 1. 开始开发前 - 同步代码
请帮我同步代码库，确保本地和远程一致：
- 服务器：dev-server
- 本地路径：/Users/me/dev/project
- 远程路径：/home/dev/project
- 分支：main

# 2. 启用自动同步 - 开始开发
请启用自动同步功能，这样我修改代码时会自动同步到远程：
- 服务器：dev-server
- 本地路径：/Users/me/dev/project
- 远程路径：/home/dev/project

# 3. 开发完成后 - 停止同步
请禁用dev-server的自动同步功能
```

### 部署工作流程

```markdown
# 1. 同步生产代码
请同步生产环境代码：
- 服务器：prod-server
- 本地路径：/Users/me/prod/app
- 远程路径：/home/prod/app
- 分支：release

# 2. 启用生产同步
请为生产环境启用自动同步：
- 服务器：prod-server
- 本地路径：/Users/me/prod/app
- 远程路径：/home/prod/app

# 3. 部署完成后停止
请禁用prod-server的自动同步
```

## 🔧 高级配置

### 服务器配置

在配置向导中可以设置：
- SSH连接信息（主机、用户名、端口）
- Docker容器配置
- 同步配置（FTP端口、用户名、密码）
- 文件包含/排除模式

### 同步配置选项

- **FTP端口**: 默认8021
- **FTP用户**: 默认syncuser
- **包含模式**: *.py, *.js, *.md
- **排除模式**: *.pyc, __pycache__, .git

## 🛠️ 故障排除

### 常见问题

1. **路径不存在错误**
   ```
   错误：本地路径不存在: /path/to/local
   解决：确保指定的本地路径存在
   ```

2. **非Git仓库错误**
   ```
   错误：本地路径不是Git仓库: /path/to/local
   解决：确保本地路径包含.git目录
   ```

3. **FTP服务启动失败**
   ```
   错误：远程FTP服务启动失败
   解决：检查远程服务器权限和网络连接
   ```

### 调试命令

```bash
# 检查同步状态
请获取dev-server的同步状态

# 查看服务器配置
请列出所有服务器配置

# 测试连接
请诊断dev-server的连接状态
```

## 📚 更多资源

- [项目文档](docs/)
- [配置指南](docs/CONFIGURATION_GUIDE.md)
- [开发指南](docs/DEVELOPMENT_GUIDE.md)
- [问题反馈](https://github.com/maricoxu/remote-terminal-mcp/issues)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## �� 许可证

MIT License
