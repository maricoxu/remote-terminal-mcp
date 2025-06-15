#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
SSH连接管理器

处理SSH连接、Jump host和远程Command执行
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


def debug_log_cmd(cmd_list, description=""):
    """打印执行的Command（调试用）"""
    if os.getenv('MCP_DEBUG') or os.getenv('SHOW_COMMANDS'):
        if isinstance(cmd_list, list):
            cmd_str = ' '.join(cmd_list)
        else:
            cmd_str = str(cmd_list)
        log_output(f"🐍 [COMMAND] {description}: {cmd_str}")

def log_output(message):
    """输出日志信息，只在非安静模式下输出"""
    if not os.getenv('MCP_QUIET'):
        print(message)


@dataclass
class ServerConfig:
    """Server配置"""
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
    password: Optional[str] = None  # 支持密码认证


@dataclass
class ConnectionStatus:
    """连接Status"""
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
        """查找配置文件，如果does not exist则自动创建默认配置"""
        # 1. 用户目录配置
        user_config_dir = Path.home() / ".remote-terminal-mcp"
        user_config_file = user_config_dir / "config.yaml"
        
        if user_config_file.exists():
            return str(user_config_file)
        
        # 2. 如果用户配置does not exist，则自动创建
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent
        template_config = project_dir / "config" / "servers.template.yaml"
        
        if template_config.exists():
            # 创建用户配置目录
            user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制模板到用户目录
            import shutil
            shutil.copy2(template_config, user_config_file)
            
            # 创建默认tmux会话（如果tmux可用且会话does not exist）
            self._create_default_tmux_session()
            
            log_output(f"📦 已自动创建默认配置: {user_config_file}")
            return str(user_config_file)
        
        # 3. 回退方案：项目本地配置
        local_config = project_dir / "config" / "servers.local.yaml"
        if local_config.exists():
            return str(local_config)
        
        # 4. 最后回退：直接使用模板
        if template_config.exists():
            return str(template_config)
        
        raise FileNotFoundError(
            "未找到配置模板文件！Please check项目完整性。\n"
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
            return False  # 其他Error
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件does not exist: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 解析Server配置
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
                    jump_host=server_config.get('jump_host'),
                    password=server_config.get('password')  # 支持密码认证
                )
                
                # 初始化连接Status
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
        """列出所有Server"""
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
        """获取Server配置"""
        return self.servers.get(server_name)
    
    def _expand_path(self, path: str) -> str:
        """展开路径中的波浪号"""
        if path.startswith('~'):
            return os.path.expanduser(path)
        return path
    
    def _validate_command(self, command: str) -> bool:
        """验证Command是否安全"""
        if not self.security_settings:
            return True  # 如果没有安全配置，允许所有Command
        
        allowed_commands = self.security_settings.get('allowed_commands', [])
        forbidden_commands = self.security_settings.get('forbidden_commands', [])
        
        # 检查禁止的Command
        for pattern in forbidden_commands:
            if re.match(pattern, command):
                return False
        
        # 检查允许的Command
        if allowed_commands:
            for pattern in allowed_commands:
                if re.match(pattern, command):
                    return True
            return False  # 如果有允许列表但不匹配，则禁止
        
        return True  # 没有限制或通过检查
    
    def _build_ssh_command(self, server: ServerConfig, command: Optional[str] = None) -> List[str]:
        """构建SSHCommand"""
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
        
        # Jump host
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
        
        # 要执行的Command
        if command:
            ssh_cmd.append(command)
        
        return ssh_cmd
    
    def execute_command(self, server_name: str, command: str) -> Tuple[bool, str]:
        """在远程ServerExecute command"""
        server = self.servers.get(server_name)
        if not server:
            return False, f"Server {server_name} does not exist"
        
        # 验证Command安全性
        if not self._validate_command(command):
            return False, f"Command被安全策略禁止: {command}"
        
        # 根据Server类型选择执行方式
        if server.type == 'script_based':
            return self._execute_script_based_command(server, command)
        else:
            return self._execute_ssh_command(server, command)
    
    def _execute_ssh_command(self, server: ServerConfig, command: str) -> Tuple[bool, str]:
        """执行SSHCommand（原有逻辑）"""
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
                output += f"⚠️ Error输出:\n{result.stderr}\n"
            
            output += f"🔢 退出码: {result.returncode}"
            
            # 更新连接Status
            self.connections[server.name].connected = result.returncode == 0
            self.connections[server.name].last_check = time.time()
            
            return result.returncode == 0, output
            
        except subprocess.TimeoutExpired:
            return False, f"⏱️ Command执行超时"
        except Exception as e:
            return False, f"❌ CommandExecution failed: {str(e)}"
    
    def _execute_script_based_command(self, server: ServerConfig, command: str) -> Tuple[bool, str]:
        """执行script_based类型Server的Command - 增强版本带连接验证"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        
        try:
            # 步骤1: 检查tmux会话是否存在
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            
            if check_result.returncode != 0:
                log_output(f"🔗 会话does not exist，正在建立连接...")
                # 会话does not exist，需要先建立连接
                success, msg = self._establish_script_based_connection(server)
                if not success:
                    return False, f"❌ 建立连接失败: {msg}"
            
            # 步骤2: 验证会话连接Status
            log_output(f"🔍 验证会话连接Status...")
            connected, status_msg = self._verify_session_connectivity(session_name)
            if not connected:
                log_output(f"⚠️ 会话连接异常: {status_msg}")
                log_output(f"🔄 重新建立连接...")
                
                # 清理异常会话
                subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                
                # 重新建立连接
                success, msg = self._establish_script_based_connection(server)
                if not success:
                    return False, f"❌ 重新连接失败: {msg}"
            
            # 步骤3: Execute command前的环境检查
            log_output(f"📋 准备Execute command: {command}")
            
            # 发送一个简单的测试Command确认会话响应
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'echo "CMD_READY_$(date +%s)"', 'Enter'], 
                         capture_output=True)
            time.sleep(1)
            
            # 检查响应
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"❌ 会话响应异常，无法Execute command"
            
            if 'CMD_READY_' not in result.stdout:
                return False, f"❌ 会话Status不稳定，建议手动检查 tmux attach -t {session_name}"
            
            # 步骤4: 执行实际Command
            log_output(f"⚡ Execute command: {command}")
            tmux_cmd = ['tmux', 'send-keys', '-t', session_name, command, 'Enter']
            result = subprocess.run(tmux_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"❌ Command发送失败: {result.stderr}"
            
            # 步骤5: 智能等待Command完成
            max_wait = 10  # 最大等待10秒
            wait_interval = 1
            
            for i in range(max_wait):
                time.sleep(wait_interval)
                
                # 捕获会话输出
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                capture_result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                if capture_result.returncode == 0:
                    output_lines = capture_result.stdout.strip().split('\n')
                    
                    # 检查Command是否完成（通过提示符或输出模式判断）
                    recent_lines = output_lines[-3:] if len(output_lines) > 3 else output_lines
                    for line in recent_lines:
                        if any(prompt in line for prompt in ['$', '#', '>', '~']):
                            # 找到提示符，Command可能已完成
                            log_output(f"✅ Command执行完成")
                            break
                else:
                    return False, f"❌ 获取输出失败: {capture_result.stderr}"
            
            # 最终获取完整输出
            final_capture = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                         capture_output=True, text=True)
            
            if final_capture.returncode == 0:
                output = f"📤 Command: {command}\n"
                output += f"🖥️  会话: {session_name}\n"
                output += f"📄 输出:\n{final_capture.stdout}"
                
                # 更新连接Status
                self.connections[server.name].connected = True
                self.connections[server.name].last_check = time.time()
                self.connections[server.name].error_message = None
                
                return True, output
            else:
                return False, f"❌ 最终输出获取失败: {final_capture.stderr}"
                
        except Exception as e:
            error_msg = f"CommandExecution failed: {str(e)}"
            self.connections[server.name].error_message = error_msg
            return False, f"❌ {error_msg}"
    
    def _establish_script_based_connection(self, server: ServerConfig) -> Tuple[bool, str]:
        """建立script_based类型的连接 - 增强版本带详细日志和Status检测"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        
        try:
            log_output(f"🚀 启动智能连接系统: {session_name}")
            
            # 步骤-1: 预检测 - 检查是否已经在期待的环境中
            log_output(f"🔍 步骤0: 环境预检测")
            already_in_target, env_msg = self._check_if_already_in_target_environment(server)
            if already_in_target:
                log_output(f"🎉 环境预检测通过！{env_msg}")
                log_output(f"⚡ 跳过连接流程，直接使用当前环境")
                
                # 更新连接状态
                self.connections[server.name].connected = True
                self.connections[server.name].last_check = time.time()
                self.connections[server.name].connection_time = time.time()
                self.connections[server.name].error_message = None
                
                return True, f"已在目标环境，无需重新连接: {env_msg}"
            else:
                log_output(f"📋 环境预检测: {env_msg}")
                log_output(f"🔄 继续建立新连接...")
            
            # 步骤0: 智能会话管理 - 检查已存在会话
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            if check_result.returncode == 0:
                log_output(f"✅ 发现已存在的会话: {session_name}")
                # 检查现有会话Status
                status_ok, status_msg = self._verify_session_connectivity(session_name)
                if status_ok:
                    log_output(f"🚀 现有会话Status良好，直接使用")
                    return True, f"会话已存在且Status良好: {session_name}"
                else:
                    log_output(f"⚠️  现有会话Status异常: {status_msg}")
                    log_output(f"🗑️  清理并重新建立连接...")
                    subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
            
            # 检查tmux是否可用
            tmux_check_cmd = ['tmux', '-V']
            debug_log_cmd(tmux_check_cmd, "检查tmux版本")
            tmux_check = subprocess.run(tmux_check_cmd, capture_output=True)
            if tmux_check.returncode != 0:
                return False, "❌ tmux不可用 - 请安装tmux: brew install tmux"
            
            # 创建新的tmux会话
            log_output(f"📋 创建新环境: {session_name}")
            create_cmd = ['tmux', 'new-session', '-d', '-s', session_name]
            debug_log_cmd(create_cmd, "创建tmux会话")
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"❌ 创建tmux会话失败: {result.stderr} - Please checktmux配置"
            
            # 获取配置
            connection_config = server.specs.get('connection', {}) if server.specs else {}
            docker_config = server.specs.get('docker', {}) if server.specs else {}
            # BOS配置现在在Docker配置内部，但也支持旧的顶级配置
            bos_config = docker_config.get('bos', {}) or server.specs.get('bos', {}) if server.specs else {}
            env_setup = server.specs.get('environment_setup', {}) if server.specs else {}
            
            # 步骤1: 启动连接工具
            connection_tool = connection_config.get('tool', 'ssh')
            log_output(f"📡 步骤1: 启动连接工具 ({connection_tool})")
            
            if connection_tool != 'ssh':
                success, msg = self._start_connection_tool(session_name, connection_tool)
                if not success:
                    return False, f"❌ 连接工具启动失败: {msg}"
            
            # 步骤2: 连接到目标Server
            connection_mode = connection_config.get('mode', 'direct')
            
            # 根据连接模式获取目标主机
            if connection_mode == 'double_jump_host':
                target_host = connection_config.get('second_jump', {}).get('host', server.host)
            else:
                target_host = connection_config.get('target', {}).get('host', server.host)
            
            if target_host:
                # 补充服务器配置信息到connection_config
                enhanced_connection_config = connection_config.copy()
                if 'password' not in enhanced_connection_config and hasattr(server, 'password') and server.password:
                    enhanced_connection_config['password'] = server.password
                
                # 确保target配置包含服务器的用户名
                if 'target' not in enhanced_connection_config:
                    enhanced_connection_config['target'] = {}
                if 'username' not in enhanced_connection_config['target'] and server.username:
                    enhanced_connection_config['target']['username'] = server.username
                if 'host' not in enhanced_connection_config['target'] and server.host:
                    enhanced_connection_config['target']['host'] = server.host
                
                log_output(f"🎯 步骤2: 连接到目标Server ({target_host})")
                success, msg = self._connect_to_target_server(session_name, target_host, enhanced_connection_config)
                if not success:
                    return False, f"❌ 目标Server连接失败: {msg}"
            
            # 步骤3: 智能Docker环境设置
            container_name = docker_config.get('container_name')
            container_image = docker_config.get('image')
            
            if container_name:
                log_output(f"🐳 步骤3: 智能Docker环境设置")
                success, msg = self._smart_container_setup_enhanced(session_name, container_name, container_image, bos_config, env_setup, docker_config)
                if not success:
                    log_output(f"⚠️ Docker容器设置失败: {msg}")
                    log_output("💡 建议: 检查Docker服务Status或容器配置")
            
            # 步骤4: 设置工作目录
            session_config = server.session or {}
            working_dir = session_config.get('working_directory', '/home/xuyehua')
            if working_dir:
                log_output(f"📁 步骤4: 设置工作目录: {working_dir}")
                success, msg = self._setup_working_directory(session_name, working_dir)
                if not success:
                    log_output(f"⚠️ 工作目录设置失败: {msg}")
            
            # 步骤5: 最终连接验证
            log_output(f"🔍 步骤5: 最终连接验证...")
            success, msg = self._verify_final_connection(session_name)
            if not success:
                return False, f"❌ 连接验证失败: {msg}"
            
            log_output(f"✅ 智能连接系统部署完成: {session_name}")
            
            # 更新连接Status
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
        """验证现有会话的连接Status"""
        try:
            # 发送测试Command
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
                    return True, "会话Status正常"
                else:
                    return False, "会话响应异常"
            else:
                return False, "无法获取会话Status"
                
        except Exception as e:
            return False, f"Status检查失败: {str(e)}"

    def _start_connection_tool(self, session_name: str, tool: str) -> Tuple[bool, str]:
        """启动连接工具并等待就绪"""
        try:
            log_output(f"   🔧 启动 {tool}...")
            send_cmd = ['tmux', 'send-keys', '-t', session_name, tool, 'Enter']
            debug_log_cmd(send_cmd, f"启动{tool}")
            subprocess.run(send_cmd, capture_output=True)
            
            # 智能等待工具启动
            max_wait = 15  # 最大等待15秒
            wait_interval = 1
            
            for i in range(max_wait):
                time.sleep(wait_interval)
                log_output(f"   ⏳ 等待工具启动... ({i+1}/{max_wait})")
                
                # 检查工具是否准备就绪
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                debug_log_cmd(capture_cmd, "捕获会话输出")
                result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout.lower()
                    # 检查各种就绪信号
                    if any(signal in output for signal in ['password:', 'fingerprint', '(yes/no)', 'ready', 'connected']):
                        log_output(f"   ✅ {tool} 已启动，等待用户认证...")
                        time.sleep(3)  # 给用户时间完成认证
                        return True, f"{tool} 启动成功"
                    elif 'error' in output or 'failed' in output:
                        return False, f"{tool} 启动失败: {output[-100:]}"
            
            return False, f"{tool} 启动超时，请手动检查"
            
        except Exception as e:
            return False, f"启动工具失败: {str(e)}"

    def _connect_to_target_server(self, session_name: str, target_host: str, connection_config: dict = None) -> Tuple[bool, str]:
        """连接到目标Server并验证连接 - 支持Jump host模式和relay模式"""
        try:
            # 检查是否需要Jump host连接
            if connection_config and connection_config.get('mode') == 'jump_host':
                return self._connect_via_jump_host(session_name, target_host, connection_config)
            
            # 检查是否需要双层Jump host连接
            if connection_config and connection_config.get('mode') == 'double_jump_host':
                return self._connect_via_double_jump_host(session_name, connection_config)
            
            # 检查是否是relay-cli模式（TJServer）
            connection_tool = connection_config.get('tool', 'ssh') if connection_config else 'ssh'
            
            if connection_tool == 'relay-cli':
                return self._connect_via_relay(session_name, target_host, connection_config)
            
            # 传统SSH直连模式
            log_output(f"   🌐 发起SSH连接到 {target_host}...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh {target_host}', 'Enter'],
                         capture_output=True)
            
            return self._verify_ssh_connection(session_name, target_host)
            
        except Exception as e:
            return False, f"连接过程失败: {str(e)}"
    
    def _connect_via_relay(self, session_name: str, target_host: str, connection_config: dict) -> Tuple[bool, str]:
        """通过relay-cli连接到目标Server - 优化版，支持二级跳转和密码认证"""
        try:
            log_output(f"   🚀 步骤1: 等待relay-cli就绪...")
            
            # 等待relay登录成功信号 - 优化：只检查bash提示符
            max_wait_relay = 20
            for i in range(max_wait_relay):
                time.sleep(1)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # 优化：简化relay成功检测 - 只要出现bash提示符就说明relay就绪
                    if 'bash-' in output and ('$' in output or '#' in output):
                        log_output(f"   ✅ Relay就绪(检测到bash提示符)！")
                        break
                    elif ('Login succeeded' in output or 'succeeded' in output):
                        log_output(f"   ✅ Relay登录成功！")
                        break
                    elif 'Login failed' in output.lower() or 'failed' in output.lower():
                        return False, "Relay登录失败，请检查认证信息"
                    elif 'Please input' in output or 'password' in output.lower():
                        if i < 5:
                            log_output(f"   🔐 Relay需要用户认证，请在另一终端执行:")
                            log_output(f"       tmux attach -t {session_name}")
                            log_output(f"       然后完成密码/指纹认证")
                        else:
                            log_output(f"   ⏳ 等待用户认证完成... ({i}/{max_wait_relay})")
            else:
                return False, "等待relay登录超时"
            
            # 步骤2: 构建正确的SSH命令并连接到目标Server
            # 从connection_config中获取目标服务器的用户名和主机信息
            target_config = connection_config.get('target', {})
            target_username = None
            actual_target_host = target_host
            
            # 检查是否配置了目标服务器的用户名 
            if target_config.get('username'):
                target_username = target_config['username']
            elif target_config.get('user'):  
                target_username = target_config['user']
            
            # 如果有配置目标主机地址，使用配置的地址
            if target_config.get('host'):
                actual_target_host = target_config['host']
            
            # 构建SSH命令
            if target_username:
                ssh_command = f"ssh {target_username}@{actual_target_host}"
                log_output(f"   🎯 步骤2: 在relay中连接到 {target_username}@{actual_target_host}")
            else:
                ssh_command = f"ssh {actual_target_host}"
                log_output(f"   🎯 步骤2: 在relay中连接到 {actual_target_host}")
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, ssh_command, 'Enter'],
                         capture_output=True)
            
            # 检查是否需要处理密码认证
            target_password = connection_config.get('password') or target_config.get('password')
            if target_password:
                # 等待密码提示并自动输入密码
                return self._verify_target_server_connection_with_password(session_name, actual_target_host, target_password)
            else:
                # 使用密钥认证
                return self._verify_target_server_connection_optimized(session_name, actual_target_host)
            
        except Exception as e:
            return False, f"Relay连接失败: {str(e)}"
    
    def _verify_target_server_connection_optimized(self, session_name: str, target_host: str) -> Tuple[bool, str]:
        """验证通过relay连接到目标Server - 优化版：基于提示符快速判断，避免不必要的命令执行"""
        try:
            max_wait = 30
            wait_interval = 2
            
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                log_output(f"   ⏳ 等待目标Server连接... ({i+wait_interval}/{max_wait}秒)")
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    lines = output.strip().split('\n')
                    recent_lines = lines[-5:] if len(lines) > 5 else lines
                    
                    # 优化：快速检查目标Server连接成功信号
                    for line in recent_lines:
                        line_lower = line.lower()
                        target_host_name = target_host.split('.')[0].lower()
                        
                        # 检查是否已连接到目标Server（而不是relay）
                        # 必须包含目标主机名或明确的目标Server指示符
                        if (target_host_name in line_lower and '@' in line) or \
                           (target_host_name in line_lower and ('welcome' in line_lower or 'last login' in line_lower)) or \
                           ('root@' + target_host_name in line_lower):
                            log_output(f"   ✅ 已成功连接到目标Server {target_host} (提示符识别)")
                            time.sleep(1)  # 减少稳定等待时间
                            return True, f"成功连接到 {target_host}"
                    
                    # 检查连接Error
                    for line in recent_lines:
                        line_lower = line.lower()
                        if any(error_signal in line_lower for error_signal in [
                            'connection refused', 'timeout', 'permission denied', 'host unreachable',
                            'no route to host', 'network unreachable'
                        ]):
                            return False, f"目标Server连接失败: {line.strip()}"
            
            # 优化：如果连接超时，只做最小化验证，不执行额外命令
            log_output(f"   🔍 连接超时，检查最终状态...")
            
            # 只检查最后几行输出，不执行新命令
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                target_hostname = target_host.split('.')[0].lower()
                
                # 检查是否在目标服务器环境（通过提示符分析）
                lines = output.strip().split('\n')
                recent_lines = lines[-3:] if len(lines) > 3 else lines
                
                for line in recent_lines:
                    line_lower = line.lower()
                    # 如果看到目标服务器的提示符，说明连接成功
                    if (target_hostname in line_lower and ('@' in line or '#' in line or '$' in line)):
                        log_output(f"   ✅ 最终验证成功，已连接到 {target_host} (提示符分析)")
                        return True, f"连接验证成功: {target_host}"
                
                # 如果还是显示relay的bash提示符，说明没有成功连接到目标
                if 'bash-' in output and target_hostname not in output.lower():
                    return False, f"仍在relay环境中，未能连接到目标服务器 {target_host}"
            
            return False, f"连接状态不明确，请手动检查会话 {session_name}"
            
        except Exception as e:
            return False, f"目标Server验证失败: {str(e)}"
    
    def _verify_target_server_connection_with_password(self, session_name: str, target_host: str, password: str) -> Tuple[bool, str]:
        """验证通过relay连接到目标Server - 支持自动密码输入"""
        try:
            max_wait = 30
            wait_interval = 1
            password_sent = False
            
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                log_output(f"   ⏳ 等待目标Server连接... ({i+wait_interval}/{max_wait}秒)")
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    lines = output.strip().split('\n')
                    recent_lines = lines[-5:] if len(lines) > 5 else lines
                    
                    # 检查是否需要输入密码
                    if not password_sent:
                        for line in recent_lines:
                            line_lower = line.lower()
                            if ('password:' in line_lower or 'password' in line_lower) and not password_sent:
                                log_output(f"   🔐 检测到密码提示，自动输入密码...")
                                subprocess.run(['tmux', 'send-keys', '-t', session_name, password, 'Enter'],
                                             capture_output=True)
                                password_sent = True
                                time.sleep(2)  # 等待密码处理
                                break
                    
                    # 检查目标Server连接成功信号
                    for line in recent_lines:
                        line_lower = line.lower()
                        target_host_name = target_host.split('.')[0].lower()
                        
                        # 检查是否已连接到目标Server
                        if (target_host_name in line_lower and '@' in line) or \
                           (target_host_name in line_lower and ('welcome' in line_lower or 'last login' in line_lower or 'hello' in line_lower)) or \
                           ('root@' + target_host_name in line_lower) or \
                           (('@' in line) and (target_host_name in line_lower or target_host in line_lower)):
                            log_output(f"   ✅ 已成功连接到目标Server {target_host} (密码认证)")
                            time.sleep(1)  
                            return True, f"成功连接到 {target_host} (使用密码认证)"
                    
                    # 检查连接Error
                    for line in recent_lines:
                        line_lower = line.lower()
                        if any(error_signal in line_lower for error_signal in [
                            'connection refused', 'timeout', 'permission denied', 'host unreachable',
                            'no route to host', 'network unreachable', 'authentication failed'
                        ]):
                            return False, f"目标Server连接失败: {line.strip()}"
            
            # 最终验证状态
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                target_hostname = target_host.split('.')[0].lower()
                
                # 检查是否在目标服务器环境
                lines = output.strip().split('\n')
                recent_lines = lines[-3:] if len(lines) > 3 else lines
                
                for line in recent_lines:
                    line_lower = line.lower()
                    # 检查目标服务器提示符
                    if (target_hostname in line_lower and ('@' in line or '#' in line or '$' in line)):
                        log_output(f"   ✅ 最终验证成功，已连接到 {target_host} (密码认证)")
                        return True, f"连接验证成功: {target_host}"
                
                # 如果还是显示relay的bash提示符，说明密码认证失败
                if 'bash-' in output and target_hostname not in output.lower():
                    return False, f"密码认证失败，仍在relay环境中，未能连接到目标服务器 {target_host}"
            
            return False, f"连接状态不明确，请手动检查会话 {session_name}"
            
        except Exception as e:
            return False, f"目标Server密码认证失败: {str(e)}"
    
    def _verify_target_server_connection(self, session_name: str, target_host: str) -> Tuple[bool, str]:
        """验证通过relay连接到目标Server - 原版保留作为备用"""
        try:
            max_wait = 30
            wait_interval = 2
            
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                log_output(f"   ⏳ 等待目标Server连接... ({i+wait_interval}/{max_wait}秒)")
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    lines = output.strip().split('\n')
                    recent_lines = lines[-5:] if len(lines) > 5 else lines
                    
                    # 检查目标Server连接成功信号
                    for line in recent_lines:
                        line_lower = line.lower()
                        target_host_name = target_host.split('.')[0].lower()
                        
                        # 检查是否已连接到目标Server（而不是relay）
                        # 必须包含目标主机名或明确的目标Server指示符
                        if (target_host_name in line_lower and '@' in line) or \
                           (target_host_name in line_lower and ('welcome' in line_lower or 'last login' in line_lower)) or \
                           ('root@' + target_host_name in line_lower):
                            log_output(f"   ✅ 已成功连接到目标Server {target_host}")
                            time.sleep(2)  # 稳定连接
                            return True, f"成功连接到 {target_host}"
                    
                    # 检查连接Error
                    for line in recent_lines:
                        line_lower = line.lower()
                        if any(error_signal in line_lower for error_signal in [
                            'connection refused', 'timeout', 'permission denied', 'host unreachable',
                            'no route to host', 'network unreachable'
                        ]):
                            return False, f"目标Server连接失败: {line.strip()}"
            
            # 最终验证 - 使用完整路径的Command
            log_output(f"   🔍 连接超时，执行最终验证...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, '/bin/echo "VERIFY_$(/bin/hostname)"', 'Enter'], 
                         capture_output=True)
            time.sleep(3)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if (result.returncode == 0 and 
                ('VERIFY_' in result.stdout and target_host.split('.')[0] in result.stdout)):
                log_output(f"   ✅ 最终验证成功，已连接到 {target_host}")
                return True, f"连接验证成功: {target_host}"
            
            return False, f"连接验证失败，可能仍在relay环境中"
            
        except Exception as e:
            return False, f"目标Server验证失败: {str(e)}"
    
    def _verify_ssh_connection(self, session_name: str, target_host: str) -> Tuple[bool, str]:
        """验证传统SSH连接"""
        try:
            max_wait = 30
            wait_interval = 2
            
            for i in range(0, max_wait, wait_interval):
                time.sleep(wait_interval)
                log_output(f"   ⏳ 等待Server连接... ({i+wait_interval}/{max_wait}秒)")
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout
                    lines = output.strip().split('\n')
                    recent_lines = lines[-5:] if len(lines) > 5 else lines  # 增加检查行数
                    
                    # 首先检查SSH连接失败的错误信号 - 这是最重要的检查
                    for line in recent_lines:
                        line_lower = line.lower()
                        # 检查SSH特定的错误信息
                        if any(error_signal in line_lower for error_signal in [
                            'could not resolve hostname', 'nodename nor servname provided',
                            'connection refused', 'connection timed out', 'permission denied', 
                            'host unreachable', 'no route to host', 'network unreachable',
                            'ssh: ', 'connection closed by'
                        ]):
                            error_msg = line.strip()
                            log_output(f"   ❌ SSH连接失败: {error_msg}")
                            
                            # 提供用户友好的错误指导
                            if 'could not resolve hostname' in line_lower or 'nodename nor servname provided' in line_lower:
                                guidance = (
                                    f"主机名解析失败，请检查:\n"
                                    f"   • 服务器地址是否正确 (当前: {target_host})\n"
                                    f"   • 网络连接是否正常\n"
                                    f"   • DNS设置是否正确\n"
                                    f"   💡 建议: 运行配置管理器重新设置服务器信息"
                                )
                            elif 'connection refused' in line_lower:
                                guidance = (
                                    f"连接被拒绝，请检查:\n"
                                    f"   • 服务器是否在线\n"
                                    f"   • SSH服务是否启动 (端口22)\n"
                                    f"   • 防火墙设置是否正确"
                                )
                            elif 'permission denied' in line_lower:
                                guidance = (
                                    f"认证失败，请检查:\n"
                                    f"   • 用户名是否正确\n"
                                    f"   • SSH密钥或密码是否正确\n"
                                    f"   • 服务器是否允许该用户登录"
                                )
                            else:
                                guidance = (
                                    f"SSH连接失败，请检查:\n"
                                    f"   • 服务器配置是否正确\n"
                                    f"   • 网络连接是否正常\n"
                                    f"   💡 建议: 运行配置管理器重新配置"
                                )
                            
                            return False, f"SSH连接失败: {error_msg}\n\n{guidance}"
                    
                    # 然后检查连接成功的信号 - 但要更严格
                    for line in recent_lines:
                        line_lower = line.lower()
                        # 只有当行中包含目标主机名时才认为连接成功
                        if target_host.lower() in line_lower and '@' in line:
                            # 进一步验证：确保不是本地机器
                            if not any(local_indicator in line_lower for local_indicator in [
                                'mac-studio', 'localhost', '127.0.0.1', 'local'
                            ]):
                                log_output(f"   ✅ 已成功连接到 {target_host}")
                                time.sleep(2)
                                return True, f"成功连接到 {target_host}"
                        
                        # 检查其他成功信号，但要求更严格的验证
                        elif any(success_signal in line_lower for success_signal in [
                            'welcome', 'last login'
                        ]) and target_host.split('.')[0].lower() in line_lower:
                            log_output(f"   ✅ 已成功连接到 {target_host}")
                            time.sleep(2)
                            return True, f"成功连接到 {target_host}"
            
            # 超时后进行最终验证
            log_output(f"   🔍 连接超时，执行最终验证...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'hostname', 'Enter'], 
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                target_hostname = target_host.split('.')[0]
                
                # 检查是否真的连接到了目标服务器
                if target_hostname.lower() in output.lower():
                    # 确保不是本地机器
                    if not any(local_indicator in output.lower() for local_indicator in [
                        'mac-studio', 'localhost', '127.0.0.1'
                    ]):
                        log_output(f"   ✅ 最终验证成功，已连接到 {target_host}")
                        return True, f"连接验证成功: {target_host}"
                
                # 如果最终验证显示在本地机器，说明SSH连接失败了
                if any(local_indicator in output.lower() for local_indicator in [
                    'mac-studio', 'localhost'
                ]):
                    guidance = (
                        f"SSH连接失败，当前仍在本地机器。请检查:\n"
                        f"   • 服务器地址是否正确 (当前: {target_host})\n"
                        f"   • 服务器是否在线和可访问\n"
                        f"   • 网络连接是否正常\n"
                        f"   💡 建议: 手动测试 'ssh {target_host}' 或重新配置服务器"
                    )
                    return False, f"SSH连接失败，未能连接到目标服务器\n\n{guidance}"
            
            return False, f"连接超时，无法确认连接状态\n\n💡 建议: 检查服务器配置和网络连接"
            
        except Exception as e:
            return False, f"SSH连接验证失败: {str(e)}"
    
    def _connect_via_jump_host(self, session_name: str, target_host: str, connection_config: dict) -> Tuple[bool, str]:
        """通过Jump host连接到目标Server - 基于cursor-bridge脚本逻辑"""
        try:
            jump_host_config = connection_config.get('jump_host', {})
            jump_host = jump_host_config.get('host', '')
            jump_password = jump_host_config.get('password', '')
            
            if not jump_host:
                return False, "Jump host配置缺失"
            
            log_output(f"   🚀 步骤1: 连接Jump host {jump_host}")
            jump_ssh_cmd = ['tmux', 'send-keys', '-t', session_name, f'ssh {jump_host}', 'Enter']
            debug_log_cmd(jump_ssh_cmd, "连接Jump host")
            subprocess.run(jump_ssh_cmd, capture_output=True)
            time.sleep(3)
            
            # 处理指纹认证（如果需要）
            capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
            debug_log_cmd(capture_cmd, "检查指纹认证")
            result = subprocess.run(capture_cmd, capture_output=True, text=True)
            if 'fingerprint' in result.stdout.lower() or 'yes/no' in result.stdout.lower():
                log_output("   🔑 接受指纹...")
                accept_cmd = ['tmux', 'send-keys', '-t', session_name, 'yes', 'Enter']
                debug_log_cmd(accept_cmd, "接受指纹")
                subprocess.run(accept_cmd, capture_output=True)
                time.sleep(2)
            
            # 输入Jump host密码
            if jump_password:
                log_output("   🔐 输入Jump host密码...")
                password_cmd = ['tmux', 'send-keys', '-t', session_name, jump_password, 'Enter']
                debug_log_cmd(password_cmd, "输入Jump host密码")
                subprocess.run(password_cmd, capture_output=True)
                time.sleep(4)
            
            # 验证Jump host连接
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            if '$' not in result.stdout and '#' not in result.stdout:
                return False, "Jump host连接失败，Please check密码"
            
            log_output(f"   ✅ Jump host连接成功")
            
            # 获取目标Server密码和用户
            target_config = connection_config.get('target', {})
            target_password = target_config.get('password')
            target_user = target_config.get('user', 'root')  # 默认用户为root
            
            # 从Jump host连接到目标Server
            log_output(f"   🎯 步骤2: 从Jump host连接到 {target_host}")
            # 检查target_host是否已经包含用户名
            if '@' in target_host:
                ssh_target = target_host  # 已经包含用户名，直接使用
            else:
                ssh_target = f'{target_user}@{target_host}'  # 使用配置中的用户名
            
            target_ssh_cmd = ['tmux', 'send-keys', '-t', session_name, f'ssh {ssh_target}', 'Enter']
            debug_log_cmd(target_ssh_cmd, "连接目标Server")
            subprocess.run(target_ssh_cmd, capture_output=True)
            time.sleep(4)
            
            # 验证目标Server连接并处理密码
            for i in range(10):  # 最多等待20秒
                time.sleep(2)
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                debug_log_cmd(capture_cmd, f"检查连接Status(第{i+1}次)")
                result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                output = result.stdout.lower()
                debug_log_cmd(f"Output: {result.stdout[-200:]}", "会话输出")
                
                # 检查是否需要输入密码
                if "password:" in output:
                    if target_password:
                        log_output(f"   🔐 输入目标Server密码...")
                        pwd_cmd = ['tmux', 'send-keys', '-t', session_name, target_password, 'Enter']
                        debug_log_cmd(pwd_cmd, "输入目标Server密码")
                        subprocess.run(pwd_cmd, capture_output=True)
                        time.sleep(3)
                        continue
                    else:
                        return False, f"目标Server需要密码但未在配置中提供: {target_host}"
                
                # 检查连接成功的标志
                if any(indicator in result.stdout for indicator in ['root@', '$', '#']) and 'password:' not in output:
                    log_output(f"   ✅ 已成功连接到目标Server: {target_host}")
                    return True, f"通过Jump host成功连接到 {target_host}"
                    
                # 检查连接失败的标志
                if any(error in output for error in ['denied', 'failed', 'connection timed out', 'no route to host']):
                    return False, f"目标Server连接失败: {result.stdout[-200:]}"
            
            return False, f"连接目标Server超时: {target_host}"
            
        except Exception as e:
            return False, f"Jump host连接失败: {str(e)}"

    def _setup_working_directory(self, session_name: str, working_dir: str) -> Tuple[bool, str]:
        """设置工作目录"""
        try:
            log_output(f"   📂 创建工作目录: {working_dir}")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'mkdir -p {working_dir}', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            log_output(f"   📂 切换到工作目录: {working_dir}")
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
                log_output(f"   ✅ 工作目录设置成功: {working_dir}")
                return True, f"工作目录已设置: {working_dir}"
            else:
                return False, f"工作目录验证失败，当前位置未知"
                
        except Exception as e:
            return False, f"设置工作目录失败: {str(e)}"

    def _verify_final_connection(self, session_name: str) -> Tuple[bool, str]:
        """最终连接验证"""
        try:
            log_output(f"   🔍 执行最终连接验证...")
            
            # 发送多个验证Command
            verification_commands = [
                ('hostname', '主机名检查'),
                ('whoami', '用户身份检查'),
                ('pwd', '当前目录检查')
            ]
            
            verification_results = []
            
            for cmd, desc in verification_commands:
                log_output(f"   🔎 {desc}...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, cmd, 'Enter'],
                             capture_output=True)
                time.sleep(1)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output_lines = result.stdout.strip().split('\n')
                    # 查找Command输出
                    for line in output_lines[-5:]:  # 检查最后5行
                        if line.strip() and not line.startswith(cmd) and cmd not in line:
                            verification_results.append(f"{desc}: {line.strip()}")
                            log_output(f"     ✅ {line.strip()}")
                            break
            
            if len(verification_results) >= 2:  # 至少2个验证通过
                return True, f"连接验证成功 - {'; '.join(verification_results)}"
            else:
                return False, f"连接验证不足，请手动检查会话Status"
                
        except Exception as e:
            return False, f"最终验证失败: {str(e)}"
    
    def _smart_container_setup(self, session_name: str, container_name: str, 
                              container_image: str, bos_config: dict, env_setup: dict) -> bool:
        """智能容器检查和处理 - 基于原始脚本逻辑"""
        try:
            log_output(f"🔍 智能检查Docker环境...")
            
            # 步骤1: 精确检查容器是否存在
            log_output(f"🔍 步骤1: 精确检查容器是否存在: {container_name}")
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
                log_output("✅ 容器已存在，进入快速连接模式...")
                return self._handle_existing_container(session_name, container_name)
            elif 'CONTAINER_EXISTS_NO' in result.stdout:
                log_output("🚀 容器does not exist，进入创建模式...")
                return self._handle_new_container(session_name, container_name, container_image, bos_config, env_setup)
            else:
                log_output("❌ 容器存在性检查结果异常")
                return False
                
        except Exception as e:
            log_output(f"❌ 智能容器设置失败: {str(e)}")
            return False

    def _smart_container_setup_enhanced(self, session_name: str, container_name: str, 
                                      container_image: str, bos_config: dict, env_setup: dict, docker_config: dict = None) -> Tuple[bool, str]:
        """增强版智能容器设置，带详细日志和Error处理"""
        try:
            log_output(f"   🔍 检查Docker环境...")
            
            # 步骤1: 验证Docker可用性
            log_output(f"   🐳 验证Docker服务...")
            success, msg = self._verify_docker_availability(session_name)
            if not success:
                return False, f"Docker不可用: {msg}"
            
            # 步骤2: 检查容器是否存在
            log_output(f"   🔍 检查容器: {container_name}")
            exists, msg = self._check_container_exists(session_name, container_name)
            if exists is None:
                return False, f"容器检查失败: {msg}"
            
            if exists:
                log_output(f"   ✅ 容器已存在，进入连接模式...")
                success, msg = self._handle_existing_container_enhanced(session_name, container_name, docker_config, bos_config)
                return success, msg
            else:
                log_output(f"   🚀 容器does not exist，进入创建模式...")
                success, msg = self._handle_new_container_enhanced(session_name, container_name, container_image, bos_config, env_setup, docker_config)
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
                    return False, f"DockerStatus异常: {output[-100:]}"
            else:
                return False, "无法检查DockerStatus"
                
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
                    return False, "容器does not exist"
                else:
                    return None, f"检查结果不明确: {output[-100:]}"
            else:
                return None, "无法获取检查结果"
                
        except Exception as e:
            return None, f"容器检查异常: {str(e)}"
    
    def _handle_existing_container_enhanced(self, session_name: str, container_name: str, docker_config: dict = None, bos_config: dict = None) -> Tuple[bool, str]:
        """增强版现有容器处理"""
        try:
            # 检查容器运行Status
            log_output(f"   🔍 检查容器运行Status...")
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
                log_output(f"   ⚠️ 容器已停止，正在启动...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker start {container_name}", 'Enter'], capture_output=True)
                
                # 等待容器启动
                max_wait = 10
                for i in range(max_wait):
                    time.sleep(1)
                    log_output(f"   ⏳ 等待容器启动... ({i+1}/{max_wait})")
                    
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"docker inspect --format='{{{{.State.Running}}}}' {container_name}", 'Enter'],
                                 capture_output=True)
                    time.sleep(1)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if 'true' in result.stdout:
                        log_output(f"   ✅ 容器启动成功")
                        break
                else:
                    return False, "容器启动超时"
            else:
                log_output(f"   ✅ 容器正在运行")
            
            # 获取配置的shell，默认为zsh
            preferred_shell = docker_config.get('shell', 'zsh') if docker_config else 'zsh'
            
            # 如果用户配置了zsh且有BOS配置，先用bash进入进行配置
            if preferred_shell == 'zsh':
                log_output(f"   🚪 检测到zsh配置，先用bash进入容器进行BOS配置...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
                time.sleep(3)
                
                # 验证是否成功进入bash
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if '@' in result.stdout or '#' in result.stdout:
                    log_output(f"   ✅ 成功用bash进入容器")
                    
                    # 如果有BOS配置，自动配置BOS和下载zsh配置
                    if bos_config:
                        log_output(f"   🔧 在bash中配置BOS和下载zsh配置文件...")
                        bos_success = self._setup_zsh_environment_with_bos(session_name, bos_config)
                        if bos_success:
                            log_output(f"   ✅ BOS配置和zsh环境设置完成")
                            return True, f"成功连接到现有容器并配置zsh环境: {container_name}"
                        else:
                            log_output(f"   ⚠️ BOS配置失败，但容器已可用，手动切换到zsh...")
                            # BOS配置失败，手动切换到zsh
                            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                          'exec zsh', 'Enter'], capture_output=True)
                            time.sleep(2)
                            return True, f"成功连接到现有容器: {container_name} (BOS配置失败，已切换到zsh)"
                    else:
                        # 没有BOS配置，直接切换到zsh
                        log_output(f"   🔄 没有BOS配置，直接切换到zsh...")
                        subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                      'exec zsh', 'Enter'], capture_output=True)
                        time.sleep(2)
                        return True, f"成功连接到现有容器: {container_name} (已切换到zsh)"
                else:
                    # bash失败，尝试直接用zsh
                    log_output(f"   🔄 bash进入失败，尝试直接使用zsh...")
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'C-c'], capture_output=True)
                    time.sleep(1)
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"docker exec -it {container_name} zsh", 'Enter'], capture_output=True)
                    time.sleep(2)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if '@' in result.stdout or '#' in result.stdout:
                        log_output(f"   ✅ 直接使用zsh成功进入容器")
                        return True, f"直接使用zsh连接到容器: {container_name}"
                    else:
                        return False, "无法进入容器，请手动检查"
            else:
                # 非zsh配置，直接使用配置的shell
                log_output(f"   🚪 进入容器 (使用 {preferred_shell})...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker exec -it {container_name} {preferred_shell}", 'Enter'], capture_output=True)
                time.sleep(3)
                
                # 验证是否成功进入
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if '@' in result.stdout or '#' in result.stdout:
                    log_output(f"   ✅ 成功进入容器 (使用 {preferred_shell})")
                    return True, f"成功连接到现有容器: {container_name} (shell: {preferred_shell})"
                else:
                    # 尝试bash作为备用
                    log_output(f"   🔄 尝试使用bash...")
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'C-c'], capture_output=True)
                    time.sleep(1)
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
                    time.sleep(2)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if '@' in result.stdout or '#' in result.stdout:
                        log_output(f"   ✅ 使用bash成功进入容器")
                        return True, f"使用bash连接到容器: {container_name}"
                    else:
                        return False, "无法进入容器，请手动检查"
                
        except Exception as e:
            return False, f"处理现有容器失败: {str(e)}"

    def _handle_new_container_enhanced(self, session_name: str, container_name: str, 
                                     container_image: str, bos_config: dict, env_setup: dict, docker_config: dict = None) -> Tuple[bool, str]:
        """增强版新容器创建"""
        try:
            log_output(f"   🚀 创建新容器: {container_name}")
            
            # 构建docker runCommand
            docker_cmd = self._build_docker_run_command(container_name, container_image, docker_config)
            log_output(f"   🔧 DockerCommand: {docker_cmd[:100]}...")
            
            # 执行创建Command
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'echo "CREATE_START_{container_name}"', 'Enter'], capture_output=True)
            time.sleep(1)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, docker_cmd, 'Enter'],
                         capture_output=True)
            
            # 等待容器创建
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                log_output(f"   ⏳ 等待容器创建... ({i+1}/{max_wait})")
                
                # 检查容器是否创建成功
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker inspect {container_name} >/dev/null 2>&1 && echo 'CREATE_SUCCESS' || echo 'CREATE_FAILED'", 
                              'Enter'], capture_output=True)
                time.sleep(2)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if 'CREATE_SUCCESS' in result.stdout:
                    log_output(f"   ✅ 容器创建成功")
                    break
                elif 'CREATE_FAILED' in result.stdout:
                    return False, "容器创建失败，Please check镜像和配置"
            else:
                return False, "容器创建超时"
            
            # 获取配置的shell，默认为zsh
            preferred_shell = docker_config.get('shell', 'zsh') if docker_config else 'zsh'
            
            # 如果用户配置了zsh且有BOS配置，先用bash进入进行配置
            if preferred_shell == 'zsh' and bos_config:
                log_output(f"   🚪 检测到zsh配置和BOS配置，先用bash进入新容器...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
                time.sleep(3)
                
                # 验证是否成功进入bash
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if '@' in result.stdout or '#' in result.stdout:
                    log_output(f"   ✅ 成功用bash进入新容器")
                    
                    # 在bash中配置BOS和下载配置文件
                    log_output(f"   🔧 在bash中配置BOS和下载zsh配置文件...")
                    bos_success = self._setup_zsh_environment_with_bos(session_name, bos_config)
                    if bos_success:
                        log_output(f"   ✅ BOS配置和zsh环境设置完成")
                        return True, f"成功创建容器并配置zsh环境: {container_name}"
                    else:
                        log_output(f"   ⚠️ BOS配置失败，但容器已可用，手动切换到zsh...")
                        # BOS配置失败，手动切换到zsh
                        subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                      'exec zsh', 'Enter'], capture_output=True)
                        time.sleep(2)
                        return True, f"成功创建容器: {container_name} (BOS配置失败，已切换到zsh)"
                else:
                    # bash进入失败，尝试直接用zsh
                    log_output(f"   🔄 bash进入失败，尝试直接使用zsh...")
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'C-c'], capture_output=True)
                    time.sleep(1)
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"docker exec -it {container_name} zsh", 'Enter'], capture_output=True)
                    time.sleep(2)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if '@' in result.stdout or '#' in result.stdout:
                        log_output(f"   ✅ 直接使用zsh成功进入新容器")
                        return True, f"成功创建并连接到容器: {container_name} (直接使用zsh)"
                    else:
                        return False, "容器创建成功但无法进入"
            else:
                # 非zsh配置或无BOS配置，直接使用配置的shell
                log_output(f"   🚪 进入新容器 (使用 {preferred_shell})...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker exec -it {container_name} {preferred_shell}", 'Enter'], capture_output=True)
                time.sleep(3)
                
                # 验证进入结果
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if '@' in result.stdout or '#' in result.stdout:
                    log_output(f"   ✅ 成功进入新容器 (使用 {preferred_shell})")
                    return True, f"成功创建并连接到容器: {container_name} (shell: {preferred_shell})"
                else:
                    # 尝试bash作为备用
                    log_output(f"   🔄 尝试使用bash...")
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
                    time.sleep(2)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if '@' in result.stdout or '#' in result.stdout:
                        log_output(f"   ✅ 使用bash成功进入新容器")
                        return True, f"成功创建并连接到容器: {container_name} (shell: bash)"
                    else:
                        return False, "容器创建成功但无法进入"
                
        except Exception as e:
            return False, f"创建新容器失败: {str(e)}"

    def _build_docker_run_command(self, container_name: str, container_image: str, docker_config: dict = None) -> str:
        """构建Docker runCommand - 支持配置文件自定义参数"""
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
            log_output(f"🔍 步骤2: 检查容器运行Status...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo '=== CONTAINER_STATUS_CHECK_START ==='", 'Enter'], capture_output=True)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect --format='{{{{.State.Running}}}}' {container_name}", 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'true' in result.stdout:
                log_output("✅ 容器正在运行")
            else:
                log_output("⚠️ 容器已停止，正在启动...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f"docker start {container_name}", 'Enter'], capture_output=True)
                time.sleep(5)
                log_output("✅ 容器启动成功")
            
            # 进入容器
            log_output(f"🚪 步骤3: 进入现有容器...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker exec -it {container_name} zsh", 'Enter'], capture_output=True)
            time.sleep(2)
            
            # 检查是否成功进入zsh，否则尝试bash
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            if '@' not in result.stdout or '#' not in result.stdout:
                log_output("⚠️ 尝试启动zsh...")
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                             capture_output=True)
                time.sleep(2)
            
            log_output("✅ 快速Connection completed！")
            return True
            
        except Exception as e:
            log_output(f"❌ 处理已存在容器失败: {str(e)}")
            return False
    
    def _handle_new_container(self, session_name: str, container_name: str, 
                            container_image: str, bos_config: dict, env_setup: dict) -> bool:
        """处理新容器创建的逻辑"""
        try:
            log_output(f"步骤1: 创建Docker容器 {container_name}")
            
            # 构建docker runCommand
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
            log_output("步骤2: 验证容器创建结果")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker inspect {container_name} >/dev/null 2>&1 && echo 'CREATE_SUCCESS' || echo 'CREATE_FAILED'", 
                          'Enter'], capture_output=True)
            time.sleep(3)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'CREATE_SUCCESS' not in result.stdout:
                log_output("❌ 容器创建失败")
                return False
            
            log_output("✅ 容器创建成功")
            
            # 进入新创建的容器
            log_output("🚪 步骤3: 进入新创建的容器...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f"docker exec -it {container_name} bash", 'Enter'], capture_output=True)
            time.sleep(3)
            
            # 如果启用自动环境配置，执行完整配置
            if env_setup.get('auto_setup', False):
                self._setup_full_environment(session_name, bos_config)
            else:
                log_output("💡 容器已创建，如需配置环境请手动执行相关Command")
            
            return True
            
        except Exception as e:
            log_output(f"❌ 处理新容器失败: {str(e)}")
            return False
    
    def _setup_full_environment(self, session_name: str, bos_config: dict) -> bool:
        """完整环境配置函数"""
        try:
            log_output("🛠️ 开始完整环境配置...")
            
            # 检查BOS工具
            log_output("步骤1: 检查BOS工具")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'which bcecmd', 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if '/bcecmd' in result.stdout:
                log_output("✅ BOS工具可用")
                self._configure_bos(session_name, bos_config)
            else:
                log_output("⚠️ BOS工具不可用，使用本地备用配置")
                self._setup_local_config(session_name)
            
            # 创建工作目录
            log_output("步骤5: 创建工作目录")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'mkdir -p /home/xuyehua', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 生成SSH密钥
            log_output("步骤6: 生成SSH密钥")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ''", 'Enter'], capture_output=True)
            time.sleep(3)
            
            # 启动zsh环境
            log_output("步骤7: 启动zsh环境")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 显示SSH公钥
            log_output("步骤8: 显示SSH公钥")
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
                log_output("✅ SSH公钥已生成:")
                log_output("━" * 80)
                log_output(ssh_key)
                log_output("━" * 80)
                log_output("💡 请复制上述公钥内容到目标Server的authorized_keys文件")
            else:
                log_output("⚠️ SSH公钥获取失败，请手动执行: cat /root/.ssh/id_rsa.pub")
            
            log_output("✅ 完整环境配置完成！")
            return True
            
        except Exception as e:
            log_output(f"❌ 环境配置失败: {str(e)}")
            return False
    
    def _configure_bos(self, session_name: str, bos_config: dict) -> bool:
        """配置BOS工具"""
        try:
            log_output("步骤2: 配置BOS工具")
            
            access_key = bos_config.get('access_key', '')
            secret_key = bos_config.get('secret_key', '')
            bucket = bos_config.get('bucket', '')
            
            if not access_key or secret_key == 'your_secret_key':
                log_output("⚠️ BOS配置不完整，跳过BOS设置")
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
                log_output("步骤3: 测试BOS连接并下载配置文件")
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
                    log_output("✅ BOS配置和连接成功！")
                    
                    # 下载其他配置文件
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"bcecmd bos cp -y {bucket}/.zshrc /root", 'Enter'],
                                 capture_output=True)
                    time.sleep(5)
                    
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f"bcecmd bos cp -y {bucket}/.zsh_history /root", 'Enter'],
                                 capture_output=True)
                    time.sleep(5)
                    
                    log_output("✅ 配置文件下载完成，p10k主题将在zsh启动时自动加载")
                    return True
                else:
                    log_output("❌ BOS连接或下载失败！")
                    return False
            
            return True
            
        except Exception as e:
            log_output(f"❌ BOS配置失败: {str(e)}")
            return False
    
    def _setup_local_config(self, session_name: str) -> bool:
        """本地配置备用方案"""
        try:
            log_output("🔧 设置本地备用配置...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          "echo 'export TERM=xterm-256color' >> ~/.bashrc", 'Enter'],
                         capture_output=True)
            time.sleep(1)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.bashrc', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            log_output("✅ 本地配置完成")
            return True
        except Exception as e:
            log_output(f"❌ 本地配置失败: {str(e)}")
            return False
    
    def test_connection(self, server_name: str) -> Tuple[bool, str]:
        """测试Server连接"""
        server = self.servers.get(server_name)
        if not server:
            return False, f"Server {server_name} does not exist"
        
        # 根据Server类型选择测试方式
        if server.type == 'script_based':
            return self._test_script_based_connection(server)
        else:
            return self._test_ssh_connection(server)
    
    def _test_ssh_connection(self, server: ServerConfig) -> Tuple[bool, str]:
        """测试SSH连接（原有逻辑）"""
        try:
            # 使用简单的echoCommand测试连接
            ssh_cmd = self._build_ssh_command(server, 'echo "connection_test"')
            
            start_time = time.time()
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=self.global_settings.get('connection_timeout', 30)
            )
            
            connection_time = time.time() - start_time
            
            # 更新连接Status
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
            return False, f"连接Error: {e}"
    
    def _test_script_based_connection(self, server: ServerConfig) -> Tuple[bool, str]:
        """测试script_based连接"""
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        
        try:
            start_time = time.time()
            
            # 检查tmux会话是否存在
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            
            if check_result.returncode == 0:
                # 会话存在，检查连接Status
                log_output(f"🔍 检测会话Status: {session_name}")
                
                # 发送简单测试Command
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
                    log_output("⚠️ 远程会话已断开，重新建立连接...")
                    
                    # 清理旧会话
                    subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                    
                    # 重新建立连接
                    success, msg = self._establish_script_based_connection(server)
                    if success:
                        return True, f"重新连接成功 ({connection_time:.2f}秒) - {msg}"
                    else:
                        return False, f"重新连接失败: {msg}"
                
                elif 'connection_test_' in output:
                    # 更新连接Status
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
                # 会话does not exist，尝试建立连接
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
            # 发送简单的保活Command（不显示输出）
            subprocess.run(['tmux', 'send-keys', '-t', session_name, '# keepalive', 'Enter'],
                         capture_output=True)
        except Exception:
            pass  # 保活失败不影响主要功能
    
    def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """获取ServerStatus"""
        server = self.servers.get(server_name)
        if not server:
            return {'error': f"Server {server_name} does not exist"}
        
        # 执行Status检查Command
        status_commands = [
            ('hostname', 'hostname'),
            ('uptime', 'uptime'),
            ('disk_usage', 'df -h | head -5'),
            ('memory', 'free -h'),
            ('load', 'cat /proc/loadavg'),
        ]
        
        if server.specs and server.specs.get('gpu_count', 0) > 0:
            status_commands.append(('gpu_status', 'nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader'))
        
        # 获取连接Status
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
        
        # 如果连接正常，获取详细Status
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
        """获取Default server"""
        return self.global_settings.get('default_server')
    
    def refresh_all_connections(self) -> Dict[str, bool]:
        """Refresh all server connection status"""
        results = {}
        for server_name in self.servers.keys():
            success, message = self.test_connection(server_name)
            results[server_name] = success
        return results 

    def get_connection_diagnostics(self, server_name: str) -> Dict[str, Any]:
        """获取连接诊断信息和修复建议"""
        server = self.get_server(server_name)
        if not server:
            return {"error": f"Server {server_name} does not exist"}
        
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
        
        # 检查会话Status
        session_check = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True)
        if session_check.returncode != 0:
            result["issues"].append(f"会话 {session_name} does not exist")
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
            result["issues"].append("sshCommand不可用")
            result["suggestions"].append("安装OpenSSH客户端")
            return result
        
        # 检查私钥文件
        if server.private_key_path:
            key_path = Path(server.private_key_path).expanduser()
            if not key_path.exists():
                result["status"] = "error"
                result["issues"].append(f"私钥文件does not exist: {key_path}")
                result["suggestions"].append(f"检查私钥路径或生成新的SSH密钥")
        
        return result

    def print_connection_diagnostics(self, server_name: str):
        """打印连接诊断报告"""
        diagnostics = self.get_connection_diagnostics(server_name)
        
        log_output(f"\n🔍 连接诊断报告: {server_name}")
        log_output("=" * 60)
        
        # 基本信息
        log_output(f"📋 Server类型: {diagnostics.get('server_type', 'N/A')}")
        log_output(f"⏰ 检查时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(diagnostics.get('timestamp', time.time())))}")
        
        # Status
        status = diagnostics.get('status', 'unknown')
        status_emoji = {"healthy": "✅", "warning": "⚠️", "error": "❌", "unknown": "❓"}
        log_output(f"🔋 连接Status: {status_emoji.get(status, '❓')} {status.upper()}")
        
        # 连接信息
        conn_info = diagnostics.get('connection_info', {})
        if conn_info:
            log_output(f"\n📡 连接信息:")
            for key, value in conn_info.items():
                log_output(f"   {key}: {value}")
        
        # 问题列表
        issues = diagnostics.get('issues', [])
        if issues:
            log_output(f"\n❌ 发现问题:")
            for i, issue in enumerate(issues, 1):
                log_output(f"   {i}. {issue}")
        
        # 修复建议
        suggestions = diagnostics.get('suggestions', [])
        if suggestions:
            log_output(f"\n💡 修复建议:")
            for i, suggestion in enumerate(suggestions, 1):
                log_output(f"   {i}. {suggestion}")
        
        # 总结
        if status == "healthy":
            log_output(f"\n🎉 连接Status良好，无需特别处理")
        elif status == "warning":
            log_output(f"\n⚠️ 连接存在轻微问题，建议按照上述建议优化")
        elif status == "error":
            log_output(f"\n🚨 连接存在严重问题，请按照建议修复后重试")
        else:
            log_output(f"\n❓ 连接Status未知，建议手动检查")
        
        log_output("=" * 60)

    def _smart_preconnect(self) -> Dict[str, bool]:
        """智能预连接常用Server"""
        preconnect_servers = self.global_settings.get('preconnect_servers', ['local-dev'])
        preconnect_timeout = self.global_settings.get('preconnect_timeout', 60)
        max_parallel = self.global_settings.get('preconnect_parallel', 3)
        
        log_output(f"🚀 启动智能预连接 ({len(preconnect_servers)}个Server)...")
        
        results = {}
        start_time = time.time()
        
        # 使用线程池进行并行连接
        import concurrent.futures
        
        def connect_server(server_name):
            if server_name not in self.servers:
                return server_name, False, f"Server{server_name}does not exist"
            
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
                    log_output(f"   {status_emoji} {server_name}: {msg} ({elapsed:.1f}s)")
                    
                except Exception as e:
                    results[server_name] = False
                    log_output(f"   ❌ {server_name}: 预连接失败 - {str(e)}")
        
        elapsed_total = time.time() - start_time
        success_count = sum(1 for success in results.values() if success)
        log_output(f"🎯 预Connection completed: {success_count}/{len(preconnect_servers)}个成功 ({elapsed_total:.1f}s)")
        
        return results

    def _show_startup_summary(self, session_result: bool, preconnect_results: Dict[str, bool] = None):
        """显示启动摘要"""
        log_output("\n" + "="*50)
        log_output("🚀 Remote Terminal MCP 已就绪")
        log_output("="*50)
        
        if session_result:
            log_output("✅ 本地开发环境已准备就绪！")
            log_output("   🖥️  tmux会话: dev-session")
            log_output("   📁 工作目录: /Users/xuyehua/Code")
            log_output("")
            log_output("💡 使用tmux会话的方式:")
            log_output("   • 直接连接: tmux attach -t dev-session")
            log_output("   • 查看会话: tmux list-sessions")
            log_output("   • 会话内操作:")
            log_output("     - Ctrl+B, D : 退出会话(保持运行)")
            log_output("     - Ctrl+B, C : 创建新窗口")
            log_output("     - Ctrl+B, N : 切换到下一个窗口")
            log_output("")
            log_output("🔧 或者使用MCP工具:")
            log_output("   • list_tmux_sessions  - 查看所有会话")
            log_output("   • run_command        - 在会话中Execute command")
            log_output("   • create_tmux_session - 创建新会话")
        else:
            log_output("⚠️  本地tmux会话创建失败")
            log_output("   📦 安装tmux以获得完整功能:")
            log_output("      • macOS: brew install tmux")
            log_output("      • Ubuntu: sudo apt install tmux")
        
        # 显示可用Server
        servers = self.list_servers()
        local_servers = [s for s in servers if s['type'] == 'local_tmux']
        remote_servers = [s for s in servers if s['type'] != 'local_tmux']
        
        log_output(f"\n📋 Server配置:")
        if local_servers:
            log_output(f"   ✅ 本地会话: {len(local_servers)}个")
        
        if remote_servers:
            configured = len([s for s in remote_servers if s.get('host')])
            total = len(remote_servers)
            log_output(f"   🌐 远程Server: {configured}/{total}个已配置")
        
        # 显示预连接结果
        if preconnect_results:
            preconnected = sum(1 for success in preconnect_results.values() if success)
            total_preconnect = len(preconnect_results)
            log_output(f"   🚀 预连接Status: {preconnected}/{total_preconnect}个已就绪")
        
        log_output(f"\n🎯 快速开始:")
        log_output("   1️⃣ 立即体验: tmux attach -t dev-session")
        log_output("   2️⃣ 配置远程: nano ~/.remote-terminal-mcp/config.yaml")
        log_output("   3️⃣ MCP工具: 通过Claude使用各种MCP工具")
        log_output("="*50 + "\n")

    def _connect_via_double_jump_host(self, session_name: str, connection_config: dict) -> Tuple[bool, str]:
        """通过双层Jump host连接到目标Server
        
        连接序列:
        1. relay-cli -> shell ready
        2. ssh user@first-jump + password
        3. ssh root@target-server + password
        """
        try:
            first_jump = connection_config.get('first_jump', {})
            second_jump = connection_config.get('second_jump', {})
            
            first_jump_host = first_jump.get('host', '')
            first_jump_password = first_jump.get('password', '')
            second_jump_host = second_jump.get('host', '')
            second_jump_user = second_jump.get('user', 'root')
            second_jump_password = second_jump.get('password', '')
            
            if not first_jump_host or not second_jump_host:
                return False, "双层Jump host配置不完整"
            
            # 步骤1: 等待relay-cli就绪（显示shell提示符）
            log_output(f"   🚀 步骤1: 等待relay-cli就绪 (shell ready)")
            max_wait = 20
            for i in range(max_wait):
                time.sleep(1)
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                debug_log_cmd(capture_cmd, f"检查relayStatus(第{i+1}次)")
                result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                if 'bash-' in result.stdout and '$' in result.stdout:
                    log_output(f"   ✅ relay-cli已就绪")
                    break
            else:
                return False, "等待relay-cli超时"
            
            # 步骤2: 连接第一层Jump host
            log_output(f"   🎯 步骤2: 连接第一层Jump host {first_jump_host}")
            first_ssh_cmd = ['tmux', 'send-keys', '-t', session_name, f'ssh {first_jump_host}', 'Enter']
            debug_log_cmd(first_ssh_cmd, "连接第一层Jump host")
            subprocess.run(first_ssh_cmd, capture_output=True)
            time.sleep(3)
            
            # 检查并输入第一层密码
            log_output(f"   🔐 输入第一层Jump host密码...")
            pwd_cmd = ['tmux', 'send-keys', '-t', session_name, first_jump_password, 'Enter']
            debug_log_cmd(pwd_cmd, "输入第一层密码")
            subprocess.run(pwd_cmd, capture_output=True)
            time.sleep(4)
            
            # 等待第一层连接成功
            log_output(f"   ⏳ 验证第一层Jump host连接...")
            first_jump_user = first_jump_host.split('@')[0] if '@' in first_jump_host else 'yh'
            for i in range(15):
                time.sleep(1)
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                debug_log_cmd(capture_cmd, f"检查第一层连接Status(第{i+1}次)")
                result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                output = result.stdout.lower()
                debug_log_cmd(None, f"第一层连接输出: Output: {result.stdout[-100:]}")
                
                # 检查第一层连接成功标志 - 具体匹配第一层提示符
                first_jump_prompt = f"[{first_jump_user}@"
                if (first_jump_prompt in result.stdout and 
                    ('~]$' in result.stdout or result.stdout.strip().endswith('$'))):
                    log_output(f"   ✅ 第一层Jump host连接成功")
                    time.sleep(1)  # 给系统稳定时间
                    break
                elif 'Permission denied' in result.stdout or 'Authentication failed' in result.stdout:
                    return False, f"第一层Jump host认证失败: {result.stdout[-200:]}"
                elif 'Connection timed out' in result.stdout:
                    return False, f"第一层Jump host连接超时: {result.stdout[-200:]}"
            else:
                # 最后检查一次，可能已经连接但显示有延迟
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                       capture_output=True, text=True)
                if f"[{first_jump_user}@" in result.stdout and '~]$' in result.stdout:
                    log_output(f"   ✅ 第一层Jump host连接成功（延迟检测）")
                else:
                    return False, "第一层Jump host连接超时"
            
            # 步骤3: 从第一层Jump host连接到目标Server
            log_output(f"   🎯 步骤3: 从第一层Jump host连接到目标Server {second_jump_host}")
            second_ssh_cmd = ['tmux', 'send-keys', '-t', session_name, f'ssh {second_jump_user}@{second_jump_host}', 'Enter']
            debug_log_cmd(second_ssh_cmd, "连接目标Server")
            subprocess.run(second_ssh_cmd, capture_output=True)
            time.sleep(4)
            
            # 验证最终连接并处理密码
            for i in range(10):
                time.sleep(2)
                capture_cmd = ['tmux', 'capture-pane', '-t', session_name, '-p']
                debug_log_cmd(capture_cmd, f"检查最终连接Status(第{i+1}次)")
                result = subprocess.run(capture_cmd, capture_output=True, text=True)
                
                output = result.stdout.lower()
                debug_log_cmd(f"Output: {result.stdout[-200:]}", "最终连接输出")
                
                # 检查是否需要输入密码
                if "password:" in output:
                    if second_jump_password:
                        log_output(f"   🔐 输入目标Server密码...")
                        pwd_cmd = ['tmux', 'send-keys', '-t', session_name, second_jump_password, 'Enter']
                        debug_log_cmd(pwd_cmd, "输入目标Server密码")
                        subprocess.run(pwd_cmd, capture_output=True)
                        time.sleep(3)
                        continue
                    else:
                        log_output(f"   ℹ️ 目标Server提示密码但配置为无需密码，等待无密码连接...")
                        time.sleep(2)
                        continue
                
                # 检查连接成功的标志
                if any(indicator in result.stdout for indicator in [f'{second_jump_user}@', '$', '#']) and 'password:' not in output:
                    log_output(f"   ✅ 已成功连接到目标Server: {second_jump_host}")
                    return True, f"通过双层Jump host成功连接到 {second_jump_host}"
                    
                # 检查连接失败的标志
                if any(error in output for error in ['denied', 'failed', 'connection timed out', 'no route to host']):
                    return False, f"目标Server连接失败: {result.stdout[-200:]}"
            
            return False, f"连接目标Server超时: {second_jump_host}"
            
        except Exception as e:
            return False, f"双层Jump host连接失败: {str(e)}"

    def simple_connect(self, server_name: str) -> Tuple[bool, str]:
        """
        一个更简单、更直接的连接方法，绕过复杂的验证。
        """
        server = self.get_server(server_name)
        if not server:
            return False, f"Server {server_name} not found."

        session_name = server.session.get('name', f"{server_name}_session") if server.session else f"{server_name}_session"
        connection_tool = server.specs.get('connection', {}).get('tool', 'ssh') if server.specs else 'ssh'

        try:
            # 1. 清理旧会话
            subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
            log_output(f"🧹 Cleared old session (if any): {session_name}")
            time.sleep(1)

            # 2. 创建新会话并直接启动连接工具
            # 注意：我们把工具直接作为命令传递给新会话
            create_cmd = ['tmux', 'new-session', '-d', '-s', session_name, connection_tool]
            debug_log_cmd(create_cmd, f"Creating new session and running {connection_tool}")
            result = subprocess.run(create_cmd, check=True, capture_output=True, text=True)
            
            log_output(f"🚀 Session {session_name} created and {connection_tool} is starting.")
            log_output("⏳ Please wait a few seconds for the tool to initialize...")
            
            # 3. 提供附加命令给用户
            # 我们不再自动附加，而是告诉用户如何附加，这更可靠
            attach_command = f"tmux attach-session -t {session_name}"
            log_output(f"✅ Connection process started. To attach, run: \\n\\n    {attach_command}\\n")

            return True, f"Connection process for {session_name} started. Please attach manually using: {attach_command}"

        except subprocess.CalledProcessError as e:
            return False, f"Failed to create tmux session for {session_name}: {e.stderr}"
        except Exception as e:
            return False, f"An unexpected error occurred during simple_connect: {str(e)}"

    def _check_if_already_in_target_environment(self, server: ServerConfig) -> Tuple[bool, str]:
        """检测当前是否已经在期待的Docker环境中"""
        try:
            # 获取期待的环境信息
            target_host = server.specs.get('connection', {}).get('target', {}).get('host', server.host)
            expected_container = server.specs.get('docker', {}).get('container_name', '')
            
            log_output(f"   🔍 检测当前环境...")
            log_output(f"   📍 期待主机: {target_host}")
            if expected_container:
                log_output(f"   🐳 期待容器: {expected_container}")
            
            # 执行环境检测命令
            detection_cmd = (
                'echo "ENV_CHECK:$([ -f /.dockerenv ] && echo DOCKER || echo HOST):'
                '$(hostname):$(echo $HOSTNAME):$(whoami)"'
            )
            
            result = subprocess.run(['bash', '-c', detection_cmd], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return False, "环境检测命令执行失败"
            
            output = result.stdout.strip()
            log_output(f"   📊 环境检测结果: {output}")
            
            # 解析检测结果
            if not output.startswith('ENV_CHECK:'):
                return False, "环境检测结果格式异常"
            
            parts = output.split(':')
            if len(parts) < 5:
                return False, "环境检测结果不完整"
            
            is_docker = parts[1] == 'DOCKER'
            current_hostname = parts[2]
            container_hostname = parts[3]
            current_user = parts[4]
            
            log_output(f"   🔍 Docker环境: {'是' if is_docker else '否'}")
            log_output(f"   🔍 当前主机: {current_hostname}")
            log_output(f"   🔍 容器主机: {container_hostname}")
            log_output(f"   🔍 当前用户: {current_user}")
            
            # 检查是否在Docker中
            if not is_docker:
                log_output(f"   ❌ 当前不在Docker容器中")
                return False, "当前不在Docker容器中"
            
            # 检查主机名是否匹配目标服务器
            target_hostname = target_host.split('.')[0].lower()
            if target_hostname not in current_hostname.lower():
                log_output(f"   ❌ 主机名不匹配 (期待: {target_hostname}, 当前: {current_hostname})")
                return False, f"主机名不匹配，当前在 {current_hostname}，期待 {target_hostname}"
            
            # 如果配置了特定容器，检查容器信息
            if expected_container:
                # 检查容器名称或相关环境
                # 注意：容器内的HOSTNAME通常是容器ID，不是容器名
                # 我们可以通过其他方式验证，比如检查特定的环境变量或文件
                log_output(f"   🔍 验证容器环境...")
                
                # 尝试检查Docker容器信息（如果可用）
                container_check_cmd = f'docker ps --format "{{{{.Names}}}}" 2>/dev/null | grep -q "^{expected_container}$" && echo "CONTAINER_FOUND" || echo "CONTAINER_NOT_FOUND"'
                container_result = subprocess.run(['bash', '-c', container_check_cmd], 
                                                capture_output=True, text=True, timeout=3)
                
                if container_result.returncode == 0 and 'CONTAINER_FOUND' in container_result.stdout:
                    log_output(f"   ✅ 确认在期待的容器 {expected_container} 中")
                else:
                    log_output(f"   ⚠️  无法确认具体容器，但Docker环境和主机匹配")
            
            log_output(f"   ✅ 当前已在期待的环境中！")
            return True, f"已在目标环境: {current_hostname} (Docker容器)"
            
        except subprocess.TimeoutExpired:
            return False, "环境检测超时"
        except Exception as e:
            log_output(f"   ❌ 环境检测异常: {str(e)}")
            return False, f"环境检测失败: {str(e)}"

    def _setup_zsh_environment_with_bos(self, session_name: str, bos_config: dict) -> bool:
        """为zsh环境配置BOS并下载配置文件 - 使用bash进行配置然后切换到zsh"""
        try:
            log_output(f"   📦 步骤1: 使用bash配置BOS工具...")
            
            # 检查bcecmd是否存在
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'which bcecmd || echo "BCECMD_NOT_FOUND"', 'Enter'], capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'BCECMD_NOT_FOUND' in result.stdout:
                log_output(f"   ⚠️ bcecmd未找到，跳过BOS配置")
                return False
            
            # 配置BOS
            access_key = bos_config.get('access_key', '')
            secret_key = bos_config.get('secret_key', '')
            
            if not access_key or not secret_key:
                log_output(f"   ⚠️ BOS配置缺少access_key或secret_key")
                return False
            
            # 检查是否为占位符值
            if access_key in ['your_access_key', 'your_real_access_key', 'your_access_key_here']:
                log_output(f"   ⚠️ 检测到占位符AK，跳过自动BOS配置")
                log_output(f"   💡 请在配置中填入真实的BOS凭据")
                return False
            
            log_output(f"   🔑 自动配置BOS认证信息...")
            
            # 创建BOS配置目录
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'mkdir -p ~/.bcecmd', 'Enter'], capture_output=True)
            time.sleep(1)
            
            # 直接创建配置文件而不是使用交互式bcecmd -c
            bos_config_json = f'''{{
  "access_key_id": "{access_key}",
  "secret_access_key": "{secret_key}",
  "region": "bj",
  "domain": "bcebos.com",
  "protocol": "https"
}}'''
            
            # 写入配置文件
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'cat > ~/.bcecmd/config.json << \'EOF\'', 'Enter'], capture_output=True)
            time.sleep(0.5)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          bos_config_json, 'Enter'], capture_output=True)
            time.sleep(0.5)
            
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'EOF', 'Enter'], capture_output=True)
            time.sleep(1)
            
            # 测试BOS连接
            log_output(f"   🔍 测试BOS连接...")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'bcecmd bos ls > /dev/null 2>&1 && echo "BOS_CONNECTION_SUCCESS" || echo "BOS_CONNECTION_FAILED"', 'Enter'], 
                         capture_output=True)
            time.sleep(3)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'BOS_CONNECTION_FAILED' in result.stdout:
                log_output(f"   ❌ BOS连接失败，请检查凭据和网络")
                return False
            elif 'BOS_CONNECTION_SUCCESS' in result.stdout:
                log_output(f"   ✅ BOS连接成功")
            else:
                log_output(f"   ⚠️ BOS连接状态未知，继续尝试下载")
            
            # 下载配置文件
            bucket = bos_config.get('bucket', '')
            config_path = bos_config.get('config_path', '')
            
            if bucket and config_path:
                log_output(f"   📥 步骤2: 从BOS下载zsh配置文件...")
                
                # 下载各个配置文件
                config_files = ['.zshrc', '.p10k.zsh', '.zsh_history']
                download_success = False
                
                for config_file in config_files:
                    bos_source = f"{bucket}/{config_path}/{config_file}"
                    target_path = f"~/{config_file}"
                    
                    download_cmd = f"bcecmd bos cp {bos_source} {target_path}"
                    log_output(f"   📥 下载 {config_file}...")
                    
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  f'{download_cmd} && echo "DOWNLOAD_SUCCESS_{config_file}" || echo "DOWNLOAD_FAILED_{config_file}"', 'Enter'], 
                                 capture_output=True)
                    time.sleep(2)
                    
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    if f'DOWNLOAD_SUCCESS_{config_file}' in result.stdout:
                        log_output(f"   ✅ {config_file} 下载成功")
                        download_success = True
                    else:
                        log_output(f"   ⚠️ {config_file} 下载失败")
                
                if download_success:
                    log_output(f"   ✅ 至少一个配置文件下载成功")
                    
                    # 切换到zsh以应用配置
                    log_output(f"   🔄 步骤3: 切换到zsh并应用配置...")
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                                  'exec zsh', 'Enter'], capture_output=True)
                    time.sleep(3)
                    
                    # 检查zsh是否成功启动
                    result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
                    
                    # 如果看到Powerlevel10k配置向导，自动跳过
                    if 'Powerlevel10k configuration wizard' in result.stdout:
                        log_output(f"   🎨 检测到Powerlevel10k配置向导，自动跳过...")
                        subprocess.run(['tmux', 'send-keys', '-t', session_name, 'q'], capture_output=True)
                        time.sleep(2)
                    
                    log_output(f"   ✅ zsh环境配置完成！")
                    return True
                else:
                    log_output(f"   ❌ 所有配置文件下载失败")
                    return False
            else:
                log_output(f"   ⚠️ BOS配置缺少bucket或config_path")
                return False
                
        except Exception as e:
            log_output(f"   ❌ zsh环境配置失败: {str(e)}")
            return False