#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试：智能自动切换模式 - 2024-06-22

测试目标：
1. 验证服务器存在时自动切换到更新模式
2. 测试参数正确传递到更新逻辑
3. 确保服务器不存在时正常创建
4. 验证错误处理和用户提示

智能切换策略说明：
- 检测逻辑：提供服务器名称时，自动检查是否已存在
- 自动切换：如果存在，自动切换到更新模式，参数传递给更新逻辑
- 无缝体验：用户无需手动判断创建还是更新
- 错误处理：如果检测失败，继续执行创建逻辑
"""

import os
import sys
import asyncio
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent.parent

# 添加项目根目录到Python路径
sys.path.insert(0, str(project_root))

# 导入测试工具
from tests.utils.mcp_testing_utils import MCPTestClient

class TestSmartAutoSwitchMode:
    """智能自动切换模式测试类"""
    
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
    
    async def test_existing_server_auto_switch(self):
        """测试1：已存在服务器的自动切换"""
        try:
            # 使用已知存在的服务器名称（如tj09）
            tool_args = {
                "name": "tj09",
                "host": "tjdm-isa-ai-p800node09.tjdm",
                "username": "xuyehua",
                "description": "测试自动切换到更新模式"
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=5)
            
            if response and response.get("content"):
                content = response["content"][0]["text"]
                
                # 检查是否自动切换到更新模式
                auto_switch_indicators = [
                    "智能模式：自动切换到更新模式" in content,
                    "检测到服务器" in content and "已存在" in content,
                    "已自动切换到更新模式" in content,
                    "您提供的更新参数" in content
                ]
                
                if any(auto_switch_indicators):
                    self.log_result("existing_server_auto_switch", True, 
                                  "已存在服务器正确自动切换到更新模式")
                    return True
                else:
                    self.log_result("existing_server_auto_switch", False, 
                                  f"未检测到自动切换标识。内容: {content[:200]}...")
                    return False
            else:
                self.log_result("existing_server_auto_switch", False, "MCP工具调用无响应")
                return False
                
        except Exception as e:
            self.log_result("existing_server_auto_switch", False, f"测试异常: {str(e)}")
            return False
    
    async def test_new_server_normal_create(self):
        """测试2：新服务器的正常创建模式"""
        try:
            # 使用不存在的服务器名称
            tool_args = {
                "name": "test-new-server-auto-switch",
                "host": "192.168.1.200",
                "username": "testuser",
                "description": "测试新服务器创建"
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=5)
            
            if response and response.get("content"):
                content = response["content"][0]["text"]
                
                # 检查是否进入正常创建模式（交互界面）
                create_indicators = [
                    "配置向导已启动" in content,
                    "交互界面" in content or "交互模式" in content,
                    "参数已作为默认值预填充" in content,
                ]
                
                # 确保没有更新模式的标识
                update_indicators = [
                    "自动切换到更新模式" in content,
                    "您提供的更新参数" in content
                ]
                
                if any(create_indicators) and not any(update_indicators):
                    self.log_result("new_server_normal_create", True, 
                                  "新服务器正确进入创建模式")
                    return True
                else:
                    self.log_result("new_server_normal_create", False, 
                                  f"创建模式检测异常。内容: {content[:200]}...")
                    return False
            else:
                self.log_result("new_server_normal_create", False, "MCP工具调用无响应")
                return False
                
        except Exception as e:
            self.log_result("new_server_normal_create", False, f"测试异常: {str(e)}")
            return False
    
    async def test_parameter_mapping_to_update(self):
        """测试3：参数正确映射到更新模式"""
        try:
            # 使用已存在的服务器，提供多个更新参数
            tool_args = {
                "name": "tj09",
                "host": "new-host.example.com",
                "username": "newuser",
                "port": 2222,
                "description": "测试参数映射"
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=5)
            
            if response and response.get("content"):
                content = response["content"][0]["text"]
                
                # 检查参数是否正确显示在更新模式中
                param_checks = [
                    "new-host.example.com" in content,  # host
                    "newuser" in content,               # username
                    "2222" in content,                  # port
                    "测试参数映射" in content            # description
                ]
                
                # 检查更新模式的提示
                update_mode_checks = [
                    "您提供的更新参数" in content,
                    "已用于更新现有服务器配置" in content,
                    "服务器配置已成功更新" in content or "自动更新" in content
                ]
                
                passed_param_checks = sum(param_checks)
                has_update_mode = any(update_mode_checks)
                
                if passed_param_checks >= 3 and has_update_mode:
                    self.log_result("parameter_mapping_to_update", True, 
                                  f"参数正确映射到更新模式 ({passed_param_checks}/4个参数)")
                    return True
                else:
                    self.log_result("parameter_mapping_to_update", False, 
                                  f"参数映射不完整 ({passed_param_checks}/4个参数，更新模式: {has_update_mode})")
                    return False
            else:
                self.log_result("parameter_mapping_to_update", False, "MCP工具调用无响应")
                return False
                
        except Exception as e:
            self.log_result("parameter_mapping_to_update", False, f"测试异常: {str(e)}")
            return False
    
    async def test_no_server_name_normal_flow(self):
        """测试4：无服务器名称时的正常流程"""
        try:
            # 不提供服务器名称，应该跳过检测直接进入创建模式
            tool_args = {
                "prompt": "我想创建一个新的服务器配置"
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=5)
            
            if response and response.get("content"):
                content = response["content"][0]["text"]
                
                # 检查是否正常进入创建模式
                create_indicators = [
                    "配置向导已启动" in content or "交互式配置模式" in content,
                    "逐步完成服务器配置" in content,
                ]
                
                # 确保没有自动切换的标识
                auto_switch_indicators = [
                    "智能模式：自动切换" in content,
                    "检测到服务器" in content and "已存在" in content
                ]
                
                if any(create_indicators) and not any(auto_switch_indicators):
                    self.log_result("no_server_name_normal_flow", True, 
                                  "无服务器名称时正常进入创建模式")
                    return True
                else:
                    self.log_result("no_server_name_normal_flow", False, 
                                  f"无名称流程异常。内容: {content[:200]}...")
                    return False
            else:
                self.log_result("no_server_name_normal_flow", False, "MCP工具调用无响应")
                return False
                
        except Exception as e:
            self.log_result("no_server_name_normal_flow", False, f"测试异常: {str(e)}")
            return False
    
    async def test_smart_switch_advantages(self):
        """测试5：智能切换优势验证"""
        try:
            # 测试智能切换的用户体验优势
            tool_args = {
                "name": "tj09",  # 已存在的服务器
                "description": "测试智能切换优势"
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=5)
            
            if response and response.get("content"):
                content = response["content"][0]["text"]
                
                # 检查智能切换的优势体现
                advantage_indicators = [
                    "智能检测" in content,
                    "自动切换" in content,
                    "避免重复配置" in content,
                    "提高效率" in content,
                    "用户体验优化" in content
                ]
                
                advantage_count = sum(1 for indicator in advantage_indicators if indicator in content)
                
                if advantage_count >= 2:
                    self.log_result("smart_switch_advantages", True, 
                                  f"智能切换优势得到体现 ({advantage_count}/5个优势)")
                    return True
                else:
                    self.log_result("smart_switch_advantages", False, 
                                  f"智能切换优势体现不足 ({advantage_count}/5个优势)")
                    return False
            else:
                self.log_result("smart_switch_advantages", False, "MCP工具调用无响应")
                return False
                
        except Exception as e:
            self.log_result("smart_switch_advantages", False, f"测试异常: {str(e)}")
            return False
    
    async def test_error_handling_graceful(self):
        """测试6：优雅的错误处理"""
        try:
            # 测试无效服务器名称时的错误处理
            tool_args = {
                "name": "",  # 空名称
                "host": "invalid-host",
                "username": "testuser"
            }
            
            response = await self.mcp_client.call_tool("create_server_config", tool_args, timeout=5)
            
            if response and response.get("content"):
                content = response["content"][0]["text"]
                
                # 检查错误处理的友好性
                error_handling_indicators = [
                    "服务器名称不能为空" in content,
                    "请输入有效的服务器名称" in content,
                    "建议" in content,
                    "帮助" in content
                ]
                
                error_handling_count = sum(1 for indicator in error_handling_indicators if indicator in content)
                
                if error_handling_count >= 2:
                    self.log_result("error_handling_graceful", True, 
                                  f"错误处理优雅且友好 ({error_handling_count}/4个指标)")
                    return True
                else:
                    self.log_result("error_handling_graceful", False, 
                                  f"错误处理不够友好 ({error_handling_count}/4个指标)")
                    return False
            else:
                self.log_result("error_handling_graceful", False, "MCP工具调用无响应")
                return False
                
        except Exception as e:
            self.log_result("error_handling_graceful", False, f"测试异常: {str(e)}")
            return False

# 保留原有的main函数用于独立运行
async def main():
    """主函数 - 用于独立运行测试"""
    print("🧪 开始智能自动切换模式回归测试...")
    print("=" * 60)
    
    # 创建测试实例
    test_instance = TestSmartAutoSwitchMode()
    test_instance.setup_class()
    
    tests = [
        ("已存在服务器自动切换", test_instance.test_existing_server_auto_switch),
        ("新服务器正常创建", test_instance.test_new_server_normal_create),
        ("参数映射到更新模式", test_instance.test_parameter_mapping_to_update),
        ("无服务器名称正常流程", test_instance.test_no_server_name_normal_flow),
        ("智能切换优势验证", test_instance.test_smart_switch_advantages),
        ("优雅错误处理", test_instance.test_error_handling_graceful),
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
        print("🎉 所有测试通过！智能自动切换模式验证成功！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 