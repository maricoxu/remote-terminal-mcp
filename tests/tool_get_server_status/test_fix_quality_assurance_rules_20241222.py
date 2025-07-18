#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试：修复质量保证规则

测试目的：
- 验证 .cursorrules 文件的质量门禁规则
- 验证回归测试目录结构和命名规范
- 验证测试内容完整性
"""
import os
import sys
import unittest
import re
from pathlib import Path

# 将项目根目录添加到sys.path，以便导入模块
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class QualityAssuranceRulesTest(unittest.TestCase):
    """测试质量保证规则"""

    def setUp(self):
        """测试初始化"""
        self.project_root = Path(__file__).parent.parent.parent
        # 以当前 tests/tool_xxx 目录为目标，而不是强绑定 tests/regression
        self.current_test_dir = Path(__file__).parent
        self.cursorrules_file = self.project_root / ".cursorrules"
        
    def test_regression_directory_structure(self):
        """测试1：验证当前测试目录结构完整性"""
        print("🧪 测试当前测试目录结构...")
        
        # 验证当前测试目录存在
        self.assertTrue(
            self.current_test_dir.exists(),
            f"当前测试目录 {self.current_test_dir} 必须存在"
        )
        
        # 验证当前目录下有测试文件
        test_files = list(self.current_test_dir.glob("test_*.py"))
        self.assertGreater(
            len(test_files), 0,
            f"当前测试目录 {self.current_test_dir} 必须包含测试文件"
        )
        
        # 验证utils目录存在
        utils_dir = self.project_root / "tests" / "utils"
        self.assertTrue(
            utils_dir.exists(),
            "测试工具目录 tests/utils/ 必须存在"
        )
        
        print("✅ 当前测试目录结构完整")
        
    def test_regression_test_naming_convention(self):
        """测试2：验证测试文件命名规范"""
        print("🧪 测试测试文件命名规范...")
        
        # 获取当前目录下所有测试文件
        test_files = list(self.current_test_dir.glob("test_*.py"))
        
        # 验证至少有一个测试文件
        self.assertGreater(
            len(test_files), 0,
            f"当前测试目录 {self.current_test_dir} 必须至少有一个测试文件"
        )
        
        # 验证文件命名规范（更宽松的规范）
        naming_pattern = re.compile(r"test_[a-zA-Z0-9_]+\.py")
        
        valid_files = []
        invalid_files = []
        
        for test_file in test_files:
            if naming_pattern.match(test_file.name):
                valid_files.append(test_file.name)
            else:
                invalid_files.append(test_file.name)
        
        if invalid_files:
            self.fail(
                f"以下测试文件不符合命名规范 'test_[问题描述].py':\n"
                f"{', '.join(invalid_files)}"
            )
        
        print(f"✅ 所有 {len(valid_files)} 个测试文件命名规范正确")
        
    def test_regression_test_content_quality(self):
        """测试3：验证测试内容完整性"""
        print("🧪 测试测试内容质量...")
        
        test_files = list(self.current_test_dir.glob("test_*.py"))
        
        for test_file in test_files:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证必须有中文注释
            self.assertRegex(
                content, r'[一-龟]+',
                f"测试文件 {test_file.name} 必须包含中文注释说明"
            )
            
            # 验证必须有测试类
            self.assertIn(
                'class', content,
                f"测试文件 {test_file.name} 必须包含测试类"
            )
            
            # 验证必须有测试方法
            self.assertRegex(
                content, r'def test_',
                f"测试文件 {test_file.name} 必须包含以test_开头的测试方法"
            )
            
            # 验证必须有文档字符串
            self.assertIn(
                '"""', content,
                f"测试文件 {test_file.name} 必须包含详细的文档字符串"
            )
        
        print(f"✅ 所有 {len(test_files)} 个测试文件内容完整")
        
    def test_regression_test_script_exists(self):
        """测试4：验证回归测试脚本存在"""
        print("🧪 测试回归测试脚本存在性...")
        
        # 验证当前测试文件存在
        current_test_file = Path(__file__)
        self.assertTrue(
            current_test_file.exists(),
            f"当前测试文件 {current_test_file} 必须存在"
        )
        
        # 验证文件大小合理
        file_size = current_test_file.stat().st_size
        self.assertGreater(
            file_size, 100,
            f"测试文件 {current_test_file.name} 大小必须大于100字节"
        )
        
        print("✅ 回归测试脚本存在且内容合理")
        
    def test_cursorrules_quality_gates(self):
        """测试5：验证.cursorrules质量门禁"""
        print("🧪 测试.cursorrules质量门禁...")
        
        # 验证.cursorrules文件存在
        self.assertTrue(
            self.cursorrules_file.exists(),
            ".cursorrules 文件必须存在"
        )
        
        # 验证文件内容
        with open(self.cursorrules_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证包含必要的规则
        required_rules = [
            '回归测试',
            '质量保证',
            '测试先行'
        ]
        
        for rule in required_rules:
            self.assertIn(
                rule, content,
                f".cursorrules 文件必须包含 '{rule}' 规则"
            )
        
        print("✅ .cursorrules质量门禁规则完整")
        
    def test_quality_assurance_workflow_compliance(self):
        """测试6：验证质量保证工作流合规性"""
        print("🧪 测试质量保证工作流合规性...")
        
        # 验证项目结构
        required_dirs = [
            'tests',
            'python',
            'python/config_manager'
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            self.assertTrue(
                dir_path.exists(),
                f"项目必须包含 {dir_name} 目录"
            )
        
        # 验证测试覆盖率
        test_dirs = list((self.project_root / 'tests').glob('tool_*'))
        self.assertGreater(
            len(test_dirs), 0,
            "项目必须包含至少一个工具测试目录"
        )
        
        print("✅ 质量保证工作流合规") 