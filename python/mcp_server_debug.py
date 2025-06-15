#!/usr/bin/env python3

import json
import sys
import os
import subprocess
import logging
from datetime import datetime

# 设置调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp_server_debug.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# 设置环境变量确保安静模式
os.environ['MCP_QUIET'] = '1'

# 添加python目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

logger.info("=== MCP Server Debug Mode Started ===")
logger.info(f"Python path: {sys.path}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Script path: {__file__}")

try:
    logger.info("尝试导入SSH Manager...")
    from enhanced_ssh_manager import EnhancedSSHManager
    logger.info("SSH Manager导入成功")
except ImportError as e:
    logger.error(f"无法导入SSH Manager: {e}")
    error_response = {"error": f"无法导入SSH Manager: {e}"}
    print(json.dumps(error_response, ensure_ascii=False), flush=True)
    sys.exit(1)

class MCPServerDebug:
    def __init__(self):
        logger.info("初始化MCP服务器...")
        try:
            self.ssh_manager = EnhancedSSHManager()
            logger.info("SSH Manager初始化成功")
        except Exception as e:
            logger.error(f"初始化SSH Manager失败: {e}")
            error_response = {"error": f"初始化SSH Manager失败: {e}"}
            print(json.dumps(error_response, ensure_ascii=False), flush=True)
            sys.exit(1)
    
    def log_request(self, request):
        """记录请求详情"""
        logger.info(f"收到请求: {request.get('method', 'unknown')} (ID: {request.get('id', 'none')})")
        logger.debug(f"完整请求: {json.dumps(request, ensure_ascii=False)}")
    
    def log_response(self, response):
        """记录响应详情"""
        logger.info(f"发送响应: ID {response.get('id', 'none')}")
        if 'error' in response:
            logger.error(f"响应包含错误: {response['error']}")
        else:
            logger.debug(f"完整响应: {json.dumps(response, ensure_ascii=False)}")
    
    def handle_request(self, request):
        self.log_request(request)
        
        try:
            method = request.get('method')
            request_id = request.get('id')
            
            if method == 'initialize':
                logger.info("处理initialize请求")
                # 使用客户端请求的协议版本
                client_protocol_version = request.get('params', {}).get('protocolVersion', '2024-11-05')
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": client_protocol_version,  # 使用客户端版本
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "remote-terminal-mcp",
                            "version": "1.0.0-debug"
                        }
                    }
                }
                logger.info(f"initialize响应已准备，协议版本: {client_protocol_version}")
                
            elif method == 'notifications/initialized':
                logger.info("处理notifications/initialized通知")
                # 这是一个通知，不需要响应，只记录日志
                return None  # 不返回响应
                
            elif method == 'tools/list':
                logger.info("处理tools/list请求")
                response = {
                    "jsonrpc": "2.0", 
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "list_servers",
                                "description": "列出所有可用的服务器",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "additionalProperties": False
                                }
                            },
                            {
                                "name": "connect_server", 
                                "description": "连接到指定服务器",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "server_name": {
                                            "type": "string",
                                            "description": "服务器名称"
                                        }
                                    },
                                    "required": ["server_name"],
                                    "additionalProperties": False
                                }
                            },
                            {
                                "name": "execute_command",
                                "description": "在指定服务器上执行命令", 
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "server_name": {
                                            "type": "string",
                                            "description": "服务器名称"
                                        },
                                        "command": {
                                            "type": "string", 
                                            "description": "要执行的命令"
                                        }
                                    },
                                    "required": ["server_name", "command"],
                                    "additionalProperties": False
                                }
                            },
                            {
                                "name": "get_server_status",
                                "description": "获取服务器状态",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "server_name": {
                                            "type": "string",
                                            "description": "服务器名称"
                                        }
                                    },
                                    "required": ["server_name"],
                                    "additionalProperties": False
                                }
                            },
                            {
                                "name": "run_local_command",
                                "description": "在本地执行命令",
                                "inputSchema": {
                                    "type": "object", 
                                    "properties": {
                                        "command": {
                                            "type": "string",
                                            "description": "要执行的本地命令"
                                        }
                                    },
                                    "required": ["command"],
                                    "additionalProperties": False
                                }
                            }
                        ]
                    }
                }
                logger.info(f"tools/list响应已准备，包含{len(response['result']['tools'])}个工具")
            
            elif method == 'tools/call':
                params = request.get('params', {})
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                logger.info(f"处理tools/call请求: {tool_name}")
                logger.debug(f"工具参数: {arguments}")
                
                if tool_name == 'list_servers':
                    logger.info("执行list_servers工具")
                    try:
                        servers = self.ssh_manager.list_servers()
                        logger.info(f"获取到{len(servers)}个服务器")
                        
                        # 只返回服务器名称和基本信息，避免大数据量
                        simple_servers = []
                        for server in servers:
                            simple_servers.append({
                                'name': server.get('name', ''),
                                'description': server.get('description', ''),
                                'connected': server.get('connected', False),
                                'type': server.get('type', '')
                            })
                        
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id, 
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(simple_servers, ensure_ascii=False, indent=2)
                                    }
                                ]
                            }
                        }
                        logger.info("list_servers工具执行成功")
                    except Exception as e:
                        logger.error(f"list_servers工具执行失败: {e}")
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -1, "message": f"list_servers失败: {e}"}
                        }
                
                elif tool_name == 'connect_server':
                    server_name = arguments.get('server_name')
                    logger.info(f"执行connect_server工具: {server_name}")
                    
                    if not server_name:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -1, "message": "缺少server_name参数"}
                        }
                    else:
                        try:
                            success, message = self.ssh_manager.smart_connect(server_name)
                            result = f"成功: {success}, 消息: {message}"
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {
                                    "content": [
                                        {
                                            "type": "text", 
                                            "text": f"连接结果: {result}"
                                        }
                                    ]
                                }
                            }
                            logger.info(f"connect_server工具执行成功: {server_name}")
                        except Exception as e:
                            logger.error(f"connect_server工具执行失败: {e}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -1, "message": f"连接失败: {e}"}
                            }
                
                elif tool_name == 'execute_command':
                    server_name = arguments.get('server_name')
                    command = arguments.get('command')
                    logger.info(f"执行execute_command工具: {server_name} -> {command}")
                    
                    if not server_name or not command:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -1, "message": "缺少server_name或command参数"}
                        }
                    else:
                        try:
                            result = self.ssh_manager.execute_command(server_name, command)
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"命令执行结果:\n{result}"
                                        }
                                    ]
                                }
                            }
                            logger.info(f"execute_command工具执行成功")
                        except Exception as e:
                            logger.error(f"execute_command工具执行失败: {e}")
                            response = {
                                "jsonrpc": "2.0", 
                                "id": request_id,
                                "error": {"code": -1, "message": f"命令执行失败: {e}"}
                            }
                
                elif tool_name == 'get_server_status':
                    server_name = arguments.get('server_name')
                    logger.info(f"执行get_server_status工具: {server_name}")
                    
                    if not server_name:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -1, "message": "缺少server_name参数"}
                        }
                    else:
                        try:
                            status = self.ssh_manager.get_connection_status(server_name)
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(status, ensure_ascii=False, indent=2)
                                        }
                                    ]
                                }
                            }
                            logger.info(f"get_server_status工具执行成功")
                        except Exception as e:
                            logger.error(f"get_server_status工具执行失败: {e}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -1, "message": f"获取状态失败: {e}"}
                            }
                
                elif tool_name == 'run_local_command':
                    command = arguments.get('command')
                    logger.info(f"执行run_local_command工具: {command}")
                    
                    if not command:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -1, "message": "缺少command参数"}
                        }
                    else:
                        try:
                            result = subprocess.run(command, shell=True, capture_output=True, text=True)
                            output = f"退出代码: {result.returncode}\n标准输出:\n{result.stdout}\n标准错误:\n{result.stderr}"
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id, 
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": output
                                        }
                                    ]
                                }
                            }
                            logger.info(f"run_local_command工具执行成功")
                        except Exception as e:
                            logger.error(f"run_local_command工具执行失败: {e}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -1, "message": f"本地命令执行失败: {e}"}
                            }
                
                else:
                    logger.warning(f"未知工具: {tool_name}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -1, "message": f"未知工具: {tool_name}"}
                    }
            
            else:
                logger.warning(f"未知方法: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id, 
                    "error": {"code": -1, "message": f"未知方法: {method}"}
                }
            
            self.log_response(response)
            return response
        
        except Exception as e:
            logger.error(f"处理请求时出错: {e}", exc_info=True)
            response = {
                "jsonrpc": "2.0",
                "id": request.get('id', None),
                "error": {"code": -1, "message": f"处理请求时出错: {e}"}
            }
            self.log_response(response)
            return response

def main():
    logger.info("启动MCP服务器主循环...")
    server = MCPServerDebug()
    
    try:
        logger.info("开始监听stdin...")
        for line_number, line in enumerate(sys.stdin, 1):
            logger.debug(f"收到第{line_number}行输入: {repr(line)}")
            line = line.strip()
            if not line:
                logger.debug("跳过空行")
                continue
            
            try:
                request = json.loads(line)
                logger.debug(f"JSON解析成功: {request}")
                response = server.handle_request(request)
                if response is not None:  # 只有非通知才发送响应
                    response_json = json.dumps(response, ensure_ascii=False)
                    print(response_json, flush=True)
                    logger.debug(f"响应已发送: {len(response_json)} 字符")
                else:
                    logger.debug("通知处理完成，无需响应")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误 (第{line_number}行): {e}")
                logger.error(f"原始数据: {repr(line)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -1, "message": f"JSON解析错误: {e}"}
                }
                print(json.dumps(error_response, ensure_ascii=False), flush=True)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正常退出")
    except Exception as e:
        logger.error(f"主循环异常: {e}", exc_info=True)
        error_response = {
            "jsonrpc": "2.0", 
            "id": None,
            "error": {"code": -1, "message": f"服务器错误: {e}"}
        }
        print(json.dumps(error_response, ensure_ascii=False), flush=True)
    finally:
        logger.info("=== MCP Server Debug Mode Ended ===")

if __name__ == "__main__":
    main() 