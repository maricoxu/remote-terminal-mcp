#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relay-CLI使用规范回归测试
=========================

测试目的：
1. 确保relay-cli使用遵循正确的语法规范
2. 验证禁止的用法能够被正确识别
3. 防止在relay-cli后面接命令参数的错误

问题描述：
- 之前在使用relay-cli时错误地添加了命令参数
- 导致连接失败，无法建立relay连接
- 需要确保只使用交互式连接方式

修复方案：
- 添加严格的relay-cli使用规范
- 禁止在relay-cli后面接任何命令参数
- 只允许纯交互式连接用法

创建日期：2025年1月5日
"""

import unittest
import re
from typing import List, Tuple

class TestRelayCLIUsageCompliance(unittest.TestCase):
    """Relay-CLI使用规范合规性测试"""
    
    def setUp(self):
        """测试准备"""
        self.correct_patterns = [
            r"^relay-cli\s*$",  # 单独运行relay-cli，不接任何参数
            r"^relay-cli$"       # 严格匹配，只有relay-cli
        ]
        
        self.forbidden_patterns = [
            r"relay-cli\s+\S+",       # relay-cli后面接任何非空白字符参数
            r"relay-cli.*--user",     # relay-cli后面接--user参数
            r"relay-cli.*--command",  # relay-cli后面接--command参数
            r"relay-cli.*--timeout",  # relay-cli后面接--timeout参数
            r"relay-cli.*--help",     # relay-cli后面接--help参数
            r"relay-cli.*--version",  # relay-cli后面接--version参数
            r"relay-cli.*\".*\"",     # relay-cli后面接引号内容
            r"relay-cli.*'.*'",       # relay-cli后面接单引号内容
            r"relay-cli.*&&",         # relay-cli后面接&&
            r"relay-cli.*\|",         # relay-cli后面接管道
            r"relay-cli.*;"           # relay-cli后面接分号
        ]
    
    def test_correct_relay_cli_usage(self):
        """测试正确的relay-cli使用方式"""
        correct_examples = [
            "relay-cli",
            "relay-cli ",  # 后面有空格也可以
            "  relay-cli  "  # 前后有空格也可以（会被strip处理）
        ]
        
        for example in correct_examples:
            with self.subTest(example=example):
                cleaned_example = example.strip()
                is_correct = any(re.search(pattern, cleaned_example) for pattern in self.correct_patterns)
                self.assertTrue(is_correct, f"正确的用法应该被识别: {example}")
    
    def test_forbidden_relay_cli_usage(self):
        """测试禁止的relay-cli使用方式"""
        forbidden_examples = [
            'relay-cli bjhw-sys-rpm0221.bjhw --user xuyehua',
            'relay-cli bjhw-sys-rpm0221.bjhw --user xuyehua --command "pwd"',
            'relay-cli server.com --user admin --timeout 5 --command "echo test"',
            'relay-cli host --user user --command "ls -la"',
            'relay-cli host --user user "direct command"',
            "relay-cli host --user user 'single quote command'",
            "relay-cli host --user user && echo 'chained'",
            "relay-cli host --user user | grep something",
            "relay-cli host --user user; echo 'semicolon'",
            "relay-cli hostname",
            "relay-cli 192.168.1.100",
            "relay-cli --help",
            "relay-cli --version"
        ]
        
        for example in forbidden_examples:
            with self.subTest(example=example):
                is_forbidden = any(re.search(pattern, example) for pattern in self.forbidden_patterns)
                self.assertTrue(is_forbidden, f"禁止的用法应该被识别: {example}")
    
    def test_parse_relay_cli_command(self):
        """测试解析relay-cli命令的功能"""
        def is_valid_relay_cli_usage(command: str) -> Tuple[bool, str]:
            """
            验证relay-cli命令是否符合规范
            
            Args:
                command: 要验证的命令字符串
                
            Returns:
                (是否有效, 错误信息或空字符串)
            """
            # 检查是否是relay-cli命令
            if not command.strip().startswith("relay-cli"):
                return True, ""  # 不是relay-cli命令，不需要验证
            
            # 检查禁止的模式
            for pattern in self.forbidden_patterns:
                if re.search(pattern, command):
                    return False, f"禁止的用法模式: {pattern}"
            
            # 检查是否符合正确的模式
            for pattern in self.correct_patterns:
                if re.search(pattern, command):
                    return True, ""
            
            return False, "不符合正确的relay-cli使用规范"
        
        # 测试正确的命令
        valid_commands = [
            "relay-cli",
            "ls -la",  # 非relay-cli命令
            "ssh user@host"  # 非relay-cli命令
        ]
        
        for cmd in valid_commands:
            with self.subTest(command=cmd):
                is_valid, error = is_valid_relay_cli_usage(cmd)
                self.assertTrue(is_valid, f"命令应该有效: {cmd}, 错误: {error}")
        
        # 测试无效的命令
        invalid_commands = [
            'relay-cli bjhw-sys-rpm0221.bjhw --user xuyehua',
            'relay-cli bjhw-sys-rpm0221.bjhw --user xuyehua --command "pwd"',
            'relay-cli host --user user --timeout 5 --command "test"',
            'relay-cli hostname',
            'relay-cli --help'
        ]
        
        for cmd in invalid_commands:
            with self.subTest(command=cmd):
                is_valid, error = is_valid_relay_cli_usage(cmd)
                self.assertFalse(is_valid, f"命令应该无效: {cmd}")
                self.assertNotEqual(error, "", f"应该有错误信息: {cmd}")
    
    def test_rule_documentation_compliance(self):
        """测试规则文档的合规性"""
        # 这个测试确保.cursorrules文件中包含了正确的规则
        try:
            with open('.cursorrules', 'r', encoding='utf-8') as f:
                rules_content = f.read()
            
            # 检查是否包含关键的规则内容
            required_sections = [
                "🚨 Relay-CLI使用严格规范",
                "relay-cli正确使用方式",
                "relay-cli严格禁止的用法",
                "绝对禁止",
                "--command"
            ]
            
            for section in required_sections:
                with self.subTest(section=section):
                    self.assertIn(section, rules_content, 
                                f"规则文件应该包含必要的章节: {section}")
        
        except FileNotFoundError:
            self.fail("找不到.cursorrules文件")
    
    def test_code_examples_in_documentation(self):
        """测试文档中的代码示例合规性"""
        # 这个测试确保所有文档中的relay-cli示例都符合规范
        
        # 模拟文档中的示例
        documentation_examples = [
            "relay-cli",  # 正确示例
            # 如果发现文档中有错误示例，它们会在这里被捕获
        ]
        
        for example in documentation_examples:
            with self.subTest(example=example):
                # 检查是否符合正确的模式
                is_correct = any(re.search(pattern, example) for pattern in self.correct_patterns)
                self.assertTrue(is_correct, f"文档示例应该符合规范: {example}")
                
                # 检查是否包含禁止的模式
                is_forbidden = any(re.search(pattern, example) for pattern in self.forbidden_patterns)
                self.assertFalse(is_forbidden, f"文档示例不应该包含禁止的用法: {example}")
    
    def test_edge_cases(self):
        """测试边界情况"""
        edge_cases = [
            # 空命令
            ("", True, "空命令应该被允许"),
            # 只有relay-cli
            ("relay-cli", True, "单独的relay-cli命令应该被允许"),
            # 有多余参数
            ("relay-cli hostname", False, "有参数的relay-cli命令应该被拒绝"),
            ("relay-cli --user user", False, "有--user参数的命令应该被拒绝"),
            # 多余的参数
            ("relay-cli hostname --user user --extra-param", False, "多余参数应该被拒绝"),
        ]
        
        for command, expected_valid, description in edge_cases:
            with self.subTest(command=command):
                if command == "":
                    # 空命令特殊处理
                    self.assertTrue(expected_valid, description)
                else:
                    # 使用正则模式检查
                    is_correct = any(re.search(pattern, command) for pattern in self.correct_patterns)
                    is_forbidden = any(re.search(pattern, command) for pattern in self.forbidden_patterns)
                    
                    if expected_valid:
                        self.assertTrue(is_correct and not is_forbidden, description)
                    else:
                        self.assertFalse(is_correct and not is_forbidden, description)


class TestRelayCLIRegressionPrevention(unittest.TestCase):
    """防止relay-cli使用回归的测试"""
    
    def test_prevent_command_parameter_regression(self):
        """防止再次添加命令参数的回归测试"""
        # 这个测试专门检查常见的错误模式
        regression_patterns = [
            r"relay-cli.*--command\s+[\"'].*[\"']",
            r"relay-cli.*--timeout\s+\d+.*--command",
            r"relay-cli.*\&\&",
            r"relay-cli.*\|",
            r"relay-cli.*;"
        ]
        
        # 这些是过去犯过的错误，确保不会再次出现
        historical_mistakes = [
            'relay-cli bjhw-sys-rpm0221.bjhw --user xuyehua --timeout 5 --command "echo test"',
            'relay-cli bjhw-sys-rpm0221.bjhw --user xuyehua --command "pwd && hostname"',
            'relay-cli server --user user --timeout 10 --command "ls -la"'
        ]
        
        for mistake in historical_mistakes:
            with self.subTest(mistake=mistake):
                # 这些错误应该被检测到
                is_error = any(re.search(pattern, mistake) for pattern in regression_patterns)
                self.assertTrue(is_error, f"历史错误应该被检测到: {mistake}")
    
    def test_correct_usage_still_works(self):
        """确保正确的用法仍然可以工作"""
        correct_usage = "relay-cli"
        
        # 正确的用法不应该匹配任何禁止的模式
        forbidden_patterns = [
            r"relay-cli\s+\S+",       # relay-cli后面接任何非空白字符参数
            r"relay-cli.*--user",     # relay-cli后面接--user参数
            r"relay-cli.*--command",  # relay-cli后面接--command参数
            r"relay-cli.*--timeout",  # relay-cli后面接--timeout参数
            r"relay-cli.*--help",     # relay-cli后面接--help参数
            r"relay-cli.*--version",  # relay-cli后面接--version参数
            r"relay-cli.*\".*\"",     # relay-cli后面接引号内容
            r"relay-cli.*'.*'",       # relay-cli后面接单引号内容
        ]
        
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertFalse(re.search(pattern, correct_usage),
                               f"正确的用法不应该匹配禁止的模式: {pattern}")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2) 