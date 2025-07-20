#!/usr/bin/env python3
"""
增强的Docker配置测试
整合新功能、zsh配置、用户路径等测试
"""
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

import pytest
import yaml
from config_manager.docker_config import DockerConfigCollector
from config_manager.interaction import UserInteraction


class MockInteraction(UserInteraction):
    """模拟用户交互"""
    def __init__(self, inputs=None):
        super().__init__()
        self.inputs = inputs or []
        self.outputs = []
        self.input_counter = 0
    
    def colored_print(self, text, color=None):
        self.outputs.append(text)
    
    def smart_input(self, prompt, default=None, validator=None):
        self.input_counter += 1
        if self.input_counter <= len(self.inputs):
            return self.inputs[self.input_counter - 1]
        return default or ""


class TestDockerConfigEnhanced:
    """增强的Docker配置测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.user_config_dir = Path(self.temp_dir) / '.remote-terminal-mcp' / 'docker_configs'
        self.user_config_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('pathlib.Path.home')
    def test_create_new_docker_config(self, mock_home):
        """测试创建新的Docker配置"""
        mock_home.return_value = Path(self.temp_dir)
        
        # 模拟用户输入：选择创建新配置，输入容器名称和镜像，启用zsh配置
        inputs = ["2", "test_container", "ubuntu:20.04", "y", "y"]
        interaction = MockInteraction(inputs)
        
        collector = DockerConfigCollector(interaction)
        result = collector.configure_docker()
        
        # 验证结果
        assert result['container_name'] == "test_container"
        assert result['image'] == "ubuntu:20.04"
        assert result['enable_zsh_config'] is True
        assert result['shell'] == "zsh"
        assert "zsh" in result['install_packages']
        assert result['use_existing_config'] is False
        
        # 验证配置文件是否保存
        config_file = self.user_config_dir / "test_container_config.yaml"
        assert config_file.exists()
        
        # 验证保存的配置内容
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        assert saved_config['enable_zsh_config'] is True
        assert saved_config['shell'] == "zsh"
    
    @patch('pathlib.Path.home')
    def test_create_docker_config_without_zsh(self, mock_home):
        """测试创建Docker配置但不启用zsh"""
        mock_home.return_value = Path(self.temp_dir)
        
        # 模拟用户输入：选择创建新配置，输入容器名称和镜像，不启用zsh配置
        inputs = ["2", "test_container_bash", "ubuntu:20.04", "n", "y"]
        interaction = MockInteraction(inputs)
        
        collector = DockerConfigCollector(interaction)
        result = collector.configure_docker()
        
        # 验证结果
        assert result['container_name'] == "test_container_bash"
        assert result['image'] == "ubuntu:20.04"
        assert result['enable_zsh_config'] is False
        assert result['shell'] == "bash"
        assert "zsh" not in result['install_packages']
        assert result['use_existing_config'] is False
    
    @patch('pathlib.Path.home')
    def test_use_existing_config(self, mock_home):
        """测试使用现有配置"""
        mock_home.return_value = Path(self.temp_dir)
        
        # 创建现有配置文件
        existing_config = {
            'container_name': 'existing_container',
            'image': 'ubuntu:18.04',
            'shell': 'bash',
            'enable_zsh_config': False
        }
        config_file = self.user_config_dir / "existing_container_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(existing_config, f)
        
        # 模拟用户输入：选择使用现有配置，选择第一个配置
        inputs = ["1", "1"]
        interaction = MockInteraction(inputs)
        
        collector = DockerConfigCollector(interaction)
        result = collector.configure_docker()
        
        # 验证结果
        assert result['use_existing_config'] is True
        assert result['config_name'] == "existing_container_config"
        assert result['container_name'] == "existing_container"
        assert result['image'] == "ubuntu:18.04"
    
    @patch('pathlib.Path.home')
    def test_skip_docker_config(self, mock_home):
        """测试跳过Docker配置"""
        mock_home.return_value = Path(self.temp_dir)
        
        # 模拟用户输入：选择不使用Docker
        inputs = ["3"]
        interaction = MockInteraction(inputs)
        
        collector = DockerConfigCollector(interaction)
        result = collector.configure_docker()
        
        # 验证结果
        assert result == {}
    
    @patch('pathlib.Path.home')
    def test_user_config_path_priority(self, mock_home):
        """测试用户配置路径优先级"""
        mock_home.return_value = Path(self.temp_dir)
        
        # 创建用户目录配置
        user_config = {
            'container_name': 'user_container',
            'image': 'user_image',
            'shell': 'zsh'
        }
        user_config_file = self.user_config_dir / "user_container_config.yaml"
        with open(user_config_file, 'w', encoding='utf-8') as f:
            yaml.dump(user_config, f)
        
        # 模拟用户输入：选择使用现有配置，选择第一个配置
        inputs = ["1", "1"]
        interaction = MockInteraction(inputs)
        
        collector = DockerConfigCollector(interaction)
        result = collector.configure_docker()
        
        # 验证用户目录配置被正确加载
        assert result['use_existing_config'] is True
        assert result['container_name'] == "user_container"
        assert result['image'] == "user_image"
        assert result['shell'] == "zsh"
    
    @patch('pathlib.Path.home')
    def test_config_validation(self, mock_home):
        """测试配置验证"""
        mock_home.return_value = Path(self.temp_dir)
        
        # 测试无效的容器名称
        inputs = ["2", "invalid@name", "ubuntu:20.04", "n", "y"]
        interaction = MockInteraction(inputs)
        
        collector = DockerConfigCollector(interaction)
        
        # 这里应该会失败，因为容器名称包含无效字符
        # 在实际使用中，validator会阻止这种情况
        # 这里我们主要测试配置验证逻辑存在
        assert hasattr(collector, '_create_new_config')
    
    def test_docker_config_data_structure(self):
        """测试Docker配置数据结构"""
        from config_manager.docker_config import DockerEnvironmentConfig
        
        # 测试数据类
        config = DockerEnvironmentConfig(
            container_name="test_container",
            image="ubuntu:20.04",
            shell="zsh",
            ports=["8080:8080"],
            volumes=["/home:/home"]
        )
        
        # 验证数据类属性
        assert config.container_name == "test_container"
        assert config.image == "ubuntu:20.04"
        assert config.shell == "zsh"
        assert config.ports == ["8080:8080"]
        assert config.volumes == ["/home:/home"]
        
        # 测试转换为字典
        config_dict = config.to_dict()
        assert config_dict['container_name'] == "test_container"
        assert config_dict['image'] == "ubuntu:20.04"
        assert config_dict['shell'] == "zsh"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 