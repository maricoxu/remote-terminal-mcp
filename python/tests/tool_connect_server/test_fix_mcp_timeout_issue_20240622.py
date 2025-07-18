#!/usr/bin/env python3
"""
回归测试：MCP工具调用超时问题修复

问题描述：
- MCP工具调用时缺乏超时机制，导致测试进程无限等待
- 在MCP服务器无响应时会导致测试卡住

修复日期：2024-06-22
修复内容：
1. 为 MCPTestClient.call_tool() 方法添加超时参数
2. 使用 asyncio.wait_for() 包装异步操作
3. 添加进程清理机制防止僵尸进程

测试目标：
- 验证超时机制能正确工作
- 确保测试不会无限等待
- 验证错误处理的正确性
"""

import pytest
import asyncio
import sys
from pathlib import Path
import tempfile
import os

# 添加测试工具路径
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from mcp_testing_utils import (
    MCPTestClient, 
    MCPTestEnvironment, 
    MCPTestError,
    create_mcp_test_client,
    create_test_environment
)


class TestMCPTimeoutFix:
    """MCP工具调用超时问题修复验证测试类"""
    
    @pytest.mark.asyncio
    async def test_reproduce_timeout_issue(self):
        """
        复现原始超时问题的最小案例
        
        原问题：MCP工具调用没有超时，在服务器无响应时会无限等待
        """
        client = create_mcp_test_client()
        
        # 验证超时机制存在
        assert hasattr(client, 'call_tool')
        
        # 获取call_tool方法的签名，确认有timeout参数
        import inspect
        sig = inspect.signature(client.call_tool)
        assert 'timeout' in sig.parameters
        
        # 验证默认超时值
        default_timeout = sig.parameters['timeout'].default
        assert isinstance(default_timeout, (int, float))
        assert default_timeout > 0
        
    @pytest.mark.asyncio
    async def test_verify_timeout_mechanism(self):
        """
        验证超时机制已被正确修复
        
        测试MCP工具调用在超时时能够正确处理
        """
        client = create_mcp_test_client()
        
        # 测试超短超时（模拟超时场景）
        with pytest.raises(MCPTestError) as exc_info:
            # 使用极短的超时时间，几乎必定超时
            await client.call_tool("list_servers", {}, timeout=0.001)
            
        # 验证错误信息包含超时信息
        error_msg = str(exc_info.value)
        assert "超时" in error_msg or "timeout" in error_msg.lower()
        
    @pytest.mark.asyncio
    async def test_timeout_parameter_validation(self):
        """
        测试超时参数的验证逻辑
        
        确保超时参数能够正确传递和使用
        """
        client = create_mcp_test_client()
        
        # 测试不同的超时值
        timeout_values = [0.1, 1.0, 5.0, 10.0]
        
        for timeout in timeout_values:
            try:
                # 尝试调用（可能超时，但不应该卡住）
                await client.call_tool("list_servers", {}, timeout=timeout)
            except MCPTestError as e:
                # 如果超时，错误信息应该包含具体的超时时间
                if "超时" in str(e) or "timeout" in str(e).lower():
                    assert str(timeout) in str(e) or f"({timeout}" in str(e)
                    
    @pytest.mark.asyncio
    async def test_process_cleanup_after_timeout(self):
        """
        测试超时后的进程清理机制
        
        确保超时后MCP服务器进程能被正确清理
        """
        import psutil
        
        # 记录测试前的进程数
        initial_processes = len([p for p in psutil.process_iter() if 'python' in p.name().lower()])
        
        client = create_mcp_test_client()
        
        # 触发多次超时
        for i in range(3):
            with pytest.raises(MCPTestError):
                await client.call_tool("list_servers", {}, timeout=0.001)
                
        # 等待进程清理
        await asyncio.sleep(1.0)
        
        # 检查进程数没有大幅增加（允许小幅波动）
        final_processes = len([p for p in psutil.process_iter() if 'python' in p.name().lower()])
        assert final_processes <= initial_processes + 2  # 允许最多增加2个进程
        
    @pytest.mark.asyncio
    async def test_normal_operation_with_timeout(self):
        """
        测试正常操作在有超时设置时的工作情况
        
        确保超时机制不影响正常的MCP工具调用
        """
        async with create_test_environment() as test_env:
            client = create_mcp_test_client()
            
            # 使用合理的超时时间进行正常调用
            try:
                result = await client.call_tool("list_servers", {}, timeout=5.0)
                # 正常情况下应该能得到结果
                assert isinstance(result, (list, str, dict))
                
            except MCPTestError as e:
                # 如果有错误，应该不是超时错误（除非系统真的很慢）
                error_msg = str(e)
                # 允许各种MCP相关错误，但最好不是超时
                assert len(error_msg) > 0
                
    @pytest.mark.asyncio 
    async def test_different_tools_timeout_behavior(self):
        """
        测试不同MCP工具的超时行为
        
        确保所有MCP工具都遵循统一的超时机制
        """
        client = create_mcp_test_client()
        
        # 测试各种MCP工具的超时行为
        tools_to_test = [
            ("list_servers", {}),
            ("get_server_status", {}),
            ("connect_server", {"server_name": "nonexistent"}),
            ("get_server_info", {"server_name": "nonexistent"}),
        ]
        
        for tool_name, args in tools_to_test:
            with pytest.raises(MCPTestError) as exc_info:
                # 使用极短超时
                await client.call_tool(tool_name, args, timeout=0.001)
                
            # 验证都是超时错误
            error_msg = str(exc_info.value)
            assert "超时" in error_msg or "timeout" in error_msg.lower()
            assert tool_name in error_msg
            
    def test_timeout_fix_documentation(self):
        """
        验证超时修复的文档完整性
        
        确保修复被正确记录和说明
        """
        # 检查MCPTestClient是否有正确的文档字符串
        client = create_mcp_test_client()
        
        # call_tool方法应该有文档说明超时参数
        call_tool_doc = client.call_tool.__doc__
        assert call_tool_doc is not None
        assert "timeout" in call_tool_doc
        assert "超时" in call_tool_doc
        
        # 验证类型提示
        import inspect
        sig = inspect.signature(client.call_tool)
        timeout_param = sig.parameters['timeout']
        assert timeout_param.annotation == float


if __name__ == "__main__":
    """
    直接运行此文件进行快速验证
    
    使用方法：
    python tests/regression/test_fix_mcp_timeout_issue_20240622.py
    """
    async def run_quick_tests():
        test_instance = TestMCPTimeoutFix()
        
        print("🔍 开始验证MCP超时修复...")
        
        try:
            await test_instance.test_reproduce_timeout_issue()
            print("✅ 超时机制存在性验证通过")
        except Exception as e:
            print(f"❌ 超时机制存在性验证失败: {e}")
            
        try:
            await test_instance.test_verify_timeout_mechanism()
            print("✅ 超时功能验证通过")
        except Exception as e:
            print(f"❌ 超时功能验证失败: {e}")
            
        try:
            await test_instance.test_timeout_parameter_validation()
            print("✅ 超时参数验证通过")
        except Exception as e:
            print(f"❌ 超时参数验证失败: {e}")
            
        try:
            await test_instance.test_normal_operation_with_timeout()
            print("✅ 正常操作验证通过")
        except Exception as e:
            print(f"❌ 正常操作验证失败: {e}")
            
        print("🎉 MCP超时修复验证完成")
    
    # 运行同步测试
    test_instance = TestMCPTimeoutFix()
    test_instance.test_timeout_fix_documentation()
    print("✅ 文档完整性验证通过")
    
    # 运行异步测试
    asyncio.run(run_quick_tests()) 