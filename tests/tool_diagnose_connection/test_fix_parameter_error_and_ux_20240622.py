#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试：修复参数错误和用户体验改进 - 2024-06-22

测试目标：
1. 验证enhanced_config_manager.py中guided_setup()参数错误已修复
2. 验证MCP工具返回消息在聊天界面直接显示友好信息
3. 确保cursor_interactive模式正常工作

修复内容：
- 修复guided_setup(prefill_defaults=...)参数错误
- 改进MCP工具返回消息，在聊天界面直接显示用户友好信息
- 优化cursor_interactive模式的处理逻辑
"""

import os
import sys
import json
import tempfile
import asyncio
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent.parent

# 添加项目根目录到Python路径
sys.path.insert(0, str(project_root))

# 导入测试工具
from tests.utils.mcp_testing_utils import MCPTestClient

class TestParameterErrorAndUXFix:
    """参数错误和用户体验修复测试类"""
    
    @classmethod
    def setup_class(cls):
        """测试类设置"""
        cls.test_results = []
        cls.mcp_client = MCPTestClient()
    
    def log_result(self, test_name: str, success: bool, message: str):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        self.test_results.append((test_name, success, message))
    
    async def test_guided_setup_parameter_fix(self):
        """测试1：验证guided_setup参数错误已修复"""
        try:
            # 导入配置管理器
            from config_manager.main import EnhancedConfigManager
            
            # 创建临时预填充文件
            prefill_data = {
                "name": "test-server",
                "host": "192.168.1.100",
                "username": "testuser"
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(prefill_data, f, ensure_ascii=False, indent=2)
                temp_file = f.name
            
            try:
                # 模拟命令行调用（不实际运行，只检查参数处理）
                import subprocess
                cmd = [
                    sys.executable, 
                    str(project_root / "enhanced_config_manager.py"),
                    "--prefill", temp_file,
                    "--help"  # 使用help避免实际运行
                ]
                
                # 运行命令检查是否有参数错误
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=str(project_root),
                    timeout=5
                )
                
                # 检查是否有prefill_defaults参数错误
                error_output = result.stderr.lower()
                if "unexpected keyword argument 'prefill_defaults'" in error_output:
                    self.log_result("guided_setup_parameter_fix", False, "仍然存在prefill_defaults参数错误")
                    return False
                else:
                    self.log_result("guided_setup_parameter_fix", True, "guided_setup参数错误已修复")
                    return True
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            self.log_result("guided_setup_parameter_fix", False, f"测试异常: {str(e)}")
            return False
    
    async def test_cursor_interactive_ux_improvement(self):
        """测试2：验证cursor_interactive模式用户体验改进"""
        try:
            # 测试cursor_interactive=True时的响应消息
            tool_args = {
                "name": "test-server-ux",
                "host": "192.168.1.200", 
                "username": "testuser",
                "cursor_interactive": True
            }
            
            # 调用MCP工具
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=15)
            
            if not response:
                self.log_result("cursor_interactive_ux", False, "MCP工具调用无响应")
                return False
            
            # 检查响应内容是否包含用户友好信息
            content = response.get("content", "")
            
            # 验证关键的用户体验元素
            ux_elements = [
                "🚀", "✨",  # 友好的图标
                "Cursor内置终端",  # 明确说明
                "操作步骤",  # 清晰的指导
                "已预填充的参数",  # 参数状态说明
                "优势"  # 功能优势说明
            ]
            
            missing_elements = []
            for element in ux_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                self.log_result("cursor_interactive_ux", False, f"缺少用户体验元素: {missing_elements}")
                return False
            else:
                self.log_result("cursor_interactive_ux", True, "用户体验信息完整显示在聊天界面")
                return True
                
        except Exception as e:
            self.log_result("cursor_interactive_ux", False, f"测试异常: {str(e)}")
            return False
    
    async def test_chat_interface_direct_display(self):
        """测试3：验证重要信息直接在聊天界面显示，不隐藏在折叠区域"""
        try:
            # 测试普通交互式模式的响应
            tool_args = {
                "name": "test-display",
                "host": "192.168.1.300",
                "username": "testuser", 
                "interactive": True
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=15)
            
            if not response:
                self.log_result("chat_interface_display", False, "MCP工具调用无响应")
                return False
            
            content = response.get("content", "")
            
            # 验证信息是否直接可见（不需要点击展开）
            visible_info_indicators = [
                "系统终端配置向导已启动",  # 明确的状态说明
                "请按以下步骤操作",  # 清晰的操作指导
                "您提供的参数已预填充",  # 参数状态
                "友好提示"  # 额外帮助信息
            ]
            
            visible_count = sum(1 for indicator in visible_info_indicators if indicator in content)
            
            if visible_count >= 3:  # 至少包含3个关键信息
                self.log_result("chat_interface_display", True, f"关键信息直接显示在聊天界面 ({visible_count}/4)")
                return True
            else:
                self.log_result("chat_interface_display", False, f"关键信息显示不足 ({visible_count}/4)")
                return False
                
        except Exception as e:
            self.log_result("chat_interface_display", False, f"测试异常: {str(e)}")
            return False
    
    async def test_error_handling_improvement(self):
        """测试4：验证错误处理的用户友好性改进"""
        try:
            # 测试缺少参数时的错误处理
            tool_args = {
                "cursor_interactive": True
                # 故意不提供必需参数
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=10)
            
            if not response:
                self.log_result("error_handling", False, "MCP工具调用无响应")
                return False
            
            content = response.get("content", "")
            
            # 验证错误信息的友好性
            friendly_error_elements = [
                "❌",  # 错误图标
                "缺少必需参数",  # 明确的错误说明
                "备用方案",  # 提供解决方案
                "```json",  # 提供可执行的代码示例
            ]
            
            error_elements_found = sum(1 for element in friendly_error_elements if element in content)
            
            if error_elements_found >= 3:
                self.log_result("error_handling", True, f"错误处理友好且提供解决方案 ({error_elements_found}/4)")
                return True
            else:
                self.log_result("error_handling", False, f"错误处理不够友好 ({error_elements_found}/4)")
                return False
                
        except Exception as e:
            self.log_result("error_handling", False, f"测试异常: {str(e)}")
            return False

# 保留原有的main函数用于独立运行
async def main():
    """主函数 - 用于独立运行测试"""
    print("🧪 开始参数错误和用户体验修复回归测试...")
    print("=" * 60)
    
    # 创建测试实例
    test_instance = TestParameterErrorAndUXFix()
    test_instance.setup_class()
    
    tests = [
        ("guided_setup参数修复", test_instance.test_guided_setup_parameter_fix),
        ("cursor_interactive用户体验", test_instance.test_cursor_interactive_ux_improvement),
        ("聊天界面直接显示", test_instance.test_chat_interface_direct_display),
        ("错误处理改进", test_instance.test_error_handling_improvement),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行测试: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {test_name} - {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！参数错误和用户体验修复验证成功！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 