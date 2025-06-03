#!/usr/bin/env python3
"""
Remote Terminal MCP Server - 远程终端管理

专注于远程服务器连接、会话管理和命令执行的MCP服务器
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
            debug_log("SSH管理器初始化成功")
        except Exception as e:
            debug_log(f"SSH管理器初始化失败: {e}")
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
    """创建错误响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": error_code,
            "message": error_message
        }
    }

def run_command(cmd, cwd=None, timeout=30):
    """执行命令并返回结果"""
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
            output += f"📤 输出:\n{result.stdout}\n"
        if result.stderr:
            output += f"⚠️ 错误输出:\n{result.stderr}\n"
        
        output += f"🔢 退出码: {result.returncode}"
        
        return output, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return f"⏱️ 命令执行超时 ({timeout}秒)", False
    except Exception as e:
        return f"❌ 命令执行失败: {str(e)}", False

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
                return "🖥️ 当前tmux会话:\n" + '\n'.join(f"  • {session}" for session in sessions)
            else:
                return "📭 没有活动的tmux会话"
        else:
            return "❌ 无法访问tmux (可能未安装或未运行)"
            
    except FileNotFoundError:
        return "❌ tmux未安装"
    except Exception as e:
        return f"❌ 列出tmux会话失败: {str(e)}"

def check_system_info():
    """检查系统信息"""
    info = []
    
    # 操作系统信息
    try:
        import platform
        info.append(f"🖥️ 系统: {platform.system()} {platform.release()}")
        info.append(f"🏷️ 主机名: {platform.node()}")
        info.append(f"⚙️ 架构: {platform.machine()}")
    except Exception as e:
        info.append(f"❌ 无法获取系统信息: {e}")
    
    # 当前目录
    try:
        cwd = os.getcwd()
        info.append(f"📁 当前目录: {cwd}")
    except Exception as e:
        info.append(f"❌ 无法获取当前目录: {e}")
    
    # 用户信息
    try:
        import getpass
        user = getpass.getuser()
        info.append(f"👤 当前用户: {user}")
    except Exception as e:
        info.append(f"❌ 无法获取用户信息: {e}")
    
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
                        "description": "获取系统信息和当前状态",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "run_command",
                        "description": "执行本地命令",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "要执行的命令"
                                },
                                "working_directory": {
                                    "type": "string",
                                    "description": "执行命令的工作目录"
                                },
                                "timeout": {
                                    "type": "integer",
                                    "description": "命令超时时间（秒）",
                                    "default": 30
                                }
                            },
                            "required": ["command"]
                        }
                    },
                    {
                        "name": "list_tmux_sessions",
                        "description": "列出当前的tmux会话",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "create_tmux_session",
                        "description": "创建新的tmux会话",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_name": {
                                    "type": "string",
                                    "description": "会话名称"
                                },
                                "working_directory": {
                                    "type": "string",
                                    "description": "会话的工作目录"
                                }
                            },
                            "required": ["session_name"]
                        }
                    },
                    {
                        "name": "list_directory",
                        "description": "列出目录内容",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "要列出的目录路径",
                                    "default": "."
                                },
                                "show_hidden": {
                                    "type": "boolean",
                                    "description": "是否显示隐藏文件",
                                    "default": False
                                }
                            }
                        }
                    },
                    {
                        "name": "list_remote_servers",
                        "description": "列出所有配置的远程服务器",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "test_server_connection",
                        "description": "测试远程服务器连接",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "要测试的服务器名称"
                                }
                            },
                            "required": ["server_name"]
                        }
                    },
                    {
                        "name": "execute_remote_command",
                        "description": "在远程服务器上执行命令",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "目标服务器名称"
                                },
                                "command": {
                                    "type": "string",
                                    "description": "要执行的命令"
                                }
                            },
                            "required": ["server_name", "command"]
                        }
                    },
                    {
                        "name": "get_server_status",
                        "description": "获取远程服务器状态信息",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "server_name": {
                                    "type": "string",
                                    "description": "服务器名称"
                                }
                            },
                            "required": ["server_name"]
                        }
                    },
                    {
                        "name": "refresh_server_connections",
                        "description": "刷新所有服务器连接状态",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
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
                return create_error_response(request_id, f"获取系统信息失败: {str(e)}")
        
        elif tool_name == "run_command":
            try:
                command = arguments.get("command", "")
                working_directory = arguments.get("working_directory")
                timeout = arguments.get("timeout", 30)
                
                if not command:
                    return create_error_response(request_id, "命令不能为空")
                
                output, success = run_command(command, working_directory, timeout)
                
                result_text = f"🔧 执行命令: {command}\n"
                if working_directory:
                    result_text += f"📁 工作目录: {working_directory}\n"
                result_text += f"\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in run_command: {e}")
                return create_error_response(request_id, f"命令执行失败: {str(e)}")
        
        elif tool_name == "list_tmux_sessions":
            try:
                sessions = list_tmux_sessions()
                return create_success_response(request_id, sessions)
            except Exception as e:
                debug_log(f"Error in list_tmux_sessions: {e}")
                return create_error_response(request_id, f"列出tmux会话失败: {str(e)}")
        
        elif tool_name == "create_tmux_session":
            try:
                session_name = arguments.get("session_name", "")
                working_directory = arguments.get("working_directory", "")
                
                if not session_name:
                    return create_error_response(request_id, "会话名称不能为空")
                
                # 构建tmux命令
                cmd = f"tmux new-session -d -s '{session_name}'"
                if working_directory:
                    cmd += f" -c '{working_directory}'"
                
                output, success = run_command(cmd)
                
                if success:
                    result_text = f"✅ 成功创建tmux会话: {session_name}\n"
                    if working_directory:
                        result_text += f"📁 工作目录: {working_directory}\n"
                    result_text += f"\n💡 使用 'tmux attach -t {session_name}' 连接到会话"
                else:
                    result_text = f"❌ 创建tmux会话失败:\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in create_tmux_session: {e}")
                return create_error_response(request_id, f"创建tmux会话失败: {str(e)}")
        
        elif tool_name == "list_directory":
            try:
                path = arguments.get("path", ".")
                show_hidden = arguments.get("show_hidden", False)
                
                # 构建ls命令
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
                return create_error_response(request_id, f"列出目录失败: {str(e)}")
        
        elif tool_name == "list_remote_servers":
            try:
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH管理器初始化失败，请检查配置文件")
                
                servers = manager.list_servers()
                if not servers:
                    return create_success_response(request_id, "📭 没有配置任何远程服务器\n\n💡 请运行 ./scripts/init-config.sh 初始化配置")
                
                result_text = f"🖥️ 配置的远程服务器 ({len(servers)}个):\n\n"
                
                for server in servers:
                    status_icon = "🟢" if server['connected'] else "🔴"
                    result_text += f"{status_icon} **{server['name']}** ({server['type']})\n"
                    result_text += f"   📍 地址: {server['host']}\n"
                    result_text += f"   📝 描述: {server['description']}\n"
                    
                    if server.get('jump_host'):
                        result_text += f"   🔗 跳板机: {server['jump_host']}\n"
                    
                    specs = server.get('specs', {})
                    if specs:
                        if specs.get('gpu_count', 0) > 0:
                            result_text += f"   🎮 GPU: {specs['gpu_count']}x {specs.get('gpu_type', 'Unknown')}\n"
                        result_text += f"   💾 内存: {specs.get('memory', 'Unknown')}\n"
                    
                    if server['last_check'] > 0:
                        import datetime
                        check_time = datetime.datetime.fromtimestamp(server['last_check'])
                        result_text += f"   ⏰ 上次检查: {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                    result_text += "\n"
                
                default_server = manager.get_default_server()
                if default_server:
                    result_text += f"🌟 默认服务器: {default_server}\n"
                
                result_text += "\n💡 使用 'test_server_connection' 测试连接状态"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in list_remote_servers: {e}")
                return create_error_response(request_id, f"列出远程服务器失败: {str(e)}")
        
        elif tool_name == "test_server_connection":
            try:
                server_name = arguments.get("server_name", "")
                if not server_name:
                    return create_error_response(request_id, "服务器名称不能为空")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH管理器初始化失败，请检查配置文件")
                
                success, message = manager.test_connection(server_name)
                
                if success:
                    result_text = f"✅ 服务器连接测试成功\n\n"
                    result_text += f"🖥️ 服务器: {server_name}\n"
                    result_text += f"📶 状态: {message}\n"
                    result_text += f"🔗 连接正常，可以执行远程命令"
                else:
                    result_text = f"❌ 服务器连接测试失败\n\n"
                    result_text += f"🖥️ 服务器: {server_name}\n"
                    result_text += f"⚠️ 错误: {message}\n"
                    result_text += f"\n💡 请检查:\n"
                    result_text += f"   • 服务器地址和端口\n"
                    result_text += f"   • SSH密钥配置\n"
                    result_text += f"   • 网络连接\n"
                    result_text += f"   • 服务器是否在线"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in test_server_connection: {e}")
                return create_error_response(request_id, f"测试服务器连接失败: {str(e)}")
        
        elif tool_name == "execute_remote_command":
            try:
                server_name = arguments.get("server_name", "")
                command = arguments.get("command", "")
                
                if not server_name:
                    return create_error_response(request_id, "服务器名称不能为空")
                if not command:
                    return create_error_response(request_id, "命令不能为空")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH管理器初始化失败，请检查配置文件")
                
                success, output = manager.execute_command(server_name, command)
                
                result_text = f"🔧 在远程服务器 **{server_name}** 执行命令\n"
                result_text += f"📝 命令: `{command}`\n\n"
                
                if success:
                    result_text += f"✅ 执行成功\n\n{output}"
                else:
                    result_text += f"❌ 执行失败\n\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in execute_remote_command: {e}")
                return create_error_response(request_id, f"执行远程命令失败: {str(e)}")
        
        elif tool_name == "get_server_status":
            try:
                server_name = arguments.get("server_name", "")
                if not server_name:
                    return create_error_response(request_id, "服务器名称不能为空")
                
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH管理器初始化失败，请检查配置文件")
                
                status = manager.get_server_status(server_name)
                
                if 'error' in status:
                    return create_error_response(request_id, status['error'])
                
                result_text = f"🖥️ 服务器状态: **{server_name}**\n\n"
                result_text += f"📍 地址: {status['host']}\n"
                result_text += f"📝 描述: {status['description']}\n"
                
                # 显示服务器规格
                specs = status.get('specs', {})
                if specs:
                    result_text += f"\n🔧 硬件配置:\n"
                    if specs.get('cpu_cores'):
                        result_text += f"   🖥️ CPU: {specs['cpu_cores']} 核心\n"
                    if specs.get('memory'):
                        result_text += f"   💾 内存: {specs['memory']}\n"
                    if specs.get('gpu_count', 0) > 0:
                        result_text += f"   🎮 GPU: {specs['gpu_count']}x {specs.get('gpu_type', 'Unknown')}\n"
                
                # 显示连接状态
                status_icon = "🟢" if status['connected'] else "🔴"
                result_text += f"\n📶 连接状态: {status_icon} {'在线' if status['connected'] else '离线'}\n"
                
                if status['last_check'] > 0:
                    import datetime
                    check_time = datetime.datetime.fromtimestamp(status['last_check'])
                    result_text += f"⏰ 上次检查: {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
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
                        result_text += f"   💾 内存使用:\n{info['memory']}\n"
                    
                    if 'disk_usage' in info:
                        result_text += f"   💿 磁盘使用:\n{info['disk_usage']}\n"
                    
                    if 'gpu_status' in info:
                        result_text += f"   🎮 GPU状态:\n{info['gpu_status']}\n"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in get_server_status: {e}")
                return create_error_response(request_id, f"获取服务器状态失败: {str(e)}")
        
        elif tool_name == "refresh_server_connections":
            try:
                manager = get_ssh_manager()
                if not manager:
                    return create_error_response(request_id, "SSH管理器初始化失败，请检查配置文件")
                
                results = manager.refresh_all_connections()
                
                if not results:
                    return create_success_response(request_id, "📭 没有配置任何服务器")
                
                result_text = f"🔄 刷新所有服务器连接状态\n\n"
                
                online_count = sum(1 for success in results.values() if success)
                total_count = len(results)
                
                result_text += f"📊 总计: {online_count}/{total_count} 服务器在线\n\n"
                
                for server_name, success in results.items():
                    status_icon = "🟢" if success else "🔴"
                    status_text = "在线" if success else "离线"
                    result_text += f"{status_icon} {server_name}: {status_text}\n"
                
                result_text += f"\n⏰ 刷新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in refresh_server_connections: {e}")
                return create_error_response(request_id, f"刷新服务器连接失败: {str(e)}")
        
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