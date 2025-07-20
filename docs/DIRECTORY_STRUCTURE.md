# 项目目录结构说明

## 📁 根目录文件
- `README.md` - 项目主要说明文档
- `LICENSE` - 项目许可证
- `.gitignore` - Git忽略文件配置
- `requirements.txt` - Python依赖包列表
- `.npmignore` - NPM忽略文件配置

## 📁 核心目录

### `python/` - Python核心代码
- `mcp_server.py` - MCP服务器主程序
- `config_manager/` - 配置管理模块
- `enhanced_ssh_manager.py` - SSH连接管理器
- `tests/` - Python测试文件
- `create_server_config.py` - 服务器配置创建工具
- `update_server_config.py` - 服务器配置更新工具

### `tests/` - 主测试目录
- 包含所有测试用例和测试工具
- 回归测试和集成测试

### `docs/` - 文档目录
- `*.md` - 所有Markdown文档
- `reports/` - 测试报告和日志

### `scripts/` - 脚本工具目录
- `*.py` - Python脚本文件
- `*.js` - JavaScript脚本文件
- `*.sh` - Shell脚本文件

### `tools/` - 测试工具目录
- `test_*.py` - 测试相关工具
- 调试和验证工具

### `config/` - 配置文件目录
- `*.yaml` - YAML配置文件
- `*.json` - JSON配置文件
- `.cursorrules` - Cursor编辑器规则
- `.windsurfrules` - Windsurf编辑器规则

### `logs/` - 日志文件目录
- `pytest_report_*.txt` - Pytest测试报告
- `pytest_tool_*.log` - 工具测试日志
- `batch_*.txt` - 批量测试报告

### `backup/` - 备份文件目录
- 旧版本的配置文件和脚本
- 压缩包和临时文件

### `templates/` - 模板文件目录
- 配置模板和示例文件

### `docker_templates/` - Docker模板目录
- Docker容器配置模板

### `docker_configs/` - Docker配置目录
- Docker相关配置文件

## 🎯 使用建议

1. **开发时**：主要使用 `python/` 目录下的文件
2. **测试时**：使用 `tests/` 目录下的测试文件
3. **配置时**：使用 `config/` 目录下的配置文件
4. **文档查看**：查看 `docs/` 目录下的文档
5. **脚本执行**：使用 `scripts/` 目录下的工具脚本

## 📝 注意事项

- 根目录保持简洁，只保留必要的项目文件
- 所有功能代码都在 `python/` 目录下
- 测试文件统一在 `tests/` 目录下
- 文档和报告统一在 `docs/` 目录下
- 工具脚本统一在 `scripts/` 目录下 