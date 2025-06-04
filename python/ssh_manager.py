#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
SSH连接管理器

处理SSH连接、跳板机和远程命令执行
"""

import os
import sys
import time
import subprocess
import threading
import yaml
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class ServerConfig:
    """服务器配置"""
    name: str
    type: str  # direct_ssh, jump_ssh, script_based
    host: str
    port: int
    username: str
    private_key_path: str
    description: str
    specs: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    jump_host: Optional[Dict[str, Any]] = None


@dataclass
class ConnectionStatus:
    """连接状态"""
    server_name: str
    connected: bool
    last_check: float
    error_message: Optional[str] = None
    connection_time: Optional[float] = None


class SSHManager:
    """SSH连接管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化SSH管理器"""
        self.servers: Dict[str, ServerConfig] = {}
        self.connections: Dict[str, ConnectionStatus] = {}
        self.global_settings: Dict[str, Any] = {}
        self.security_settings: Dict[str, Any] = {}
        
        # 查找并加载配置文件
        self.config_path = self._find_config_file() if config_path is None else config_path
        self._load_config()
        
        # 创建默认tmux会话
        session_result = self._create_default_tmux_session()
        
        # 智能预连接（如果启用）
        preconnect_results = {}
        if self.global_settings.get('auto_preconnect', False):
            preconnect_results = self._smart_preconnect()
        
        # 显示启动摘要（非调试模式且成功初始化时）
        if not os.getenv('MCP_DEBUG') and not os.getenv('MCP_QUIET'):
            self._show_startup_summary(session_result, preconnect_results)
    
    def _find_config_file(self) -> str:
        """查找配置文件，如果不存在则自动创建默认配置"""
        # 1. 用户目录配置
        user_config_dir = Path.home() / ".remote-terminal-mcp"
        user_config_file = user_config_dir / "config.yaml"
        
        if user_config_file.exists():
            return str(user_config_file)
        
        # 2. 如果用户配置不存在，则自动创建
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent
        template_config = project_dir / "config" / "servers.template.yaml"
        
        if template_config.exists():
            # 创建用户配置目录
            user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制模板到用户目录
            import shutil
            shutil.copy2(template_config, user_config_file)
            
            # 创建默认tmux会话（如果tmux可用且会话不存在）
            self._create_default_tmux_session()
            
            print(f"📦 已自动创建默认配置: {user_config_file}")
            return str(user_config_file)
        
        # 3. 回退方案：项目本地配置
        local_config = project_dir / "config" / "servers.local.yaml"
        if local_config.exists():
            return str(local_config)
        
        # 4. 最后回退：直接使用模板
        if template_config.exists():
            return str(template_config)
        
        raise FileNotFoundError(
            "未找到配置模板文件！请检查项目完整性。\n"
            f"缺失文件: {template_config}"
        )
    
    def _create_default_tmux_session(self):
        """自动创建默认tmux会话，为用户提供即开即用的本地体验"""
        try:
            # 检查tmux是否可用
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
            if result.returncode != 0:
                return False
            
            # 检查dev-session是否已存在
            result = subprocess.run(['tmux', 'has-session', '-t', 'dev-session'], 
                                 capture_output=True)
            if result.returncode == 0:
                return True  # 会话已存在
            
            # 尝试在不同目录创建会话
            working_dirs = [
                str(Path.home() / "Code"),
                str(Path.home() / "code"), 
                str(Path.home() / "workspace"),
                str(Path.home())
            ]
            
            for working_dir in working_dirs:
                if Path(working_dir).exists():
                    try:
                        subprocess.run([
                            'tmux', 'new-session', 
                            '-d', '-s', 'dev-session',
                            '-c', working_dir
                        ], check=True, capture_output=True)
                        return True  # 成功创建
                        
                    except subprocess.CalledProcessError:
                        continue  # 尝试下一个目录
            
            return False  # 所有目录都失败
            
        except FileNotFoundError:
            return False  # tmux未安装
        except Exception:
            return False  # 其他错误
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 解析服务器配置
            servers_config = config.get('servers', {})
            for server_name, server_config in servers_config.items():
                # 为script_based类型构建specs字典
                specs = server_config.get('specs', {})
                
                # 如果是script_based类型，将connection、docker等配置放入specs
                if server_config.get('type') == 'script_based':
                    if 'connection' in server_config:
                        specs['connection'] = server_config['connection']
                    if 'docker' in server_config:
                        specs['docker'] = server_config['docker']
                    if 'bos' in server_config:
                        specs['bos'] = server_config['bos']
                    if 'environment_setup' in server_config:
                        specs['environment_setup'] = server_config['environment_setup']
                
                self.servers[server_name] = ServerConfig(
                    name=server_name,
                    type=server_config.get('type', 'direct_ssh'),
                    host=server_config.get('host', ''),
                    port=server_config.get('port', 22),
                    username=server_config.get('username', ''),
                    private_key_path=server_config.get('private_key_path', ''),
                    description=server_config.get('description', ''),
                    specs=specs,
                    session=server_config.get('session'),
                    jump_host=server_config.get('jump_host')
                )
                
                # 初始化连接状态
                self.connections[server_name] = ConnectionStatus(
                    server_name=server_name,
                    connected=False,
                    last_check=0
                )
            
            # 解析全局设置
            self.global_settings = config.get('global_settings', {})
            self.security_settings = config.get('security', {})
            
        except Exception as e:
            raise Exception(f"解析配置文件失败: {e}")
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器"""
        servers_info = []
        for server_name, server in self.servers.items():
            status = self.connections[server_name]
            
            server_info = {
                'name': server_name,
                'host': server.host,
                'description': server.description,
                'type': server.type,
                'connected': status.connected,
                'last_check': status.last_check,
                'specs': server.specs or {}
            }
            
            if server.jump_host:
                server_info['jump_host'] = server.jump_host['host']
            
            servers_info.append(server_info)
        
        return servers_info
    
    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """获取服务器配置"""
        return self.servers.get(server_name)
    
    def _expand_path(self, path: str) -> str:
        """展开路径中的波浪号"""
        if path.startswith('~'):
            return os.path.expanduser(path)
        return path
    
    def _validate_command(self, command: str) -> bool:
        """验证命令是否安全"""
        if not self.security_settings:
            return True  # 如果没有安全配置，允许所有命令
        
        allowed_commands = self.security_settings.get('allowed_commands', [])
        forbidden_commands = self.security_settings.get('forbidden_commands', [])
        
        # 检查禁止的命令
        for pattern in forbidden_commands:
            if re.match(pattern, command):
                return False
        
        # 检查允许的命令
        if allowed_commands:
            for pattern in allowed_commands:
                if re.match(pattern, command):
                    return True
            return False  # 如果有允许列表但不匹配，则禁止
        
        return True  # 没有限制或通过检查
    
    def _build_ssh_command(self, server: ServerConfig, command: Optional[str] = None) -> List[str]:
        """构建SSH命令"""
        ssh_cmd = ['ssh']
        
        # SSH选项
        ssh_options = self.global_settings.get('ssh_options', {})
        for key, value in ssh_options.items():
            ssh_cmd.extend(['-o', f'{key}={value}'])
        
        # 连接超时
        timeout = self.global_settings.get('connection_timeout', 30)
        ssh_cmd.extend(['-o', f'ConnectTimeout={timeout}'])
        
        # 私钥
        key_path = self._expand_path(server.private_key_path)
        if os.path.exists(key_path):
            ssh_cmd.extend(['-i', key_path])
        
        # 端口
        if server.port != 22:
            ssh_cmd.extend(['-p', str(server.port)])
        
        # 跳板机
        if server.type == 'jump_ssh' and server.jump_host:
            jump_host_info = server.jump_host
            jump_key_path = self._expand_path(jump_host_info.get('private_key_path', server.private_key_path))
            
            proxy_command = f"ssh -i {jump_key_path} -o StrictHostKeyChecking=no "
            proxy_command += f"-o UserKnownHostsFile=/dev/null "
            proxy_command += f"{jump_host_info['username']}@{jump_host_info['host']} "
            proxy_command += f"-p {jump_host_info.get('port', 22)} nc %h %p"
            
            ssh_cmd.extend(['-o', f'ProxyCommand={proxy_command}'])
        
        # 目标主机
        ssh_cmd.append(f"{server.username}@{server.host}")
        
        # 要执行的命令
        if command:
            ssh_cmd.append(command)
        
        return ssh_cmd
    
    def execute_command(self, server_name: str, command: str) -> Tuple[bool, str]:
        """在远程服务器执行命令"""
        server = self.servers.get(server_name)
        if not server:
            return False, f"服务器 {server_name} 不存在"
        
        # 验证命令安全性
        if not self._validate_command(command):
            return False, f"命令被安全策略禁止: {command}"
        
        # 根据服务器类型选择执行方式
        if server.type == 'script_based':
            return self._execute_script_based_command(server, command)
        else:
            return self._execute_ssh_command(server, command)
    
    def _execute_ssh_command(self, server: ServerConfig, command: str) -> Tuple[bool, str]:
        """执行SSH命令（原有逻辑）"""
        try:
            ssh_cmd = self._build_ssh_command(server, command)
            
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=self.global_settings.get('command_timeout', 300)
            )
            
            output = ""
            if result.stdout:
                output += f"📤 输出:\n{result.stdout}\n"
            if result.stderr:
                output += f"⚠️ 错误输出:\n{result.stderr}\n"
            
            output += f"🔢 退出码: {result.returncode}"
            
            # 更新连接状态
            self.connections[server.name].connected = result.returncode == 0
            self.connections[server.name].last_check = time.time()
            
            return result.returncode == 0, output
            
        except subprocess.TimeoutExpired:
            return False, f"⏱️ 命令执行超时"
        except Exception as e:
            return False, f"❌ 命令执行失败: {str(e)}"
    
    def _execute_script_based_command(self, server: ServerConfig, command: str) -> Tuple[bool, str]:
        """执行script_based类型服务器的命令 - 增强版本带连接验证"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        
        try:
            # 步骤1: 检查tmux会话是否存在
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            
            if check_result.returncode != 0:
                print(f"🔗 会话不存在，正在建立连接...")
                # 会话不存在，需要先建立连接
                success, msg = self._establish_script_based_connection(server)
                if not success:
                    return False, f"❌ 建立连接失败: {msg}"
            
            # 步骤2: 验证会话连接状态
            print(f"🔍 验证会话连接状态...")
            connected, status_msg = self._verify_session_connectivity(session_name)
            if not connected:
                print(f"⚠️ 会话连接异常: {status_msg}")
                print(f"🔄 重新建立连接...")
                
                # 清理异常会话
                subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                
                # 重新建立连接
                success, msg = self._establish_script_based_connection(server)
                if not success:
                    return False, f"❌ 重新连接失败: {msg}"
            
            # 步骤3: 执行命令前的环境检查
            print(f"📋 准备执行命令: {command}")
            
            # 发送一个简单的测试命令确认会话响应
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'echo "CMD_READY_$(date +%s)"', 'Enter'], 
                         capture_output=True)
            time.sleep(1)
            
            # 检查响应
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"❌ 会话响应异常，无法执行命令"
            
            if 'CMD_READY_' not in result.stdout:
                return False, f"❌ 会话状态不稳定，建议手动检查 tmux attach -t {session_name}"
            
            # 步骤4: 执行实际命令
            print(f"⚡ 执行命令: {command}")
            tmux_cmd = ['tmux', 'send-keys', '-t', session_name, command, 'Enter']
            result = subprocess.run(tmux_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"❌ 命令发送失败: {result.stderr}"
            
            # 步骤5: 智能等待命令完成
            max_wait = 10  # 最大等待10秒
            wait_interval = 1
            
            for i in range(max_wait):
                time.sleep(wait_interval)
                
                # 捕获会话输出
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                capture_result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                if capture_result.returncode == 0:
                    output_lines = capture_result.stdout.strip().split('\n')
                    
                    # 检查命令是否完成（通过提示符或输出模式判断）
                    recent_lines = output_lines[-3:] if len(output_lines) > 3 else output_lines
                    for line in recent_lines:
                        if any(prompt in line for prompt in ['$', '#', '>', '~']):
                            # 找到提示符，命令可能已完成
                            print(f"✅ 命令执行完成")
                            break
                else:
                    return False, f"❌ 获取输出失败: {capture_result.stderr}"
            
            # 最终获取完整输出
            final_capture = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                         capture_output=True, text=True)
            
            if final_capture.returncode == 0:
                output = f"📤 命令: {command}\n"
                output += f"🖥️  会话: {session_name}\n"
                output += f"📄 输出:\n{final_capture.stdout}"
                
                # 更新连接状态
                self.connections[server.name].connected = True
                self.connections[server.name].last_check = time.time()
                self.connections[server.name].error_message = None
                
                return True, output
            else:
                return False, f"❌ 最终输出获取失败: {final_capture.stderr}"
                
        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            self.connections[server.name].error_message = error_msg
            return False, f"❌ {error_msg}"
    
    def _establish_script_based_connection(self, server: ServerConfig) -> Tuple[bool, str]:
        """建立script_based类型的连接 - 增强版本带详细日志和状态检测"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        
        try:
            print(f"🚀 启动智能连接系统: {session_name}")
            
            # 步骤0: 智能会话管理 - 检查已存在会话
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            if check_result.returncode == 0:
                print(f"✅ 发现已存在的会话: {session_name}")
                # 检查现有会话状态
                status_ok, status_msg = self._verify_session_connectivity(session_name)
                if status_ok:
                    print(f"🚀 现有会话状态良好，直接使用")
                    return True, f"会话已存在且状态良好: {session_name}"
                else:
                    print(f"⚠️  现有会话状态异常: {status_msg}")
                    print(f"🗑️  清理并重新建立连接...")
                    subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
            
            # 检查tmux是否可用
            tmux_check = subprocess.run(['tmux', '-V'], capture_output=True)
            if tmux_check.returncode != 0:
                return False, "❌ tmux不可用 - 请安装tmux: brew install tmux"
            
            # 创建新的tmux会话
            print(f"📋 创建新环境: {session_name}")
            create_cmd = ['tmux', 'new-session', '-d', '-s', session_name]
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"❌ 创建tmux会话失败: {result.stderr} - 请检查tmux配置"
            
            # 获取配置
            connection_config = server.specs.get('connection', {}) if server.specs else {}
            docker_config = server.specs.get('docker', {}) if server.specs else {}
            bos_config = server.specs.get('bos', {}) if server.specs else {}
            env_setup = server.specs.get('environment_setup', {}) if server.specs else {}
            
            # 步骤1: 启动连接工具
            connection_tool = connection_config.get('tool', 'ssh')
            print(f"📡 步骤1: 启动连接工具 ({connection_tool})")
            
            if connection_tool != 'ssh':
                success, msg = self._start_connection_tool(session_name, connection_tool)
                if not success:
                    return False, f"❌ 连接工具启动失败: {msg}"
            
            # 步骤2: 连接到目标服务器
            target_host = connection_config.get('target', {}).get('host', server.host)
            if target_host:
                print(f"🎯 步骤2: 连接到目标服务器 ({target_host})")
                success, msg = self._connect_to_target_server(session_name, target_host, connection_config)
                if not success:
                    return False, f"❌ 目标服务器连接失败: {msg}"
            
            # 步骤3: 智能Docker环境设置
            container_name = docker_config.get('container_name')
            container_image = docker_config.get('image')
            
            if container_name:
                print(f"🐳 步骤3: 智能Docker环境设置")
                success, msg = self._smart_container_setup_enhanced(session_name, container_name, container_image, bos_config, env_setup)
                if not success:
                    print(f"⚠️ Docker容器设置失败: {msg}")
                    print("💡 建议: 检查Docker服务状态或容器配置")
            
            # 步骤4: 设置工作目录
            session_config = server.session or {}
            working_dir = session_config.get('working_directory', '/home/xuyehua')
            if working_dir:
                print(f"📁 步骤4: 设置工作目录: {working_dir}")
                success, msg = self._setup_working_directory(session_name, working_dir)
                if not success:
                    print(f"⚠️ 工作目录设置失败: {msg}")
            
            # 步骤5: 最终连接验证
            print(f"🔍 步骤5: 最终连接验证...")
            success, msg = self._verify_final_connection(session_name)
            if not success:
                return False, f"❌ 连接验证失败: {msg}"
            
            print(f"✅ 智能连接系统部署完成: {session_name}")
            
            # 更新连接状态
            self.connections[server.name].connected = True
            self.connections[server.name].last_check = time.time()
            self.connections[server.name].connection_time = time.time()
            self.connections[server.name].error_message = None
            
            return True, f"智能连接已建立，会话: {session_name}"
            
        except Exception as e:
            error_msg = f"建立连接失败: {str(e)}"
            self.connections[server.name].error_message = error_msg
            return False, error_msg

    def _verify_session_connectivity(self, session_name: str) -> Tuple[bool, str]:
        """验证现有会话的连接状态"""
        try:
            # 发送测试命令
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'echo "CONNECTION_TEST_$(date +%s)"', 'Enter'], 
                         capture_output=True)
            time.sleep(1)
            
            # 获取输出
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                # 检查是否在远程环境
                if 'MacBook-Pro' in output or 'localhost' in output:
                    return False, "会话已断开，回到本地环境"
                elif 'CONNECTION_TEST_' in output:
                    return True, "会话状态正常"
                else:
                    return False, "会话响应异常"
            else:
                return False, "无法获取会话状态"
                
        except Exception as e:
            return False, f"状态检查失败: {str(e)}"

    def _start_connection_tool(self, session_name: str, tool: str) -> Tuple[bool, str]:
        """启动连接工具并等待就绪"""
        try:
            print(f"   🔧 启动 {tool}...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, tool, 'Enter'], 
                         capture_output=True)
            
            # 智能等待工具启动
            max_wait = 15  # 最大等待15秒
            wait_interval = 1
            
            for i in range(max_wait):
                time.sleep(wait_interval)
                print(f"   ⏳ 等待工具启动... ({i+1}/{max_wait})")
                
                # 检查工具是否准备就绪
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout.lower()
                    # 检查各种就绪信号
                    if any(signal in output for signal in ['password:', 'fingerprint', '(yes/no)', 'ready', 'connected']):
                        print(f"   ✅ {tool} 已启动，等待用户认证...")
                        time.sleep(3)  # 给用户时间完成认证
                        return True, f"{tool} 启动成功"
                    elif 'error' in output or 'failed' in output:
                        return False, f"{tool} 启动失败: {output[-100:]}"
            
            return False, f"{tool} 启动超时，请手动检查"
            
        except Exception as e:
            return False, f"启动工具失败: {str(e)}"

    def _connect_to_target_server(self, session_name: str, target_host: str, connection_config: dict = None) -> Tuple[bool, str]:
        """连接到目标服务器并验证连接 - 支持跳板机模式和relay模式"""
        try:
            # 检查是否需要跳板机连接
            if connection_config and connection_config.get('mode') == 'jump_host':
                return self._connect_via_jump_host(session_name, target_host, connection_config)
            
            # 检查是否是relay-cli模式（TJ服务器）
            connection_tool = connection_config.get('tool', 'ssh') if connection_config else 'ssh'
            
            if connection_tool == 'relay-cli':
                return self._connect_via_relay(session_name, target_host, connection_config)
            
            # 传统SSH直连模式
            print(f"   🌐 发起SSH连接到 {target_host}...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh {target_host}', 'Enter'],
                         capture_output=True)
            
            return self._verify_ssh_connection(session_name, target_host)
            
        except Exception as e:
            return False, f"连接过程失败: {str(e)}"
    
    def _connect_via_relay(self, session_name: str, target_host: str, connection_config: dict) -> Tuple[bool, str]:
        """通过relay-cli连接到目标服务器 - 基于cursor-bridge TJ脚本逻辑"""
        try:
            print(f"   🚀 步骤1: 等待relay-cli就绪...")
            
            # 等待relay登录成功信号
            max_wait_relay = 20
            for i in range(max_wait_relay):
                time.sleep(1)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    # 检查relay登录成功信号 - 多种检测方式
                    if ('Login Giano succeeded by BEEP' in output or 'succeeded by BEEP' in output or
                        ('Last login:' in output and '-bash-baidu-ssl$' in output) or
                        ('-bash-baidu-ssl$' in output and 'Last login:' in output)):
                        print(f"   ✅ Relay登录成功！")
                        break
                    elif 'Login Giano failed by BEEP' in output:
                        return False, "Relay登录失败，请检查认证"
                    elif 'Please input' in output or 'password' in output.lower():
                        if i < 5:
                            print(f"   🔐 Relay需要用户认证，请在另一终端执行:")
                            print(f"       tmux attach -t {session_name}")
                            print(f"       然后完成密码/指纹认证")
                        else:
                            print(f"   ⏳ 等待用户认证完成... ({i}/{max_wait_relay})")
            else:
                return False, "等待relay登录超时"
            
            # 步骤2: 在relay中SSH到目标服务器
            print(f"   🎯 步骤2: 在relay中连接到 {target_host}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh {target_host}', 'Enter'],
                         capture_output=True)
            
            # 等待目标服务器连接
            return self._verify_target_server_connection(session_name, target_host)
            
        except Exception as e:
            return False, f"Relay连接失败: {str(e)}"
    
    def _verify_target_server_connection(self, session_name: str, target_host: str) -> Tuple[bool, str]:
        """验证通过relay连接到目标服务器"""
        try:
            max_wait = 30
            wait_interval = 2
            
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                print(f"   ⏳ 等待目标服务器连接... ({i+wait_interval}/{max_wait}秒)")
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    lines = output.strip().split('\n')
                    recent_lines = lines[-5:] if len(lines) > 5 else lines
                    
                    # 检查目标服务器连接成功信号
                    for line in recent_lines:
                        line_lower = line.lower()
                        target_host_name = target_host.split('.')[0].lower()
                        
                        # 检查是否已连接到目标服务器（而不是relay）
                        # 必须包含目标主机名或明确的目标服务器指示符
                        if (target_host_name in line_lower and '@' in line) or \
                           (target_host_name in line_lower and ('welcome' in line_lower or 'last login' in line_lower)) or \
                           ('root@' + target_host_name in line_lower):
                            print(f"   ✅ 已成功连接到目标服务器 {target_host}")
                            time.sleep(2)  # 稳定连接
                            return True, f"成功连接到 {target_host}"
                    
                    # 检查连接错误
                    for line in recent_lines:
                        line_lower = line.lower()
                        if any(error_signal in line_lower for error_signal in [
                            'connection refused', 'timeout', 'permission denied', 'host unreachable',
                            'no route to host', 'network unreachable'
                        ]):
                            return False, f"目标服务器连接失败: {line.strip()}"
            
            # 最终验证 - 使用完整路径的命令
            print(f"   🔍 连接超时，执行最终验证...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, '/bin/echo "VERIFY_$(/bin/hostname)"', 'Enter'], 
                         capture_output=True)
            time.sleep(3)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if (result.returncode == 0 and 
                ('VERIFY_' in result.stdout and target_host.split('.')[0] in result.stdout)):
                print(f"   ✅ 最终验证成功，已连接到 {target_host}")
                return True, f"连接验证成功: {target_host}"
            
            return False, f"连接验证失败，可能仍在relay环境中"
            
        except Exception as e:
            return False, f"目标服务器验证失败: {str(e)}"
    
    def _verify_ssh_connection(self, session_name: str, target_host: str) -> Tuple[bool, str]:
        """验证传统SSH连接"""
        try:
            max_wait = 30
            wait_interval = 2
            
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                print(f"   ⏳ 等待服务器连接... ({i+wait_interval}/{max_wait}秒)")
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    lines = output.strip().split('\n')
                    recent_lines = lines[-3:] if len(lines) > 3 else lines
                    
                    # 检查连接成功的信号
                    for line in recent_lines:
                        line_lower = line.lower()
                        if any(success_signal in line_lower for success_signal in [
                            target_host.lower(), 'welcome', 'login', '@', '$', '#'
                        ]):
                            if target_host.lower() in line_lower or '@' in line:
                                print(f"   ✅ 已成功连接到 {target_host}")
                                time.sleep(2)
                                return True, f"成功连接到 {target_host}"
                    
                    # 检查错误信号
                    for line in recent_lines:
                        line_lower = line.lower()
                        if any(error_signal in line_lower for error_signal in [
                            'connection refused', 'timeout', 'permission denied', 'host unreachable'
                        ]):
                            return False, f"连接失败: {line.strip()}"
            
            # 最终验证
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'hostname', 'Enter'], 
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and target_host.split('.')[0] in result.stdout:
                print(f"   ✅ 最终验证成功，已连接到 {target_host}")
                return True, f"连接验证成功: {target_host}"
            
            return False, f"连接超时，无法确认连接状态"
            
        except Exception as e:
            return False, f"SSH连接验证失败: {str(e)}"
    
    def _connect_via_jump_host(self, session_name: str, target_host: str, connection_config: dict) -> Tuple[bool, str]:
        """通过跳板机连接到目标服务器 - 基于cursor-bridge脚本逻辑"""
        try:
            jump_host_config = connection_config.get('jump_host', {})
            jump_host = jump_host_config.get('host', '')
            jump_password = jump_host_config.get('password', '')
            
            if not jump_host:
                return False, "跳板机配置缺失"
            
            print(f"   🚀 步骤1: 连接跳板机 {jump_host}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh {jump_host}', 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 处理指纹认证（如果需要）
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            if 'fingerprint' in result.stdout.lower() or 'yes/no' in result.stdout.lower():
                print("   🔑 接受指纹...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'yes', 'Enter'],
                             capture_output=True)
                time.sleep(2)
            
            # 输入跳板机密码
            if jump_password:
                print("   🔐 输入跳板机密码...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, jump_password, 'Enter'],
                             capture_output=True)
                time.sleep(4)
            
            # 验证跳板机连接
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            if '$' not in result.stdout and '#' not in result.stdout:
                return False, "跳板机连接失败，请检查密码"
            
            print(f"   ✅ 跳板机连接成功")
            
            # 从跳板机连接到目标服务器
            print(f"   🎯 步骤2: 从跳板机连接到 {target_host}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh root@{target_host}', 'Enter'],
                         capture_output=True)
            time.sleep(4)
            
            # 验证目标服务器连接
            for i in range(10):  # 最多等待20秒
                time.sleep(2)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if 'root@' in result.stdout:
                    print(f"   ✅ 已成功连接到目标服务器: {target_host}")
                    return True, f"通过跳板机成功连接到 {target_host}"
                    
                if 'denied' in result.stdout.lower() or 'failed' in result.stdout.lower():
                    return False, f"目标服务器连接被拒绝: {target_host}"
            
            return False, f"连接目标服务器超时: {target_host}"
            
        except Exception as e:
            return False, f"跳板机连接失败: {str(e)}"

    def _setup_working_directory(self, session_name: str, working_dir: str) -> Tuple[bool, str]:
        """设置工作目录"""
        try:
            print(f"   📂 创建工作目录: {working_dir}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'mkdir -p {working_dir}', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            print(f"   📂 切换到工作目录: {working_dir}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'cd {working_dir}', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 验证目录切换
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'pwd', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and working_dir in result.stdout:
                print(f"   ✅ 工作目录设置成功: {working_dir}")
                return True, f"工作目录已设置: {working_dir}"
            else:
                return False, f"工作目录验证失败，当前位置未知"
                
        except Exception as e:
            return False, f"设置工作目录失败: {str(e)}"

    def _verify_final_connection(self, session_name: str) -> Tuple[bool, str]:
        """最终连接验证"""
        try:
            print(f"   🔍 执行最终连接验证...")
            
            # 发送多个验证命令
            verification_commands = [
                ('hostname', '主机名检查'),
                ('whoami', '用户身份检查'),
                ('pwd', '当前目录检查')
            ]
            
            verification_results = []
            
            for cmd, desc in verification_commands:
                print(f"   🔎 {desc}...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, cmd, 'Enter'],
                             capture_output=True)
                time.sleep(1)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output_lines = result.stdout.strip().split('\n')
                    # 查找命令输出
                    for line in output_lines[-5:]:  # 检查最后5行
                        if line.strip() and not line.startswith(cmd) and cmd not in line:
                            verification_results.append(f"{desc}: {line.strip()}")
                            print(f"     ✅ {line.strip()}")
                            break
            
            if len(verification_results) >= 2:  # 至少2个验证通过
                return True, f"连接验证成功 - {'; '.join(verification_results)}"
            else:
                return False, f"连接验证不足，请手动检查会话状态"
                
        except Exception as e:
            return False, f"最终验证失败: {str(e)}"
    
    def _smart_container_setup(self, session_name: str, container_name: str, 
                              container_image: str, bos_config: dict, env_setup: dict) -> bool:
        """智能容器检查和处理 - 基于原始脚本逻辑"""
        try:
            print(f"🔍 智能检查Docker环境...")
            
            # 步骤1: 精确检查容器是否存在
            print(f"🔍 步骤1: 精确检查容器是否存在: {container_name}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo '=== CONTAINER_EXIST_CHECK_START ==='", 'Enter'], capture_output=True)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect {container_name} >/dev/null 2>&1 && echo 'CONTAINER_EXISTS_YES' || echo 'CONTAINER_EXISTS_NO'", 
                          'Enter'], capture_output=True)
            time.sleep(3)
            
            # 获取检查结果
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo '=== CAPTURE_POINT ==='", 'Enter'], capture_output=True)
            time.sleep(1)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            # 分析容器存在性
            if 'CONTAINER_EXISTS_YES' in result.stdout:
                print("✅ 容器已存在，进入快速连接模式...")
                return self._handle_existing_container(session_name, container_name)
            elif 'CONTAINER_EXISTS_NO' in result.stdout:
                print("🚀 容器不存在，进入创建模式...")
                return self._handle_new_container(session_name, container_name, container_image, bos_config, env_setup)
            else:
                print("❌ 容器存在性检查结果异常")
                return False
                
        except Exception as e:
            print(f"❌ 智能容器设置失败: {str(e)}")
            return False

    def _smart_container_setup_enhanced(self, session_name: str, container_name: str, 
                                      container_image: str, bos_config: dict, env_setup: dict) -> Tuple[bool, str]:
        """增强版智能容器设置，带详细日志和错误处理"""
        try:
            print(f"   🔍 检查Docker环境...")
            
            # 步骤1: 验证Docker可用性
            print(f"   🐳 验证Docker服务...")
            success, msg = self._verify_docker_availability(session_name)
            if not success:
                return False, f"Docker不可用: {msg}"
            
            # 步骤2: 检查容器是否存在
            print(f"   🔍 检查容器: {container_name}")
            exists, msg = self._check_container_exists(session_name, container_name)
            if exists is None:
                return False, f"容器检查失败: {msg}"
            
            if exists:
                print(f"   ✅ 容器已存在，进入连接模式...")
                success, msg = self._handle_existing_container_enhanced(session_name, container_name)
                return success, msg
            else:
                print(f"   🚀 容器不存在，进入创建模式...")
                success, msg = self._handle_new_container_enhanced(session_name, container_name, container_image, bos_config, env_setup)
                return success, msg
                
        except Exception as e:
            error_msg = f"容器设置失败: {str(e)}"
            return False, error_msg

    def _verify_docker_availability(self, session_name: str) -> Tuple[bool, str]:
        """验证Docker服务可用性"""
        try:
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'docker --version', 'Enter'], 
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout.lower()
                if 'docker version' in output:
                    return True, "Docker服务正常"
                elif 'command not found' in output:
                    return False, "Docker未安装"
                elif 'permission denied' in output:
                    return False, "Docker权限不足，建议: sudo usermod -aG docker $USER"
                elif 'cannot connect' in output:
                    return False, "Docker服务未启动，建议: sudo systemctl start docker"
                else:
                    return False, f"Docker状态异常: {output[-100:]}"
            else:
                return False, "无法检查Docker状态"
                
        except Exception as e:
            return False, f"Docker检查失败: {str(e)}"

    def _check_container_exists(self, session_name: str, container_name: str) -> Tuple[Optional[bool], str]:
        """检查容器是否存在"""
        try:
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'echo "CONTAINER_CHECK_START_{container_name}"', 'Enter'], 
                         capture_output=True)
            time.sleep(1)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect {container_name} >/dev/null 2>&1 && echo 'EXISTS_YES' || echo 'EXISTS_NO'", 
                          'Enter'], capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                if 'EXISTS_YES' in output:
                    return True, "容器存在"
                elif 'EXISTS_NO' in output:
                    return False, "容器不存在"
                else:
                    return None, f"检查结果不明确: {output[-100:]}"
            else:
                return None, "无法获取检查结果"
                
        except Exception as e:
            return None, f"容器检查异常: {str(e)}"
    
    def _handle_existing_container_enhanced(self, session_name: str, container_name: str) -> Tuple[bool, str]:
        """增强版现有容器处理"""
        try:
            # 检查容器运行状态
            print(f"   🔍 检查容器运行状态...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'echo "STATUS_CHECK_{container_name}"', 'Enter'], capture_output=True)
            time.sleep(1)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect --format='{{{{.State.Running}}}}' {container_name}", 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            is_running = 'true' in result.stdout
            
            if not is_running:
                print(f"   ⚠️ 容器已停止，正在启动...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker start {container_name}", 'Enter'], capture_output=True)
                
                # 等待容器启动
                max_wait = 10
                for i in range(max_wait):
                    time.sleep(1)
                    print(f"   ⏳ 等待容器启动... ({i+1}/{max_wait})")
                    
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"docker inspect --format='{{{{.State.Running}}}}' {container_name}", 'Enter'],
                                 capture_output=True)
                    time.sleep(1)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if 'true' in result.stdout:
                        print(f"   ✅ 容器启动成功")
                        break
                else:
                    return False, "容器启动超时"
            else:
                print(f"   ✅ 容器正在运行")
            
            # 进入容器
            print(f"   🚪 进入容器...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker exec -it {container_name} zsh", 'Enter'], capture_output=True)
            time.sleep(3)
            
            # 验证是否成功进入
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            output = result.stdout
            if '@' in output or '#' in output:
                print(f"   ✅ 成功进入容器")
                return True, f"成功连接到现有容器: {container_name}"
            else:
                # 尝试bash
                print(f"   🔄 尝试使用bash...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'C-c'], capture_output=True)
                time.sleep(1)
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
                time.sleep(2)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if '@' in result.stdout or '#' in result.stdout:
                    print(f"   ✅ 使用bash成功进入容器")
                    return True, f"使用bash连接到容器: {container_name}"
                else:
                    return False, "无法进入容器，请手动检查"
                
        except Exception as e:
            return False, f"处理现有容器失败: {str(e)}"

    def _handle_new_container_enhanced(self, session_name: str, container_name: str, 
                                     container_image: str, bos_config: dict, env_setup: dict) -> Tuple[bool, str]:
        """增强版新容器创建"""
        try:
            print(f"   🚀 创建新容器: {container_name}")
            
            # 构建docker run命令
            docker_cmd = self._build_docker_run_command(container_name, container_image)
            print(f"   🔧 Docker命令: {docker_cmd[:100]}...")
            
            # 执行创建命令
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'echo "CREATE_START_{container_name}"', 'Enter'], capture_output=True)
            time.sleep(1)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, docker_cmd, 'Enter'],
                         capture_output=True)
            
            # 等待容器创建
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                print(f"   ⏳ 等待容器创建... ({i+1}/{max_wait})")
                
                # 检查容器是否创建成功
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker inspect {container_name} >/dev/null 2>&1 && echo 'CREATE_SUCCESS' || echo 'CREATE_FAILED'", 
                              'Enter'], capture_output=True)
                time.sleep(2)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if 'CREATE_SUCCESS' in result.stdout:
                    print(f"   ✅ 容器创建成功")
                    break
                elif 'CREATE_FAILED' in result.stdout:
                    return False, "容器创建失败，请检查镜像和配置"
            else:
                return False, "容器创建超时"
            
            # 进入新创建的容器
            print(f"   🚪 进入新容器...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker exec -it {container_name} zsh", 'Enter'], capture_output=True)
            time.sleep(3)
            
            # 验证进入结果
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if '@' in result.stdout or '#' in result.stdout:
                print(f"   ✅ 成功进入新容器")
                return True, f"成功创建并连接到容器: {container_name}"
            else:
                return False, "容器创建成功但无法进入"
                
        except Exception as e:
            return False, f"创建新容器失败: {str(e)}"

    def _build_docker_run_command(self, container_name: str, container_image: str, docker_config: dict = None) -> str:
        """构建Docker run命令 - 支持配置文件自定义参数"""
        # 使用配置文件中的run_options，如果没有则使用默认值
        if docker_config and docker_config.get('run_options'):
            run_options = docker_config['run_options']
            return f"docker run --name={container_name} {run_options} {container_image}"
        
        # 默认参数（与cursor-bridge脚本保持一致）
        return (
            f"docker run --privileged --name={container_name} --ulimit core=-1 "
            f"--security-opt seccomp=unconfined -dti --net=host --uts=host --ipc=host "
            f"--security-opt=seccomp=unconfined -v /home:/home -v /data1:/data1 "
            f"-v /data2:/data2 -v /data3:/data3 -v /data4:/data4 --shm-size=256g "
            f"--restart=always {container_image}"
        )

    def _handle_existing_container(self, session_name: str, container_name: str) -> bool:
        """处理已存在容器的逻辑"""
        try:
            print(f"🔍 步骤2: 检查容器运行状态...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo '=== CONTAINER_STATUS_CHECK_START ==='", 'Enter'], capture_output=True)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect --format='{{{{.State.Running}}}}' {container_name}", 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'true' in result.stdout:
                print("✅ 容器正在运行")
            else:
                print("⚠️ 容器已停止，正在启动...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker start {container_name}", 'Enter'], capture_output=True)
                time.sleep(5)
                print("✅ 容器启动成功")
            
            # 进入容器
            print(f"🚪 步骤3: 进入现有容器...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker exec -it {container_name} zsh", 'Enter'], capture_output=True)
            time.sleep(2)
            
            # 检查是否成功进入zsh，否则尝试bash
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            if '@' not in result.stdout or '#' not in result.stdout:
                print("⚠️ 尝试启动zsh...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                             capture_output=True)
                time.sleep(2)
            
            print("✅ 快速连接完成！")
            return True
            
        except Exception as e:
            print(f"❌ 处理已存在容器失败: {str(e)}")
            return False
    
    def _handle_new_container(self, session_name: str, container_name: str, 
                            container_image: str, bos_config: dict, env_setup: dict) -> bool:
        """处理新容器创建的逻辑"""
        try:
            print(f"步骤1: 创建Docker容器 {container_name}")
            
            # 构建docker run命令
            docker_run_cmd = (
                f"docker run --privileged --name={container_name} --ulimit core=-1 "
                f"--security-opt seccomp=unconfined -dti --net=host --uts=host --ipc=host "
                f"--security-opt=seccomp=unconfined -v /home:/home -v /data1:/data1 "
                f"-v /data2:/data2 -v /data3:/data3 -v /data4:/data4 --shm-size=256g "
                f"--restart=always {container_image}"
            )
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo '=== CONTAINER_CREATE_START ==='", 'Enter'], capture_output=True)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, docker_run_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(10)
            
            # 验证容器创建
            print("步骤2: 验证容器创建结果")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect {container_name} >/dev/null 2>&1 && echo 'CREATE_SUCCESS' || echo 'CREATE_FAILED'", 
                          'Enter'], capture_output=True)
            time.sleep(3)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'CREATE_SUCCESS' not in result.stdout:
                print("❌ 容器创建失败")
                return False
            
            print("✅ 容器创建成功")
            
            # 进入新创建的容器
            print("🚪 步骤3: 进入新创建的容器...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
            time.sleep(3)
            
            # 如果启用自动环境配置，执行完整配置
            if env_setup.get('auto_setup', False):
                self._setup_full_environment(session_name, bos_config)
            else:
                print("💡 容器已创建，如需配置环境请手动执行相关命令")
            
            return True
            
        except Exception as e:
            print(f"❌ 处理新容器失败: {str(e)}")
            return False
    
    def _setup_full_environment(self, session_name: str, bos_config: dict) -> bool:
        """完整环境配置函数"""
        try:
            print("🛠️ 开始完整环境配置...")
            
            # 检查BOS工具
            print("步骤1: 检查BOS工具")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'which bcecmd', 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if '/bcecmd' in result.stdout:
                print("✅ BOS工具可用")
                self._configure_bos(session_name, bos_config)
            else:
                print("⚠️ BOS工具不可用，使用本地备用配置")
                self._setup_local_config(session_name)
            
            # 创建工作目录
            print("步骤5: 创建工作目录")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'mkdir -p /home/xuyehua', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 生成SSH密钥
            print("步骤6: 生成SSH密钥")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ''", 'Enter'], capture_output=True)
            time.sleep(3)
            
            # 启动zsh环境
            print("步骤7: 启动zsh环境")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 显示SSH公钥
            print("步骤8: 显示SSH公钥")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo '=== SSH_KEY_DISPLAY_START ===' && cat /root/.ssh/id_rsa.pub", 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            # 提取SSH公钥
            lines = result.stdout.split('\n')
            ssh_key = None
            for line in lines:
                if line.startswith('ssh-rsa') or line.startswith('ssh-ed25519'):
                    ssh_key = line.strip()
                    break
            
            if ssh_key:
                print("✅ SSH公钥已生成:")
                print("━" * 80)
                print(ssh_key)
                print("━" * 80)
                print("💡 请复制上述公钥内容到目标服务器的authorized_keys文件")
            else:
                print("⚠️ SSH公钥获取失败，请手动执行: cat /root/.ssh/id_rsa.pub")
            
            print("✅ 完整环境配置完成！")
            return True
            
        except Exception as e:
            print(f"❌ 环境配置失败: {str(e)}")
            return False
    
    def _configure_bos(self, session_name: str, bos_config: dict) -> bool:
        """配置BOS工具"""
        try:
            print("步骤2: 配置BOS工具")
            
            access_key = bos_config.get('access_key', '')
            secret_key = bos_config.get('secret_key', '')
            bucket = bos_config.get('bucket', '')
            
            if not access_key or secret_key == 'your_secret_key':
                print("⚠️ BOS配置不完整，跳过BOS设置")
                return False
            
            # 启动bcecmd配置
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'bcecmd -c', 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 输入Access Key
            subprocess.run(['tmux', 'send-keys', '-t', session_name, access_key, 'Enter'],
                         capture_output=True)
            time.sleep(0.1)
            
            # 输入Secret Key
            subprocess.run(['tmux', 'send-keys', '-t', session_name, secret_key, 'Enter'],
                         capture_output=True)
            time.sleep(0.1)
            
            # 使用默认配置（连续回车）
            for i in range(11):
                subprocess.run(['tmux', 'send-keys', '-t', session_name, '', 'Enter'],
                             capture_output=True)
                time.sleep(0.1)
            
            time.sleep(5)
            
            # 测试BOS连接
            if bucket:
                print("步骤3: 测试BOS连接并下载配置文件")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"bcecmd bos cp -y {bucket}/.p10k.zsh /root", 'Enter'],
                             capture_output=True)
                time.sleep(5)
                
                # 检查下载是否成功
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              "if [ -f /root/.p10k.zsh ]; then echo 'BOS_DOWNLOAD_SUCCESS'; else echo 'BOS_DOWNLOAD_FAILED'; fi", 
                              'Enter'], capture_output=True)
                time.sleep(2)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if 'BOS_DOWNLOAD_SUCCESS' in result.stdout:
                    print("✅ BOS配置和连接成功！")
                    
                    # 下载其他配置文件
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"bcecmd bos cp -y {bucket}/.zshrc /root", 'Enter'],
                                 capture_output=True)
                    time.sleep(5)
                    
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"bcecmd bos cp -y {bucket}/.zsh_history /root", 'Enter'],
                                 capture_output=True)
                    time.sleep(5)
                    
                    print("✅ 配置文件下载完成，p10k主题将在zsh启动时自动加载")
                    return True
                else:
                    print("❌ BOS连接或下载失败！")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ BOS配置失败: {str(e)}")
            return False
    
    def _setup_local_config(self, session_name: str) -> bool:
        """本地配置备用方案"""
        try:
            print("🔧 设置本地备用配置...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo 'export TERM=xterm-256color' >> ~/.bashrc", 'Enter'],
                         capture_output=True)
            time.sleep(1)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.bashrc', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            print("✅ 本地配置完成")
            return True
        except Exception as e:
            print(f"❌ 本地配置失败: {str(e)}")
            return False
    
    def test_connection(self, server_name: str) -> Tuple[bool, str]:
        """测试服务器连接"""
        server = self.servers.get(server_name)
        if not server:
            return False, f"服务器 {server_name} 不存在"
        
        # 根据服务器类型选择测试方式
        if server.type == 'script_based':
            return self._test_script_based_connection(server)
        else:
            return self._test_ssh_connection(server)
    
    def _test_ssh_connection(self, server: ServerConfig) -> Tuple[bool, str]:
        """测试SSH连接（原有逻辑）"""
        try:
            # 使用简单的echo命令测试连接
            ssh_cmd = self._build_ssh_command(server, 'echo "connection_test"')
            
            start_time = time.time()
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=self.global_settings.get('connection_timeout', 30)
            )
            
            connection_time = time.time() - start_time
            
            # 更新连接状态
            status = self.connections[server.name]
            status.last_check = time.time()
            status.connection_time = connection_time
            
            if result.returncode == 0 and 'connection_test' in result.stdout:
                status.connected = True
                status.error_message = None
                return True, f"连接成功 ({connection_time:.2f}秒)"
            else:
                status.connected = False
                error_msg = result.stderr.strip() or "连接失败"
                status.error_message = error_msg
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            self.connections[server.name].connected = False
            self.connections[server.name].error_message = "连接超时"
            return False, "连接超时"
        except Exception as e:
            self.connections[server.name].connected = False
            self.connections[server.name].error_message = str(e)
            return False, f"连接错误: {e}"
    
    def _test_script_based_connection(self, server: ServerConfig) -> Tuple[bool, str]:
        """测试script_based连接"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        
        try:
            start_time = time.time()
            
            # 检查tmux会话是否存在
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            
            if check_result.returncode == 0:
                # 会话存在，检查连接状态
                print(f"🔍 检测会话状态: {session_name}")
                
                # 发送简单测试命令
                test_cmd = ['tmux', 'send-keys', '-t', session_name, 'echo "connection_test_$(date)"', 'Enter']
                subprocess.run(test_cmd, capture_output=True)
                time.sleep(1)
                
                # 获取输出
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                capture_result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                connection_time = time.time() - start_time
                
                # 检查是否在远程环境
                output = capture_result.stdout
                if 'MacBook-Pro-3.local' in output or 'xuyehua@MacBook' in output:
                    # 会话已断开，回到本地
                    print("⚠️ 远程会话已断开，重新建立连接...")
                    
                    # 清理旧会话
                    subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                    
                    # 重新建立连接
                    success, msg = self._establish_script_based_connection(server)
                    if success:
                        return True, f"重新连接成功 ({connection_time:.2f}秒) - {msg}"
                    else:
                        return False, f"重新连接失败: {msg}"
                
                elif 'connection_test_' in output:
                    # 更新连接状态
                    status = self.connections[server.name]
                    status.connected = True
                    status.last_check = time.time()
                    status.connection_time = connection_time
                    status.error_message = None
                    
                    # 发送保活信号
                    self._send_keepalive(session_name)
                    
                    return True, f"连接正常 ({connection_time:.2f}秒) - 会话: {session_name}"
                else:
                    return False, "会话无响应"
            else:
                # 会话不存在，尝试建立连接
                success, msg = self._establish_script_based_connection(server)
                connection_time = time.time() - start_time
                
                if success:
                    return True, f"连接已建立 ({connection_time:.2f}秒) - {msg}"
                else:
                    return False, f"建立连接失败: {msg}"
                    
        except Exception as e:
            self.connections[server.name].connected = False
            self.connections[server.name].error_message = str(e)
            return False, f"测试连接失败: {str(e)}"
    
    def _send_keepalive(self, session_name: str):
        """发送保活信号到远程会话"""
        try:
            # 发送简单的保活命令（不显示输出）
            subprocess.run(['tmux', 'send-keys', '-t', session_name, '# keepalive', 'Enter'],
                         capture_output=True)
        except Exception:
            pass  # 保活失败不影响主要功能
    
    def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """获取服务器状态"""
        server = self.servers.get(server_name)
        if not server:
            return {'error': f"服务器 {server_name} 不存在"}
        
        # 执行状态检查命令
        status_commands = [
            ('hostname', 'hostname'),
            ('uptime', 'uptime'),
            ('disk_usage', 'df -h | head -5'),
            ('memory', 'free -h'),
            ('load', 'cat /proc/loadavg'),
        ]
        
        if server.specs and server.specs.get('gpu_count', 0) > 0:
            status_commands.append(('gpu_status', 'nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader'))
        
        # 获取连接状态
        connection_status = self.connections.get(server_name)
        if not connection_status:
            connection_status = ConnectionStatus(server_name, False, 0, "未初始化")
        
        server_status = {
            'name': server_name,
            'host': server.host,
            'description': server.description,
            'specs': server.specs or {},
            'connected': connection_status.connected,
            'last_check': connection_status.last_check,
            'info': {}
        }
        
        # 如果连接正常，获取详细状态
        if connection_status.connected:
            for info_name, cmd in status_commands:
                success, output = self.execute_command(server_name, cmd)
                if success:
                    # 提取输出内容（去掉输出格式标记）
                    lines = output.split('\n')
                    content = []
                    for line in lines:
                        if line.startswith('📤 输出:'):
                            continue
                        if line.startswith('🔢 退出码:'):
                            break
                        content.append(line)
                    server_status['info'][info_name] = '\n'.join(content).strip()
        
        return server_status
    
    def get_default_server(self) -> Optional[str]:
        """获取默认服务器"""
        return self.global_settings.get('default_server')
    
    def refresh_all_connections(self) -> Dict[str, bool]:
        """刷新所有服务器连接状态"""
        results = {}
        for server_name in self.servers.keys():
            success, message = self.test_connection(server_name)
            results[server_name] = success
        return results 

    def get_connection_diagnostics(self, server_name: str) -> Dict[str, Any]:
        """获取连接诊断信息和修复建议"""
        server = self.get_server(server_name)
        if not server:
            return {"error": f"服务器 {server_name} 不存在"}
        
        diagnostics = {
            "server_name": server_name,
            "server_type": server.type,
            "timestamp": time.time(),
            "status": "unknown",
            "issues": [],
            "suggestions": [],
            "connection_info": {}
        }
        
        try:
            if server.type == "script_based":
                diagnostics.update(self._diagnose_script_based_connection(server))
            else:
                diagnostics.update(self._diagnose_ssh_connection(server))
                
        except Exception as e:
            diagnostics["status"] = "error"
            diagnostics["issues"].append(f"诊断过程失败: {str(e)}")
            
        return diagnostics
    
    def _diagnose_script_based_connection(self, server: ServerConfig) -> Dict[str, Any]:
        """诊断script_based连接"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        result = {
            "status": "healthy",
            "issues": [],
            "suggestions": [],
            "connection_info": {
                "session_name": session_name,
                "connection_tool": server.specs.get('connection', {}).get('tool', 'ssh') if server.specs else 'ssh',
                "target_host": server.specs.get('connection', {}).get('target', {}).get('host', 'N/A') if server.specs else 'N/A',
                "container_name": server.specs.get('docker', {}).get('container_name', 'N/A') if server.specs else 'N/A'
            }
        }
        
        # 检查tmux可用性
        tmux_check = subprocess.run(['tmux', '-V'], capture_output=True)
        if tmux_check.returncode != 0:
            result["status"] = "error"
            result["issues"].append("tmux不可用")
            result["suggestions"].append("安装tmux: brew install tmux (macOS) 或 sudo apt install tmux (Ubuntu)")
            return result
        
        # 检查会话状态
        session_check = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True)
        if session_check.returncode != 0:
            result["issues"].append(f"会话 {session_name} 不存在")
            result["suggestions"].append(f"运行 test_connection 重新建立连接")
        else:
            # 检查会话连接性
            connected, msg = self._verify_session_connectivity(session_name)
            if not connected:
                result["status"] = "warning"
                result["issues"].append(f"会话连接异常: {msg}")
                result["suggestions"].append(f"建议重新连接: 清理会话并重新建立")
        
        # 检查连接工具
        connection_tool = result["connection_info"]["connection_tool"]
        if connection_tool != 'ssh':
            tool_check = subprocess.run(['which', connection_tool], capture_output=True)
            if tool_check.returncode != 0:
                result["status"] = "error"
                result["issues"].append(f"连接工具 {connection_tool} 不可用")
                result["suggestions"].append(f"安装 {connection_tool} 或检查PATH环境变量")
        
        return result
    
    def _diagnose_ssh_connection(self, server: ServerConfig) -> Dict[str, Any]:
        """诊断SSH连接"""
        result = {
            "status": "healthy",
            "issues": [],
            "suggestions": [],
            "connection_info": {
                "host": server.host,
                "port": server.port,
                "username": server.username,
                "private_key": server.private_key_path
            }
        }
        
        # 检查SSH可用性
        ssh_check = subprocess.run(['which', 'ssh'], capture_output=True)
        if ssh_check.returncode != 0:
            result["status"] = "error"
            result["issues"].append("ssh命令不可用")
            result["suggestions"].append("安装OpenSSH客户端")
            return result
        
        # 检查私钥文件
        if server.private_key_path:
            key_path = Path(server.private_key_path).expanduser()
            if not key_path.exists():
                result["status"] = "error"
                result["issues"].append(f"私钥文件不存在: {key_path}")
                result["suggestions"].append(f"检查私钥路径或生成新的SSH密钥")
        
        return result

    def print_connection_diagnostics(self, server_name: str):
        """打印连接诊断报告"""
        diagnostics = self.get_connection_diagnostics(server_name)
        
        print(f"\n🔍 连接诊断报告: {server_name}")
        print("=" * 60)
        
        # 基本信息
        print(f"📋 服务器类型: {diagnostics.get('server_type', 'N/A')}")
        print(f"⏰ 检查时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(diagnostics.get('timestamp', time.time())))}")
        
        # 状态
        status = diagnostics.get('status', 'unknown')
        status_emoji = {"healthy": "✅", "warning": "⚠️", "error": "❌", "unknown": "❓"}
        print(f"🔋 连接状态: {status_emoji.get(status, '❓')} {status.upper()}")
        
        # 连接信息
        conn_info = diagnostics.get('connection_info', {})
        if conn_info:
            print(f"\n📡 连接信息:")
            for key, value in conn_info.items():
                print(f"   {key}: {value}")
        
        # 问题列表
        issues = diagnostics.get('issues', [])
        if issues:
            print(f"\n❌ 发现问题:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        
        # 修复建议
        suggestions = diagnostics.get('suggestions', [])
        if suggestions:
            print(f"\n💡 修复建议:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion}")
        
        # 总结
        if status == "healthy":
            print(f"\n🎉 连接状态良好，无需特别处理")
        elif status == "warning":
            print(f"\n⚠️ 连接存在轻微问题，建议按照上述建议优化")
        elif status == "error":
            print(f"\n🚨 连接存在严重问题，请按照建议修复后重试")
        else:
            print(f"\n❓ 连接状态未知，建议手动检查")
        
        print("=" * 60)

    def _smart_preconnect(self) -> Dict[str, bool]:
        """智能预连接常用服务器"""
        preconnect_servers = self.global_settings.get('preconnect_servers', ['local-dev'])
        preconnect_timeout = self.global_settings.get('preconnect_timeout', 60)
        max_parallel = self.global_settings.get('preconnect_parallel', 3)
        
        print(f"🚀 启动智能预连接 ({len(preconnect_servers)}个服务器)...")
        
        results = {}
        start_time = time.time()
        
        # 使用线程池进行并行连接
        import concurrent.futures
        
        def connect_server(server_name):
            if server_name not in self.servers:
                return server_name, False, f"服务器{server_name}不存在"
            
            try:
                success, msg = self.test_connection(server_name)
                return server_name, success, msg
            except Exception as e:
                return server_name, False, f"连接异常: {str(e)}"
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # 提交所有预连接任务
            future_to_server = {
                executor.submit(connect_server, server_name): server_name 
                for server_name in preconnect_servers
            }
            
            # 等待结果，但有超时限制
            for future in concurrent.futures.as_completed(future_to_server, timeout=preconnect_timeout):
                server_name = future_to_server[future]
                try:
                    server_name, success, msg = future.result()
                    results[server_name] = success
                    
                    status_emoji = "✅" if success else "❌"
                    elapsed = time.time() - start_time
                    print(f"   {status_emoji} {server_name}: {msg} ({elapsed:.1f}s)")
                    
                except Exception as e:
                    results[server_name] = False
                    print(f"   ❌ {server_name}: 预连接失败 - {str(e)}")
        
        elapsed_total = time.time() - start_time
        success_count = sum(1 for success in results.values() if success)
        print(f"🎯 预连接完成: {success_count}/{len(preconnect_servers)}个成功 ({elapsed_total:.1f}s)")
        
        return results

    def _show_startup_summary(self, session_result: bool, preconnect_results: Dict[str, bool] = None):
        """显示启动摘要"""
        print("\n" + "="*50)
        print("🚀 Remote Terminal MCP 已就绪")
        print("="*50)
        
        if session_result:
            print("✅ 本地开发环境已准备就绪！")
            print("   🖥️  tmux会话: dev-session")
            print("   📁 工作目录: /Users/xuyehua/Code")
            print()
            print("💡 使用tmux会话的方式:")
            print("   • 直接连接: tmux attach -t dev-session")
            print("   • 查看会话: tmux list-sessions")
            print("   • 会话内操作:")
            print("     - Ctrl+B, D : 退出会话(保持运行)")
            print("     - Ctrl+B, C : 创建新窗口")
            print("     - Ctrl+B, N : 切换到下一个窗口")
            print()
            print("🔧 或者使用MCP工具:")
            print("   • list_tmux_sessions  - 查看所有会话")
            print("   • run_command        - 在会话中执行命令")
            print("   • create_tmux_session - 创建新会话")
        else:
            print("⚠️  本地tmux会话创建失败")
            print("   📦 安装tmux以获得完整功能:")
            print("      • macOS: brew install tmux")
            print("      • Ubuntu: sudo apt install tmux")
        
        # 显示可用服务器
        servers = self.list_servers()
        local_servers = [s for s in servers if s['type'] == 'local_tmux']
        remote_servers = [s for s in servers if s['type'] != 'local_tmux']
        
        print(f"\n📋 服务器配置:")
        if local_servers:
            print(f"   ✅ 本地会话: {len(local_servers)}个")
        
        if remote_servers:
            configured = len([s for s in remote_servers if s.get('host')])
            total = len(remote_servers)
            print(f"   🌐 远程服务器: {configured}/{total}个已配置")
        
        # 显示预连接结果
        if preconnect_results:
            preconnected = sum(1 for success in preconnect_results.values() if success)
            total_preconnect = len(preconnect_results)
            print(f"   🚀 预连接状态: {preconnected}/{total_preconnect}个已就绪")
        
        print(f"\n🎯 快速开始:")
        print("   1️⃣ 立即体验: tmux attach -t dev-session")
        print("   2️⃣ 配置远程: nano ~/.remote-terminal-mcp/config.yaml")
        print("   3️⃣ MCP工具: 通过Claude使用各种MCP工具")
        print("="*50 + "\n") 