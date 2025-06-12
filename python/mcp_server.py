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

# 服务器信息
SERVER_NAME = "remote-terminal-mcp"
SERVER_VERSION = "0.4.47-cursor-compatible"

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'

# 延迟导入
try:
    from ssh_manager import SSHManager
except Exception as e:
    print(f"FATAL: Failed to import SSHManager. Error: {e}\n{traceback.format_exc()}")
    sys.exit(1)

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
                manager = SSHManager()
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
                        success, message = manager.simple_connect(server_name)
                        content = message
                    else:
                        content = "Error: server_name parameter is required"
                        
                elif tool_name == "execute_command":
                    command = tool_arguments.get("command")
                    server = tool_arguments.get("server")
                    if command:
                        result = manager.execute_command(command, server)
                        content = str(result)
                    else:
                        content = "Error: command parameter is required"
                        
                elif tool_name == "get_server_status":
                    server_name = tool_arguments.get("server_name")
                    status = manager.get_server_status(server_name)
                    content = str(status)
                    
                elif tool_name == "run_local_command":
                    cmd = tool_arguments.get("cmd")
                    cwd = tool_arguments.get("cwd")
                    timeout = tool_arguments.get("timeout", 30)
                    if cmd:
                        output, success = run_command(cmd, cwd, timeout)
                        content = output
                    else:
                        content = "Error: cmd parameter is required"
                    
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Server shut down by KeyboardInterrupt.")
    except Exception as e:
        tb_str = traceback.format_exc()
        debug_log(f"Unhandled exception in top-level: {e}\n{tb_str}")