#!/usr/bin/env python3
"""
Remote Terminal MCP Server

MCP server focused on remote server connections, session management and command execution
"""

import asyncio
import json
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# -- Robust Startup Logger --
PY_LOG_FILE = Path.home() / 'mcp_service_debug.log'
def startup_log(msg):
    """A simple, robust logger that writes to a file immediately."""
    with open(PY_LOG_FILE, 'a') as f:
        f.write(f"[PYTHON] [{datetime.now().isoformat()}] {msg}\\n")

startup_log("--- Python script started (v0.4.15) ---")

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'
startup_log("MCP_QUIET env var set.")

# 延迟导入
try:
    startup_log("Attempting to import SSHManager...")
    from ssh_manager import SSHManager
    startup_log("SSHManager imported successfully.")
except Exception as e:
    startup_log(f"FATAL: Failed to import SSHManager. Error: {e}\\n{traceback.format_exc()}")
    sys.exit(1)

# 调试模式
DEBUG = os.getenv('MCP_DEBUG', '0') == '1'
startup_log(f"Debug mode is {'ON' if DEBUG else 'OFF'}.")

# 初始化SSH管理器
ssh_manager = None

def get_ssh_manager():
    """获取SSH管理器实例"""
    global ssh_manager
    if ssh_manager is None:
        try:
            startup_log("Attempting to initialize SSHManager...")
            ssh_manager = SSHManager()
            startup_log("SSHManager initialized successfully.")
        except Exception as e:
            startup_log(f"ERROR: Failed to initialize SSHManager. It will be unavailable. Error: {e}\\n{traceback.format_exc()}")
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

def send_server_ready(request_id):
    """主动发送 server_ready 消息"""
    ready_message = {
        "jsonrpc": "2.0",
        "method": "server_ready",
        "params": {
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "system_info",
                        "description": "Get system information and current status",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "run_command",
                        "description": "Execute local command",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "Command to execute"},
                                "working_directory": {"type": "string", "description": "Working directory for command execution"},
                                "timeout": {"type": "integer", "description": "Command timeout in seconds", "default": 30}
                            },
                            "required": ["command"]
                        }
                    },
                    {
                        "name": "list_tmux_sessions",
                        "description": "List current tmux sessions",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
        }
    }
    message_str = json.dumps(ready_message)
    print(f"Content-Length: {len(message_str)}\r\n\r\n{message_str}", flush=True)
    debug_log("Sent server_ready message.")

async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method", "")
    request_id = request.get("id")
    
    debug_log(f"Received request: method='{method}', id='{request_id}'")
    
    if request_id is None:
        return None
    
    try:
        if method == "initialize":
            debug_log("Handling 'initialize' request.")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {
                        "name": "remote-terminal-mcp",
                        "version": "0.2.1" # Version update
                    }
                }
            }
        
        elif method == "shutdown":
            debug_log("Handling 'shutdown' request.")
            return { "jsonrpc": "2.0", "id": request_id, "result": {} }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": { "tools": [
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
                ]}
            }
            
        elif method == "tools/run":
            tool_name = request.get("params", {}).get("name")
            tool_input = request.get("params", {}).get("input", {})
            
            if tool_name == "connect_to_server":
                server_name = tool_input.get("server_name")
                # ... (logic for connect_to_server)
            # ... (other tools)
            else:
                return create_error_response(request_id, f"Unknown tool: {tool_name}")
        else:
            return create_error_response(request_id, f"Unsupported method: {method}")
        
    except Exception as e:
        tb_str = traceback.format_exc()
        error_msg = f"An unexpected error occurred in handle_request: {e}\n{tb_str}"
        debug_log(error_msg)
        return create_error_response(request_id, f"Internal server error: {e}")

async def main():
    """主事件循环"""
    debug_log("MCP Server is running...")
    
    # 在进入主循环之前发送 server_ready
    # MCP协议中，首次通信通常由客户端发起initialize，但有些环境需要服务器主动声明
    # 为了兼容性，我们先发一个信号
    # 注意：这里的 request_id 只是个占位符，因为这不是对某个请求的响应
    send_server_ready(request_id="initialization")
    
    while True:
        line = await asyncio.get_event_loop().run_in_executor(
            None, sys.stdin.readline
        )
        if not line:
            break
            
        if line.strip().startswith('Content-Length:'):
            content_length = int(line.split(':')[1].strip())
            # Skip the blank line
            await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            
            content = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sys.stdin.read(content_length)
            )
            
            try:
                request = json.loads(content)
                response = await handle_request(request)
                if response:
                    response_str = json.dumps(response)
                    print(f'Content-Length: {len(response_str)}\r\n\r\n{response_str}', flush=True)
            except json.JSONDecodeError:
                debug_log("Failed to decode JSON from content.")
            except Exception as e:
                debug_log(f"Error handling request: {traceback.format_exc()}")

if __name__ == "__main__":
    startup_log("Entered main execution block (__name__ == '__main__').")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Server manually interrupted.")
        startup_log("Server manually interrupted.")
    except Exception as e:
        startup_log(f"FATAL: Unhandled exception in asyncio.run(main()). Error: {e}\\n{traceback.format_exc()}")
    finally:
        debug_log("Server shutting down.")
        startup_log("--- Python script finished ---")