#!/usr/bin/env python3
"""
Remote Terminal MCP Server

MCP server focused on remote server connections, session management and command execution
"""

import asyncio
import json
import sys
import os
import subprocess
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'

from ssh_manager import SSHManager

# 调试模式
DEBUG = os.getenv('MCP_DEBUG') == '1'

# 初始化SSH管理器
ssh_manager = None

def get_ssh_manager():
    """获取SSH管理器实例"""
    global ssh_manager
    if ssh_manager is None:
        try:
            ssh_manager = SSHManager()
            debug_log("SSH manager initialized successfully")
        except Exception as e:
            debug_log(f"SSH manager initialization failed: {e}")
            ssh_manager = None
    return ssh_manager

def debug_log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

def create_success_response(request_id, text_content):
    """创建成功响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": text_content
                }
            ]
        }
    }

def create_error_response(request_id, error_message, error_code=-32603):
    """创建Error响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": error_code,
            "message": error_message
        }
    }

def run_command(cmd, cwd=None, timeout=30):
    """Execute command并返回结果"""
    try:
        debug_log(f"Running command: {cmd}")
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=cwd
        )
        
        output = ""
        if result.stdout:
            output += f"Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Error output:\n{result.stderr}\n"
        
        output += f"Exit code: {result.returncode}"
        
        return output, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return f"Command execution timeout ({timeout}s)", False
    except Exception as e:
        return f"Command execution failed: {str(e)}", False

def list_tmux_sessions():
    """列出tmux会话"""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            sessions = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    sessions.append(line)
            
            if sessions:
                return "Current tmux sessions:\n" + '\n'.join(f"  • {session}" for session in sessions)
            else:
                return "No active tmux sessions"
        else:
            return "Cannot access tmux (not installed or not running)"
            
    except FileNotFoundError:
        return "tmux not installed"
    except Exception as e:
        return f"Failed to list tmux sessions: {str(e)}"

def check_system_info():
    """检查系统信息"""
    info = []
    
    # 操作系统信息
    try:
        import platform
        info.append(f"System: {platform.system()} {platform.release()}")
        info.append(f"Hostname: {platform.node()}")
        info.append(f"Architecture: {platform.machine()}")
    except Exception as e:
        info.append(f"Cannot get system info: {e}")
    
    # 当前目录
    try:
        cwd = os.getcwd()
        info.append(f"Current directory: {cwd}")
    except Exception as e:
        info.append(f"Cannot get current directory: {e}")
    
    # 用户信息
    try:
        import getpass
        user = getpass.getuser()
        info.append(f"Current user: {user}")
    except Exception as e:
        info.append(f"Cannot get user info: {e}")
    
    return "\n".join(info)

async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method", "")
    request_id = request.get("id")
    
    debug_log(f"Received method: {method}, id: {request_id}")
    
    # 如果没有id，这是一个通知，不需要响应
    if request_id is None:
        debug_log(f"Received notification: {method}, no response needed")
        if method.startswith("notifications/"):
            debug_log(f"Handling notification: {method}")
        return None
    
    # 处理需要响应的请求
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {
                    "name": "remote-terminal-mcp",
                    "version": "0.2.0"
                }
            }
        }
        debug_log(f"Initialize response: {json.dumps(response)}")
        return response
        
    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "system_info",
                        "description": "Get system information and current status",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "run_command",
                        "description": "Execute local command",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "Command to execute"
                                },
                                "working_directory": {
                                    "type": "string",
                                    "description": "Working directory for command execution"
                                },
                                "timeout": {
                                    "type": "integer",
                                    "description": "Command timeout in seconds",
                                    "default": 30
                                }
                            },
                            "required": ["command"]
                        }
                    },
                    {
                        "name": "list_tmux_sessions",
                        "description": "List current tmux sessions",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "create_tmux_session",
                        "description": "Create new tmux session",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_name": {
                                    "type": "string",
                                    "description": "Session name"
                                },
                                "working_directory": {
                                    "type": "string",
                                    "description": "Working directory for session"
                                }
                            },
                            "required": ["session_name"]
                        }
                    },
                    {
                        "name": "list_directory",
                        "description": "List directory contents",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Directory path to list",
                                    "default": "."
                                },
                                "show_hidden": {
                                    "type": "boolean",
                                    "description": "Whether to show hidden files",
                                    "default": False
                                }
                            }
                        }
                    },
                    {
                        "name": "list_remote_servers",
                        "description": "List all configured remote servers",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "test_server_connection",
                        "description": "Test remote server connection",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "Server name to test"
                                }
                            },
                            "required": ["server_name"]
                        }
                    },
                    {
                        "name": "execute_remote_command",
                        "description": "Execute command on remote server",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "Target server name"
                                },
                                "command": {
                                    "type": "string",
                                    "description": "Command to execute"
                                }
                            },
                            "required": ["server_name", "command"]
                        }
                    },
                    {
                        "name": "get_server_status",
                        "description": "Get remote server status information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "Server name"
                                }
                            },
                            "required": ["server_name"]
                        }
                    },
                    {
                        "name": "refresh_server_connections",
                        "description": "Refresh all server connection status",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "establish_connection",
                        "description": "Establish full connection to remote server with configuration diagnosis, error reporting and intelligent session management",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "Server name to connect to"
                                },
                                "force_recreate": {
                                    "type": "boolean",
                                    "description": "Force recreate session even if exists",
                                    "default": False
                                },
                                "debug_mode": {
                                    "type": "boolean", 
                                    "description": "Enable debug mode to preserve failed sessions for diagnosis",
                                    "default": True
                                }
                            },
                            "required": ["server_name"]
                        }
                    }
                ]
            }
        }
        debug_log(f"Tools list response: {json.dumps(response)}")
        return response
        
    elif method == "tools/call":
        # 处理工具调用
        tool_name = request.get("params", {}).get("name", "")
        arguments = request.get("params", {}).get("arguments", {})
        
        debug_log(f"Tool call: {tool_name}, arguments: {arguments}")
        
        if tool_name == "system_info":
            try:
                info = check_system_info()
                return create_success_response(request_id, info)
            except Exception as e:
                debug_log(f"Error in system_info: {e}")
                return create_error_response(request_id, f"Failed to get system info: {str(e)}")
        
        elif tool_name == "run_command":
            try:
                command = arguments.get("command", "")
                working_directory = arguments.get("working_directory")
                timeout = arguments.get("timeout", 30)
                
                if not command:
                    return create_error_response(request_id, "Command cannot be empty")
                
                output, success = run_command(command, working_directory, timeout)
                
                result_text = f"Command: {command}\n"
                if working_directory:
                    result_text += f"Working directory: {working_directory}\n"
                result_text += f"\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in run_command: {e}")
                return create_error_response(request_id, f"Command execution failed: {str(e)}")
        
        elif tool_name == "list_tmux_sessions":
            try:
                sessions = list_tmux_sessions()
                return create_success_response(request_id, sessions)
            except Exception as e:
                debug_log(f"Error in list_tmux_sessions: {e}")
                return create_error_response(request_id, f"Failed to list tmux sessions: {str(e)}")
        
        elif tool_name == "create_tmux_session":
            try:
                session_name = arguments.get("session_name", "")
                working_directory = arguments.get("working_directory", "")
                
                if not session_name:
                    return create_error_response(request_id, "Session name cannot be empty")
                
                # 构建tmuxCommand
                cmd = f"tmux new-session -d -s '{session_name}'"
                if working_directory:
                    cmd += f" -c '{working_directory}'"
                
                output, success = run_command(cmd)
                
                if success:
                    result_text = f"Successfully created tmux session: {session_name}\n"
                    if working_directory:
                        result_text += f"Working directory: {working_directory}\n"
                    result_text += f"\nUse 'tmux attach -t {session_name}' to connect to session"
                else:
                    result_text = f"Failed to create tmux session:\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in create_tmux_session: {e}")
                return create_error_response(request_id, f"Failed to create tmux session: {str(e)}")
        
        elif tool_name == "list_directory":
            try:
                path = arguments.get("path", ".")
                show_hidden = arguments.get("show_hidden", False)
                
                # 构建lsCommand
                cmd = "ls -la" if show_hidden else "ls -l"
                cmd += f" '{path}'"
                
                output, success = run_command(cmd)
                
                if success:
                    result_text = f"📁 目录内容: {path}\n\n{output}"
                else:
                    result_text = f"❌ 无法列出目录内容:\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in list_directory: {e}")
                return create_error_response(request_id, f"Failed to list directory: {str(e)}")
        
        elif tool_name == "list_remote_servers":
            try:
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH manager initialization failed, please check configuration file")
                
                servers = manager.list_servers()
                if not servers:
                    return create_success_response(request_id, "📭 No remote servers configured\n\n💡 Please run ./scripts/init-config.sh to initialize configuration")
                
                result_text = f"🖥️ Configured remote servers ({len(servers)}个):\n\n"
                
                for server in servers:
                    status_icon = "🟢" if server['connected'] else "🔴"
                    result_text += f"{status_icon} **{server['name']}** ({server['type']})\n"
                    result_text += f"   📍 Address: {server['host']}\n"
                    result_text += f"   📝 Description: {server['description']}\n"
                    
                    if server.get('jump_host'):
                        result_text += f"   🔗 Jump host: {server['jump_host']}\n"
                    
                    specs = server.get('specs', {})
                    if specs:
                        if specs.get('gpu_count', 0) > 0:
                            result_text += f"   🎮 GPU: {specs['gpu_count']}x {specs.get('gpu_type', 'Unknown')}\n"
                        result_text += f"   💾 Memory: {specs.get('memory', 'Unknown')}\n"
                    
                    if server['last_check'] > 0:
                        import datetime
                        check_time = datetime.datetime.fromtimestamp(server['last_check'])
                        result_text += f"   ⏰ Last check: {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                    result_text += "\n"
                
                default_server = manager.get_default_server()
                if default_server:
                    result_text += f"🌟 Default server: {default_server}\n"
                
                result_text += "\n💡 Use 'test_server_connection' to test connection status"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in list_remote_servers: {e}")
                return create_error_response(request_id, f"Failed to list remote servers: {str(e)}")
        
        elif tool_name == "test_server_connection":
            try:
                server_name = arguments.get("server_name", "")
                if not server_name:
                    return create_error_response(request_id, "Server name不能为空")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH manager initialization failed, please check configuration file")
                
                success, message = manager.test_connection(server_name)
                
                if success:
                    result_text = f"✅ Server connection test successful\n\n"
                    result_text += f"🖥️ Server: {server_name}\n"
                    result_text += f"📶 Status: {message}\n"
                    result_text += f"🔗 Connection normal, can execute remote commands"
                else:
                    result_text = f"❌ Server连接测试失败\n\n"
                    result_text += f"🖥️ Server: {server_name}\n"
                    result_text += f"⚠️ Error: {message}\n"
                    result_text += f"\n💡 Please check:\n"
                    result_text += f"   • ServerAddress和端口\n"
                    result_text += f"   • SSH key configuration\n"
                    result_text += f"   • Network connection\n"
                    result_text += f"   • Server是否Online"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in test_server_connection: {e}")
                return create_error_response(request_id, f"测试Server连接失败: {str(e)}")
        
        elif tool_name == "execute_remote_command":
            try:
                server_name = arguments.get("server_name", "")
                command = arguments.get("command", "")
                
                if not server_name:
                    return create_error_response(request_id, "Server name不能为空")
                if not command:
                    return create_error_response(request_id, "Command cannot be empty")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH manager initialization failed, please check configuration file")
                
                success, output = manager.execute_command(server_name, command)
                
                result_text = f"🔧 在远程Server **{server_name}** Execute command\n"
                result_text += f"📝 Command: `{command}`\n\n"
                
                if success:
                    result_text += f"✅ Execution successful\n\n{output}"
                else:
                    result_text += f"❌ Execution failed\n\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in execute_remote_command: {e}")
                return create_error_response(request_id, f"Failed to execute remote command: {str(e)}")
        
        elif tool_name == "get_server_status":
            try:
                server_name = arguments.get("server_name", "")
                if not server_name:
                    return create_error_response(request_id, "Server name不能为空")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH manager initialization failed, please check configuration file")
                
                status = manager.get_server_status(server_name)
                
                if 'error' in status:
                    return create_error_response(request_id, status['error'])
                
                result_text = f"🖥️ ServerStatus: **{server_name}**\n\n"
                result_text += f"📍 Address: {status['host']}\n"
                result_text += f"📝 Description: {status['description']}\n"
                
                # 显示Server规格
                specs = status.get('specs', {})
                if specs:
                    result_text += f"\n🔧 硬件配置:\n"
                    if specs.get('cpu_cores'):
                        result_text += f"   🖥️ CPU: {specs['cpu_cores']} 核心\n"
                    if specs.get('memory'):
                        result_text += f"   💾 Memory: {specs['memory']}\n"
                    if specs.get('gpu_count', 0) > 0:
                        result_text += f"   🎮 GPU: {specs['gpu_count']}x {specs.get('gpu_type', 'Unknown')}\n"
                
                # 显示连接Status
                status_icon = "🟢" if status['connected'] else "🔴"
                result_text += f"\n📶 连接Status: {status_icon} {'Online' if status['connected'] else 'Offline'}\n"
                
                if status['last_check'] > 0:
                    import datetime
                    check_time = datetime.datetime.fromtimestamp(status['last_check'])
                    result_text += f"⏰ Last check: {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                # 显示详细信息
                info = status.get('info', {})
                if info:
                    result_text += f"\n📊 系统信息:\n"
                    
                    if 'hostname' in info:
                        result_text += f"   🏷️ 主机名: {info['hostname']}\n"
                    
                    if 'uptime' in info:
                        result_text += f"   ⏱️ 运行时间: {info['uptime']}\n"
                    
                    if 'load' in info:
                        result_text += f"   📈 系统负载: {info['load']}\n"
                    
                    if 'memory' in info:
                        result_text += f"   💾 Memory使用:\n{info['memory']}\n"
                    
                    if 'disk_usage' in info:
                        result_text += f"   💿 磁盘使用:\n{info['disk_usage']}\n"
                    
                    if 'gpu_status' in info:
                        result_text += f"   🎮 GPUStatus:\n{info['gpu_status']}\n"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in get_server_status: {e}")
                return create_error_response(request_id, f"获取ServerStatus失败: {str(e)}")
        
        elif tool_name == "refresh_server_connections":
            try:
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH manager initialization failed, please check configuration file")
                
                results = manager.refresh_all_connections()
                
                if not results:
                    return create_success_response(request_id, "📭 没有配置任何Server")
                
                result_text = f"🔄 Refresh all server connection status\n\n"
                
                online_count = sum(1 for success in results.values() if success)
                total_count = len(results)
                
                result_text += f"📊 Total: {online_count}/{total_count} ServerOnline\n\n"
                
                for server_name, success in results.items():
                    status_icon = "🟢" if success else "🔴"
                    status_text = "Online" if success else "Offline"
                    result_text += f"{status_icon} {server_name}: {status_text}\n"
                
                result_text += f"\n⏰ 刷新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in refresh_server_connections: {e}")
                return create_error_response(request_id, f"刷新Server连接失败: {str(e)}")
        
        elif tool_name == "establish_connection":
            try:
                server_name = arguments.get("server_name", "")
                force_recreate = arguments.get("force_recreate", False)
                debug_mode = arguments.get("debug_mode", True)
                
                if not server_name:
                    return create_error_response(request_id, "Server name不能为空")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH manager initialization failed, please check configuration file")
                
                # 获取Server配置
                server = manager.get_server(server_name)
                if not server:
                    available_servers = [s['name'] for s in manager.list_servers()]
                    return create_error_response(request_id, 
                        f"Server '{server_name}' does not exist\n\n"
                        f"可用Server: {', '.join(available_servers) if available_servers else '无'}\n\n"
                        f"💡 Please check配置文件: ~/.remote-terminal-mcp/config.yaml")
                
                result_text = f"🚀 建立连接到Server: **{server_name}**\n\n"
                
                # 步骤1: 配置验证
                result_text += "🔍 **步骤1: 配置验证**\n"
                config_issues = []
                
                # 验证必要的配置字段
                if server.type == "script_based":
                    if not server.specs:
                        config_issues.append("缺少specs配置")
                    else:
                        connection_config = server.specs.get('connection', {})
                        if not connection_config:
                            config_issues.append("缺少connection配置")
                        else:
                            # 验证Jump host配置
                            if connection_config.get('mode') == 'jump_host':
                                jump_host = connection_config.get('jump_host', {})
                                if not jump_host.get('host'):
                                    config_issues.append("Jump host配置缺少host")
                                if not jump_host.get('password'):
                                    config_issues.append("Jump host配置缺少password")
                            
                            # 验证目标Server配置
                            target_config = connection_config.get('target', {})
                            if not target_config.get('host'):
                                config_issues.append("目标Server配置缺少host")
                
                if config_issues:
                    result_text += f"❌ Configuration validation failed\n"
                    for issue in config_issues:
                        result_text += f"   • {issue}\n"
                    result_text += f"\n🔧 **修复建议**:\n"
                    result_text += f"编辑配置文件: ~/.remote-terminal-mcp/config.yaml\n"
                    result_text += f"在 servers.{server_name} 下添加缺失的配置项\n"
                    return create_error_response(request_id, result_text)
                
                result_text += "✅ 配置验证通过\n\n"
                
                # 步骤2: Session管理
                result_text += "📋 **步骤2: Session管理**\n"
                session_name = server.session.name if server.session else f"{server_name}_dev"
                
                # 检查现有session
                session_exists = False
                try:
                    check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                                capture_output=True)
                    session_exists = (check_result.returncode == 0)
                except:
                    pass
                
                if session_exists:
                    if force_recreate:
                        result_text += f"🔄 强制重建session: {session_name}\n"
                        subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                        session_exists = False
                    else:
                        result_text += f"♻️ 检测到现有session: {session_name}\n"
                        # 检查sessionStatus
                        try:
                            pane_content = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'], 
                                                        capture_output=True, text=True)
                            if pane_content.returncode == 0:
                                # 简单检查是否看起来像是活跃连接
                                content = pane_content.stdout.lower()
                                if any(indicator in content for indicator in ['@', '$', '#', 'login', 'welcome']):
                                    result_text += f"✅ Session connection status good, use existing session directly\n"
                                    result_text += f"\n🎯 **Connection completed**\n"
                                    result_text += f"使用Command连接: `tmux attach -t {session_name}`\n"
                                    return create_success_response(request_id, result_text)
                                else:
                                    result_text += f"⚠️ Session exists but connection status unknown, will re-establish connection\n"
                        except:
                            result_text += f"⚠️ Cannot check session status, will re-establish connection\n"
                
                # Step 3: Establish connection
                result_text += "\n🔗 **Step 3: Establish connection**\n"
                
                try:
                    success, connection_message = manager._establish_script_based_connection(server)
                    
                    if success:
                        result_text += f"✅ Connection established successfully\n"
                        result_text += f"📝 详情: {connection_message}\n"
                        result_text += f"\n🎯 **Connection completed**\n"
                        result_text += f"使用Command连接: `tmux attach -t {session_name}`\n"
                        
                        # 提供快速Command
                        result_text += f"\n💡 **快速操作**:\n"
                        result_text += f"• 连接session: `tmux attach -t {session_name}`\n"
                        result_text += f"• 分离session: Ctrl+B, 然后按 D\n"
                        result_text += f"• 查看所有session: `tmux list-sessions`\n"
                        
                    else:
                        # 连接失败处理
                        result_text += f"❌ 连接建立失败\n"
                        result_text += f"📝 Error详情: {connection_message}\n"
                        
                        # 智能Error诊断
                        result_text += f"\n🔧 **Error诊断和修复建议**:\n"
                        
                        if "connection timed out" in connection_message.lower():
                            result_text += f"• Network connection超时 - 检查Network connection和ServerAddress\n"
                            result_text += f"• 如果使用Jump host，验证Jump hostAddress是否正确\n"
                        elif "permission denied" in connection_message.lower():
                            result_text += f"• 认证失败 - 检查用户名和密码是否正确\n"
                            result_text += f"• 验证SSH key configuration\n"
                        elif "host unreachable" in connection_message.lower():
                            result_text += f"• 主机不可达 - 检查Network connection和IPAddress\n"
                        else:
                            result_text += f"• 检查Server配置文件\n"
                            result_text += f"• 验证Network connection和认证信息\n"
                            result_text += f"• 检查目标Server是否运行\n"
                        
                        # Session处理策略
                        if debug_mode:
                            # 重命名失败的session用于调试
                            debug_session_name = f"{session_name}_debug_{int(time.time())}"
                            try:
                                subprocess.run(['tmux', 'rename-session', '-t', session_name, debug_session_name], 
                                             capture_output=True)
                                result_text += f"\n🐛 **调试模式**:\n"
                                result_text += f"失败的session已重命名为: `{debug_session_name}`\n"
                                result_text += f"使用 `tmux attach -t {debug_session_name}` 查看现场\n"
                                result_text += f"调试完成后使用 `tmux kill-session -t {debug_session_name}` 清理\n"
                            except:
                                result_text += f"\n⚠️ 无法重命名debug session\n"
                        else:
                            # 直接删除失败的session
                            try:
                                subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                                result_text += f"\n🧹 失败的session已清理\n"
                            except:
                                pass
                        
                        return create_error_response(request_id, result_text)
                
                except Exception as e:
                    error_message = str(e)
                    result_text += f"❌ 连接过程异常\n"
                    result_text += f"📝 异常详情: {error_message}\n"
                    
                    result_text += f"\n🔧 **异常处理建议**:\n"
                    result_text += f"• 检查SSH管理器配置\n"
                    result_text += f"• 验证Server配置完整性\n"
                    result_text += f"• 重启MCPServer\n"
                    
                    if debug_mode and session_exists:
                        debug_session_name = f"{session_name}_error_{int(time.time())}"
                        try:
                            subprocess.run(['tmux', 'rename-session', '-t', session_name, debug_session_name], 
                                         capture_output=True)
                            result_text += f"\n🐛 异常session已保留为: `{debug_session_name}`\n"
                        except:
                            pass
                    
                    return create_error_response(request_id, result_text)
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in establish_connection: {e}")
                return create_error_response(request_id, f"建立连接失败: {str(e)}")
        
        else:
            return create_error_response(request_id, f"未知工具: {tool_name}", -32601)
            
    else:
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Method not supported"
            }
        }
        debug_log(f"Error response: {json.dumps(response)}")
        return response

async def main():
    """主函数"""
    debug_log("Starting Remote Terminal MCP server...")
    
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                debug_log("No more input, exiting...")
                break
            
            if line.strip():
                debug_log(f"Received input: {line.strip()}")
                request = json.loads(line.strip())
                response = await handle_request(request)
                
                # 只有当有响应时才输出
                if response is not None:
                    output = json.dumps(response)
                    debug_log(f"Sending output: {output}")
                    print(output, flush=True)
                
        except Exception as e:
            debug_log(f"Error processing request: {e}")
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Received interrupt, exiting...")
        pass