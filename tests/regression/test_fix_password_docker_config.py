#!/usr/bin/env python3
"""
回归测试：验证密码配置和Docker配置功能
测试日期：2024-12-21
问题描述：配置向导缺少密码配置和Docker配置选项
修复内容：添加密码配置步骤（可选）和Docker配置步骤
"""

import sys
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
import io

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from enhanced_config_manager import EnhancedConfigManager

def test_password_configuration():
    """测试密码配置功能"""
    print("🔐 Testing password configuration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.yaml"
        manager = EnhancedConfigManager(str(config_path))
        
        # 测试1：跳过密码配置（直接回车）
        with patch('builtins.input', return_value=''):
            password = manager._configure_password()
            assert password is None, "Password should be None when skipped"
        
        # 测试2：设置密码
        with patch('builtins.input', return_value='test_password'):
            password = manager._configure_password()
            assert password == 'test_password', "Password should be set correctly"
        
        # 测试3：更新已有密码（保持不变）
        prefill = {'password': 'existing_password'}
        with patch('builtins.input', return_value='keep'):
            password = manager._configure_password(prefill=prefill)
            assert password == 'existing_password', "Existing password should be kept"
        
        # 测试4：更新已有密码（设置新密码）
        with patch('builtins.input', side_effect=['new', 'new_password']):
            password = manager._configure_password(prefill=prefill)
            assert password == 'new_password', "New password should be set"
    
    print("✅ Password configuration test passed")

def test_docker_configuration():
    """测试Docker配置功能"""
    print("🐳 Testing Docker configuration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.yaml"
        manager = EnhancedConfigManager(str(config_path))
        
        # 测试1：不启用Docker
        with patch('builtins.input', return_value='2'):
            docker_config = manager._configure_docker()
            assert docker_config is None, "Docker config should be None when disabled"
        
        # 测试2：启用Docker并配置基本选项
        inputs = [
            '1',  # 启用Docker
            'ubuntu:22.04',  # 镜像
            'test_container',  # 容器名
            # 端口映射 - 有默认值，我们覆盖前两个，跳过第三个
            '8080:8080',  # 端口1 (覆盖默认的8080:8080)
            '9000:9000',  # 端口2 (覆盖默认的8888:8888)  
            '',  # 端口3 (跳过默认的6006:6006)
            '',  # 添加端口（跳过）
            # 卷挂载 - 有默认值，我们覆盖
            '/home:/home',  # 卷1 (覆盖默认的/home:/home)
            '/data:/data',  # 卷2 (覆盖默认的/data:/data)
            '',  # 添加卷（跳过）
            'bash',  # Shell
            '1'  # 自动创建
        ]
        
        with patch('builtins.input', side_effect=inputs):
            docker_config = manager._configure_docker()
            
            assert docker_config is not None, "Docker config should not be None"
            assert docker_config['image'] == 'ubuntu:22.04', "Docker image incorrect"
            assert docker_config['container_name'] == 'test_container', "Container name incorrect"
            assert '8080:8080' in docker_config['ports'], "Port mapping missing"
            assert '9000:9000' in docker_config['ports'], "Port mapping missing"
            assert '/home:/home' in docker_config['volumes'], "Volume mapping missing"
            assert '/data:/data' in docker_config['volumes'], "Volume mapping missing"
            assert docker_config['shell'] == 'bash', "Shell incorrect"
            
            assert docker_config['auto_create'] is True, f"Auto create should be True, but got {docker_config['auto_create']}"
    
    print("✅ Docker configuration test passed")

def test_guided_setup_with_password_and_docker():
    """测试完整的引导设置包含密码和Docker配置"""
    print("🔧 Testing complete guided setup with password and Docker...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.yaml"
        manager = EnhancedConfigManager(str(config_path))
        
        # 模拟用户输入：创建新服务器，包含密码和Docker配置
        inputs = [
            'test_server',  # 服务器名称
            '2',  # SSH直连
            'user@test.host',  # 服务器地址
            '22',  # 端口
            'test_password',  # 密码
            '1',  # 启用Docker
            'ubuntu:20.04',  # Docker镜像
            'test_container',  # 容器名
            # 端口映射（有3个默认值）
            '8080:8080',  # 端口1 (覆盖默认的8080:8080)
            '',  # 端口2 (跳过8888:8888)
            '',  # 端口3 (跳过6006:6006)
            '',  # 不添加更多端口
            # 卷挂载（有2个默认值）
            '/home:/home',  # 卷1 (覆盖默认的/home:/home)
            '',  # 卷2 (跳过/data:/data)
            '',  # 不添加更多卷
            'bash',  # Shell
            '1'  # 自动创建容器
        ]
        
        with patch('builtins.input', side_effect=inputs):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                manager.guided_setup()
        
        # 验证配置文件是否正确生成
        assert config_path.exists(), "Config file should be created"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        assert 'servers' in config, "Config should contain servers section"
        assert 'test_server' in config['servers'], "Test server should be in config"
        
        server_config = config['servers']['test_server']
        
        # 验证基本配置
        assert server_config['host'] == 'test.host', "Host incorrect"
        assert server_config['username'] == 'user', "Username incorrect"
        assert server_config['port'] == 22, "Port incorrect"
        assert server_config['connection_type'] == 'ssh', "Connection type incorrect"
        
        # 验证密码配置
        assert server_config['password'] == 'test_password', "Password not saved correctly"
        
        # 验证Docker配置
        assert server_config['docker_enabled'] is True, "Docker should be enabled"
        assert server_config['docker_image'] == 'ubuntu:20.04', "Docker image incorrect"
        assert server_config['docker_container'] == 'test_container', "Docker container incorrect"
        assert '8080:8080' in server_config['docker_ports'], "Docker port mapping missing"
        assert '/home:/home' in server_config['docker_volumes'], "Docker volume mapping missing"
        assert server_config['docker_shell'] == 'bash', "Docker shell incorrect"
        assert server_config['docker_auto_create'] is True, "Docker auto create should be True"
    
    print("✅ Complete guided setup test passed")

def test_update_server_with_password_and_docker():
    """测试更新现有服务器的密码和Docker配置"""
    print("🔄 Testing server update with password and Docker...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.yaml"
        manager = EnhancedConfigManager(str(config_path))
        
        # 首先创建一个基本服务器配置
        existing_config = {
            'servers': {
                'existing_server': {
                    'host': 'old.host',
                    'username': 'olduser',
                    'port': 22,
                    'connection_type': 'ssh'
                }
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(existing_config, f, allow_unicode=True)
        
        # 模拟更新现有服务器，添加密码和Docker配置
        inputs = [
            'existing_server',  # 选择现有服务器
            '2',  # SSH直连
            'newuser@new.host',  # 新的服务器地址
            '2222',  # 新端口
            'new_password',  # 添加密码
            '1',  # 启用Docker
            'nginx:latest',  # Docker镜像
            'nginx_container',  # 容器名
            # 端口映射（有3个默认值）
            '80:80',  # 端口1 (覆盖默认的8080:8080)
            '',  # 端口2 (跳过8888:8888)
            '',  # 端口3 (跳过6006:6006)
            '',  # 不添加更多端口
            # 卷挂载（有2个默认值）
            '/var/www:/var/www',  # 卷1 (覆盖默认的/home:/home)
            '',  # 卷2 (跳过/data:/data)
            '',  # 不添加更多卷
            'sh',  # Shell
            '2'  # 手动管理容器
        ]
        
        with patch('builtins.input', side_effect=inputs):
            with patch('sys.stdout', new_callable=io.StringIO):
                manager.guided_setup()
        
        # 验证配置是否正确更新
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config['servers']['existing_server']
        
        # 验证基本配置更新
        assert server_config['host'] == 'new.host', "Host not updated"
        assert server_config['username'] == 'newuser', "Username not updated"
        assert server_config['port'] == 2222, "Port not updated"
        
        # 验证新增的密码配置
        assert server_config['password'] == 'new_password', "Password not added"
        
        # 验证新增的Docker配置
        assert server_config['docker_enabled'] is True, "Docker not enabled"
        assert server_config['docker_image'] == 'nginx:latest', "Docker image incorrect"
        assert server_config['docker_container'] == 'nginx_container', "Docker container incorrect"
        assert server_config['docker_auto_create'] is False, "Docker auto create should be False"
    
    print("✅ Server update test passed")

def run_all_tests():
    """运行所有测试"""
    print("🧪 Starting password and Docker configuration regression tests...")
    print("=" * 60)
    
    try:
        test_password_configuration()
        test_docker_configuration()
        test_guided_setup_with_password_and_docker()
        test_update_server_with_password_and_docker()
        
        print("=" * 60)
        print("🎉 All password and Docker configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 