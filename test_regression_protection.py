#!/usr/bin/env python3
"""
回归测试保护脚本
防止新功能破坏已有功能的自动化测试
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

class RegressionProtector:
    """回归测试保护器"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        # 获取项目根目录
        self.project_root = Path(__file__).parent
    
    def run_test(self, test_name, test_command):
        """运行单个测试"""
        print(f"\n🧪 运行测试: {test_name}")
        print("=" * 50)
        
        try:
            result = subprocess.run(
                test_command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=60,
                cwd=str(self.project_root)  # 设置工作目录
            )
            
            if result.returncode == 0:
                print(f"✅ {test_name} - 通过")
                self.test_results.append((test_name, "PASS", ""))
                return True
            else:
                print(f"❌ {test_name} - 失败")
                print(f"错误输出: {result.stderr}")
                self.test_results.append((test_name, "FAIL", result.stderr))
                self.failed_tests.append(test_name)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name} - 超时")
            self.test_results.append((test_name, "TIMEOUT", "测试超时"))
            self.failed_tests.append(test_name)
            return False
        except Exception as e:
            print(f"💥 {test_name} - 异常: {e}")
            self.test_results.append((test_name, "ERROR", str(e)))
            self.failed_tests.append(test_name)
            return False
    
    def run_core_tests(self):
        """运行核心功能测试"""
        print("🛡️ 开始回归测试保护检查")
        print("=" * 60)
        
        # 核心测试列表
        core_tests = [
            ("Shell配置测试", "python3 test_shell_config.py"),
            # ("Zsh连接测试", "python3 test_zsh_connection.py"),  # 暂时禁用，需要实际网络连接
            ("配置文件语法检查", f"python3 -c 'import sys; sys.path.insert(0, \"{self.project_root}/python\"); import config_manager.main; print(\"配置管理器导入成功\")'"),
            ("MCP服务器语法检查", f"python3 -c 'import sys; sys.path.insert(0, \"{self.project_root}/python\"); import mcp_server; print(\"MCP服务器导入成功\")'"),
        ]
        
        # 运行所有测试
        for test_name, test_command in core_tests:
            self.run_test(test_name, test_command)
        
        # 生成报告
        self.generate_report()
        
        # 返回是否所有测试都通过
        return len(self.failed_tests) == 0
    
    def generate_report(self):
        """生成测试报告"""
        print("\n📊 回归测试报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {len(self.failed_tests)}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ 失败的测试:")
            for test_name in self.failed_tests:
                print(f"  - {test_name}")
            
            print(f"\n⚠️ 警告: 有 {len(self.failed_tests)} 个测试失败!")
            print("建议在提交代码前修复这些问题。")
        else:
            print(f"\n✅ 所有测试通过! 代码质量良好。")
        
        # 保存报告到文件
        self.save_report_to_file()
    
    def save_report_to_file(self):
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"regression_test_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"回归测试报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for test_name, status, error in self.test_results:
                f.write(f"{test_name}: {status}\n")
                if error:
                    f.write(f"  错误: {error}\n")
                f.write("\n")
        
        print(f"📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    protector = RegressionProtector()
    
    print("🚀 Remote Terminal - 回归测试保护")
    print("防止新功能破坏已有功能")
    print("=" * 60)
    
    # 运行核心测试
    all_passed = protector.run_core_tests()
    
    # 根据结果设置退出码
    if all_passed:
        print("\n🎉 所有测试通过! 可以安全提交代码。")
        sys.exit(0)
    else:
        print("\n🚨 有测试失败! 请修复后再提交代码。")
        sys.exit(1)

if __name__ == "__main__":
    main() 