#!/usr/bin/env python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config_manager.main import EnhancedConfigManager
from python.enhanced_ssh_manager import create_enhanced_manager

# 模拟MCP工具调用
def simulate_list_servers():
    config_manager = EnhancedConfigManager()
    manager = create_enhanced_manager()
    
    # 获取详细的服务器配置信息
    detailed_servers = []
    
    try:
        # 从配置管理器获取完整配置
        all_servers = config_manager.get_existing_servers()
        
        for server_name, server_config in all_servers.items():
            # 获取连接状态
            connection_status = manager.get_connection_status(server_name)
            
            # 解析连接类型和跳板信息
            connection_type = server_config.get('connection_type', 'ssh')
            is_relay = connection_type == 'relay'
            
            # 获取跳板信息
            jump_info = ""
            if is_relay:
                specs = server_config.get('specs', {})
                connection_specs = specs.get('connection', {})
                jump_host = connection_specs.get('jump_host', {})
                if jump_host:
                    jump_info = f"{jump_host.get('username', 'unknown')}@{jump_host.get('host', 'unknown')}"
                else:
                    # 直接relay连接（无跳板）
                    target = connection_specs.get('target', {})
                    if target:
                        jump_info = "直连relay"
            
            # 获取Docker配置信息
            docker_info = ""
            specs = server_config.get('specs', {})
            docker_config = specs.get('docker', {})
            if docker_config:
                image = docker_config.get('image', '')
                container = docker_config.get('container_name', '')
                ports = docker_config.get('ports', [])
                
                # 简化镜像名显示
                if image:
                    if 'iregistry.baidu-int.com' in image:
                        image_short = image.split('/')[-1] if '/' in image else image
                    else:
                        image_short = image
                else:
                    image_short = "未配置"
                
                docker_info = f"{image_short}"
                if container:
                    docker_info += f" ({container})"
                if ports:
                    port_str = ", ".join([str(p) for p in ports[:2]])  # 只显示前2个端口
                    if len(ports) > 2:
                        port_str += f"... (+{len(ports)-2})"
                    docker_info += f" [{port_str}]"
            
            # 获取BOS配置信息
            bos_info = ""
            bos_config = specs.get('bos', {})
            if bos_config:
                bucket = bos_config.get('bucket', '')
                if bucket:
                    bos_info = bucket.replace('bos://', '')
            
            # 构建详细服务器信息
            server_detail = {
                'name': server_name,
                'description': server_config.get('description', ''),
                'host': server_config.get('host', ''),
                'username': server_config.get('username', ''),
                'port': server_config.get('port', 22),
                'connection_type': connection_type,
                'is_relay': is_relay,
                'jump_info': jump_info,
                'docker_info': docker_info,
                'bos_info': bos_info,
                'connected': connection_status.get('connected', False),
                'session_name': server_config.get('session', {}).get('name', f"{server_name}_session")
            }
            
            detailed_servers.append(server_detail)
    
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"
    
    # 创建美观的表格输出
    if detailed_servers:
        content = "🖥️  **远程服务器配置列表**\n\n"
        
        for i, server in enumerate(detailed_servers, 1):
            # 连接状态图标
            status_icon = "��" if server.get('connected') else "🔴"
            
            # 连接类型图标
            if server.get('is_relay'):
                type_icon = "🔀" if server.get('jump_info') and server.get('jump_info') != "直连relay" else "🔗"
                type_text = "二级跳板" if server.get('jump_info') and server.get('jump_info') != "直连relay" else "Relay连接"
            else:
                type_icon = "🔗"
                type_text = "直连SSH"
            
            content += f"**{i}. {server['name']}** {status_icon}\n"
            content += f"   📝 {server.get('description', '无描述')}\n"
            content += f"   {type_icon} **连接方式**: {type_text}\n"
            content += f"   🎯 **目标**: {server.get('username', '')}@{server.get('host', '')}:{server.get('port', 22)}\n"
            
            # 跳板信息
            if server.get('jump_info') and server.get('jump_info') != "直连relay":
                content += f"   🚀 **跳板**: {server['jump_info']}\n"
            
            # Docker配置
            if server.get('docker_info'):
                content += f"   🐳 **Docker**: {server['docker_info']}\n"
            
            # BOS配置
            if server.get('bos_info'):
                content += f"   ☁️  **BOS**: {server['bos_info']}\n"
            
            # 会话信息
            if server.get('session_name'):
                content += f"   📺 **会话**: {server['session_name']}\n"
            
            content += "\n"
        
        # 添加统计信息
        total_servers = len(detailed_servers)
        connected_count = sum(1 for s in detailed_servers if s.get('connected'))
        relay_count = sum(1 for s in detailed_servers if s.get('is_relay'))
        docker_count = sum(1 for s in detailed_servers if s.get('docker_info'))
        
        content += "📊 **统计信息**:\n"
        content += f"   • 总服务器数: {total_servers}\n"
        content += f"   • 已连接: {connected_count}/{total_servers}\n"
        content += f"   • Relay连接: {relay_count}\n"
        content += f"   • Docker配置: {docker_count}\n"
        
        return content
    else:
        return "📋 暂无配置的服务器"

if __name__ == "__main__":
    result = simulate_list_servers()
    print(result)
