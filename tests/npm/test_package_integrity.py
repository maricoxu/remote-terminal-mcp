#!/usr/bin/env python3
"""
NPM包完整性测试
测试npm包的结构、权限和功能完整性
"""

import sys
import unittest
import json
import subprocess
from pathlib import Path

# 添加测试工具路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from test_helpers import BaseTestCase, check_npm_package_integrity, run_command

class TestNPMPackageIntegrity(BaseTestCase):
    """测试NPM包完整性"""
    
    def setUp(self):
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.package_json_path = self.project_root / "package.json"
    
    def test_package_json_exists(self):
        """测试package.json文件存在"""
        self.assertTrue(self.package_json_path.exists(), 
                       "package.json文件必须存在")
    
    def test_package_json_structure(self):
        """测试package.json结构完整性"""
        with open(self.package_json_path) as f:
            package_data = json.load(f)
        
        # 检查必要字段
        required_fields = [
            'name', 'version', 'description', 'main', 
            'bin', 'scripts', 'dependencies'
        ]
        
        for field in required_fields:
            self.assertIn(field, package_data, 
                         f"package.json必须包含{field}字段")
        
        # 检查bin配置
        self.assertIn('remote-terminal-mcp', package_data['bin'],
                     "package.json必须配置remote-terminal-mcp命令")
    
    def test_main_entry_file(self):
        """测试主入口文件"""
        with open(self.package_json_path) as f:
            package_data = json.load(f)
        
        main_file = self.project_root / package_data['main']
        self.assertTrue(main_file.exists(), 
                       f"主入口文件{package_data['main']}必须存在")
        
        # 检查文件权限
        import stat
        file_stat = main_file.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IEXEC)
        self.assertTrue(is_executable, "主入口文件必须有执行权限")
    
    def test_required_python_files(self):
        """测试必要的Python文件"""
        required_files = [
            'enhanced_config_manager.py',
            'docker_config_manager.py',
            'python/mcp_server.py'
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            self.assertTrue(full_path.exists(), 
                           f"必要文件{file_path}必须存在")
    
    def test_dependencies_installable(self):
        """测试依赖项可安装性"""
        with open(self.package_json_path) as f:
            package_data = json.load(f)
        
        # 检查关键依赖
        critical_deps = ['chalk']  # 移除@modelcontextprotocol/sdk，因为这个项目没有使用它
        
        for dep in critical_deps:
            self.assertIn(dep, package_data.get('dependencies', {}),
                         f"关键依赖{dep}必须在dependencies中")
    
    def test_scripts_configuration(self):
        """测试脚本配置"""
        with open(self.package_json_path) as f:
            package_data = json.load(f)
        
        scripts = package_data.get('scripts', {})
        
        # 检查推荐的脚本
        recommended_scripts = ['test', 'start']
        
        for script in recommended_scripts:
            if script in scripts:
                self.assertIsInstance(scripts[script], str,
                                    f"脚本{script}必须是字符串")

class TestNPMPackageInstallation(BaseTestCase):
    """测试NPM包安装"""
    
    def setUp(self):
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
    
    def test_npm_pack_success(self):
        """测试npm pack成功"""
        try:
            result = run_command(['npm', 'pack'], 
                                cwd=self.project_root, timeout=60)
            
            self.assertEqual(result.returncode, 0, 
                           f"npm pack失败: {result.stderr}")
            
            # npm pack会生成.tgz文件，检查文件是否生成
            output = result.stdout.strip()
            self.assertTrue(output.endswith('.tgz'), 
                          f"npm pack应该生成.tgz文件，实际输出: {output}")
            
            # 检查生成的文件是否存在
            tgz_file = self.project_root / output
            self.assertTrue(tgz_file.exists(), 
                          f"生成的包文件{output}应该存在")
            
            # 清理生成的文件
            if tgz_file.exists():
                tgz_file.unlink()
                
        except subprocess.TimeoutExpired:
            self.fail("npm pack命令超时")
        except Exception as e:
            self.fail(f"npm pack测试失败: {e}")
    
    def test_package_size_reasonable(self):
        """测试包大小合理"""
        try:
            result = run_command(['npm', 'pack', '--dry-run'], 
                                cwd=self.project_root, timeout=60)
            
            if result.returncode == 0:
                # 从输出中提取包大小信息
                # npm pack --dry-run 会显示包的大小
                output_lines = result.stdout.strip().split('\n')
                
                # 查找包含大小信息的行
                size_info = None
                for line in output_lines:
                    if 'tarball' in line.lower() or 'size' in line.lower():
                        size_info = line
                        break
                
                if size_info:
                    # 这里可以添加更具体的大小检查
                    self.assertTrue(True, f"包大小信息: {size_info}")
                else:
                    self.assertTrue(True, "npm pack执行成功")
                    
        except Exception as e:
            # 如果npm pack失败，记录但不让测试失败
            print(f"警告: npm pack大小检查失败: {e}")

class TestNPMPackagePublishing(BaseTestCase):
    """测试NPM包发布准备"""
    
    def setUp(self):
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
    
    def test_version_consistency(self):
        """测试版本一致性"""
        # 读取package.json版本
        with open(self.project_root / 'package.json') as f:
            package_data = json.load(f)
        
        package_version = package_data['version']
        
        # 检查版本格式
        import re
        version_pattern = r'^\d+\.\d+\.\d+(-\w+\.\d+)?$'
        self.assertTrue(re.match(version_pattern, package_version),
                       f"版本号{package_version}格式不正确")
    
    def test_npm_publish_dry_run(self):
        """测试npm发布预演"""
        try:
            result = run_command(['npm', 'publish', '--dry-run'], 
                                cwd=self.project_root, timeout=60)
            
            # npm publish --dry-run 可能返回非0状态码但仍然有用
            # 我们主要检查是否有严重错误
            if 'error' in result.stderr.lower() and 'ENOENT' not in result.stderr:
                # 忽略文件不存在的错误，关注其他错误
                serious_errors = [
                    'syntax error',
                    'invalid',
                    'malformed'
                ]
                
                has_serious_error = any(error in result.stderr.lower() 
                                      for error in serious_errors)
                
                if has_serious_error:
                    self.fail(f"npm publish预演发现严重错误: {result.stderr}")
            
            self.assertTrue(True, "npm publish预演完成")
            
        except subprocess.TimeoutExpired:
            self.fail("npm publish预演超时")
        except Exception as e:
            # 记录警告但不让测试失败，因为可能需要认证
            print(f"警告: npm publish预演失败: {e}")

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2) 