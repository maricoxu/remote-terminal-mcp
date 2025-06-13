#!/usr/bin/env python3
"""
Enhanced Configuration Manager for Remote Terminal MCP
支持4种配置方式的综合管理工具
"""

import os
import sys
import yaml
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class EnhancedConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.templates_dir = self.config_dir / "templates"
        self.ensure_directories()
        
    def ensure_directories(self):
        """确保必要的目录存在"""
        self.config_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.create_default_templates()
    
    def create_default_templates(self):
        """创建默认配置模板"""
        templates = {
            "ssh_server.yaml": {
                "servers": {
                    "example-ssh": {
                        "host": "your-server.com",
                        "user": "your-username",
                        "port": 22,
                        "type": "ssh",
                        "description": "Standard SSH server"
                    }
                }
            },
            "relay_server.yaml": {
                "servers": {
                    "example-relay": {
                        "host": "target-server.internal",
                        "user": "your-username", 
                        "type": "relay",
                        "relay_command": "relay-cli -t your-token -s target-server.internal",
                        "description": "Server via relay-cli (Baidu internal)"
                    }
                }
            },
            "docker_server.yaml": {
                "servers": {
                    "example-docker": {
                        "host": "docker-host.com",
                        "user": "your-username",
                        "type": "docker",
                        "container_name": "dev_container",
                        "docker_image": "ubuntu:20.04",
                        "auto_create_container": True,
                        "tmux_session": "dev_session",
                        "description": "Docker development environment"
                    }
                }
            },
            "complex_server.yaml": {
                "servers": {
                    "example-complex": {
                        "host": "complex-server.com",
                        "user": "developer",
                        "port": 2222,
                        "type": "relay",
                        "relay_command": "relay-cli -t token123 -s complex-server.com",
                        "container_name": "pytorch_env",
                        "docker_image": "pytorch/pytorch:latest",
                        "auto_create_container": True,
                        "tmux_session": "ml_work",
                        "environment": {
                            "CUDA_VISIBLE_DEVICES": "0,1",
                            "PYTHONPATH": "/workspace"
                        },
                        "post_connect_commands": [
                            "cd /workspace",
                            "source activate pytorch",
                            "echo 'Environment ready!'"
                        ],
                        "description": "Complex ML development environment"
                    }
                }
            }
        }
        
        for template_name, content in templates.items():
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
    
    def main_menu(self):
        """主菜单"""
        print("\n🚀 Remote Terminal Configuration Manager")
        print("=" * 50)
        print("1. 快速配置 (Quick Setup) - 5分钟完成")
        print("2. 向导配置 (Guided Setup) - 详细步骤指导") 
        print("3. 模板配置 (Template Setup) - 基于模板快速创建")
        print("4. 手动配置 (Manual Setup) - 直接编辑YAML")
        print("5. 管理现有配置 (Manage Existing)")
        print("6. 测试连接 (Test Connection)")
        print("0. 退出 (Exit)")
        print("=" * 50)
        
        while True:
            choice = input("\n请选择操作 (0-6): ").strip()
            if choice == "1":
                return self.quick_setup()
            elif choice == "2":
                return self.guided_setup()
            elif choice == "3":
                return self.template_setup()
            elif choice == "4":
                return self.manual_setup()
            elif choice == "5":
                return self.manage_existing()
            elif choice == "6":
                return self.test_connection()
            elif choice == "0":
                print("再见！")
                return
            else:
                print("❌ 无效选择，请重新输入")
    
    def quick_setup(self):
        """快速配置 - 3-5个问题解决"""
        print("\n⚡ 快速配置模式")
        print("只需回答几个关键问题，自动生成配置")
        print("-" * 30)
        
        # 基本信息
        server_name = input("服务器名称 (如: gpu-server-1): ").strip()
        if not server_name:
            print("❌ 服务器名称不能为空")
            return
            
        server_host = input("服务器地址 (如: 192.168.1.100): ").strip()
        if not server_host:
            print("❌ 服务器地址不能为空")
            return
            
        username = input("用户名 (如: ubuntu): ").strip()
        if not username:
            print("❌ 用户名不能为空")
            return
        
        # 连接方式
        print("\n连接方式:")
        print("1. 直接SSH连接")
        print("2. 通过relay-cli连接 (百度内网)")
        connection_type = input("选择连接方式 (1/2): ").strip()
        
        # 是否使用Docker
        use_docker = input("是否使用Docker容器? (y/N): ").strip().lower() == 'y'
        
        # 生成配置
        config = {"servers": {}}
        
        if connection_type == "2":
            # Relay连接
            token = input("Relay token (可选): ").strip()
            relay_cmd = f"relay-cli -t {token} -s {server_host}" if token else f"relay-cli -s {server_host}"
            
            config["servers"][server_name] = {
                "host": server_host,
                "user": username,
                "type": "relay",
                "relay_command": relay_cmd,
                "description": f"Quick setup: {server_name} via relay-cli"
            }
        else:
            # SSH连接
            config["servers"][server_name] = {
                "host": server_host,
                "user": username,
                "port": 22,
                "type": "ssh", 
                "description": f"Quick setup: {server_name} via SSH"
            }
        
        # Docker配置
        if use_docker:
            container_name = input("Docker容器名称 (如: dev_env): ").strip() or "dev_env"
            config["servers"][server_name].update({
                "container_name": container_name,
                "auto_create_container": True,
                "tmux_session": f"{server_name}_session"
            })
        
        # 保存配置
        self.save_config(config)
        print(f"\n✅ 快速配置完成！配置已保存到 {self.config_path}")
        print(f"现在可以使用: python mcp_server.py connect {server_name}")
        
    def guided_setup(self):
        """向导配置 - 详细步骤"""
        print("\n🎯 向导配置模式")
        print("详细步骤指导，适合复杂配置需求")
        print("-" * 30)
        
        # 第1步：基本信息
        print("\n📋 第1步：基本信息")
        server_name = self.get_input("服务器名称", "必填，用于标识服务器")
        server_host = self.get_input("服务器地址", "IP地址或域名")
        username = self.get_input("用户名", "SSH登录用户名")
        
        # 第2步：连接方式
        print("\n🔗 第2步：连接方式")
        print("1. SSH直连 - 适用于公网服务器或VPN环境")
        print("2. Relay连接 - 适用于百度内网服务器")
        print("3. 跳板机连接 - 通过中间服务器连接")
        
        connection_type = self.get_choice("选择连接方式", ["1", "2", "3"])
        
        config = {"servers": {server_name: {
            "host": server_host,
            "user": username,
            "description": f"Guided setup: {server_name}"
        }}}
        
        if connection_type == "1":
            # SSH直连
            port = int(self.get_input("SSH端口", "默认22", "22"))
            config["servers"][server_name].update({
                "port": port,
                "type": "ssh"
            })
        elif connection_type == "2":
            # Relay连接
            token = self.get_input("Relay Token", "从管理员获取")
            relay_cmd = f"relay-cli -t {token} -s {server_host}"
            config["servers"][server_name].update({
                "type": "relay",
                "relay_command": relay_cmd
            })
        else:
            # 跳板机连接
            jump_host = self.get_input("跳板机地址", "中间服务器地址")
            jump_user = self.get_input("跳板机用户名", "跳板机登录用户")
            config["servers"][server_name].update({
                "type": "ssh",
                "port": 22,
                "jump_host": jump_host,
                "jump_user": jump_user
            })
        
        # 第3步：Docker配置
        print("\n🐳 第3步：Docker配置")
        if self.confirm("是否使用Docker容器?"):
            container_name = self.get_input("容器名称", "Docker容器名称")
            docker_image = self.get_input("Docker镜像", "如: ubuntu:20.04", "ubuntu:20.04")
            auto_create = self.confirm("自动创建容器?")
            
            config["servers"][server_name].update({
                "container_name": container_name,
                "docker_image": docker_image,
                "auto_create_container": auto_create
            })
        
        # 第4步：会话管理
        print("\n📺 第4步：会话管理")
        if self.confirm("是否自动创建tmux会话?"):
            session_name = self.get_input("会话名称", "tmux会话名称", f"{server_name}_session")
            config["servers"][server_name]["tmux_session"] = session_name
        
        # 第5步：环境变量和启动命令
        print("\n⚙️ 第5步：高级配置")
        if self.confirm("是否需要设置环境变量?"):
            env_vars = {}
            while True:
                var_name = input("环境变量名 (回车结束): ").strip()
                if not var_name:
                    break
                var_value = input(f"{var_name}的值: ").strip()
                env_vars[var_name] = var_value
            if env_vars:
                config["servers"][server_name]["environment"] = env_vars
        
        if self.confirm("是否需要连接后自动执行命令?"):
            commands = []
            print("输入命令，每行一个，空行结束:")
            while True:
                cmd = input("命令: ").strip()
                if not cmd:
                    break
                commands.append(cmd)
            if commands:
                config["servers"][server_name]["post_connect_commands"] = commands
        
        # 保存配置
        self.save_config(config)
        print(f"\n✅ 向导配置完成！配置已保存到 {self.config_path}")
        
    def template_setup(self):
        """模板配置"""
        print("\n📋 模板配置模式")
        print("基于预定义模板快速创建配置")
        print("-" * 30)
        
        # 列出可用模板
        templates = list(self.templates_dir.glob("*.yaml"))
        if not templates:
            print("❌ 没有找到模板文件")
            return
        
        print("\n可用模板:")
        for i, template in enumerate(templates, 1):
            # 读取模板描述
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    template_data = yaml.safe_load(f)
                    servers = template_data.get('servers', {})
                    if servers:
                        server_name = list(servers.keys())[0]
                        description = servers[server_name].get('description', '无描述')
                        print(f"{i}. {template.stem} - {description}")
                    else:
                        print(f"{i}. {template.stem} - 空模板")
            except Exception as e:
                print(f"{i}. {template.stem} - 读取失败: {e}")
        
        # 选择模板
        while True:
            try:
                choice = int(input(f"\n选择模板 (1-{len(templates)}): "))
                if 1 <= choice <= len(templates):
                    selected_template = templates[choice - 1]
                    break
                else:
                    print("❌ 无效选择")
            except ValueError:
                print("❌ 请输入数字")
        
        # 加载模板
        try:
            with open(selected_template, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 加载模板失败: {e}")
            return
        
        # 定制模板
        print(f"\n正在定制模板: {selected_template.name}")
        customized_config = self.customize_template(template_config)
        
        # 保存配置
        if customized_config:
            self.save_config(customized_config)
            print(f"\n✅ 模板配置完成！配置已保存到 {self.config_path}")
    
    def manual_setup(self):
        """手动配置 - 直接编辑YAML"""
        print("\n✏️ 手动配置模式")
        print("直接编辑YAML配置文件")
        print("-" * 30)
        
        # 选择编辑器
        editors = ["nano", "vim", "code", "subl"]
        available_editors = []
        
        for editor in editors:
            if subprocess.run(["which", editor], capture_output=True).returncode == 0:
                available_editors.append(editor)
        
        if not available_editors:
            print("❌ 没有找到可用的编辑器")
            return
        
        print("\n可用编辑器:")
        for i, editor in enumerate(available_editors, 1):
            print(f"{i}. {editor}")
        
        while True:
            try:
                choice = int(input(f"选择编辑器 (1-{len(available_editors)}): "))
                if 1 <= choice <= len(available_editors):
                    selected_editor = available_editors[choice - 1]
                    break
                else:
                    print("❌ 无效选择")
            except ValueError:
                print("❌ 请输入数字")
        
        # 准备配置文件
        if not self.config_path.exists():
            # 创建示例配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(self.get_config_template())
        
        # 打开编辑器
        print(f"\n正在打开编辑器: {selected_editor}")
        print("💡 提示: 保存并关闭编辑器后将验证配置")
        
        try:
            subprocess.run([selected_editor, str(self.config_path)])
            
            # 验证配置
            if self.validate_config():
                print("✅ 配置文件验证通过!")
            else:
                print("❌ 配置文件验证失败，请检查语法")
                
        except Exception as e:
            print(f"❌ 编辑器启动失败: {e}")
    
    def get_config_template(self):
        """获取配置文件模板"""
        return """# Remote Terminal MCP Configuration
# 详细配置说明和示例

servers:
  # SSH直连示例
  ssh-server:
    host: "192.168.1.100"           # 服务器地址
    user: "ubuntu"                  # 用户名
    port: 22                        # SSH端口
    type: "ssh"                     # 连接类型
    description: "SSH direct connection"
    
  # Relay连接示例 (百度内网)
  relay-server:
    host: "internal-server.baidu.com"
    user: "work"
    type: "relay"
    relay_command: "relay-cli -t your-token -s internal-server.baidu.com"
    description: "Baidu internal server via relay-cli"
    
  # Docker服务器示例
  docker-server:
    host: "docker-host.com"
    user: "developer"
    type: "ssh"
    port: 22
    container_name: "dev_container"      # Docker容器名
    docker_image: "ubuntu:20.04"        # Docker镜像
    auto_create_container: true          # 自动创建容器
    tmux_session: "dev_session"          # tmux会话名
    description: "Docker development environment"
    
  # 复杂配置示例
  complex-server:
    host: "ml-server.com"
    user: "researcher"
    type: "relay"
    relay_command: "relay-cli -t token123 -s ml-server.com"
    container_name: "pytorch_env"
    docker_image: "pytorch/pytorch:latest"
    auto_create_container: true
    tmux_session: "ml_work"
    environment:                         # 环境变量
      CUDA_VISIBLE_DEVICES: "0,1"
      PYTHONPATH: "/workspace"
    post_connect_commands:               # 连接后执行的命令
      - "cd /workspace"
      - "source activate pytorch"
      - "echo 'ML environment ready!'"
    description: "Complex ML development environment"

# 配置字段说明:
# 
# 必填字段:
#   host: 服务器地址
#   user: 用户名
#   type: 连接类型 (ssh/relay)
#   description: 服务器描述
#
# SSH连接字段:
#   port: SSH端口 (默认22)
#
# Relay连接字段:
#   relay_command: relay-cli命令
#
# Docker字段:
#   container_name: 容器名称
#   docker_image: Docker镜像
#   auto_create_container: 是否自动创建容器
#
# 可选字段:
#   tmux_session: tmux会话名
#   environment: 环境变量字典
#   post_connect_commands: 连接后执行的命令列表
#   jump_host: 跳板机地址
#   jump_user: 跳板机用户名
"""
    
    def customize_template(self, template_config: Dict) -> Optional[Dict]:
        """定制模板配置"""
        if not template_config.get('servers'):
            print("❌ 模板格式错误")
            return None
        
        customized = {"servers": {}}
        
        for server_name, server_config in template_config['servers'].items():
            print(f"\n定制服务器: {server_name}")
            
            # 基本信息
            new_name = input(f"服务器名称 [{server_name}]: ").strip() or server_name
            new_host = input(f"服务器地址 [{server_config.get('host', '')}]: ").strip() or server_config.get('host', '')
            new_user = input(f"用户名 [{server_config.get('user', '')}]: ").strip() or server_config.get('user', '')
            
            # 复制原配置
            new_config = server_config.copy()
            new_config['host'] = new_host
            new_config['user'] = new_user
            
            # 特殊字段处理
            if 'relay_command' in server_config:
                current_cmd = server_config['relay_command']
                new_cmd = input(f"Relay命令 [{current_cmd}]: ").strip() or current_cmd
                new_config['relay_command'] = new_cmd
            
            if 'container_name' in server_config:
                current_container = server_config['container_name']
                new_container = input(f"容器名称 [{current_container}]: ").strip() or current_container
                new_config['container_name'] = new_container
            
            customized['servers'][new_name] = new_config
        
        return customized
    
    def manage_existing(self):
        """管理现有配置"""
        if not self.config_path.exists():
            print("❌ 配置文件不存在")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return
        
        servers = config.get('servers', {})
        if not servers:
            print("❌ 没有配置的服务器")
            return
        
        print("\n📋 现有服务器配置:")
        server_list = list(servers.keys())
        for i, server_name in enumerate(server_list, 1):
            server_info = servers[server_name]
            print(f"{i}. {server_name} - {server_info.get('description', '无描述')}")
        
        print("\n操作选项:")
        print("1. 查看详细配置")
        print("2. 删除服务器")
        print("3. 导出配置")
        print("0. 返回主菜单")
        
        choice = input("选择操作: ").strip()
        
        if choice == "1":
            # 查看详细配置
            server_idx = int(input(f"选择服务器 (1-{len(server_list)}): ")) - 1
            if 0 <= server_idx < len(server_list):
                server_name = server_list[server_idx]
                print(f"\n{server_name} 详细配置:")
                print(yaml.dump({server_name: servers[server_name]}, default_flow_style=False))
        
        elif choice == "2":
            # 删除服务器
            server_idx = int(input(f"选择要删除的服务器 (1-{len(server_list)}): ")) - 1
            if 0 <= server_idx < len(server_list):
                server_name = server_list[server_idx]
                if self.confirm(f"确认删除服务器 {server_name}?"):
                    del config['servers'][server_name]
                    self.save_config(config)
                    print(f"✅ 已删除服务器 {server_name}")
        
        elif choice == "3":
            # 导出配置
            export_path = input("导出文件路径 [config_backup.yaml]: ").strip() or "config_backup.yaml"
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                print(f"✅ 配置已导出到 {export_path}")
            except Exception as e:
                print(f"❌ 导出失败: {e}")
    
    def test_connection(self):
        """测试连接"""
        if not self.config_path.exists():
            print("❌ 配置文件不存在")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return
        
        servers = config.get('servers', {})
        if not servers:
            print("❌ 没有配置的服务器")
            return
        
        print("\n🔍 测试服务器连接:")
        server_list = list(servers.keys())
        for i, server_name in enumerate(server_list, 1):
            print(f"{i}. {server_name}")
        
        try:
            choice = int(input(f"选择要测试的服务器 (1-{len(server_list)}): "))
            if 1 <= choice <= len(server_list):
                server_name = server_list[choice - 1]
                print(f"正在测试连接到 {server_name}...")
                # 这里可以调用实际的连接测试逻辑
                print("💡 提示: 连接测试功能需要集成到主程序中")
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入数字")
    
    # 辅助方法
    def get_input(self, prompt: str, hint: str = "", default: str = "") -> str:
        """获取用户输入"""
        full_prompt = f"{prompt}"
        if hint:
            full_prompt += f" ({hint})"
        if default:
            full_prompt += f" [{default}]"
        full_prompt += ": "
        
        result = input(full_prompt).strip()
        return result or default
    
    def get_choice(self, prompt: str, choices: List[str]) -> str:
        """获取用户选择"""
        while True:
            choice = input(f"{prompt} ({'/'.join(choices)}): ").strip()
            if choice in choices:
                return choice
            print(f"❌ 请选择: {', '.join(choices)}")
    
    def confirm(self, prompt: str) -> bool:
        """确认提示"""
        return input(f"{prompt} (y/N): ").strip().lower() == 'y'
    
    def save_config(self, config: Dict):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            raise
    
    def validate_config(self) -> bool:
        """验证配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                print("❌ 配置文件格式错误：根节点必须是字典")
                return False
            
            if 'servers' not in config:
                print("❌ 配置文件格式错误：缺少 servers 节点")
                return False
            
            servers = config['servers']
            if not isinstance(servers, dict):
                print("❌ 配置文件格式错误：servers 必须是字典")
                return False
            
            for server_name, server_config in servers.items():
                if not isinstance(server_config, dict):
                    print(f"❌ 服务器 {server_name} 配置格式错误")
                    return False
                
                required_fields = ['host', 'user', 'type']
                for field in required_fields:
                    if field not in server_config:
                        print(f"❌ 服务器 {server_name} 缺少必填字段: {field}")
                        return False
            
            return True
            
        except yaml.YAMLError as e:
            print(f"❌ YAML语法错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 验证配置文件失败: {e}")
            return False

def main():
    """主函数"""
    config_manager = EnhancedConfigManager()
    config_manager.main_menu()

if __name__ == "__main__":
    main()