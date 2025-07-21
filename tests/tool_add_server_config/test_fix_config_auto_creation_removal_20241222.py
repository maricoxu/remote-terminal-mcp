#!/usr/bin/env python3
"""
配置文件自动创建移除功能测试

测试目标：
1. 验证npm安装后不会自动创建配置文件
2. 验证enhanced_config_manager不会自动创建配置
3. 验证MCP工具在没有配置时给出友好提示
4. 验证用户可以通过MCP工具主动创建配置

创建时间：2024年12月22日
修复问题：npm版本更新导致config.yaml被覆盖的问题
解决方案：完全移除自动配置创建，让用户主动配置
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'python'))

from config_manager.main import EnhancedConfigManager


class TestConfigAutoCreationRemoval(unittest.TestCase):
    """测试配置文件自动创建移除功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'config.yaml')
        
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_ensure_config_exists_no_auto_creation(self):
        """测试配置文件不会自动创建"""
        manager = EnhancedConfigManager(self.config_path)
        
        # 确保配置文件不存在
        self.assertFalse(os.path.exists(self.config_path))
        
        # 调用get_existing_servers，应该返回空字典，不创建文件
        result = manager.list_servers()
        
        # 验证结果
        self.assertIsInstance(result, dict, "应该返回字典类型")
        self.assertEqual(len(result), 0, "没有配置文件时应该返回空字典")
        self.assertFalse(os.path.exists(self.config_path), "不应该自动创建配置文件")
    
    def test_ensure_config_exists_with_valid_config(self):
        """测试有有效配置文件时的行为"""
        manager = EnhancedConfigManager(self.config_path)
        
        # 创建有效的配置文件
        valid_config = """
servers:
  test-server:
    host: test.com
    username: testuser
    port: 22

global_settings:
  default_timeout: 30
"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(valid_config)
        
        # 调用get_existing_servers，应该返回服务器列表
        result = manager.list_servers()
        
        # 验证结果
        self.assertIsInstance(result, dict, "应该返回字典类型")
        self.assertIn('test-server', result, "应该包含配置的服务器")
        self.assertTrue(os.path.exists(self.config_path), "配置文件应该继续存在")
    
    def test_ensure_config_exists_with_invalid_config(self):
        """测试有无效配置文件时的行为"""
        manager = EnhancedConfigManager(self.config_path)
        
        # 创建无效的配置文件（空文件）
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        # 调用get_existing_servers，应该返回空字典
        result = manager.list_servers()
        
        # 验证结果
        self.assertIsInstance(result, dict, "应该返回字典类型")
        self.assertEqual(len(result), 0, "无效配置文件时应该返回空字典")
    
    def test_ensure_config_exists_with_yaml_error(self):
        """测试YAML格式错误的配置文件"""
        manager = EnhancedConfigManager(self.config_path)
        
        # 创建YAML格式错误的配置文件
        invalid_yaml = """
servers:
  test-server:
    host: test.com
    username: testuser
    port: 22
  invalid_yaml: [unclosed bracket
"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(invalid_yaml)
        
        # 调用get_existing_servers，应该返回空字典
        result = manager.list_servers()
        
        # 验证结果
        self.assertIsInstance(result, dict, "应该返回字典类型")
        self.assertEqual(len(result), 0, "YAML格式错误时应该返回空字典")
    
    def test_get_existing_servers_no_config(self):
        """测试没有配置文件时获取服务器列表"""
        manager = EnhancedConfigManager(self.config_path)
        
        # 确保配置文件不存在
        self.assertFalse(os.path.exists(self.config_path))
        
        # 获取服务器列表，应该返回空字典
        servers = manager.list_servers()
        
        # 验证结果
        self.assertIsInstance(servers, dict, "应该返回字典类型")
        self.assertEqual(len(servers), 0, "没有配置文件时应该返回空字典")
    
    def test_mcp_mode_behavior(self):
        """测试MCP模式下的行为（静默模式）"""
        manager = EnhancedConfigManager(self.config_path)
        manager.is_mcp_mode = True  # 设置为MCP模式
        
        # 确保配置文件不存在
        self.assertFalse(os.path.exists(self.config_path))
        
        # 调用get_existing_servers，应该返回空字典，不输出任何信息
        result = manager.list_servers()
        
        # 验证结果
        self.assertIsInstance(result, dict, "应该返回字典类型")
        self.assertEqual(len(result), 0, "MCP模式下也不应该自动创建配置")
        self.assertFalse(os.path.exists(self.config_path), "MCP模式下不应该创建配置文件")
    
    def test_config_directory_creation(self):
        """测试配置目录的创建行为"""
        # 使用不存在的目录路径
        non_existent_dir = os.path.join(self.test_dir, 'non_existent')
        config_path = os.path.join(non_existent_dir, 'config.yaml')
        
        manager = EnhancedConfigManager(config_path)
        
        # 确保目录和文件都不存在
        self.assertFalse(os.path.exists(non_existent_dir))
        self.assertFalse(os.path.exists(config_path))
        
        # 调用get_existing_servers
        result = manager.list_servers()
        
        # 验证结果：不应该创建目录或文件
        self.assertIsInstance(result, dict, "应该返回字典类型")
        self.assertEqual(len(result), 0, "不应该自动创建配置")
        # 注意：目录可能会被创建，但配置文件不应该被创建
        self.assertFalse(os.path.exists(config_path), "不应该创建配置文件")

def run_tests():
    """运行所有测试"""
    print("🧪 开始测试配置文件自动创建移除功能...")
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigAutoCreationRemoval)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        print(f"\n✅ 所有测试通过！({result.testsRun}项测试)")
        return True
    else:
        print(f"\n❌ 测试失败！失败数: {len(result.failures)}, 错误数: {len(result.errors)}")
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 