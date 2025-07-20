# 🚀 Remote Terminal MCP 快速设置指南

在新电脑上快速恢复本地开发环境。

## 第一步：克隆仓库

```bash
git clone https://github.com/maricoxu/remote-terminal-mcp.git
cd remote-terminal-mcp
```

## 第二步：一键设置

```bash
# 检查环境状态
./check_mcp_status.sh

# 设置本地开发环境
./local-dev.sh setup

# 验证功能
./local-dev.sh test
```

## 第三步：配置Cursor

本地MCP配置已自动添加到 `~/.cursor/mcp.json`

**重启Cursor** 即可使用本地版本！

## 快速验证

运行以下命令确认一切正常：

```bash
# 检查整体状态
./check_mcp_status.sh

# 查看MCP配置状态
node update_mcp_config.js status

# 测试MCP服务器
./local-dev.sh test
```

应该看到：
- ✅ 本地版本: 已配置
- ⏸️ NPM版本: 已禁用

## 开始开发

```bash
# 启动调试服务器
./local-dev.sh start

# 在Cursor中使用MCP工具测试功能
# 修改代码后直接测试，无需重新安装
```

## 发布流程

稳定后准备发布：

```bash
# 恢复npm版本
node update_mcp_config.js restore-npm

# 发布到npm
npm run publish:patch
```

## 工具说明

| 脚本 | 功能 |
|------|------|
| `./check_mcp_status.sh` | 环境状态检查 |
| `./local-dev.sh setup` | 一键环境设置 |
| `./local-dev.sh test` | 功能测试 |
| `./local-dev.sh start` | 启动调试服务器 |
| `node update_mcp_config.js status` | MCP配置状态 |

---

**就是这么简单！** 🎉 