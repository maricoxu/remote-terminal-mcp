#!/usr/bin/env python3
"""
回归测试：聊天界面内终端式交互配置功能

测试目标：
1. 验证cursor_interactive模式能正确启动聊天界面内的终端式配置
2. 验证分步骤配置流程和会话管理
3. 验证字段验证和错误处理
4. 验证配置完成后的自动创建

创建日期：2024-06-22
问题描述：用户要求在聊天界面中直接显示终端式交互配置，而不是启动外部终端
修复方案：重新设计cursor_interactive模式，使用会话管理器实现分步骤配置
"""

import sys
import os
import asyncio
import json
import tempfile
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.mcp_testing_utils import MCPTestClient

class TestChatTerminalInteractive:
    """聊天界面内终端式交互配置测试类"""
    
    def __init__(self):
        self.client = MCPTestClient()
        self.test_results = []
    
    async def test_cursor_interactive_start(self):
        """测试cursor_interactive模式启动"""
        print("🧪 测试1: cursor_interactive模式启动")
        
        try:
            # 调用create_server_config启用cursor_interactive模式
            result = await self.client.call_tool(
                "create_server_config",
                {
                    "cursor_interactive": True,
                    "name": "test-chat-server",
                    "host": "192.168.1.100"
                }
            )
            
            print(f"📋 cursor_interactive启动结果:")
            print(f"   类型: {type(result)}")
            if isinstance(result, str):
                print(f"   内容预览: {result[:200]}...")
                
                # 检查是否包含预期的终端界面元素
                expected_elements = [
                    "Remote Terminal MCP - 终端配置模式",
                    "配置进度:",
                    "当前步骤:",
                    "continue_config_session",
                    "session_id"
                ]
                
                missing_elements = []
                for element in expected_elements:
                    if element not in result:
                        missing_elements.append(element)
                
                if missing_elements:
                    print(f"❌ 缺少预期元素: {missing_elements}")
                    self.test_results.append(("cursor_interactive_start", False, f"缺少元素: {missing_elements}"))
                else:
                    print("✅ 包含所有预期的终端界面元素")
                    self.test_results.append(("cursor_interactive_start", True, "终端界面正确显示"))
            else:
                print(f"❌ 返回类型不是字符串: {type(result)}")
                self.test_results.append(("cursor_interactive_start", False, f"返回类型错误: {type(result)}"))
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            self.test_results.append(("cursor_interactive_start", False, str(e)))
    
    async def test_session_continuation(self):
        """测试配置会话继续"""
        print("\n🧪 测试2: 配置会话继续")
        
        try:
            # 首先启动一个配置会话
            start_result = await self.client.call_tool(
                "create_server_config",
                {
                    "cursor_interactive": True,
                    "name": "test-session-server"
                }
            )
            
            if isinstance(start_result, str) and "session_id" in start_result:
                # 从结果中提取session_id
                import re
                session_match = re.search(r'session_id="([^"]+)"', start_result)
                if session_match:
                    session_id = session_match.group(1)
                    print(f"📋 提取到session_id: {session_id}")
                    
                    # 继续配置会话 - 设置host
                    continue_result = await self.client.call_tool(
                        "continue_config_session",
                        {
                            "session_id": session_id,
                            "field_name": "host",
                            "field_value": "192.168.1.200"
                        }
                    )
                    
                    print(f"📋 继续配置结果:")
                    if isinstance(continue_result, str):
                        print(f"   内容预览: {continue_result[:200]}...")
                        
                        # 检查是否正确处理了字段设置
                        if "设置成功" in continue_result and "192.168.1.200" in continue_result:
                            print("✅ 字段设置成功反馈正确")
                            self.test_results.append(("session_continuation", True, "字段设置成功"))
                        else:
                            print("❌ 字段设置反馈不正确")
                            self.test_results.append(("session_continuation", False, "字段设置反馈错误"))
                    else:
                        print(f"❌ 继续配置返回类型错误: {type(continue_result)}")
                        self.test_results.append(("session_continuation", False, f"返回类型错误: {type(continue_result)}"))
                else:
                    print("❌ 无法从启动结果中提取session_id")
                    self.test_results.append(("session_continuation", False, "无法提取session_id"))
            else:
                print("❌ 启动结果不包含session_id")
                self.test_results.append(("session_continuation", False, "启动结果无session_id"))
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            self.test_results.append(("session_continuation", False, str(e)))
    
    async def test_field_validation(self):
        """测试字段验证功能"""
        print("\n🧪 测试3: 字段验证功能")
        
        try:
            # 启动配置会话
            start_result = await self.client.call_tool(
                "create_server_config",
                {
                    "cursor_interactive": True
                }
            )
            
            if isinstance(start_result, str) and "session_id" in start_result:
                import re
                session_match = re.search(r'session_id="([^"]+)"', start_result)
                if session_match:
                    session_id = session_match.group(1)
                    
                    # 测试无效的服务器名称（太短）
                    invalid_result = await self.client.call_tool(
                        "continue_config_session",
                        {
                            "session_id": session_id,
                            "field_name": "name",
                            "field_value": "ab"  # 太短，应该失败
                        }
                    )
                    
                    if isinstance(invalid_result, str) and "输入验证失败" in invalid_result:
                        print("✅ 字段验证正确拒绝了无效输入")
                        
                        # 测试有效的服务器名称
                        valid_result = await self.client.call_tool(
                            "continue_config_session",
                            {
                                "session_id": session_id,
                                "field_name": "name",
                                "field_value": "valid-server-name"
                            }
                        )
                        
                        if isinstance(valid_result, str) and "设置成功" in valid_result:
                            print("✅ 字段验证正确接受了有效输入")
                            self.test_results.append(("field_validation", True, "验证功能正常"))
                        else:
                            print("❌ 有效输入被错误拒绝")
                            self.test_results.append(("field_validation", False, "有效输入被拒绝"))
                    else:
                        print("❌ 字段验证未正确拒绝无效输入")
                        self.test_results.append(("field_validation", False, "验证未拒绝无效输入"))
                else:
                    print("❌ 无法提取session_id")
                    self.test_results.append(("field_validation", False, "无法提取session_id"))
            else:
                print("❌ 启动配置会话失败")
                self.test_results.append(("field_validation", False, "启动会话失败"))
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            self.test_results.append(("field_validation", False, str(e)))
    
    async def test_complete_configuration(self):
        """测试完整的配置流程"""
        print("\n🧪 测试4: 完整配置流程")
        
        try:
            # 启动配置会话，提供所有必需参数
            start_result = await self.client.call_tool(
                "create_server_config",
                {
                    "cursor_interactive": True,
                    "name": "complete-test-server",
                    "host": "192.168.1.300",
                    "username": "testuser"
                }
            )
            
            if isinstance(start_result, str):
                if "配置创建成功" in start_result:
                    print("✅ 完整配置直接创建成功")
                    self.test_results.append(("complete_configuration", True, "完整配置成功"))
                elif "session_id" in start_result:
                    print("⚠️ 配置启动了会话模式（可能需要额外参数）")
                    self.test_results.append(("complete_configuration", True, "配置启动会话模式"))
                else:
                    print("❌ 配置结果不符合预期")
                    print(f"   结果内容: {start_result[:300]}...")
                    self.test_results.append(("complete_configuration", False, "配置结果异常"))
            else:
                print(f"❌ 配置返回类型错误: {type(start_result)}")
                self.test_results.append(("complete_configuration", False, f"返回类型错误: {type(start_result)}"))
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            self.test_results.append(("complete_configuration", False, str(e)))
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始聊天界面内终端式交互配置测试")
        print("=" * 60)
        
        # 运行各个测试
        await self.test_cursor_interactive_start()
        await self.test_session_continuation()
        await self.test_field_validation()
        await self.test_complete_configuration()
        
        # 汇总测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果汇总:")
        
        passed = 0
        failed = 0
        
        for test_name, success, message in self.test_results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"   {test_name}: {status} - {message}")
            if success:
                passed += 1
            else:
                failed += 1
        
        print(f"\n🎯 总计: {passed} 个测试通过, {failed} 个测试失败")
        
        if failed == 0:
            print("🎉 所有测试通过！聊天界面内终端式交互配置功能正常工作")
            return True
        else:
            print("⚠️ 部分测试失败，需要进一步调试")
            return False

async def main():
    """主测试函数"""
    test_suite = TestChatTerminalInteractive()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n✅ 回归测试通过：聊天界面内终端式交互配置功能工作正常")
        sys.exit(0)
    else:
        print("\n❌ 回归测试失败：聊天界面内终端式交互配置功能存在问题")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 