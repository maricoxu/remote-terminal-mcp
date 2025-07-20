# Remote Terminal MCP 本地开发指南

## 概述

本指南帮助你在本地开发和测试Remote Terminal MCP，在稳定后再发布到npm。

## 目录结构

```
remote-terminal-mcp/
├── index.js                    # Node.js入口文件（supervisor）
├── python/
│   └── mcp_server.py          # Python MCP服务器
├── enhanced_config_manager.py  # 配置管理模块
├── local-dev.sh               # 本地开发脚本
├── update_mcp_config.js       # MCP配置更新脚本
├── test_local_mcp.js          # 本地MCP测试脚本
└── package.json               # npm包配置
```

## 快速开始

### 1. 设置本地MCP环境

```bash
# 运行设置脚本
./local-dev.sh setup

# 或者手动配置
node update_mcp_config.js add-local
```

### 2. 测试MCP服务器

```bash
# 运行快速测试
./local-dev.sh test

# 或者
node test_local_mcp.js
```

### 3. 启动MCP服务器（调试模式）

```bash
# 启动服务器进行调试
./local-dev.sh start
```

### 4. 在Cursor中使用

配置已自动更新到 `~/.cursor/mcp.json`，重启Cursor即可使用本地版本。

## 开发工作流

### 阶段1：本地开发

1. **修改代码**
   - 编辑 `python/mcp_server.py` 或其他文件
   - 保存更改

2. **测试功能**
   ```bash
   # 运行本地测试
   ./local-dev.sh test
   
   # 检查状态
   node update_mcp_config.js status
   ```

3. **在Cursor中验证**
   - 重启Cursor
   - 使用MCP工具测试功能

### 阶段2：稳定性验证

1. **全面测试**
   ```bash
   # 运行所有测试
   npm test
   
   # 运行特定测试
   npm run test:local
   npm run test:integration
   ```

2. **长期运行测试**
   ```bash
   # 启动服务器并保持运行
   ./local-dev.sh start
   ```

### 阶段3：准备发布

1. **恢复npm版本配置**
   ```bash
   node update_mcp_config.js restore-npm
   ```

2. **版本管理**
   ```bash
   # 更新版本
   npm run version:patch  # 或 minor, major
   
   # 发布到npm
   npm run publish:patch  # 或 minor, major
   ```

## 配置管理

### 当前状态检查

```bash
node update_mcp_config.js status
```

### 切换版本

```bash
# 使用本地版本
node update_mcp_config.js add-local

# 恢复npm版本
node update_mcp_config.js restore-npm
```

## 调试工具

### 1. 本地开发脚本 (`local-dev.sh`)

```bash
./local-dev.sh help        # 显示帮助
./local-dev.sh setup       # 设置环境
./local-dev.sh test        # 运行测试
./local-dev.sh start       # 启动服务器
./local-dev.sh config      # 显示配置
./local-dev.sh clean       # 清理临时文件
```

### 2. MCP配置管理 (`update_mcp_config.js`)

```bash
node update_mcp_config.js add-local     # 添加本地版本
node update_mcp_config.js restore-npm   # 恢复npm版本
node update_mcp_config.js status        # 显示状态
```

### 3. 测试脚本 (`test_local_mcp.js`)

```bash
node test_local_mcp.js     # 运行MCP服务器测试
```

## 环境变量

本地开发时会自动设置以下环境变量：

- `MCP_DEBUG=1` - 启用调试模式
- `MCP_LOCAL_MODE=true` - 本地开发模式
- `PYTHONPATH=/path/to/project` - Python路径

## 日志和调试

### 查看日志

```bash
# 启动时会显示详细日志
./local-dev.sh start

# 或者直接运行
MCP_DEBUG=1 node index.js
```

### 调试Python代码

在 `python/mcp_server.py` 中添加调试输出：

```python
import sys
print(f"[DEBUG] Your debug message", file=sys.stderr)
```

## 常见问题

### 1. Python依赖问题

```bash
# 手动安装依赖
python3 -m pip install -r requirements.txt --user
```

### 2. 权限问题

```bash
# 确保脚本有执行权限
chmod +x local-dev.sh
chmod +x test_local_mcp.js
```

### 3. Cursor不识别本地版本

- 确保重启Cursor
- 检查 `~/.cursor/mcp.json` 配置
- 运行 `node update_mcp_config.js status` 检查状态

### 4. 配置备份

每次修改 `~/.cursor/mcp.json` 都会自动创建备份：

```bash
ls -la ~/.cursor/mcp.json.backup.*
```

## 发布流程

当本地版本稳定后：

1. **提交代码**
   ```bash
   git add .
   git commit -m "feat: stable local version ready for npm"
   ```

2. **恢复npm配置**
   ```bash
   node update_mcp_config.js restore-npm
   ```

3. **运行预发布测试**
   ```bash
   npm run test:pre-publish
   ```

4. **发布到npm**
   ```bash
   npm run publish:patch
   ```

5. **验证npm版本**
   - 重启Cursor
   - 确认使用npm版本正常工作

## 注意事项

1. **不要同时启用本地版本和npm版本** - 可能会造成冲突
2. **本地开发时记得定期备份配置** - 配置更新脚本会自动备份
3. **发布前务必运行完整测试** - 确保所有功能正常
4. **保持版本同步** - 本地测试通过后及时发布

## 支持

如有问题，请查看：
- 日志输出
- 配置文件状态
- Python依赖安装情况
- Cursor重启情况 