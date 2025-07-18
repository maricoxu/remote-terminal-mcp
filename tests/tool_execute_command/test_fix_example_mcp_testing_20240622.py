#!/usr/bin/env python3
"""
回归测试示例：MCP工具测试框架验证

测试文件说明：
- 问题描述：展示如何使用MCP工具进行功能测试
- 修复日期：2024-06-22
- 测试目标：验证MCP工具调用框架的正确性

此文件作为回归测试的模板和示例使用
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 添加测试工具路径
# 保证兼容老路径，优先从 tests/utils 代理到 python/tests/utils
# 统一用绝对路径导入，彻底避免循环和路径问题
from python.tests.utils.mcp_testing_utils import (
    MCPTestClient, 
    MCPTestEnvironment, 
    MCPTestError,
    create_mcp_test_client,
    create_test_environment
)


class TestMCPToolingFramework:
    """MCP工具测试框架验证测试类"""
    
    @pytest.mark.asyncio
    async def test_reproduce_original_issue(self):
        """
        复现原始问题的最小案例
        
        假设问题：MCP工具调用时无法正确处理错误响应
        """
        # 这里是问题复现逻辑的示例
        # 在实际使用中，这里应该包含能够复现原始问题的最小代码
        
        client = create_mcp_test_client()
        
        # 尝试调用不存在的工具，应该得到明确的错误信息
        with pytest.raises(MCPTestError) as exc_info:
            await client.call_tool("non_existent_tool")
            
        # 验证错误信息是否包含期望的内容
        assert "non_existent_tool" in str(exc_info.value) or "不存在" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_verify_fix(self):
        """
        验证问题已被正确修复
        
        测试MCP工具调用能够正确处理正常情况和异常情况
        """
        async with create_test_environment() as test_env:
            client = create_mcp_test_client()
            
            # 测试正常的MCP工具调用
            try:
                # list_servers 应该正常工作（即使没有配置服务器），使用较短超时避免卡住
                result = await client.call_tool("list_servers", {}, timeout=3.0)
                
                # 结果应该是可解析的（可能是空列表或包含服务器信息）
                assert isinstance(result, (list, str))
                
            except MCPTestError as e:
                # 如果有错误，应该是有意义的错误信息
                assert len(str(e)) > 0
                assert "MCP" in str(e) or "服务器" in str(e) or "超时" in str(e)
                
    @pytest.mark.asyncio
    async def test_boundary_conditions(self):
        """
        测试相关的边界条件
        
        测试MCP工具在各种边界条件下的表现
        """
        client = create_mcp_test_client()
        
        # 测试空参数调用
        try:
            await client.call_tool("list_servers", {}, timeout=2.0)
            # 应该正常工作
        except MCPTestError:
            # 或者给出明确的错误信息
            pass
            
        # 测试无效参数类型
        with pytest.raises((MCPTestError, TypeError, ValueError)):
            await client.call_tool("connect_server", {"server_name": None}, timeout=2.0)
            
        # 测试超长参数
        with pytest.raises((MCPTestError, ValueError)):
            long_name = "x" * 10000
            await client.call_tool("connect_server", {"server_name": long_name}, timeout=2.0)
            
    @pytest.mark.asyncio
    async def test_integration_with_other_components(self):
        """
        确保修复不影响其他功能
        
        测试MCP工具调用与其他组件的集成
        """
        async with create_test_environment() as test_env:
            client = create_mcp_test_client()
            
            # 创建测试配置
            test_config = {
                "servers": {
                    "test-server": {
                        "type": "ssh",
                        "host": "localhost",
                        "user": "testuser",
                        "port": 22
                    }
                }
            }
            
            test_env.create_test_config("test-server", test_config)
            
            # 测试配置读取功能
            servers = None
            try:
                servers = await client.call_tool("list_servers", {}, timeout=3.0)
                # 应该能够读取到配置（或给出合理的错误信息）
                assert isinstance(servers, (list, str))
                
            except MCPTestError as e:
                # 错误信息应该有意义
                error_msg = str(e)
                assert len(error_msg) > 0
                
            # 测试服务器信息获取
            try:
                if isinstance(servers, list) and len(servers) > 0:
                    # 如果有服务器，尝试获取详细信息
                    info = await client.call_tool("get_server_info", {"server_name": "test-server"}, timeout=3.0)
                    assert isinstance(info, (dict, str))
                    
            except MCPTestError:
                # 在测试环境中可能无法连接，这是正常的
                pass
                
    @pytest.mark.asyncio
    async def test_mcp_tool_error_handling(self):
        """
        测试MCP工具的错误处理机制
        
        验证各种错误情况下的响应是否正确
        """
        client = create_mcp_test_client()
        
        # 测试连接不存在的服务器
        with pytest.raises(MCPTestError):
            await client.call_tool("connect_server", {"server_name": "non_existent_server"}, timeout=2.0)
            
        # 测试在未连接时执行命令
        with pytest.raises(MCPTestError):
            await client.call_tool("execute_command", {"command": "echo test", "server": "non_existent_server"}, timeout=2.0)
            
        # 测试获取不存在服务器的信息
        with pytest.raises(MCPTestError):
            await client.call_tool("get_server_info", {"server_name": "non_existent_server"}, timeout=2.0)
            
    @pytest.mark.asyncio
    async def test_mcp_tool_command_validation(self):
        """
        测试MCP工具的命令参数验证
        
        确保工具能够正确验证输入参数
        """
        client = create_mcp_test_client()
        
        # 测试空命令
        with pytest.raises((MCPTestError, ValueError)):
            await client.call_tool("execute_command", {"command": ""}, timeout=2.0)
            
        # 测试危险命令（应该有安全检查）
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf /*",
            ":(){ :|:& };:",  # fork炸弹
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises((MCPTestError, ValueError)):
                await client.call_tool("execute_command", {"command": cmd}, timeout=2.0)
                
    def test_mcp_testing_utils_import(self):
        """
        测试MCP测试工具类的导入和基本功能
        
        确保测试框架本身工作正常
        """
        # 测试客户端创建
        client = create_mcp_test_client()
        assert client is not None
        assert hasattr(client, 'call_tool')
        assert hasattr(client, 'list_servers')
        assert hasattr(client, 'connect_server')
        
        # 测试环境管理器创建
        env = create_test_environment()
        assert env is not None
        assert hasattr(env, '__aenter__')
        assert hasattr(env, '__aexit__')
        
    @pytest.mark.asyncio
    async def test_environment_isolation(self):
        """
        测试环境隔离功能
        
        确保测试环境不会影响生产配置
        """
        import os
        
        # 记录原始环境
        original_config_path = os.environ.get("MCP_CONFIG_PATH")
        
        async with create_test_environment() as test_env:
            # 在测试环境中，配置路径应该已经改变
            current_config_path = os.environ.get("MCP_CONFIG_PATH")
            assert current_config_path != original_config_path
            assert "mcp_test_" in current_config_path
            
        # 退出测试环境后，配置路径应该恢复
        restored_config_path = os.environ.get("MCP_CONFIG_PATH")
        assert restored_config_path == original_config_path


if __name__ == "__main__":
    """
    直接运行此文件进行快速测试
    
    使用方法：
    python tests/regression/test_fix_example_mcp_testing_20240622.py
    """
    # 运行简单的同步测试
    test_instance = TestMCPToolingFramework()
    test_instance.test_mcp_testing_utils_import()
    print("✅ 基础导入测试通过")
    
    # 运行异步测试
    async def run_async_tests():
        test_instance = TestMCPToolingFramework()
        
        try:
            await test_instance.test_environment_isolation()
            print("✅ 环境隔离测试通过")
        except Exception as e:
            print(f"❌ 环境隔离测试失败: {e}")
            
        try:
            await test_instance.test_verify_fix()
            print("✅ 修复验证测试通过")
        except Exception as e:
            print(f"❌ 修复验证测试失败: {e}")
    
    # 运行异步测试
    asyncio.run(run_async_tests())
    print("🎉 示例回归测试完成") 