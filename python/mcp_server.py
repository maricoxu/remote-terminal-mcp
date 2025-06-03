#!/usr/bin/env python3
"""
Cursor-Bridge MCP Server
专业级GPU服务器集群管理的MCP服务

Features:
- tmux会话管理
- 服务器连接管理
- GPU资源监控
- 统一配置管理

@author xuyehua
@version 0.1.0
"""

import asyncio
import json
import sys
import subprocess
import os
import yaml
from typing import Any, Dict, List, Optional
from datetime import datetime

class CursorBridgeMCPServer:
    """Cursor-Bridge MCP服务器主类"""
    
    def __init__(self):
        self.debug_mode = os.getenv('MCP_DEBUG') == '1'
        self.config_file = os.getenv('CURSOR_BRIDGE_CONFIG')
        self.servers_file = os.getenv('CURSOR_BRIDGE_SERVERS')
        
        # 加载配置
        self.config = self.load_config()
        self.servers = self.load_servers()
        
        # 定义工具
        self.tools = {
            "execute_command": {
                "description": "在指定的tmux会话中执行命令",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session": {
                            "type": "string",
                            "description": "tmux会话名称",
                            "default": "default"
                        },
                        "command": {
                            "type": "string", 
                            "description": "要执行的命令"
                        },
                        "server": {
                            "type": "string",
                            "description": "目标服务器ID (可选，用于远程执行)"
                        }
                    },
                    "required": ["command"]
                }
            },
            "list_tmux_sessions": {
                "description": "列出所有可用的tmux会话",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server": {
                            "type": "string",
                            "description": "服务器ID (可选)"
                        }
                    }
                }
            },
            "list_servers": {
                "description": "列出所有配置的服务器",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "series": {
                            "type": "string",
                            "description": "服务器系列筛选 (HG, TJ, CPU)",
                            "enum": ["HG", "TJ", "CPU"]
                        },
                        "status": {
                            "type": "string",
                            "description": "状态筛选 (active, inactive)",
                            "enum": ["active", "inactive"]
                        }
                    }
                }
            },
            "get_server_info": {
                "description": "获取特定服务器的详细信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "服务器ID"
                        }
                    },
                    "required": ["server_id"]
                }
            },
            "connect_to_server": {
                "description": "连接到指定的GPU服务器",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "服务器ID"
                        },
                        "session_name": {
                            "type": "string",
                            "description": "tmux会话名称",
                            "default": "default"
                        }
                    },
                    "required": ["server_id"]
                }
            },
            "monitor_gpu": {
                "description": "监控GPU使用情况",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "服务器ID"
                        }
                    }
                }
            }
        }
        
        if self.debug_mode:
            self.log("🐍 Cursor-Bridge MCP Server 初始化完成")
            self.log(f"📋 已加载 {len(self.servers)} 台服务器")
            self.log(f"🛠️  已注册 {len(self.tools)} 个工具")

    def log(self, message):
        """调试日志"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}", file=sys.stderr)

    def load_config(self):
        """加载主配置文件"""
        if not self.config_file or not os.path.exists(self.config_file):
            return self.get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                self.log(f"✅ 已加载配置: {self.config_file}")
                return config
        except Exception as e:
            self.log(f"❌ 配置加载失败: {e}")
            return self.get_default_config()

    def load_servers(self):
        """加载服务器配置"""
        if not self.servers_file or not os.path.exists(self.servers_file):
            return {}
        
        try:
            with open(self.servers_file, 'r') as f:
                servers_config = yaml.safe_load(f)
                servers = servers_config.get('servers', {})
                self.log(f"✅ 已加载服务器配置: {len(servers)} 台")
                return servers
        except Exception as e:
            self.log(f"❌ 服务器配置加载失败: {e}")
            return {}

    def get_default_config(self):
        """默认配置"""
        return {
            'settings': {
                'default_tmux_session': 'default',
                'auto_create_session': True,
                'debug_mode': False
            }
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP请求"""
        try:
            method = request.get("method")
            
            if self.debug_mode:
                self.log(f"📨 收到请求: {method}")
            
            if method == "initialize":
                return await self.handle_initialize(request)
            elif method == "tools/list":
                return await self.handle_list_tools(request)
            elif method == "tools/call":
                return await self.handle_tool_call(request)
            else:
                return self.error_response(request.get("id"), -32601, f"未知方法: {method}")
                
        except Exception as e:
            self.log(f"❌ 请求处理错误: {e}")
            return self.error_response(request.get("id"), -32603, str(e))

    async def handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "cursor-bridge-mcp",
                    "version": "0.1.0"
                }
            }
        }

    async def handle_list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """列出可用工具"""
        tools_list = []
        for name, tool in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {"tools": tools_list}
        }

    async def handle_tool_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用"""
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if self.debug_mode:
            self.log(f"🔧 调用工具: {tool_name}")

        # 工具路由
        tool_methods = {
            "execute_command": self.execute_command,
            "list_tmux_sessions": self.list_tmux_sessions,
            "list_servers": self.list_servers,
            "get_server_info": self.get_server_info,
            "connect_to_server": self.connect_to_server,
            "monitor_gpu": self.monitor_gpu
        }

        if tool_name not in tool_methods:
            return self.error_response(request.get("id"), -32602, f"未知工具: {tool_name}")

        try:
            result = await tool_methods[tool_name](arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }
        except Exception as e:
            self.log(f"❌ 工具执行错误: {e}")
            return self.error_response(request.get("id"), -32603, f"工具执行失败: {e}")

    async def execute_command(self, args: Dict[str, Any]) -> str:
        """在tmux会话中执行命令"""
        session = args.get("session", self.config['settings']['default_tmux_session'])
        command = args.get("command")
        server = args.get("server")
        
        if not command:
            return "❌ 错误: 命令不能为空"
        
        try:
            # 检查会话是否存在
            check_cmd = ["tmux", "has-session", "-t", session]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # 创建新会话
                if self.config['settings']['auto_create_session']:
                    create_cmd = ["tmux", "new-session", "-d", "-s", session]
                    subprocess.run(create_cmd, check=True)
                    self.log(f"📋 创建新会话: {session}")
                else:
                    return f"❌ 会话 '{session}' 不存在且自动创建已禁用"
                
            # 在会话中执行命令
            exec_cmd = ["tmux", "send-keys", "-t", session, command, "Enter"]
            subprocess.run(exec_cmd, check=True)
            
            server_info = f" (服务器: {server})" if server else ""
            return f"✅ 命令已在会话 '{session}' 中执行{server_info}: {command}"
            
        except subprocess.CalledProcessError as e:
            return f"❌ 执行失败: {e}"
        except Exception as e:
            return f"❌ 错误: {e}"

    async def list_tmux_sessions(self, args: Dict[str, Any]) -> str:
        """列出所有tmux会话"""
        server = args.get("server")
        
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}:#{session_windows}:#{session_created}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n')
                if sessions and sessions[0]:
                    session_list = []
                    for session_info in sessions:
                        parts = session_info.split(':')
                        if len(parts) >= 3:
                            name, windows, created = parts[0], parts[1], parts[2]
                            session_list.append(f"📋 {name} ({windows} 窗口)")
                    
                    server_info = f" - 服务器: {server}" if server else ""
                    return f"🖥️ 可用的tmux会话{server_info}:\n" + '\n'.join(session_list)
                else:
                    return "📋 当前没有活跃的tmux会话"
            else:
                return "❌ 无法获取tmux会话列表"
                
        except Exception as e:
            return f"❌ 错误: {e}"

    async def list_servers(self, args: Dict[str, Any]) -> str:
        """列出所有配置的服务器"""
        series_filter = args.get("series")
        status_filter = args.get("status")
        
        if not self.servers:
            return "❌ 没有配置任何服务器"
        
        servers_list = []
        for server_id, config in self.servers.items():
            # 应用筛选器
            if series_filter and config.get('series') != series_filter:
                continue
            if status_filter and config.get('status') != status_filter:
                continue
                
            gpu_info = f"{config.get('gpu_count', 0)}x {config.get('gpu_type', 'Unknown')}"
            status_emoji = "🟢" if config.get('status') == 'active' else "🔴"
            
            servers_list.append(
                f"{status_emoji} **{server_id}** ({config.get('series', 'Unknown')})\n"
                f"   📍 {config.get('name', 'Unknown')}\n"
                f"   🏠 {config.get('host', 'Unknown')}\n"
                f"   🎮 {gpu_info}\n"
                f"   📍 {config.get('location', 'Unknown')}"
            )
        
        if not servers_list:
            return f"❌ 没有找到匹配的服务器 (筛选: series={series_filter}, status={status_filter})"
        
        total_gpus = sum(server.get('gpu_count', 0) for server in self.servers.values() 
                        if not series_filter or server.get('series') == series_filter)
        
        header = f"🌉 服务器集群概览 (共 {len(servers_list)} 台服务器, {total_gpus} 个GPU)\n\n"
        return header + '\n\n'.join(servers_list)

    async def get_server_info(self, args: Dict[str, Any]) -> str:
        """获取特定服务器的详细信息"""
        server_id = args.get("server_id")
        
        if not server_id:
            return "❌ 错误: 服务器ID不能为空"
        
        if server_id not in self.servers:
            available = ', '.join(self.servers.keys())
            return f"❌ 服务器 '{server_id}' 不存在\n可用服务器: {available}"
        
        config = self.servers[server_id]
        status_emoji = "🟢" if config.get('status') == 'active' else "🔴"
        
        info = f"""{status_emoji} **{config.get('name', server_id)}**

📊 **基本信息**
• ID: {server_id}
• 系列: {config.get('series', 'Unknown')}
• 状态: {config.get('status', 'Unknown')}
• 位置: {config.get('location', 'Unknown')}

🖥️ **硬件配置**
• 主机: {config.get('host', 'Unknown')}
• GPU类型: {config.get('gpu_type', 'Unknown')}
• GPU数量: {config.get('gpu_count', 0)}
• 容器名: {config.get('container_name', 'Unknown')}

🌐 **连接配置**"""

        if config.get('jump_host'):
            info += f"\n• 跳板机: {config['jump_host']}"
        
        return info

    async def connect_to_server(self, args: Dict[str, Any]) -> str:
        """连接到服务器 (当前版本显示连接指令)"""
        server_id = args.get("server_id")
        session_name = args.get("session_name", "default")
        
        if not server_id:
            return "❌ 错误: 服务器ID不能为空"
        
        if server_id not in self.servers:
            available = ', '.join(self.servers.keys())
            return f"❌ 服务器 '{server_id}' 不存在\n可用服务器: {available}"
        
        config = self.servers[server_id]
        
        if config.get('status') != 'active':
            return f"⚠️ 服务器 '{server_id}' 当前状态为 {config.get('status')}"
        
        # 生成连接指令 (未来版本将实现自动连接)
        connection_info = f"""🌉 准备连接到服务器: **{config.get('name', server_id)}**

📋 **连接信息**
• 服务器: {server_id} ({config.get('series')}系列)
• 主机: {config.get('host')}
• GPU: {config.get('gpu_count')}x {config.get('gpu_type')}
• 目标会话: {session_name}

🔧 **手动连接命令** (当前版本)"""

        if config.get('jump_host'):
            connection_info += f"""
```bash
# 通过跳板机连接
ssh -J {config['jump_host']} {config['host']}

# 进入容器
docker exec -it {config.get('container_name', 'user_container')} bash

# 连接或创建tmux会话
tmux attach -t {session_name} || tmux new -s {session_name}
```"""
        else:
            connection_info += f"""
```bash
# 直接连接
ssh {config['host']}

# 进入容器  
docker exec -it {config.get('container_name', 'user_container')} bash

# 连接或创建tmux会话
tmux attach -t {session_name} || tmux new -s {session_name}
```"""

        connection_info += f"""

💡 **下个版本预告**: 将支持一键自动连接！
🛠️ **当前功能**: 可以使用 execute_command 在现有会话中执行命令"""

        return connection_info

    async def monitor_gpu(self, args: Dict[str, Any]) -> str:
        """监控GPU使用情况 (模拟数据)"""
        server_id = args.get("server_id")
        
        if server_id and server_id not in self.servers:
            return f"❌ 服务器 '{server_id}' 不存在"
        
        # 当前版本返回提示信息
        if server_id:
            config = self.servers[server_id]
            return f"""🎮 GPU监控 - {config.get('name', server_id)}

📊 **当前状态** (示例数据)
• GPU 0: 45% 使用率, 温度: 68°C, 内存: 8.2GB/24GB
• GPU 1: 72% 使用率, 温度: 75°C, 内存: 15.6GB/24GB
• GPU 2: 12% 使用率, 温度: 52°C, 内存: 2.1GB/24GB
• GPU 3: 89% 使用率, 温度: 82°C, 内存: 22.8GB/24GB

💡 **实时监控命令**:
```bash
nvidia-smi
watch -n 1 nvidia-smi
```

🔮 **下个版本**: 将支持实时GPU监控数据！"""
        else:
            # 返回集群概览
            total_servers = len([s for s in self.servers.values() if s.get('gpu_count', 0) > 0])
            total_gpus = sum(s.get('gpu_count', 0) for s in self.servers.values())
            
            return f"""🌉 集群GPU监控概览

📊 **集群状态**
• 总服务器: {total_servers} 台
• 总GPU: {total_gpus} 个
• 在线服务器: {len([s for s in self.servers.values() if s.get('status') == 'active'])} 台

💡 使用 get_server_info 查看具体服务器信息
🔮 下个版本将支持实时集群监控！"""

    def error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

async def main():
    """主函数"""
    server = CursorBridgeMCPServer()
    
    # 读取stdin的JSON-RPC请求
    async def read_stdin():
        request_count = 0
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    if server.debug_mode:
                        server.log("📝 stdin已关闭，退出服务器")
                    break
                
                if line.strip():  # 只处理非空行
                    request_count += 1
                    if server.debug_mode:
                        server.log(f"📨 收到请求 #{request_count}")
                    
                    request = json.loads(line.strip())
                    response = await server.handle_request(request)
                    
                    if server.debug_mode:
                        server.log(f"📤 发送响应 #{request_count}")
                    
                    print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                if server.debug_mode:
                    server.log(f"❌ JSON解析错误: {e}")
                continue
            except Exception as e:
                if server.debug_mode:
                    server.log(f"❌ 处理请求时出错: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }
                print(json.dumps(error_response), flush=True)

    await read_stdin()

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print("Cursor-Bridge MCP Server v0.1.0")
        sys.exit(0)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 服务器被用户中断", file=sys.stderr)
    except Exception as e:
        print(f"💥 服务器崩溃: {e}", file=sys.stderr)
        sys.exit(1)