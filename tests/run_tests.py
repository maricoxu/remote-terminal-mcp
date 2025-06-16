#!/usr/bin/env python3
"""
测试运行器
支持运行不同类型的测试：本地测试、npm测试、集成测试
"""

import sys
import os
import unittest
import argparse
from pathlib import Path
from typing import List, Optional
import time

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'python'))

# 添加测试工具路径
sys.path.insert(0, str(Path(__file__).parent / 'utils'))
from test_helpers import TestReporter

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.tests_dir = Path(__file__).parent
        self.reporter = TestReporter()
    
    def discover_tests(self, test_type: str = "all") -> List[str]:
        """发现测试文件"""
        test_files = []
        
        if test_type in ["all", "local"]:
            local_tests = list((self.tests_dir / "local").glob("test_*.py"))
            test_files.extend([str(f) for f in local_tests])
        
        if test_type in ["all", "npm"]:
            npm_tests = list((self.tests_dir / "npm").glob("test_*.py"))
            test_files.extend([str(f) for f in npm_tests])
        
        if test_type in ["all", "integration"]:
            integration_tests = list((self.tests_dir / "integration").glob("test_*.py"))
            test_files.extend([str(f) for f in integration_tests])
        
        return test_files
    
    def run_test_file(self, test_file: str, verbose: bool = False) -> unittest.TestResult:
        """运行单个测试文件"""
        # 动态导入测试模块
        test_path = Path(test_file)
        module_name = test_path.stem
        
        # 添加测试文件所在目录到路径
        sys.path.insert(0, str(test_path.parent))
        
        try:
            # 导入测试模块
            spec = __import__(module_name)
            
            # 创建测试套件
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(spec)
            
            # 运行测试
            runner = unittest.TextTestRunner(
                verbosity=2 if verbose else 1,
                stream=sys.stdout,
                buffer=True
            )
            
            result = runner.run(suite)
            return result
            
        except Exception as e:
            print(f"❌ 运行测试文件 {test_file} 失败: {e}")
            # 创建一个失败的结果
            result = unittest.TestResult()
            result.errors.append((test_file, str(e)))
            return result
        finally:
            # 清理路径
            if str(test_path.parent) in sys.path:
                sys.path.remove(str(test_path.parent))
    
    def run_tests(self, test_type: str = "all", verbose: bool = False, 
                  specific_test: Optional[str] = None) -> bool:
        """运行测试"""
        print(f"🚀 开始运行 {test_type} 测试...")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"🧪 测试目录: {self.tests_dir}")
        print("=" * 60)
        
        start_time = time.time()
        
        if specific_test:
            # 运行特定测试文件
            test_files = [specific_test] if Path(specific_test).exists() else []
            if not test_files:
                print(f"❌ 测试文件不存在: {specific_test}")
                return False
        else:
            # 发现测试文件
            test_files = self.discover_tests(test_type)
        
        if not test_files:
            print(f"⚠️  没有找到 {test_type} 类型的测试文件")
            return True
        
        print(f"📋 发现 {len(test_files)} 个测试文件:")
        for test_file in test_files:
            print(f"  - {Path(test_file).name}")
        print()
        
        # 运行所有测试
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        for test_file in test_files:
            print(f"🧪 运行测试: {Path(test_file).name}")
            print("-" * 40)
            
            result = self.run_test_file(test_file, verbose)
            
            # 统计结果
            tests_run = result.testsRun
            failures = len(result.failures)
            errors = len(result.errors)
            
            total_tests += tests_run
            total_failures += failures
            total_errors += errors
            
            # 记录结果
            if failures == 0 and errors == 0:
                self.reporter.add_result(Path(test_file).name, "PASS", 
                                       f"{tests_run} 个测试通过")
                print(f"✅ {Path(test_file).name}: {tests_run} 个测试通过")
            else:
                error_msg = f"{failures} 个失败, {errors} 个错误"
                self.reporter.add_result(Path(test_file).name, "FAIL", error_msg)
                print(f"❌ {Path(test_file).name}: {error_msg}")
            
            print()
        
        # 生成总结报告
        end_time = time.time()
        duration = end_time - start_time
        
        print("=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"总测试数: {total_tests}")
        print(f"通过: {total_tests - total_failures - total_errors}")
        print(f"失败: {total_failures}")
        print(f"错误: {total_errors}")
        print(f"耗时: {duration:.2f} 秒")
        
        # 保存详细报告
        report_file = self.tests_dir / f"test_report_{test_type}_{int(time.time())}.txt"
        self.reporter.save_report(report_file)
        print(f"📄 详细报告已保存到: {report_file}")
        
        # 返回是否所有测试都通过
        success = total_failures == 0 and total_errors == 0
        
        if success:
            print("🎉 所有测试通过！")
        else:
            print("💥 有测试失败，请检查上面的错误信息")
        
        return success
    
    def run_pre_commit_tests(self) -> bool:
        """运行提交前测试（本地测试 + 回归测试）"""
        print("🔍 运行提交前测试...")
        
        # 运行本地测试
        local_success = self.run_tests("local", verbose=False)
        
        if not local_success:
            print("❌ 本地测试失败，请修复后再提交")
            return False
        
        print("✅ 提交前测试通过")
        return True
    
    def run_pre_publish_tests(self) -> bool:
        """运行发布前测试（所有测试）"""
        print("📦 运行发布前测试...")
        
        # 运行所有测试
        all_success = self.run_tests("all", verbose=True)
        
        if not all_success:
            print("❌ 发布前测试失败，请修复后再发布")
            return False
        
        print("✅ 发布前测试通过")
        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Remote Terminal MCP 测试运行器")
    
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "local", "npm", "integration"],
        help="要运行的测试类型 (默认: all)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )
    
    parser.add_argument(
        "-f", "--file",
        help="运行特定的测试文件"
    )
    
    parser.add_argument(
        "--pre-commit",
        action="store_true",
        help="运行提交前测试"
    )
    
    parser.add_argument(
        "--pre-publish",
        action="store_true",
        help="运行发布前测试"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.pre_commit:
            success = runner.run_pre_commit_tests()
        elif args.pre_publish:
            success = runner.run_pre_publish_tests()
        else:
            success = runner.run_tests(
                test_type=args.test_type,
                verbose=args.verbose,
                specific_test=args.file
            )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"💥 测试运行器出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 