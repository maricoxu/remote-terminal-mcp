# 回归测试目录

## 📋 目录说明

本目录专门用于存放回归测试案例，确保每次问题修复后不会出现功能回退。

## 🎯 文件命名规范

测试文件请按以下格式命名：
```
test_fix_[问题描述]_[日期].py
```

示例：
- `test_fix_ssh_connection_timeout_20240622.py`
- `test_fix_config_validation_error_20240622.py`
- `test_fix_docker_container_start_20240622.py`

## 📝 测试内容要求

每个回归测试文件应该包含：

### 1. 问题复现测试
```python
def test_reproduce_original_issue():
    """复现原始问题的最小案例"""
    pass
```

### 2. 修复验证测试
```python
def test_verify_fix():
    """验证问题已被正确修复"""
    pass
```

### 3. 边界条件测试
```python
def test_boundary_conditions():
    """测试相关的边界条件"""
    pass
```

### 4. 集成测试
```python
def test_integration_with_other_components():
    """确保修复不影响其他功能"""
    pass
```

## 🔧 MCP工具测试规范

所有测试必须通过MCP工具来执行验证，不允许使用额外脚本：

```python
import asyncio
from mcp_testing_utils import MCPTestClient

async def test_mcp_functionality():
    """使用MCP工具进行功能测试"""
    client = MCPTestClient()
    
    # 使用list_servers验证配置
    servers = await client.call_tool("list_servers")
    
    # 使用connect_server测试连接
    result = await client.call_tool("connect_server", {
        "server_name": "test-server"
    })
    
    # 使用execute_command验证命令执行
    cmd_result = await client.call_tool("execute_command", {
        "command": "echo 'test'",
        "server": "test-server"
    })
    
    assert "test" in cmd_result
```

## 📊 测试运行

运行所有回归测试：
```bash
python -m pytest tests/regression/ -v
```

运行特定日期的测试：
```bash
python -m pytest tests/regression/test_fix_*20240622*.py -v
```

## 🚨 质量保证规则（强制执行）

### 🔴 强制性回归测试要求

**每修复一个问题后，必须无条件执行以下流程：**

1. **立即创建测试案例**：
   - 在 `tests/regression/` 目录下创建对应的测试文件
   - 测试文件命名格式：`test_fix_[问题描述]_[日期].py`
   - 测试必须能够独立运行并验证修复效果

2. **全量回归测试执行**：
   - 运行 `scripts/run-regression-tests.sh` 执行所有回归测试
   - 确保新修复不会破坏已有功能
   - 所有测试必须通过才能提交代码

3. **质量门禁**：
   - 🚫 没有回归测试的修复不允许提交
   - 🚫 回归测试失败的代码不允许合并
   - 🚫 测试覆盖不足的修复必须补充测试
   - ✅ 只有通过全部回归测试的代码才能发布

### 🔄 强制修复工作流

1. **问题分析**：使用结构化思维分析问题
2. **测试先行**：先写能复现问题的测试案例（TDD原则）
3. **代码修改**：按照MCP优先原则修改代码
4. **MCP测试**：使用MCP工具验证修复效果
5. **回归测试验证**：确保新测试通过，验证问题已修复
6. **全量回归测试**：运行所有回归测试，确保无破坏性变更
7. **测试结果确认**：所有测试必须通过才能继续
8. **文档更新**：更新相关文档和说明
9. **提交规范**：使用规范的commit信息，包含测试信息

## 📚 测试最佳实践

1. **测试独立性**：每个测试都应该能独立运行
2. **环境清理**：测试后要清理测试环境
3. **清晰断言**：使用有意义的断言消息
4. **文档完整**：每个测试都要有详细的中文注释
5. **MCP优先**：优先使用MCP工具进行验证
6. **测试先行**：发现问题时，先写测试再修复
7. **全量验证**：每次修复都要运行全部回归测试 