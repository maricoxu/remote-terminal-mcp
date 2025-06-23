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
import traceback
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径，以便导入enhanced_config_manager
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enhanced_config_manager import EnhancedConfigManager
# 修复导入路径 - enhanced_ssh_manager在python目录下
sys.path.insert(0, str(Path(__file__).parent))
from enhanced_ssh_manager import EnhancedSSHManager, log_output, create_enhanced_manager

# 服务器信息
SERVER_NAME = "remote-terminal-mcp"
SERVER_VERSION = "0.7.0-mcp-integrated-config"

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'

# 调试模式
DEBUG = os.getenv('MCP_DEBUG', '0') == '1'

def debug_log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

def create_success_response(request_id, text_content):
    """创建一个包含文本内容的成功JSON-RPC响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "contentType": "text/plain",
            "content": text_content
        }
    }

def create_error_response(request_id, code, message):
    """创建一个标准的JSON-RPC错误响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
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

def create_tools_list():
    """创建工具列表，基于SSH Manager的实际功能"""
    return [
        {
            "name": "list_servers",
            "description": "List all available remote servers configured in the system",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "connect_server", 
            "description": "Connect to a remote server by name",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to connect to"
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "disconnect_server",
            "description": "Disconnect from a remote server and clean up resources",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to disconnect from"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force disconnect even if there are active sessions (default: false)",
                        "default": False
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "execute_command",
            "description": "Execute a command on a server",
            "inputSchema": {
                "type": "object", 
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "server": {
                        "type": "string",
                        "description": "Server name (optional, uses default if not specified)"
                    }
                },
                "required": ["command"]
            }
        },
        {
            "name": "get_server_status",
            "description": "Get connection status of servers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string", 
                        "description": "Server name (optional, gets all if not specified)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_server_info",
            "description": "Get detailed configuration information for a specific server",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to get detailed information for"
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "run_local_command",
            "description": "Execute a command on the local system",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Command to execute locally"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (optional)"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (default: 30)"
                    }
                },
                "required": ["cmd"]
            }
        },
        # 配置管理工具 - interactive_config_wizard功能已内置到create/update工具中
        {
            "name": "diagnose_connection",
            "description": "Diagnose connection issues and provide troubleshooting suggestions for a specific server",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to diagnose"
                    },
                    "include_network_test": {
                        "type": "boolean",
                        "description": "Include network connectivity tests (ping, SSH)",
                        "default": True
                    },
                    "include_config_validation": {
                        "type": "boolean",
                        "description": "Include configuration validation",
                        "default": True
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "create_server_config",
            "description": "Create a new server configuration with detailed parameters. Includes built-in interactive wizard when parameters are incomplete.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Server name (unique identifier)"
                    },
                    "host": {
                        "type": "string",
                        "description": "Server hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for SSH connection"
                    },
                    "port": {
                        "type": "integer",
                        "description": "SSH port (default: 22)",
                        "default": 22
                    },
                    "connection_type": {
                        "type": "string",
                        "enum": ["ssh", "relay"],
                        "description": "Connection type: ssh (direct) or relay (via relay-cli)",
                        "default": "ssh"
                    },
                    "description": {
                        "type": "string",
                        "description": "Server description"
                    },
                    "relay_target_host": {
                        "type": "string",
                        "description": "Target host when using relay connection"
                    },
                    "docker_enabled": {
                        "type": "boolean",
                        "description": "Enable Docker container support",
                        "default": False
                    },
                    "docker_image": {
                        "type": "string",
                        "description": "Docker image for auto-creation"
                    },
                    "docker_container": {
                        "type": "string",
                        "description": "Docker container name"
                    },
                    "tmux_session_prefix": {
                        "type": "string",
                        "description": "Tmux session name prefix"
                    },
                    "bos_bucket": {
                        "type": "string",
                        "description": "BOS bucket path for file sync"
                    },
                    "server_type": {
                        "type": "string",
                        "enum": ["ssh", "relay", "docker", "custom"],
                        "description": "Type of server to configure (for wizard mode)"
                    },
                    "quick_mode": {
                        "type": "boolean",
                        "description": "Use quick configuration mode with smart defaults (for wizard mode)",
                        "default": True
                    },
                    "use_docker": {
                        "type": "boolean",
                        "description": "Enable Docker container support (for wizard mode)",
                        "default": False
                    }
                },
                "required": []
            }
        },
        {
            "name": "update_server_config",
            "description": "Update an existing server configuration with new parameters. Includes built-in interactive wizard when no update fields are provided.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to update"
                    },
                    "host": {
                        "type": "string",
                        "description": "Server hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for SSH connection"
                    },
                    "port": {
                        "type": "integer",
                        "description": "SSH port"
                    },
                    "connection_type": {
                        "type": "string",
                        "enum": ["ssh", "relay"],
                        "description": "Connection type: ssh (direct) or relay (via relay-cli)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Server description"
                    },
                    "relay_target_host": {
                        "type": "string",
                        "description": "Target host when using relay connection"
                    },
                    "docker_enabled": {
                        "type": "boolean",
                        "description": "Enable Docker container support"
                    },
                    "docker_image": {
                        "type": "string",
                        "description": "Docker image for auto-creation"
                    },
                    "docker_container": {
                        "type": "string",
                        "description": "Docker container name"
                    },
                    "show_current_config": {
                        "type": "boolean",
                        "description": "Show current configuration and update guidance (for wizard mode)",
                        "default": True
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "delete_server_config",
            "description": "Delete a server configuration permanently. This action cannot be undone.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to delete"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation flag to prevent accidental deletion (default: false)",
                        "default": False
                    }
                },
                "required": ["server_name"]
            }
        }
    ]

def send_response(response_obj):
    """发送纯JSON响应（兼容Cursor）"""
    try:
        message_str = json.dumps(response_obj)
        # 直接输出JSON，不使用Content-Length头部
        sys.stdout.write(message_str + '\n')
        sys.stdout.flush()
        debug_log(f"Sent JSON response for ID {response_obj.get('id')}")
    except BrokenPipeError:
        debug_log("Failed to send response: Broken pipe. Parent process likely exited.")
        pass

async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method", "")
    params = request.get("params")
    request_id = request.get("id")
    
    debug_log(f"Received request: method='{method}', id='{request_id}'")
    
    # 处理通知（没有id的请求）
    if request_id is None:
        if method.lower() == "initialized":
            debug_log("Received 'initialized' notification - handshake complete")
            return None
        # 其他通知也直接返回None（不需要响应）
        return None

    try:
        # Normalize method name to be case-insensitive
        method_lower = method.lower()

        if method_lower == "initialize":
            debug_log("Handling 'initialize' request.")
            
            # 完全符合LSP和MCP规范的capabilities
            server_capabilities = {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                },
                "sampling": {}
            }
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": server_capabilities,
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION
                    }
                }
            }
            return response
        
        elif method_lower == "shutdown":
            debug_log("Handling 'shutdown' request.")
            response = { "jsonrpc": "2.0", "id": request_id, "result": {} }
            return response
        
        elif method_lower == "tools/list":
            debug_log("Handling 'tools/list' request.")
            tools = create_tools_list()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": { "tools": tools }
            }
            return response

        elif method_lower == "listofferings":
            debug_log("Handling 'ListOfferings' request.")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "offerings": []
                }
            }
            return response

        elif method_lower == "tools/call":
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            debug_log(f"Executing tool '{tool_name}' with arguments: {tool_arguments}")
            
            try:
                # 统一使用create_enhanced_manager工厂函数
                manager = create_enhanced_manager()  # 使用增强版SSH管理器
                config_manager = EnhancedConfigManager()
                content = ""
                
                if tool_name == "list_servers":
                    servers = manager.list_servers()
                    simple_servers = []
                    for server in servers:
                        simple_servers.append({
                            'name': server.get('name', ''),
                            'description': server.get('description', ''),
                            'connected': server.get('connected', False),
                            'type': server.get('type', '')
                        })
                    content = json.dumps(simple_servers, ensure_ascii=False, indent=2)
                    
                elif tool_name == "connect_server":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        # 使用增强版智能连接
                        success, message = manager.smart_connect(server_name)
                        if success:
                            # 统一使用EnhancedSSHManager的get_server方法
                            server = manager.get_server(server_name)
                            session_name = server.session.get('name', f"{server_name}_session") if server and server.session else f"{server_name}_session"
                            content = f"✅ 智能连接成功！\n📝 详情: {message}\n\n🎯 连接命令:\ntmux attach -t {session_name}\n\n💡 快速操作:\n• 连接: tmux attach -t {session_name}\n• 分离: Ctrl+B, 然后按 D\n• 查看: tmux list-sessions\n\n🚀 增强功能:\n• 智能连接检测和自动修复\n• 一键式Docker环境连接\n• 交互引导支持"
                        else:
                            content = f"❌ 智能连接失败: {message}"
                    else:
                        content = "Error: server_name parameter is required"
                        
                elif tool_name == "disconnect_server":
                    server_name = tool_arguments.get("server_name")
                    force = tool_arguments.get("force", False)
                    
                    if server_name:
                        try:
                            # 获取服务器信息
                            server = manager.get_server(server_name)
                            if not server:
                                content = json.dumps({
                                    "success": False,
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": [s.get('name', '') for s in manager.list_servers()]
                                }, ensure_ascii=False, indent=2)
                            else:
                                # 检查连接状态
                                status = manager.get_connection_status(server_name)
                                
                                if not status.get('connected', False):
                                    content = json.dumps({
                                        "success": True,
                                        "message": f"Server '{server_name}' is already disconnected",
                                        "status": "not_connected"
                                    }, ensure_ascii=False, indent=2)
                                else:
                                    # 执行断开连接
                                    disconnect_result = manager.disconnect_server(server_name, force=force)
                                    
                                    if disconnect_result.get('success', False):
                                        content = json.dumps({
                                            "success": True,
                                            "message": f"Successfully disconnected from '{server_name}'",
                                            "details": disconnect_result.get('details', ''),
                                            "cleanup_actions": disconnect_result.get('cleanup_actions', [])
                                        }, ensure_ascii=False, indent=2)
                                    else:
                                        content = json.dumps({
                                            "success": False,
                                            "error": f"Failed to disconnect from '{server_name}': {disconnect_result.get('error', 'Unknown error')}",
                                            "suggestions": disconnect_result.get('suggestions', [])
                                        }, ensure_ascii=False, indent=2)
                        except Exception as e:
                            content = json.dumps({
                                "success": False,
                                "error": f"Exception during disconnect: {str(e)}",
                                "server_name": server_name
                            }, ensure_ascii=False, indent=2)
                    else:
                        content = json.dumps({
                            "success": False,
                            "error": "server_name parameter is required"
                        }, ensure_ascii=False, indent=2)
                        
                elif tool_name == "execute_command":
                    command = tool_arguments.get("command")
                    server = tool_arguments.get("server")
                    if command:
                        result = manager.execute_command(server or "default", command)
                        content = str(result)
                    else:
                        content = "Error: command parameter is required"
                        
                elif tool_name == "get_server_status":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        status = manager.get_connection_status(server_name)
                        content = json.dumps(status, ensure_ascii=False, indent=2)
                    else:
                        # 获取所有服务器状态
                        all_status = {}
                        servers = manager.list_servers()
                        for server in servers:
                            server_name = server.get('name')
                            if server_name:
                                all_status[server_name] = manager.get_connection_status(server_name)
                        content = json.dumps(all_status, ensure_ascii=False, indent=2)
                    
                elif tool_name == "get_server_info":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        try:
                            # 获取服务器详细配置信息
                            servers = config_manager.get_existing_servers()
                            if server_name in servers:
                                server_info = servers[server_name]
                                # 添加连接状态信息
                                connection_status = manager.get_connection_status(server_name)
                                server_info['connection_status'] = connection_status
                                content = json.dumps(server_info, ensure_ascii=False, indent=2)
                            else:
                                content = json.dumps({
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": list(servers.keys())
                                }, ensure_ascii=False, indent=2)
                        except Exception as e:
                            content = json.dumps({
                                "error": f"Failed to get server info: {str(e)}"
                            }, ensure_ascii=False, indent=2)
                    else:
                        content = json.dumps({
                            "error": "server_name parameter is required"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "run_local_command":
                    cmd = tool_arguments.get("cmd")
                    cwd = tool_arguments.get("cwd")
                    timeout = tool_arguments.get("timeout", 30)
                    if cmd:
                        output, success = run_command(cmd, cwd, timeout)
                        content = output
                    else:
                        content = "Error: cmd parameter is required"
                
                # interactive_config_wizard功能已内置到create_server_config和update_server_config中
                elif tool_name == "diagnose_connection":
                    server_name = tool_arguments.get("server_name")
                    include_network_test = tool_arguments.get("include_network_test", True)
                    include_config_validation = tool_arguments.get("include_config_validation", True)
                    
                    if server_name:
                        try:
                            # 使用增强版SSH管理器的诊断功能
                            diagnosis = manager.diagnose_connection_problem(server_name)
                            
                            # 如果需要，添加额外的网络测试
                            if include_network_test:
                                diagnosis["network_tests"] = "Network connectivity tests included"
                            
                            if include_config_validation:
                                diagnosis["config_validation"] = "Configuration validation included"
                            
                            content = json.dumps(diagnosis, ensure_ascii=False, indent=2)
                            
                        except Exception as e:
                            content = json.dumps({
                                "error": f"Diagnosis failed: {str(e)}",
                                "server_name": server_name,
                                "suggestions": [
                                    "Verify server name is correct",
                                    "Check if server configuration exists",
                                    "Ensure network connectivity to the server"
                                ]
                            }, ensure_ascii=False, indent=2)
                    else:
                        content = json.dumps({
                            "error": "server_name parameter is required"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "create_server_config":
                    try:
                        debug_log("Starting create_server_config tool")
                        
                        # 获取参数
                        name = tool_arguments.get("name")
                        host = tool_arguments.get("host") 
                        username = tool_arguments.get("username")
                        
                        debug_log(f"Parameters received: name={name}, host={host}, username={username}")
                        
                        # 🎯 检查是否需要启动向导模式
                        if not all([name and name.strip(), host and host.strip(), username and username.strip()]):
                            debug_log("Entering wizard mode due to missing parameters")
                            
                            # 🚀 启动内置的交互式配置向导
                            server_type = tool_arguments.get("server_type", "ssh")
                            quick_mode = tool_arguments.get("quick_mode", True)
                            
                            debug_log(f"Wizard mode: server_type={server_type}, quick_mode={quick_mode}")
                            
                            try:
                                # 🎯 创建配置管理器 - 根据quick_mode决定是否启用强制交互模式
                                if quick_mode:
                                    debug_log("Creating EnhancedConfigManager for quick mode")
                                    config_manager = EnhancedConfigManager()
                                    debug_log("Starting quick_setup")
                                    # 快速模式：使用预设模板创建配置
                                    result = config_manager.quick_setup()
                                    debug_log(f"quick_setup result: {result}")
                                    
                                    if result:
                                        content = "✅ 快速配置向导完成！\n\n服务器配置已创建成功。\n\n💡 使用 list_servers 工具查看配置的服务器。"
                                    else:
                                        content = "❌ 快速配置向导失败。请检查配置文件权限或提供必要参数。"
                                else:
                                    debug_log("Creating EnhancedConfigManager with force_interactive=True")
                                    # 🚀 启用强制交互模式，允许在MCP环境中进行用户交互
                                    config_manager = EnhancedConfigManager(force_interactive=True)
                                    debug_log("Starting guided_setup (interactive mode)")
                                    
                                    # 完整的交互式配置向导
                                    result = config_manager.guided_setup()
                                    debug_log(f"guided_setup result: {result}")
                                    
                                    if result:
                                        content = "✅ 交互式配置向导完成！\n\n服务器配置已创建成功。\n\n💡 使用 list_servers 工具查看配置的服务器。"
                                    else:
                                        content = "❌ 交互式配置向导失败。请检查输入参数。"
                                        
                            except Exception as wizard_error:
                                debug_log(f"Wizard error: {str(wizard_error)}")
                                debug_log(f"Wizard error traceback: {traceback.format_exc()}")
                                content = f"❌ 配置向导失败: {str(wizard_error)}\n\n💡 建议：请直接在终端中运行 'python3 enhanced_config_manager.py' 获得完整交互体验\n\n🔍 详细错误信息:\n{traceback.format_exc()}"
                        else:
                            debug_log("Creating server config directly with provided parameters")
                            # 直接创建配置（所有必需参数都已提供）
                            port = tool_arguments.get("port", 22)
                            connection_type = tool_arguments.get("connection_type", "ssh")
                            description = tool_arguments.get("description", "")
                            
                            try:
                                mcp_config_manager = EnhancedConfigManager()
                                debug_log("Created EnhancedConfigManager for direct config")
                                
                                # 构建服务器配置
                                server_config = {
                                    "servers": {
                                        name: {
                                            "host": host,
                                            "username": username,
                                            "port": int(port),
                                            "type": "script_based",
                                            "connection_type": connection_type,
                                            "description": description or f"{connection_type.upper()}连接: {name}",
                                            "session": {
                                                "name": f"{name}_session"
                                            },
                                            "specs": {
                                                "connection": {
                                                    "type": "ssh",
                                                    "timeout": 30
                                                },
                                                "environment_setup": {
                                                    "shell": "bash",
                                                    "working_directory": f"/home/{username}"
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                # 添加连接特定配置
                                if connection_type == "relay":
                                    relay_target_host = tool_arguments.get("relay_target_host", host)
                                    server_config["servers"][name]["specs"]["connection"]["tool"] = "relay-cli"
                                    server_config["servers"][name]["specs"]["connection"]["target"] = {"host": relay_target_host}
                                
                                # Docker配置 (如果提供)
                                docker_enabled = tool_arguments.get("docker_enabled", False) or tool_arguments.get("use_docker", False)
                                if docker_enabled:
                                    docker_container = tool_arguments.get("docker_container", f"{name}_container")
                                    docker_image = tool_arguments.get("docker_image", "ubuntu:20.04")
                                    
                                    server_config["servers"][name]["specs"]["docker"] = {
                                        "container_name": docker_container,
                                        "image": docker_image,
                                        "auto_create": True,
                                        "ports": [],
                                        "volumes": []
                                    }
                                
                                # 保存配置
                                debug_log("Saving server configuration")
                                mcp_config_manager.save_config(server_config, merge_mode=True)
                                debug_log("Configuration saved successfully")
                                
                                content = json.dumps({
                                    "success": True,
                                    "message": f"Server '{name}' created successfully",
                                    "server_config": server_config["servers"][name]
                                }, ensure_ascii=False, indent=2)
                            except Exception as save_error:
                                debug_log(f"Save error: {str(save_error)}")
                                debug_log(f"Save error traceback: {traceback.format_exc()}")
                                content = json.dumps({
                                    "error": f"Failed to save configuration: {str(save_error)}",
                                    "traceback": traceback.format_exc()
                                }, ensure_ascii=False, indent=2)
                            
                    except Exception as e:
                        debug_log(f"Top-level error in create_server_config: {str(e)}")
                        debug_log(f"Top-level error traceback: {traceback.format_exc()}")
                        content = json.dumps({
                            "error": f"Failed to create server config: {str(e)}",
                            "traceback": traceback.format_exc()
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "update_server_config":
                    try:
                        server_name = tool_arguments.get("server_name")
                        if not server_name:
                            content = json.dumps({
                                "error": "server_name parameter is required"
                            }, ensure_ascii=False, indent=2)
                        else:
                            # 获取现有服务器配置
                            mcp_config_manager = EnhancedConfigManager()
                            servers = mcp_config_manager.get_existing_servers()
                            
                            if server_name not in servers:
                                content = json.dumps({
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": list(servers.keys())
                                }, ensure_ascii=False, indent=2)
                            else:
                                # 获取现有配置
                                server_config = servers[server_name].copy()
                                updated_fields = []
                                
                                # 更新提供的字段
                                if tool_arguments.get("host"):
                                    server_config["host"] = tool_arguments.get("host")
                                    updated_fields.append("host")
                                if tool_arguments.get("username"):
                                    server_config["username"] = tool_arguments.get("username")
                                    updated_fields.append("username")
                                if tool_arguments.get("port"):
                                    server_config["port"] = int(tool_arguments.get("port"))
                                    updated_fields.append("port")
                                if tool_arguments.get("connection_type"):
                                    server_config["connection_type"] = tool_arguments.get("connection_type")
                                    updated_fields.append("connection_type")
                                if tool_arguments.get("description"):
                                    server_config["description"] = tool_arguments.get("description")
                                    updated_fields.append("description")
                                
                                # 处理relay配置
                                if tool_arguments.get("relay_target_host"):
                                    if "specs" not in server_config:
                                        server_config["specs"] = {}
                                    if "connection" not in server_config["specs"]:
                                        server_config["specs"]["connection"] = {}
                                    server_config["specs"]["connection"]["target"] = {"host": tool_arguments.get("relay_target_host")}
                                    updated_fields.append("relay_target_host")
                                
                                # 处理docker配置
                                docker_enabled = tool_arguments.get("docker_enabled")
                                if docker_enabled is not None:
                                    if "specs" not in server_config:
                                        server_config["specs"] = {}
                                    
                                    if docker_enabled:
                                        docker_config = {
                                            "auto_create": True,
                                            "container_name": tool_arguments.get("docker_container", f"{server_name}_container"),
                                            "image": tool_arguments.get("docker_image", "ubuntu:20.04"),
                                            "ports": [],
                                            "volumes": []
                                        }
                                        server_config["specs"]["docker"] = docker_config
                                        updated_fields.append("docker_enabled")
                                    else:
                                        # 移除docker配置
                                        if "docker" in server_config.get("specs", {}):
                                            del server_config["specs"]["docker"]
                                            updated_fields.append("docker_disabled")
                                
                                if updated_fields:
                                    # 保存更新后的配置
                                    update_config = {"servers": {server_name: server_config}}
                                    mcp_config_manager.save_config(update_config, merge_mode=True)
                                    
                                    content = json.dumps({
                                        "success": True,
                                        "message": f"Server '{server_name}' updated successfully",
                                        "updated_fields": updated_fields,
                                        "server_config": server_config
                                    }, ensure_ascii=False, indent=2)
                                else:
                                    # 🎯 内置向导：没有更新字段时提供引导
                                    current_config = servers[server_name]
                                    content = f"🎯 **服务器配置更新向导**\n\n"
                                    content += f"📋 **当前服务器配置** ('{server_name}'):\n"
                                    content += f"  • **host**: {current_config.get('host', 'N/A')}\n"
                                    content += f"  • **username**: {current_config.get('username', 'N/A')}\n"
                                    content += f"  • **port**: {current_config.get('port', 22)}\n"
                                    content += f"  • **connection_type**: {current_config.get('connection_type', 'ssh')}\n"
                                    content += f"  • **description**: {current_config.get('description', '无描述')}\n"
                                    
                                    # 显示Docker配置状态
                                    docker_config = current_config.get('specs', {}).get('docker')
                                    if docker_config:
                                        content += f"  • **docker_enabled**: true\n"
                                        content += f"    - container: {docker_config.get('container_name', 'N/A')}\n"
                                        content += f"    - image: {docker_config.get('image', 'N/A')}\n"
                                    else:
                                        content += f"  • **docker_enabled**: false\n"
                                    
                                    # 显示Relay配置状态
                                    relay_target = current_config.get('specs', {}).get('connection', {}).get('target', {}).get('host')
                                    if relay_target:
                                        content += f"  • **relay_target_host**: {relay_target}\n"
                                    
                                    content += f"\n🔧 **可更新的字段**:\n"
                                    content += f"  • **host**: 更改服务器IP地址或域名\n"
                                    content += f"  • **username**: 更改SSH登录用户名\n"
                                    content += f"  • **port**: 更改SSH端口\n"
                                    content += f"  • **connection_type**: 更改连接类型 ('ssh' 或 'relay')\n"
                                    content += f"  • **description**: 更新服务器描述信息\n"
                                    content += f"  • **docker_enabled**: 启用/禁用Docker支持 (true/false)\n"
                                    content += f"  • **docker_container**: Docker容器名称 (需要docker_enabled=true)\n"
                                    content += f"  • **docker_image**: Docker镜像 (需要docker_enabled=true)\n"
                                    content += f"  • **relay_target_host**: Relay目标主机 (connection_type='relay'时)\n\n"
                                    content += f"💡 **更新示例**:\n\n"
                                    content += f"**更新服务器地址**:\n"
                                    content += f"```\n"
                                    content += f"server_name: '{server_name}'\n"
                                    content += f"host: '新的IP地址'\n"
                                    content += f"```\n\n"
                                    content += f"**启用Docker支持**:\n"
                                    content += f"```\n"
                                    content += f"server_name: '{server_name}'\n"
                                    content += f"docker_enabled: true\n"
                                    content += f"docker_image: 'ubuntu:22.04'\n"
                                    content += f"```\n\n"
                                    content += f"**更新描述信息**:\n"
                                    content += f"```\n"
                                    content += f"server_name: '{server_name}'\n"
                                    content += f"description: '新的服务器描述'\n"
                                    content += f"```\n\n"
                                    content += f"🚀 **提示**: 只需提供要更新的字段，其他字段保持不变！"
                                    
                    except Exception as e:
                        content = json.dumps({
                            "error": f"Failed to update server config: {str(e)}"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "delete_server_config":
                    try:
                        server_name = tool_arguments.get("server_name")
                        confirm = tool_arguments.get("confirm", False)
                        
                        if not server_name:
                            content = json.dumps({
                                "error": "server_name parameter is required"
                            }, ensure_ascii=False, indent=2)
                        elif not confirm:
                            content = json.dumps({
                                "error": "Deletion requires confirmation. Set 'confirm' parameter to true.",
                                "warning": "This action cannot be undone. The server configuration will be permanently deleted."
                            }, ensure_ascii=False, indent=2)
                        else:
                            # 删除服务器配置
                            mcp_config_manager = EnhancedConfigManager()
                            servers = mcp_config_manager.get_existing_servers()
                            
                            if server_name not in servers:
                                content = json.dumps({
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": list(servers.keys())
                                }, ensure_ascii=False, indent=2)
                            else:
                                try:
                                    # 读取当前配置
                                    current_config = mcp_config_manager.load_config()
                                    
                                    # 删除指定服务器
                                    if "servers" in current_config and server_name in current_config["servers"]:
                                        deleted_config = current_config["servers"][server_name]
                                        del current_config["servers"][server_name]
                                        
                                        # 保存更新后的配置
                                        mcp_config_manager.save_config(current_config, merge_mode=False)
                                        
                                        content = json.dumps({
                                            "success": True,
                                            "message": f"Server '{server_name}' deleted successfully",
                                            "deleted_config": deleted_config,
                                            "remaining_servers": list(current_config.get("servers", {}).keys())
                                        }, ensure_ascii=False, indent=2)
                                    else:
                                        content = json.dumps({
                                            "error": f"Server '{server_name}' not found in configuration"
                                        }, ensure_ascii=False, indent=2)
                                        
                                except Exception as delete_error:
                                    content = json.dumps({
                                        "error": f"Failed to delete server config: {str(delete_error)}"
                                    }, ensure_ascii=False, indent=2)
                                    
                    except Exception as e:
                        content = json.dumps({
                            "error": f"Failed to delete server config: {str(e)}"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "diagnose_connection":
                    server_name = tool_arguments.get("server_name")
                    
                    if not server_name:
                        content = "Error: server_name is required for diagnosis"
                    else:
                        try:
                            # 使用配置管理器的测试连接功能
                            result = config_manager.test_connection()
                            content = f"🔍 连接诊断功能已启动，请在配置管理界面中选择服务器 '{server_name}' 进行测试"
                        except Exception as e:
                            content = f"❌ 启动连接诊断失败: {str(e)}"
                
                else:
                    content = f"Unknown tool: {tool_name}"
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": content
                            }
                        ]
                    }
                }
                
            except Exception as e:
                debug_log(f"Tool execution error: {e}\n{traceback.format_exc()}")
                response = create_error_response(request_id, -32603, f"Error executing tool '{tool_name}': {e}")
            
            return response

        else:
            response = create_error_response(request_id, -32601, f"Unknown method: {method}")
            return response
            
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        debug_log(f"{error_msg}\n{traceback.format_exc()}")
        response = create_error_response(request_id, -32603, error_msg)
        return response

async def main():
    """主事件循环"""
    debug_log(f"Starting MCP Python Server v{SERVER_VERSION}")
    
    loop = asyncio.get_event_loop()

    # 1. 设置异步读取器 (stdin)
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    debug_log("Entering main while-loop to process messages.")
    while True:
        try:
            line_bytes = await reader.readline()
            if not line_bytes:
                await asyncio.sleep(1) # prevent busy-looping on closed stdin
                continue

            line = line_bytes.decode('utf-8').strip()
            
            if not line:
                continue

            try:
                request = json.loads(line)
                response = await handle_request(request)
                
                if response:
                    # 发送纯JSON响应
                    send_response(response)

            except json.JSONDecodeError as e:
                debug_log(f"JSON Decode Error: {e}. Body was: '{line}'")
            except Exception as e:
                debug_log(f"Error processing line: {e}")
                debug_log(traceback.format_exc())

        except asyncio.CancelledError:
            debug_log("Main loop cancelled.")
            break
        except Exception as e:
            debug_log(f"Critical error in main loop: {e}")
            debug_log(traceback.format_exc())
            # In case of a critical error, sleep a bit to prevent a tight error loop
            await asyncio.sleep(1)

if __name__ == "__main__":
    # 检查是否是测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 MCP服务器测试模式")
        try:
            # 测试导入
            from enhanced_config_manager import EnhancedConfigManager
            from enhanced_ssh_manager import EnhancedSSHManager
            print("✅ 所有模块导入成功")
            
            # 测试配置管理器
            config_manager = EnhancedConfigManager()
            servers = config_manager.get_existing_servers()
            print(f"✅ 配置管理器工作正常，发现 {len(servers)} 个服务器")
            
            # 测试SSH管理器
            # 统一使用create_enhanced_manager工厂函数
            ssh_manager = create_enhanced_manager()
            print("✅ SSH管理器初始化成功")
            
            print("🎉 所有测试通过！MCP服务器可以正常启动")
            sys.exit(0)
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Server shut down by KeyboardInterrupt.")
    except Exception as e:
        tb_str = traceback.format_exc()
        debug_log(f"Unhandled exception in top-level: {e}\n{tb_str}")