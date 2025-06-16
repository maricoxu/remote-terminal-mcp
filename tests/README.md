# Remote Terminal MCP 测试指南

这个目录包含了 Remote Terminal MCP 项目的完整测试套件，旨在确保代码质量和防止回归问题。

## 📁 测试目录结构

```
tests/
├── local/                    # 本地开发环境测试
│   ├── test_regression_prevention.py  # 回归测试
│   └── test_mcp_tools.py              # MCP工具测试
├── npm/                      # npm包测试
│   └── test_package_integrity.py      # 包完整性测试
├── integration/              # 集成测试
│   └── test_end_to_end.py             # 端到端测试
├── utils/                    # 测试工具
│   └── test_helpers.py               # 测试辅助函数
├── run_tests.py             # 测试运行器
└── README.md               # 本文档
```

## 🚀 快速开始

### 运行所有测试
```bash
npm test
# 或者
python3 tests/run_tests.py
```

### 运行特定类型的测试
```bash
# 本地开发测试
npm run test:local

# npm包测试
npm run test:npm

# 集成测试
npm run test:integration

# 详细输出
npm run test:verbose
```

### 提交前测试
```bash
npm run test:pre-commit
```

### 发布前测试
```bash
npm run test:pre-publish
```

## 📋 测试类型说明

### 1. 本地测试 (local/)
- **目的**: 测试本地开发环境中的功能
- **包含**: 
  - 回归测试：防止已修复的问题再次出现
  - MCP工具测试：验证MCP服务器功能
  - 配置管理测试：确保配置系统正常工作
- **运行时机**: 开发过程中、提交前

### 2. NPM包测试 (npm/)
- **目的**: 验证npm包的完整性和可发布性
- **包含**:
  - 包结构测试：检查必要文件是否存在
  - 权限测试：确保文件有正确的执行权限
  - 依赖测试：验证依赖项配置正确
  - 安装测试：模拟npm安装过程
- **运行时机**: 发布前

### 3. 集成测试 (integration/)
- **目的**: 测试完整的用户工作流程
- **包含**:
  - 端到端工作流程测试
  - 用户场景测试
  - 错误处理测试
- **运行时机**: 发布前、重大更改后

## 🛠️ 测试工具

### TestRunner (run_tests.py)
主要的测试运行器，支持：
- 自动发现测试文件
- 分类运行测试
- 生成测试报告
- 提供详细的错误信息

### TestHelpers (utils/test_helpers.py)
提供通用的测试工具：
- `TestEnvironment`: 测试环境管理
- `MockConfigManager`: 模拟配置管理器
- `BaseTestCase`: 基础测试用例类
- 各种辅助函数

## 📊 测试报告

测试运行后会生成详细的报告文件：
- 位置: `tests/test_report_<type>_<timestamp>.txt`
- 包含: 测试结果统计、失败详情、运行时间等

## 🔧 开发工作流程

### 日常开发
1. 修改代码
2. 运行相关的本地测试: `npm run test:local`
3. 修复任何失败的测试

### 提交前
1. 运行提交前测试: `npm run test:pre-commit`
2. 确保所有测试通过
3. 提交代码

### 发布前
1. 运行完整测试套件: `npm run test:pre-publish`
2. 确保所有测试通过
3. 发布包

## 📝 编写新测试

### 添加本地测试
1. 在 `tests/local/` 目录创建 `test_*.py` 文件
2. 继承 `BaseTestCase` 类
3. 编写测试方法（以 `test_` 开头）

```python
from test_helpers import BaseTestCase

class TestMyFeature(BaseTestCase):
    def test_my_feature(self):
        # 测试代码
        self.assertTrue(True, "测试通过")
```

### 添加npm测试
1. 在 `tests/npm/` 目录创建测试文件
2. 专注于包相关的测试（结构、权限、安装等）

### 添加集成测试
1. 在 `tests/integration/` 目录创建测试文件
2. 测试完整的用户工作流程

## 🚨 回归测试

回归测试专门用于防止已修复的问题再次出现：

### 当前回归测试覆盖
- 配置目录一致性（防止 `.remote-terminal` vs `.remote-terminal-mcp` 问题）
- MCP工具可用性
- Docker命令生成完整性
- 配置管理器API稳定性

### 添加新的回归测试
当发现并修复bug时，应该：
1. 在 `tests/local/test_regression_prevention.py` 中添加相应测试
2. 确保测试能够检测到该问题
3. 验证修复后测试通过

## 🔍 故障排除

### 测试失败
1. 查看详细的错误信息
2. 检查测试报告文件
3. 使用 `-v` 参数获取更详细的输出

### 导入错误
确保Python路径正确设置，测试运行器会自动处理大部分路径问题。

### 权限问题
确保测试文件有执行权限：
```bash
chmod +x tests/run_tests.py
```

## 📈 持续改进

### 测试覆盖率
定期检查测试覆盖率，确保新功能有相应的测试。

### 性能监控
监控测试运行时间，优化慢速测试。

### 测试维护
- 定期更新测试以反映代码变化
- 删除过时的测试
- 重构重复的测试代码

## 🤝 贡献指南

### 提交测试
1. 确保测试有清晰的文档
2. 使用描述性的测试名称
3. 包含必要的断言和错误信息

### 代码风格
- 使用中文注释和文档字符串
- 遵循项目的代码风格
- 保持测试简洁明了

---

通过这个完整的测试框架，我们可以确保 Remote Terminal MCP 项目的质量和稳定性，防止回归问题，并为持续开发提供信心。 