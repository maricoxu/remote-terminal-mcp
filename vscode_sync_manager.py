#!/usr/bin/env python3
"""
VSCode同步管理器
负责管理.vscode/sftp.json配置文件，支持多profile配置
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_output(message, level="INFO"):
    """统一的日志输出函数"""
    if not os.getenv('MCP_QUIET'):
        level_emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }
        emoji = level_emoji.get(level, "📋")
        print(f"{emoji} {message}")


class VSCodeSyncManager:
    """VSCode SFTP配置管理器"""
    
    def __init__(self, workspace_path: str = None):
        """初始化VSCode同步管理器"""
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.vscode_dir = self.workspace_path / ".vscode"
        self.sftp_config_path = self.vscode_dir / "sftp.json"
        
        # 确保.vscode目录存在
        self.vscode_dir.mkdir(exist_ok=True)
        
        log_output(f"🔧 VSCode同步管理器初始化完成，工作目录: {self.workspace_path}", "SUCCESS")
    
    def load_sftp_config(self) -> Dict[str, Any]:
        """加载现有的SFTP配置"""
        if not self.sftp_config_path.exists():
            log_output("📄 未找到现有的sftp.json配置文件，将创建新配置", "INFO")
            return {}
        
        try:
            with open(self.sftp_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                log_output(f"✅ 成功加载现有SFTP配置，包含 {len(config.get('profiles', {}))} 个profiles", "SUCCESS")
                return config
        except json.JSONDecodeError as e:
            log_output(f"❌ SFTP配置文件格式错误: {e}", "ERROR")
            return {}
        except Exception as e:
            log_output(f"❌ 加载SFTP配置失败: {e}", "ERROR")
            return {}
    
    def save_sftp_config(self, config: Dict[str, Any]) -> bool:
        """保存SFTP配置到文件"""
        try:
            with open(self.sftp_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            log_output(f"✅ SFTP配置已保存到: {self.sftp_config_path}", "SUCCESS")
            return True
        except Exception as e:
            log_output(f"❌ 保存SFTP配置失败: {e}", "ERROR")
            return False
    
    def create_profile(self, server_name: str, sync_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的SFTP profile配置"""
        profile_name = f"remote-terminal-{server_name}"
        
        # 构建profile配置
        profile_config = {
            "name": f"远程终端-{server_name}",
            "protocol": "ftp",
            "host": sync_config.get('host'),
            "port": sync_config.get('ftp_port', 8021),
            "username": sync_config.get('ftp_user', 'ftpuser'),
            "password": sync_config.get('ftp_password'),
            "remotePath": sync_config.get('remote_workspace', '/home/Code'),
            "uploadOnSave": True,
            "passive": True,
            "ignore": [
                ".vscode",
                ".git",
                ".DS_Store",
                "node_modules/**",
                "*.log"
            ]
        }
        
        log_output(f"🔧 创建SFTP profile: {profile_name}", "INFO")
        return {profile_name: profile_config}
    
    def add_or_update_profile(self, server_name: str, sync_config: Dict[str, Any]) -> bool:
        """添加或更新SFTP profile"""
        try:
            # 加载现有配置
            config = self.load_sftp_config()
            
            # 确保profiles字段存在
            if 'profiles' not in config:
                config['profiles'] = {}
            
            # 创建新的profile
            new_profile = self.create_profile(server_name, sync_config)
            profile_name = list(new_profile.keys())[0]
            
            # 检查是否已存在
            if profile_name in config['profiles']:
                log_output(f"⚠️ Profile {profile_name} 已存在，将更新配置", "WARNING")
            else:
                log_output(f"➕ 添加新的Profile: {profile_name}", "INFO")
            
            # 添加或更新profile
            config['profiles'].update(new_profile)
            
            # 设置默认profile（如果没有设置的话）
            if 'defaultProfile' not in config:
                config['defaultProfile'] = profile_name
                log_output(f"🎯 设置默认Profile: {profile_name}", "INFO")
            
            # 保存配置
            return self.save_sftp_config(config)
            
        except Exception as e:
            log_output(f"❌ 添加/更新Profile失败: {e}", "ERROR")
            return False
    
    def list_profiles(self) -> List[str]:
        """列出所有可用的profiles"""
        config = self.load_sftp_config()
        profiles = list(config.get('profiles', {}).keys())
        log_output(f"📋 找到 {len(profiles)} 个SFTP profiles: {', '.join(profiles)}", "INFO")
        return profiles
    
    def set_active_profile(self, profile_name: str) -> bool:
        """设置活动的profile"""
        try:
            # 使用VSCode命令切换profile
            cmd = ['code', '--command', 'sftp.setProfile', profile_name]
            
            log_output(f"🔄 切换到SFTP Profile: {profile_name}", "INFO")
            
            # 尝试执行VSCode命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                log_output(f"✅ 成功切换到Profile: {profile_name}", "SUCCESS")
                return True
            else:
                log_output(f"⚠️ VSCode命令执行失败，可能需要手动切换Profile", "WARNING")
                log_output(f"💡 请在VSCode中执行: Ctrl+Shift+P -> SFTP: Set Profile -> {profile_name}", "INFO")
                return False
                
        except subprocess.TimeoutExpired:
            log_output("⚠️ VSCode命令执行超时，请手动切换Profile", "WARNING")
            return False
        except FileNotFoundError:
            log_output("⚠️ 未找到VSCode命令，请确保VSCode已安装并添加到PATH", "WARNING")
            log_output(f"💡 请在VSCode中手动执行: Ctrl+Shift+P -> SFTP: Set Profile -> {profile_name}", "INFO")
            return False
        except Exception as e:
            log_output(f"❌ 切换Profile失败: {e}", "ERROR")
            return False
    
    def remove_profile(self, server_name: str) -> bool:
        """移除指定服务器的profile"""
        try:
            config = self.load_sftp_config()
            profile_name = f"remote-terminal-{server_name}"
            
            if 'profiles' in config and profile_name in config['profiles']:
                del config['profiles'][profile_name]
                log_output(f"🗑️ 已移除Profile: {profile_name}", "INFO")
                
                # 如果删除的是默认profile，清除默认设置
                if config.get('defaultProfile') == profile_name:
                    if config['profiles']:
                        # 设置第一个profile为默认
                        config['defaultProfile'] = list(config['profiles'].keys())[0]
                        log_output(f"🎯 默认Profile已更改为: {config['defaultProfile']}", "INFO")
                    else:
                        # 没有其他profile了，移除默认设置
                        config.pop('defaultProfile', None)
                        log_output("🎯 已清除默认Profile设置", "INFO")
                
                return self.save_sftp_config(config)
            else:
                log_output(f"⚠️ Profile {profile_name} 不存在", "WARNING")
                return True
                
        except Exception as e:
            log_output(f"❌ 移除Profile失败: {e}", "ERROR")
            return False
    
    def get_profile_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """获取指定服务器的profile信息"""
        config = self.load_sftp_config()
        profile_name = f"remote-terminal-{server_name}"
        
        if 'profiles' in config and profile_name in config['profiles']:
            return config['profiles'][profile_name]
        return None
    
    def validate_workspace(self) -> bool:
        """验证当前工作目录是否适合设置同步"""
        # 检查是否在git仓库中
        git_dir = self.workspace_path / ".git"
        if git_dir.exists():
            log_output("✅ 检测到Git仓库，适合设置同步", "SUCCESS")
            return True
        
        # 检查是否有常见的项目文件
        project_files = [
            "package.json", "requirements.txt", "Cargo.toml", 
            "go.mod", "pom.xml", "build.gradle", "Makefile"
        ]
        
        for file_name in project_files:
            if (self.workspace_path / file_name).exists():
                log_output(f"✅ 检测到项目文件 {file_name}，适合设置同步", "SUCCESS")
                return True
        
        log_output("⚠️ 当前目录可能不是项目根目录，建议在项目根目录中设置同步", "WARNING")
        return True  # 仍然允许设置，但给出警告


def create_vscode_sync_manager(workspace_path: str = None) -> VSCodeSyncManager:
    """创建VSCode同步管理器实例"""
    return VSCodeSyncManager(workspace_path)


if __name__ == "__main__":
    # 测试代码
    manager = create_vscode_sync_manager()
    
    # 测试配置
    test_sync_config = {
        'host': 'test-server.com',
        'ftp_port': 8021,
        'ftp_user': 'testuser',
        'ftp_password': 'testpass',
        'remote_workspace': '/home/Code/test'
    }
    
    # 添加测试profile
    if manager.add_or_update_profile('test-server', test_sync_config):
        print("✅ 测试profile添加成功")
        
        # 列出profiles
        profiles = manager.list_profiles()
        print(f"📋 当前profiles: {profiles}")
        
        # 获取profile信息
        info = manager.get_profile_info('test-server')
        print(f"📄 Profile信息: {info}") 