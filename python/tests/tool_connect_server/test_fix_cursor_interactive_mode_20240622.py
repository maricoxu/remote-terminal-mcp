#!/usr/bin/env python3
"""
回归测试：Cursor内置终端交互配置模式

测试目标：验证新增的cursor_interactive参数能够正确工作
问题描述：用户希望在Cursor内置终端中运行交互式配置，而不是启动外部终端窗口
修复方案：添加cursor_interactive模式，生成可在Cursor内置终端中运行的命令

测试用例：
1. 测试cursor_interactive=True时的内置终端命令生成
2. 测试参数预填充功能
3. 测试Docker参数的处理
4. 测试cursor_interactive优先级
"""

import sys
import os
import asyncio
import tempfile
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))

from tests.utils.mcp_testing_utils import MCPTestEnvironment, create_mcp_test_client


class TestCursorTerminalInteractiveMode:
    """Cursor内置终端交互模式测试类"""
    
    def __init__(self):
        self.test_results = []
    
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
    
    async def test_cursor_terminal_interactive_missing_params(self):
        """测试1：cursor_interactive=True且缺少参数时的内置终端命令生成"""
        test_name = "cursor_terminal_interactive_missing_params"
        
        async with MCPTestEnvironment() as env:
            try:
                client = create_mcp_test_client()
                
                # 测试只提供部分参数
                result = await client.call_tool('create_server_config', {
                    'name': 'test-server',
                    'cursor_interactive': True,
                    'interactive': False
                }, timeout=10.0)
                
                result_str = str(result)
                
                # 验证内置终端模式关键元素
                checks = [
                    ('Cursor内置终端交互配置', 'Cursor内置终端模式标识'),
                    ('最佳体验', '体验说明'),
                    ('已提供的参数', '参数状态显示'),
                    ('✅ **name**: `test-server`', '已提供参数显示'),
                    ('启动配置向导', '启动说明'),
                    ('```bash', 'bash代码块'),
                    ('enhanced_config_manager.py --interactive', '交互命令'),
                    ('--name test-server', '参数预填充'),
                    ('点击上方代码块右上角的 ▶️ 运行按钮', '使用说明'),
                    ('Cursor内置终端优势', '优势说明'),
                    ('界面内集成', '优势描述'),
                    ('完整终端体验', '优势描述')
                ]
                
                all_passed = True
                missing_checks = []
                
                for check, description in checks:
                    if check in result_str:
                        print(f"  ✅ {description}: 发现")
                    else:
                        print(f"  ❌ {description}: 未发现")
                        all_passed = False
                        missing_checks.append(description)
                
                if all_passed:
                    self.log_result(test_name, True, "内置终端命令生成正确")
                else:
                    self.log_result(test_name, False, f"缺少: {', '.join(missing_checks)}")
                    
            except Exception as e:
                self.log_result(test_name, False, f"异常: {str(e)}")
    
    async def test_cursor_terminal_interactive_with_prefill(self):
        """测试2：cursor_interactive=True且提供多个参数时的预填充功能"""
        test_name = "cursor_terminal_interactive_with_prefill"
        
        async with MCPTestEnvironment() as env:
            try:
                client = create_mcp_test_client()
                
                # 测试提供多个参数
                result = await client.call_tool('create_server_config', {
                    'name': 'test-prefill-server',
                    'host': '192.168.1.100',
                    'port': 2222,
                    'connection_type': 'relay',
                    'description': '测试预填充服务器',
                    'cursor_interactive': True,
                    'interactive': False
                }, timeout=10.0)
                
                result_str = str(result)
                
                # 验证参数预填充
                checks = [
                    ('✅ **name**: `test-prefill-server`', 'name参数显示'),
                    ('✅ **host**: `192.168.1.100`', 'host参数显示'),
                    ('✅ **port**: `2222`', 'port参数显示'),
                    ('✅ **connection_type**: `relay`', 'connection_type参数显示'),
                    ('✅ **description**: `测试预填充服务器`', 'description参数显示'),
                    ('--name test-prefill-server', 'name命令行参数'),
                    ('--host 192.168.1.100', 'host命令行参数'),
                    ('--port 2222', 'port命令行参数'),
                    ('--connection-type relay', 'connection-type命令行参数'),
                    ("--description '测试预填充服务器'", 'description命令行参数'),
                    ('这些参数将自动预填充到配置向导中', '预填充说明')
                ]
                
                all_passed = True
                missing_checks = []
                
                for check, description in checks:
                    if check in result_str:
                        print(f"  ✅ {description}: 发现")
                    else:
                        print(f"  ❌ {description}: 未发现")
                        all_passed = False
                        missing_checks.append(description)
                
                if all_passed:
                    self.log_result(test_name, True, "参数预填充功能正确")
                else:
                    self.log_result(test_name, False, f"缺少: {', '.join(missing_checks)}")
                    
            except Exception as e:
                self.log_result(test_name, False, f"异常: {str(e)}")
    
    async def test_cursor_terminal_interactive_docker_params(self):
        """测试3：cursor_interactive=True且包含Docker参数时的处理"""
        test_name = "cursor_terminal_interactive_docker_params"
        
        async with MCPTestEnvironment() as env:
            try:
                client = create_mcp_test_client()
                
                # 测试Docker参数
                result = await client.call_tool('create_server_config', {
                    'name': 'test-docker-server',
                    'host': '192.168.1.102',
                    'username': 'docker-user',
                    'docker_enabled': True,
                    'docker_image': 'ubuntu:22.04',
                    'docker_container': 'my-container',
                    'cursor_interactive': True,
                    'interactive': False
                }, timeout=10.0)
                
                result_str = str(result)
                
                # 验证Docker参数处理
                checks = [
                    ('✅ **docker_enabled**: `True`', 'docker_enabled参数显示'),
                    ('--docker-enabled true', 'docker-enabled命令行参数'),
                    ('--docker-image ubuntu:22.04', 'docker-image命令行参数'),
                    ('--docker-container my-container', 'docker-container命令行参数'),
                    ('✅ **name**: `test-docker-server`', 'name参数显示'),
                    ('✅ **host**: `192.168.1.102`', 'host参数显示'),
                    ('✅ **username**: `docker-user`', 'username参数显示')
                ]
                
                all_passed = True
                missing_checks = []
                
                for check, description in checks:
                    if check in result_str:
                        print(f"  ✅ {description}: 发现")
                    else:
                        print(f"  ❌ {description}: 未发现")
                        all_passed = False
                        missing_checks.append(description)
                
                if all_passed:
                    self.log_result(test_name, True, "Docker参数处理正确")
                else:
                    self.log_result(test_name, False, f"缺少: {', '.join(missing_checks)}")
                    
            except Exception as e:
                self.log_result(test_name, False, f"异常: {str(e)}")
    
    async def test_cursor_terminal_interactive_vs_traditional(self):
        """测试4：验证cursor_interactive=True会覆盖interactive=True"""
        test_name = "cursor_terminal_interactive_vs_traditional"
        
        async with MCPTestEnvironment() as env:
            try:
                client = create_mcp_test_client()
                
                # 测试同时设置两个参数
                result = await client.call_tool('create_server_config', {
                    'name': 'test-priority-server',
                    'cursor_interactive': True,
                    'interactive': True  # 应该被cursor_interactive覆盖
                }, timeout=10.0)
                
                result_str = str(result)
                
                # 验证使用了Cursor内置终端而不是传统交互
                cursor_terminal_mode = 'Cursor内置终端交互配置' in result_str
                traditional_mode = '交互配置界面已启动' in result_str and '新的终端窗口' in result_str
                bash_command = '```bash' in result_str and 'enhanced_config_manager.py --interactive' in result_str
                
                if cursor_terminal_mode and bash_command and not traditional_mode:
                    self.log_result(test_name, True, "cursor_interactive优先级正确，使用内置终端模式")
                elif traditional_mode:
                    self.log_result(test_name, False, "仍然使用传统终端模式")
                else:
                    self.log_result(test_name, False, "模式识别失败")
                    
            except Exception as e:
                self.log_result(test_name, False, f"异常: {str(e)}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Cursor内置终端交互模式回归测试")
        print("=" * 60)
        
        # 按顺序运行测试
        await self.test_cursor_terminal_interactive_missing_params()
        await self.test_cursor_terminal_interactive_with_prefill()
        await self.test_cursor_terminal_interactive_docker_params()
        await self.test_cursor_terminal_interactive_vs_traditional()
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        return failed_tests == 0


async def main():
    """主函数"""
    try:
        tester = TestCursorTerminalInteractiveMode()
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 所有测试通过！Cursor内置终端交互模式功能正常。")
            return 0
        else:
            print("\n💥 存在测试失败，需要检查Cursor内置终端交互模式实现。")
            return 1
            
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 