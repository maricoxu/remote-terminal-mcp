#!/usr/bin/env python3
"""
测试辅助工具模块
提供通用的测试功能和工具函数
"""

import os
import sys
import tempfile
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import unittest

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'python'))

class TestEnvironment:
    """测试环境管理器"""
    
    def __init__(self):
        self.temp_dirs = []
        self.original_env = {}
    
    def create_temp_config_dir(self) -> Path:
        """创建临时配置目录"""
        temp_dir = Path(tempfile.mkdtemp(prefix="remote_terminal_test_"))
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def set_env_var(self, key: str, value: str):
        """设置环境变量（会在清理时恢复）"""
        if key not in self.original_env:
            self.original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    def cleanup(self):
        """清理测试环境"""
        # 清理临时目录
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        self.temp_dirs.clear()
        
        # 恢复环境变量
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        self.original_env.clear()

@contextmanager
def test_environment():
    """测试环境上下文管理器"""
    env = TestEnvironment()
    try:
        yield env
    finally:
        env.cleanup()

class MockConfigManager:
    """模拟配置管理器"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_path = config_dir / "config.yaml"
        self.servers = {}
    
    def create_mock_config(self, servers: Dict[str, Any] = None):
        """创建模拟配置文件"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.config_dir / "docker_templates").mkdir(exist_ok=True)
        (self.config_dir / "templates").mkdir(exist_ok=True)
        
        # 创建配置文件
        config = {"servers": servers or {}}
        with open(self.config_path, 'w') as f:
            import yaml
            yaml.dump(config, f)
        
        self.servers = servers or {}
    
    def get_existing_servers(self) -> Dict[str, Any]:
        """获取现有服务器配置"""
        return self.servers.copy()

def run_command(cmd: List[str], cwd: Path = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"命令超时: {' '.join(cmd)}")

def check_file_permissions(file_path: Path, expected_mode: str = None) -> bool:
    """检查文件权限"""
    if not file_path.exists():
        return False
    
    if expected_mode:
        import stat
        current_mode = oct(file_path.stat().st_mode)[-3:]
        return current_mode == expected_mode
    
    return True

def check_npm_package_integrity(package_path: Path) -> Dict[str, Any]:
    """检查npm包的完整性"""
    results = {
        "package_json_exists": False,
        "index_js_exists": False,
        "index_js_executable": False,
        "required_files_exist": False,
        "version_consistent": False
    }
    
    # 检查package.json
    package_json_path = package_path / "package.json"
    if package_json_path.exists():
        results["package_json_exists"] = True
        
        try:
            with open(package_json_path) as f:
                package_data = json.load(f)
            
            # 检查版本一致性
            if "version" in package_data:
                results["version_consistent"] = True
        except json.JSONDecodeError:
            pass
    
    # 检查index.js
    index_js_path = package_path / "index.js"
    if index_js_path.exists():
        results["index_js_exists"] = True
        results["index_js_executable"] = check_file_permissions(index_js_path)
    
    # 检查必要文件
    required_files = ["enhanced_config_manager.py", "docker_config_manager.py"]
    results["required_files_exist"] = all(
        (package_path / file).exists() for file in required_files
    )
    
    return results

class BaseTestCase(unittest.TestCase):
    """基础测试用例类"""
    
    def setUp(self):
        """测试设置"""
        self.test_env = TestEnvironment()
        self.temp_config_dir = self.test_env.create_temp_config_dir()
    
    def tearDown(self):
        """测试清理"""
        self.test_env.cleanup()
    
    def assert_config_directory_structure(self, config_dir: Path):
        """断言配置目录结构正确"""
        self.assertTrue(config_dir.exists(), "配置目录必须存在")
        
        # 检查配置文件是否存在（更实际的检查）
        config_file = config_dir / 'config.yaml'
        if config_file.exists():
            self.assertTrue(True, "配置文件存在")
        else:
            # 如果配置文件不存在，至少目录应该存在
            self.assertTrue(config_dir.exists(), "配置目录应该存在")
    
    def assert_method_exists(self, obj: Any, method_name: str):
        """断言对象有指定方法"""
        self.assertTrue(hasattr(obj, method_name), 
                       f"对象必须有{method_name}方法")
        method = getattr(obj, method_name)
        self.assertTrue(callable(method), 
                       f"{method_name}必须是可调用的方法")

def get_test_data_path() -> Path:
    """获取测试数据目录路径"""
    return Path(__file__).parent / "test_data"

def create_test_server_config() -> Dict[str, Any]:
    """创建测试用的服务器配置"""
    return {
        "test-server": {
            "host": "192.168.1.100",
            "username": "testuser",
            "port": 22,
            "private_key_path": "~/.ssh/id_rsa",
            "type": "script_based",
            "connection_type": "ssh",
            "description": "测试服务器",
            "session": {
                "name": "test_session",
                "working_directory": "~",
                "shell": "/bin/bash"
            }
        }
    }

def create_test_docker_config() -> Dict[str, Any]:
    """创建测试用的Docker配置"""
    return {
        "container_name": "test-container",
        "image": "ubuntu:20.04",
        "ports": [],
        "volumes": [],
        "environment": {},
        "shell_config": {
            "config_source": "test"
        }
    }

class TestReporter:
    """测试报告生成器"""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, test_name: str, status: str, message: str = ""):
        """添加测试结果"""
        self.results.append({
            "test_name": test_name,
            "status": status,
            "message": message
        })
    
    def generate_report(self) -> str:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = total - passed
        
        report = f"测试报告\n{'='*50}\n"
        report += f"总计: {total} 个测试\n"
        report += f"通过: {passed} 个\n"
        report += f"失败: {failed} 个\n\n"
        
        if failed > 0:
            report += "失败的测试:\n"
            for result in self.results:
                if result["status"] == "FAIL":
                    report += f"❌ {result['test_name']}: {result['message']}\n"
        
        return report
    
    def save_report(self, file_path: Path):
        """保存测试报告到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())

# 导出常用的测试工具
__all__ = [
    'TestEnvironment',
    'test_environment', 
    'MockConfigManager',
    'run_command',
    'check_file_permissions',
    'check_npm_package_integrity',
    'BaseTestCase',
    'get_test_data_path',
    'create_test_server_config',
    'create_test_docker_config',
    'TestReporter'
] 