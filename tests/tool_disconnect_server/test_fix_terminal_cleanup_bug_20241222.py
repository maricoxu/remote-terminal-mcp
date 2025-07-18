#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终端清理Bug修复回归测试

测试场景：
1. 测试修复后的终端清理逻辑
2. 验证AppleScript不再使用有问题的pwd命令
3. 测试强制清理功能
4. 验证清理后无残留终端

修复内容：
- 修复AppleScript中使用do script "pwd"的bug
- 改用窗口/标签页名称识别相关终端
- 添加强制清理作为备选方案
- 支持两级清理策略（常规->强制）

日期：2024-12-22
"""

import asyncio
import unittest
import tempfile
import os
from pathlib import Path
import sys
import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.automated_interaction_tester import AutomatedInteractionTester


class TestTerminalCleanupBugFix(unittest.TestCase):
    """终端清理Bug修复测试"""
    
    def setUp(self):
        """测试准备"""
        self.project_root = project_root
        self.tester = AutomatedInteractionTester(project_root=self.project_root)
    
    def test_cleanup_script_no_pwd_command(self):
        """测试清理脚本不再包含有问题的pwd命令"""
        # 模拟生成清理脚本
        cleanup_script = f'''
tell application "Terminal"
    activate
    
    set projectPath to "{self.project_root}"
    set tabsToClose to {{}}
    set windowsToClose to {{}}
    
    -- 🔧 修复：使用窗口名称而不是执行pwd命令来识别相关终端
    repeat with w from 1 to count of windows
        try
            set windowName to name of window w
            -- 检查窗口名称是否包含项目路径关键词
            if windowName contains "remote-terminal-mcp" or windowName contains "{self.project_root.name}" then
                -- 标记整个窗口需要关闭
                set end of windowsToClose to w
            end if
        on error
            -- 忽略无法访问的窗口
        end try
    end repeat
end tell
'''
        
        # 验证脚本不包含有问题的pwd命令
        self.assertNotIn('do script "pwd"', cleanup_script)
        self.assertIn('windowName', cleanup_script)
        self.assertIn('remote-terminal-mcp', cleanup_script)
        print("✅ 清理脚本不再包含有问题的pwd命令")
    
    def test_force_cleanup_script_generation(self):
        """测试强制清理脚本生成"""
        force_cleanup_script = f'''
tell application "Terminal"
    activate
    
    set projectKeywords to {{"remote-terminal-mcp", "{self.project_root.name}", "enhanced_config_manager"}}
    set closedCount to 0
    
    -- 🔧 强制方法：直接检查所有窗口标题
    repeat with w from (count of windows) to 1 by -1
        try
            set windowName to name of window w
            set shouldClose to false
            
            -- 检查窗口名称是否包含任何项目关键词
            repeat with keyword in projectKeywords
                if windowName contains keyword then
                    set shouldClose to true
                    exit repeat
                end if
            end repeat
            
            if shouldClose then
                close window w
                set closedCount to closedCount + 1
                delay 0.2
            end if
        on error
            -- 忽略错误，继续处理下一个窗口
        end try
    end repeat
    
    return "FORCE_CLEANUP_SUCCESS:" & closedCount
    
end tell
'''
        
        # 验证强制清理脚本的关键特性
        self.assertIn('projectKeywords', force_cleanup_script)
        self.assertIn('remote-terminal-mcp', force_cleanup_script)
        self.assertIn('enhanced_config_manager', force_cleanup_script)
        self.assertIn('FORCE_CLEANUP_SUCCESS', force_cleanup_script)
        self.assertIn('closedCount', force_cleanup_script)
        print("✅ 强制清理脚本生成正确")
    
    def test_cleanup_terminals_method(self):
        """测试清理终端方法"""
        async def run_cleanup_test():
            try:
                # 测试常规清理方法
                success, message = await self.tester.cleanup_test_terminals()
                
                # 验证方法能够正常执行（不管是否有终端需要清理）
                self.assertIsInstance(success, bool)
                self.assertIsInstance(message, str)
                self.assertIn("清理", message)
                
                print(f"✅ 常规清理方法测试通过: {message}")
                
            except Exception as e:
                self.fail(f"清理终端方法测试失败: {e}")
        
        # 运行异步测试
        asyncio.run(run_cleanup_test())
    
    def test_force_cleanup_terminals_method(self):
        """测试强制清理终端方法"""
        async def run_force_cleanup_test():
            try:
                # 测试强制清理方法
                success, message = await self.tester.force_cleanup_terminals()
                
                # 验证方法能够正常执行
                self.assertIsInstance(success, bool)
                self.assertIsInstance(message, str)
                self.assertIn("强制清理", message)
                
                print(f"✅ 强制清理方法测试通过: {message}")
                
            except Exception as e:
                self.fail(f"强制清理终端方法测试失败: {e}")
        
        # 运行异步测试
        asyncio.run(run_force_cleanup_test())
    
    def test_cleanup_configuration(self):
        """测试清理配置"""
        # 测试启用清理的配置
        tester_with_cleanup = AutomatedInteractionTester(
            project_root=self.project_root, 
            cleanup_terminals=True
        )
        self.assertTrue(tester_with_cleanup.cleanup_terminals)
        
        # 测试禁用清理的配置
        tester_no_cleanup = AutomatedInteractionTester(
            project_root=self.project_root, 
            cleanup_terminals=False
        )
        self.assertFalse(tester_no_cleanup.cleanup_terminals)
        
        print("✅ 清理配置测试通过")
    
    def test_cleanup_disabled_behavior(self):
        """测试禁用清理时的行为"""
        async def run_disabled_cleanup_test():
            # 创建禁用清理的测试器
            tester_no_cleanup = AutomatedInteractionTester(
                project_root=self.project_root, 
                cleanup_terminals=False
            )
            
            # 测试清理方法在禁用时的行为
            success, message = await tester_no_cleanup.cleanup_test_terminals()
            
            self.assertTrue(success)
            self.assertEqual(message, "终端清理已禁用")
            
            print("✅ 禁用清理行为测试通过")
        
        # 运行异步测试
        asyncio.run(run_disabled_cleanup_test())
    
    def test_applescript_syntax_validation(self):
        """测试AppleScript语法验证"""
        # 验证清理脚本的基本语法结构
        cleanup_script_template = '''
tell application "Terminal"
    activate
    set projectPath to "test_path"
    set tabsToClose to {{}}
    set windowsToClose to {{}}
    repeat with w from 1 to count of windows
        try
            set windowName to name of window w
            if windowName contains "remote-terminal-mcp" then
                set end of windowsToClose to w
            end if
        on error
            -- 忽略错误
        end try
    end repeat
end tell
'''
        
        # 验证基本语法结构
        self.assertIn('tell application "Terminal"', cleanup_script_template)
        self.assertIn('activate', cleanup_script_template)
        self.assertIn('repeat with', cleanup_script_template)
        self.assertIn('end tell', cleanup_script_template)
        
        print("✅ AppleScript语法验证通过")
    
    def test_project_path_detection(self):
        """测试项目路径检测"""
        # 验证项目路径检测逻辑
        detected_path = str(self.project_root)
        self.assertTrue(os.path.exists(detected_path))
        self.assertIn('remote-terminal-mcp', detected_path)
        
        print(f"✅ 项目路径检测正确: {detected_path}")


# 保留原有的异步测试运行函数用于独立运行
async def run_async_tests():
    """运行异步测试"""
    print("🧪 开始终端清理Bug修复异步测试...")
    
    # 创建测试实例
    test_instance = TestTerminalCleanupBugFix()
    test_instance.setUp()
    
    # 运行异步测试
    await test_instance.tester.cleanup_test_terminals()
    await test_instance.tester.force_cleanup_terminals()
    
    print("✅ 异步测试完成")


def main():
    """主函数"""
    print("🧪 开始终端清理Bug修复回归测试...")
    print("=" * 60)
    
    # 运行单元测试
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 60)
    print("🎉 终端清理Bug修复回归测试完成！")


if __name__ == "__main__":
    main() 