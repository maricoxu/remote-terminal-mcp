#!/usr/bin/env python3
"""
回归测试：修复 save_config 参数名不匹配问题
日期：2025-01-15
问题：save_config() got an unexpected keyword argument 'merge_mode'
修复：将 merge_mode 参数改为 merge 参数
"""
import unittest
import sys
import os
from pathlib import Path
import tempfile
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'python'))

from config_manager.main import EnhancedConfigManager


class TestSaveConfigParameterFix(unittest.TestCase):
    """测试 save_config 方法参数名修复"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'config.yaml'
        self.config_manager = EnhancedConfigManager(str(self.config_path))
        
    def tearDown(self):
        """测试后清理"""
        if self.config_path.exists():
            self.config_path.unlink()
        if Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_save_config_with_merge_parameter(self):
        """测试 save_config 方法使用正确的 merge 参数"""
        test_config = {
            'servers': {
                'test_server': {
                    'host': 'test.example.com',
                    'username': 'testuser',
                    'port': 22,
                    'description': 'Test server'
                }
            }
        }
        
        # 这应该成功工作，不抛出参数错误
        try:
            self.config_manager.io.save_config(test_config, merge=True)
            self.assertTrue(True, "save_config with merge=True succeeded")
        except TypeError as e:
            if "merge_mode" in str(e):
                self.fail(f"save_config still uses old parameter name: {e}")
            else:
                raise
        
        # 验证配置文件是否正确保存
        self.assertTrue(self.config_path.exists(), "Config file should be created")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        
        self.assertIn('servers', saved_config)
        self.assertIn('test_server', saved_config['servers'])
        self.assertEqual(saved_config['servers']['test_server']['host'], 'test.example.com')
    
    def test_save_config_with_merge_false(self):
        """测试 save_config 方法使用 merge=False 参数"""
        test_config = {
            'servers': {
                'test_server': {
                    'host': 'test.example.com',
                    'username': 'testuser',
                    'port': 22,
                    'description': 'Test server'
                }
            }
        }
        
        # 这应该成功工作，不抛出参数错误
        try:
            self.config_manager.io.save_config(test_config, merge=False)
            self.assertTrue(True, "save_config with merge=False succeeded")
        except TypeError as e:
            if "merge_mode" in str(e):
                self.fail(f"save_config still uses old parameter name: {e}")
            else:
                raise
        
        # 验证配置文件是否正确保存
        self.assertTrue(self.config_path.exists(), "Config file should be created")
    
    def test_save_config_parameter_name_consistency(self):
        """测试 save_config 方法参数名一致性"""
        import inspect
        
        # 获取 save_config 方法的签名
        sig = inspect.signature(self.config_manager.io.save_config)
        param_names = list(sig.parameters.keys())
        
        # 验证参数名
        self.assertIn('config', param_names, "save_config should have 'config' parameter")
        self.assertIn('merge', param_names, "save_config should have 'merge' parameter")
        self.assertNotIn('merge_mode', param_names, "save_config should not have 'merge_mode' parameter")
    
    def test_regression_server_deletion_scenario(self):
        """测试服务器删除场景的回归测试"""
        # 创建测试配置
        initial_config = {
            'servers': {
                'test_server1': {
                    'host': 'test1.example.com',
                    'username': 'user1',
                    'port': 22
                },
                'test_server2': {
                    'host': 'test2.example.com', 
                    'username': 'user2',
                    'port': 22
                }
            }
        }
        
        # 保存初始配置
        self.config_manager.io.save_config(initial_config, merge=False)
        
        # 模拟删除服务器的操作
        updated_config = {
            'servers': {
                'test_server1': {
                    'host': 'test1.example.com',
                    'username': 'user1',
                    'port': 22
                }
                # test_server2 被删除了
            }
        }
        
        # 这应该成功工作（这是导致原始错误的场景）
        try:
            self.config_manager.io.save_config(updated_config, merge=False)
            self.assertTrue(True, "Server deletion scenario succeeded")
        except TypeError as e:
            if "merge_mode" in str(e):
                self.fail(f"Server deletion failed due to parameter name issue: {e}")
            else:
                raise
        
        # 验证删除是否成功
        with open(self.config_path, 'r', encoding='utf-8') as f:
            final_config = yaml.safe_load(f)
        
        self.assertIn('test_server1', final_config['servers'])
        self.assertNotIn('test_server2', final_config['servers'])


if __name__ == '__main__':
    print("🧪 运行 save_config 参数名修复的回归测试...")
    unittest.main(verbosity=2) 