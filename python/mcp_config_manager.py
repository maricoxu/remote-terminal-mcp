#!/usr/bin/env python3
"""
MCP Configuration Manager

专门为MCP集成设计的配置管理器，提供通过Cursor对话进行配置管理的功能
"""

import os
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import tempfile

@dataclass
class ServerConfig:
    """服务器配置数据类"""
    name: str
    host: str
    username: str
    port: int = 22
    connection_type: str = "ssh"  # ssh, relay
    relay_target_host: Optional[str] = None
    docker_enabled: bool = False
    docker_container: Optional[str] = None
    docker_image: Optional[str] = None
    description: Optional[str] = None
    bos_bucket: Optional[str] = None
    tmux_session_prefix: Optional[str] = None

class MCPConfigManager:
    """MCP配置管理器"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'remote-terminal-mcp'
        self.config_file = self.config_dir / 'config.yaml'
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            'servers': {},
            'settings': {
                'default_connection_timeout': 30,
                'auto_create_tmux_session': True,
                'default_docker_image': 'ubuntu:20.04'
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            return {'servers': {}, 'settings': {}}
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    def create_server_config(self, config_data: Dict[str, Any]) -> str:
        """创建服务器配置"""
        try:
            # 验证必需字段
            required_fields = ['name', 'host', 'username']
            missing_fields = [field for field in required_fields if not config_data.get(field)]
            if missing_fields:
                return f"❌ 缺少必需字段: {', '.join(missing_fields)}"
            
            # 创建服务器配置对象
            server_config = ServerConfig(**config_data)
            
            # 加载现有配置
            config = self.load_config()
            if 'servers' not in config:
                config['servers'] = {}
            
            # 检查服务器名称是否已存在
            if server_config.name in config['servers']:
                return f"❌ 服务器 '{server_config.name}' 已存在，请使用不同的名称"
            
            # 添加新服务器配置
            config['servers'][server_config.name] = asdict(server_config)
            
            # 保存配置
            self.save_config(config)
            
            return f"✅ 服务器 '{server_config.name}' 配置已创建"
            
        except Exception as e:
            return f"❌ 创建配置失败: {str(e)}"
    
    def list_server_configs(self) -> List[Dict[str, Any]]:
        """列出所有服务器配置"""
        config = self.load_config()
        servers = config.get('servers', {})
        
        server_list = []
        for name, server_config in servers.items():
            server_list.append({
                'name': name,
                'host': server_config.get('host', ''),
                'username': server_config.get('username', ''),
                'connection_type': server_config.get('connection_type', 'ssh'),
                'description': server_config.get('description', ''),
                'docker_enabled': server_config.get('docker_enabled', False)
            })
        
        return server_list
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """获取特定服务器配置"""
        config = self.load_config()
        servers = config.get('servers', {})
        return servers.get(server_name)
    
    def update_server_config(self, server_name: str, updates: Dict[str, Any]) -> str:
        """更新服务器配置"""
        try:
            config = self.load_config()
            servers = config.get('servers', {})
            
            if server_name not in servers:
                return f"❌ 服务器 '{server_name}' 不存在"
            
            # 更新配置
            servers[server_name].update(updates)
            
            # 保存配置
            self.save_config(config)
            
            return f"✅ 服务器 '{server_name}' 配置已更新"
            
        except Exception as e:
            return f"❌ 更新配置失败: {str(e)}"
    
    def delete_server_config(self, server_name: str) -> str:
        """删除服务器配置"""
        try:
            config = self.load_config()
            servers = config.get('servers', {})
            
            if server_name not in servers:
                return f"❌ 服务器 '{server_name}' 不存在"
            
            # 删除配置
            del servers[server_name]
            
            # 保存配置
            self.save_config(config)
            
            return f"✅ 服务器 '{server_name}' 配置已删除"
            
        except Exception as e:
            return f"❌ 删除配置失败: {str(e)}"
    
    def test_server_connection(self, server_name: str) -> str:
        """测试服务器连接"""
        try:
            server_config = self.get_server_config(server_name)
            if not server_config:
                return f"❌ 服务器 '{server_name}' 不存在"
            
            host = server_config['host']
            port = server_config.get('port', 22)
            username = server_config['username']
            connection_type = server_config.get('connection_type', 'ssh')
            
            result_lines = [f"🔍 测试服务器连接: {server_name}"]
            result_lines.append(f"   主机: {host}:{port}")
            result_lines.append(f"   用户: {username}")
            result_lines.append(f"   连接类型: {connection_type}")
            result_lines.append("")
            
            # 测试网络连通性
            result_lines.append("📡 网络连通性测试:")
            try:
                ping_result = subprocess.run(
                    ['ping', '-c', '3', host], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if ping_result.returncode == 0:
                    result_lines.append("   ✅ Ping 测试成功")
                else:
                    result_lines.append("   ❌ Ping 测试失败")
            except Exception as e:
                result_lines.append(f"   ⚠️  Ping 测试异常: {str(e)}")
            
            # 测试SSH连接
            result_lines.append("")
            result_lines.append("🔐 SSH连接测试:")
            try:
                if connection_type == "relay":
                    # 使用relay-cli测试
                    relay_target = server_config.get('relay_target_host', host)
                    ssh_cmd = ['relay-cli', 'ssh', f"{username}@{relay_target}", 'echo "Connection test successful"']
                else:
                    # 直接SSH测试
                    ssh_cmd = ['ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', 
                              f"{username}@{host}", 'echo "Connection test successful"']
                
                ssh_result = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if ssh_result.returncode == 0:
                    result_lines.append("   ✅ SSH连接测试成功")
                else:
                    result_lines.append("   ❌ SSH连接测试失败")
                    if ssh_result.stderr:
                        result_lines.append(f"   错误信息: {ssh_result.stderr.strip()}")
                        
            except Exception as e:
                result_lines.append(f"   ⚠️  SSH连接测试异常: {str(e)}")
            
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"❌ 连接测试失败: {str(e)}"
    
    def export_configs(self, export_path: Optional[str] = None) -> str:
        """导出配置"""
        try:
            config = self.load_config()
            
            if export_path is None:
                export_path = str(Path.home() / 'remote-terminal-mcp-config-export.yaml')
            
            with open(export_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            return f"✅ 配置已导出到: {export_path}"
            
        except Exception as e:
            return f"❌ 导出配置失败: {str(e)}"
    
    def import_configs(self, import_path: str) -> str:
        """导入配置"""
        try:
            if not os.path.exists(import_path):
                return f"❌ 导入文件不存在: {import_path}"
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = yaml.safe_load(f)
            
            if not isinstance(imported_config, dict):
                return "❌ 导入文件格式无效"
            
            # 合并配置
            current_config = self.load_config()
            
            # 合并服务器配置
            if 'servers' in imported_config:
                if 'servers' not in current_config:
                    current_config['servers'] = {}
                current_config['servers'].update(imported_config['servers'])
            
            # 合并设置
            if 'settings' in imported_config:
                if 'settings' not in current_config:
                    current_config['settings'] = {}
                current_config['settings'].update(imported_config['settings'])
            
            # 保存合并后的配置
            self.save_config(current_config)
            
            imported_servers = len(imported_config.get('servers', {}))
            return f"✅ 配置导入成功，导入了 {imported_servers} 个服务器配置"
            
        except Exception as e:
            return f"❌ 导入配置失败: {str(e)}"
    
    def run_quick_setup_wizard(self, server_type: str = "ssh") -> str:
        """运行快速设置向导（模拟交互式配置）"""
        try:
            # 这里提供一个模拟的快速配置流程
            # 在实际使用中，用户会通过Cursor对话提供这些信息
            
            templates = {
                "ssh": {
                    "name": "new-ssh-server",
                    "host": "example.com",
                    "username": "user",
                    "port": 22,
                    "connection_type": "ssh",
                    "description": "SSH服务器配置模板"
                },
                "relay": {
                    "name": "new-relay-server",
                    "host": "relay-host.com",
                    "username": "user",
                    "port": 22,
                    "connection_type": "relay",
                    "relay_target_host": "target-host.com",
                    "description": "Relay服务器配置模板"
                },
                "docker": {
                    "name": "new-docker-server",
                    "host": "docker-host.com",
                    "username": "user",
                    "port": 22,
                    "connection_type": "ssh",
                    "docker_enabled": True,
                    "docker_container": "my_container",
                    "docker_image": "ubuntu:20.04",
                    "description": "Docker服务器配置模板"
                }
            }
            
            if server_type not in templates:
                return f"❌ 不支持的服务器类型: {server_type}"
            
            template = templates[server_type]
            
            instructions = [
                f"🚀 {server_type.upper()} 服务器快速配置向导",
                "",
                "📋 配置模板已生成，请根据实际情况修改以下参数：",
                "",
                "🔧 使用 create_server_config 工具创建配置，参数如下：",
                ""
            ]
            
            for key, value in template.items():
                instructions.append(f"   {key}: {value}")
            
            instructions.extend([
                "",
                "💡 示例用法：",
                f"   请帮我创建一个名为 'my-server' 的{server_type}服务器配置，",
                f"   主机地址是 'my-host.com'，用户名是 'myuser'",
                "",
                "🎯 或者直接说：",
                f"   '配置一个新的{server_type}服务器'"
            ])
            
            return "\n".join(instructions)
            
        except Exception as e:
            return f"❌ 快速设置向导失败: {str(e)}"
    
    def diagnose_connection_issues(self, server_name: str, 
                                 include_network_test: bool = True,
                                 include_config_validation: bool = True) -> str:
        """诊断连接问题"""
        try:
            server_config = self.get_server_config(server_name)
            if not server_config:
                return f"❌ 服务器 '{server_name}' 不存在"
            
            diagnosis_lines = [f"🔍 连接诊断报告: {server_name}"]
            diagnosis_lines.append("=" * 50)
            
            # 配置验证
            if include_config_validation:
                diagnosis_lines.append("")
                diagnosis_lines.append("📋 配置验证:")
                
                required_fields = ['name', 'host', 'username']
                missing_fields = [field for field in required_fields if not server_config.get(field)]
                
                if missing_fields:
                    diagnosis_lines.append(f"   ❌ 缺少必需字段: {', '.join(missing_fields)}")
                else:
                    diagnosis_lines.append("   ✅ 基本配置完整")
                
                # 检查端口
                port = server_config.get('port', 22)
                if not isinstance(port, int) or port <= 0 or port > 65535:
                    diagnosis_lines.append(f"   ⚠️  端口配置异常: {port}")
                else:
                    diagnosis_lines.append(f"   ✅ 端口配置正常: {port}")
                
                # 检查连接类型
                connection_type = server_config.get('connection_type', 'ssh')
                if connection_type not in ['ssh', 'relay']:
                    diagnosis_lines.append(f"   ⚠️  连接类型未知: {connection_type}")
                else:
                    diagnosis_lines.append(f"   ✅ 连接类型: {connection_type}")
            
            # 网络测试
            if include_network_test:
                diagnosis_lines.append("")
                diagnosis_lines.append("🌐 网络连通性:")
                
                host = server_config['host']
                try:
                    ping_result = subprocess.run(
                        ['ping', '-c', '1', host], 
                        capture_output=True, 
                        text=True, 
                        timeout=5
                    )
                    if ping_result.returncode == 0:
                        diagnosis_lines.append(f"   ✅ {host} 网络可达")
                    else:
                        diagnosis_lines.append(f"   ❌ {host} 网络不可达")
                except Exception as e:
                    diagnosis_lines.append(f"   ⚠️  网络测试异常: {str(e)}")
            
            # 常见问题建议
            diagnosis_lines.append("")
            diagnosis_lines.append("💡 常见问题排查建议:")
            diagnosis_lines.append("   1. 检查网络连接和防火墙设置")
            diagnosis_lines.append("   2. 验证SSH密钥或密码认证")
            diagnosis_lines.append("   3. 确认服务器SSH服务正在运行")
            diagnosis_lines.append("   4. 检查用户名和主机地址是否正确")
            
            if server_config.get('connection_type') == 'relay':
                diagnosis_lines.append("   5. 确认relay-cli工具已正确安装和配置")
            
            if server_config.get('docker_enabled'):
                diagnosis_lines.append("   6. 检查Docker服务状态和容器配置")
            
            return "\n".join(diagnosis_lines)
            
        except Exception as e:
            return f"❌ 连接诊断失败: {str(e)}" 