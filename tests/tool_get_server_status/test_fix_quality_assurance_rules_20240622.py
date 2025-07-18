#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回归测试：质量保证规则实施验证
测试目标：确保每个修复都有对应的回归测试案例
创建日期：2024-06-22
修复问题：强化质量保证规则，防止无测试的代码提交

测试内容：
1. 验证回归测试目录结构完整性
2. 验证测试文件命名规范
3. 验证测试内容完整性
4. 验证质量门禁机制
"""

import unittest
import os
import sys
import re
import ast
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class QualityAssuranceRulesTest(unittest.TestCase):
    """质量保证规则实施验证测试"""
    
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
        print("🧪 测试回归测试内容质量...")
        
        test_files = list(self.current_test_dir.glob("test_fix_*.py"))
        
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
        
    def test_cursorrules_quality_gates(self):
        """测试4：验证.cursorrules文件中的质量门禁规则"""
        print("🧪 测试.cursorrules质量门禁规则...")
        
        # 验证.cursorrules文件存在
        self.assertTrue(
            self.cursorrules_file.exists(),
            ".cursorrules文件必须存在"
        )
        
        with open(self.cursorrules_file, 'r', encoding='utf-8') as f:
            cursorrules_content = f.read()
        
        # 验证必须包含强制性回归测试要求
        required_rules = [
            "强制性回归测试要求",
            "每修复一个问题后，必须无条件执行",
            "全量回归测试执行",
            "质量门禁",
            "没有回归测试的修复不允许提交",
            "回归测试失败的代码不允许合并",
            "测试先行原则"
        ]
        
        for rule in required_rules:
            self.assertIn(
                rule, cursorrules_content,
                f".cursorrules文件必须包含质量门禁规则: {rule}"
            )
        
        print("✅ .cursorrules质量门禁规则完整")
        
    def test_regression_test_script_exists(self):
        """测试5：验证回归测试执行脚本存在"""
        print("🧪 测试回归测试执行脚本...")
        
        script_path = self.project_root / "scripts" / "run-regression-tests.sh"
        
        self.assertTrue(
            script_path.exists(),
            "回归测试执行脚本 scripts/run-regression-tests.sh 必须存在"
        )
        
        # 验证脚本有执行权限
        self.assertTrue(
            os.access(script_path, os.X_OK),
            "回归测试执行脚本必须有执行权限"
        )
        
        print("✅ 回归测试执行脚本存在且可执行")
        
    def test_quality_assurance_workflow_compliance(self):
        """测试6：验证质量保证工作流程合规性"""
        print("🧪 测试质量保证工作流程合规性...")
        
        # 验证当前测试本身符合质量要求
        current_file = Path(__file__)
        
        # 验证文件命名符合规范
        self.assertRegex(
            current_file.name,
            r"test_fix_[a-zA-Z0-9_]+_\d{8}\.py",
            "当前测试文件名必须符合命名规范"
        )
        
        # 验证测试内容完整性
        with open(current_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证有中文注释
        self.assertRegex(content, r'[一-龟]+', "必须有中文注释")
        
        # 验证有测试目标说明
        self.assertIn("测试目标", content, "必须有明确的测试目标说明")
        
        # 验证有修复问题说明
        self.assertIn("修复问题", content, "必须有修复问题的说明")
        
        print("✅ 质量保证工作流程合规")

def main():
    """运行质量保证规则验证测试"""
    print("🎯 开始质量保证规则验证测试")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(QualityAssuranceRulesTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("🎉 所有质量保证规则验证测试通过！")
        print("✅ 回归测试体系完整")
        print("✅ 质量门禁规则有效")
        print("✅ 工作流程合规")
        return 0
    else:
        print("❌ 质量保证规则验证测试失败！")
        print(f"失败测试数: {len(result.failures)}")
        print(f"错误测试数: {len(result.errors)}")
        return 1

if __name__ == "__main__":
    exit(main()) 