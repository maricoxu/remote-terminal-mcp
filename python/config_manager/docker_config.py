"""
Docker相关配置收集 - 增强版
支持简单模式和完整模式，集成模板系统
"""
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from .interaction import UserInteraction

@dataclass
class DockerEnvironmentConfig:
    """Docker环境配置数据类"""
    # 基础配置
    container_name: str
    image: str
    auto_create: bool = True
    
    # 高级配置
    ports: List[str] = field(default_factory=list)  # ["8080:80", "3000:3000"]
    volumes: List[str] = field(default_factory=list)  # ["/host:/container"]
    environment: Dict[str, str] = field(default_factory=dict)  # {"CUDA_VISIBLE_DEVICES": "0,1"}
    working_directory: str = "/workspace"
    
    # Shell配置
    shell: str = "bash"  # bash, zsh, sh
    
    # 运行参数
    privileged: bool = True
    network_mode: str = "host"  # host, bridge, none
    restart_policy: str = "always"
    
    # 硬件加速器配置
    gpus: str = ""  # all, "0,1", none, ""
    accelerator_type: str = "none"  # none, nvidia, xpu, custom
    memory_limit: str = ""  # "8g", "16g"
    shm_size: str = "64g"
    
    # 开发环境特定
    install_packages: List[str] = field(default_factory=list)  # ["python3", "git", "vim"]
    setup_commands: List[str] = field(default_factory=list)  # 容器创建后执行的命令
    
    # 模板信息
    template_type: str = "custom"  # development, ml, web, custom
    description: str = ""

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "container_name": self.container_name,
            "image": self.image,
            "auto_create": self.auto_create,
            "ports": self.ports,
            "volumes": self.volumes,
            "environment": self.environment,
            "working_directory": self.working_directory,
            "shell": self.shell,
            "privileged": self.privileged,
            "network_mode": self.network_mode,
            "restart_policy": self.restart_policy,
            "gpus": self.gpus,
            "accelerator_type": self.accelerator_type,
            "memory_limit": self.memory_limit,
            "shm_size": self.shm_size,
            "install_packages": self.install_packages,
            "setup_commands": self.setup_commands,
            "template_type": self.template_type,
            "description": self.description
        }

class DockerConfigCollector:
    def __init__(self, interaction: UserInteraction):
        self.ia = interaction
        self.templates_dir = Path(__file__).resolve().parent.parent.parent / 'docker_templates'

    def configure_docker(self, defaults: dict = None) -> dict:
        """配置Docker设置 - 支持简单和完整模式"""
        prefill = defaults or {}
        if prefill is None:
            prefill = {}
            
        self.ia.colored_print(f"\n🐳 配置Docker设置...", )
        
        # 选择配置模式
        self.ia.colored_print("选择配置模式:")
        self.ia.colored_print("1. 简单模式 (基础配置)")
        self.ia.colored_print("2. 完整模式 (高级配置)")
        self.ia.colored_print("3. 使用模板")
        self.ia.colored_print("4. 不使用Docker")
        
        mode_choice = self.ia.smart_input("选择模式", default="1")
        
        if mode_choice == "4":
            return {}
        elif mode_choice == "3":
            return self._configure_from_template(prefill)
        elif mode_choice == "2":
            return self._configure_full_mode(prefill)
        else:
            return self._configure_simple_mode(prefill)

    def _configure_simple_mode(self, prefill: dict) -> dict:
        """简单模式配置"""
        self.ia.colored_print("\n📝 简单模式配置", )
        
        # 基础配置
        docker_config = {}
        docker_config['image'] = self.ia.smart_input("Docker镜像", default=prefill.get('image', 'ubuntu:20.04'))
        docker_config['container_name'] = self.ia.smart_input("容器名称", default=prefill.get('container_name', ''))
        
        # 选择使用现有容器还是创建新容器
        use_existing = prefill.get('use_existing', False)
        default_existing_choice = "1" if use_existing else "2"
        self.ia.colored_print("\n1. 使用已存在的Docker容器\n2. 创建并使用新容器")
        existing_choice = self.ia.smart_input("选择", default=default_existing_choice)
        
        if existing_choice == "1":
            docker_config['use_existing'] = True
            container_name = self.ia.smart_input("请输入容器名称", default=prefill.get('container_name', ''))
            if container_name:
                docker_config['container_name'] = container_name
            else:
                self.ia.colored_print("⚠️ 未输入容器名称，将创建新容器", )
                docker_config['use_existing'] = False
        
        if not docker_config.get('use_existing', False):
            docker_config['use_existing'] = False
        
        return docker_config

    def _configure_full_mode(self, prefill: dict) -> dict:
        """完整模式配置"""
        self.ia.colored_print("\n🔧 完整模式配置", )
        
        # 基础配置
        container_name = self.ia.smart_input(
            "容器名称",
            default=prefill.get('container_name', ''),
            validator=lambda x: bool(x and re.match(r'^[a-zA-Z0-9_-]+$', x))
        )
        
        image = self.ia.smart_input(
            "Docker镜像",
            default=prefill.get('image', 'ubuntu:20.04')
        )
        
        # 端口映射
        self.ia.colored_print("\n📡 端口映射 (格式: host:container，多个用逗号分隔)")
        ports_input = self.ia.smart_input(
            "端口映射",
            default=prefill.get('ports', '')
        )
        ports = [p.strip() for p in ports_input.split(",") if p.strip()] if ports_input else []
        
        # 挂载目录
        self.ia.colored_print("\n📁 挂载目录 (格式: host:container，多个用逗号分隔)")
        volumes_input = self.ia.smart_input(
            "挂载目录",
            default=prefill.get('volumes', '/home:/home')
        )
        volumes = [v.strip() for v in volumes_input.split(",") if v.strip()] if volumes_input else []
        
        # Shell配置
        shell = self.ia.smart_input(
            "默认Shell",
            default=prefill.get('shell', 'bash'),
            validator=lambda x: x in ['bash', 'zsh', 'sh']
        )
        
        # 硬件加速器
        self.ia.colored_print("\n🚀 硬件加速器配置")
        self.ia.colored_print("1. 无加速器\n2. NVIDIA GPU\n3. 跳过")
        accelerator_choice = self.ia.smart_input("选择", default="1")
        
        gpus = ""
        accelerator_type = "none"
        if accelerator_choice == "2":
            gpus = self.ia.smart_input("GPU设备 (all 或 0,1,2)", default="all")
            accelerator_type = "nvidia"
        
        # 内存限制
        memory_limit = self.ia.smart_input(
            "内存限制 (如: 8g, 16g，直接回车跳过)",
            default=prefill.get('memory_limit', '')
        )
        
        # 安装包
        packages_input = self.ia.smart_input(
            "安装包 (用逗号分隔，直接回车跳过)",
            default=prefill.get('install_packages', '')
        )
        install_packages = [p.strip() for p in packages_input.split(",") if p.strip()] if packages_input else []
        
        # 构建配置
        docker_config = {
            'container_name': container_name,
            'image': image,
            'ports': ports,
            'volumes': volumes,
            'shell': shell,
            'gpus': gpus,
            'accelerator_type': accelerator_type,
            'memory_limit': memory_limit,
            'install_packages': install_packages,
            'use_existing': False,
            'template_type': 'custom',
            'description': f'完整配置: {container_name}'
        }
        
        return docker_config

    def _configure_from_template(self, prefill: dict) -> dict:
        """从模板配置"""
        self.ia.colored_print("\n📋 使用Docker模板", )
        
        # 检查模板目录
        if not self.templates_dir.exists():
            self.ia.colored_print(f"⚠️ 模板目录未找到: {self.templates_dir}", )
            return self._configure_simple_mode(prefill)
        
        # 列出可用模板
        templates = list(self.templates_dir.glob("*.yaml"))
        if not templates:
            self.ia.colored_print("⚠️ 没有找到Docker模板", )
            return self._configure_simple_mode(prefill)
        
        self.ia.colored_print("📋 可用模板:")
        for i, template in enumerate(templates, 1):
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                template_type = config.get('template_type', 'unknown')
                description = config.get('description', '无描述')
                self.ia.colored_print(f"  {i}. {template.stem} ({template_type}) - {description}")
            except Exception:
                self.ia.colored_print(f"  {i}. {template.stem} (读取失败)")
        
        # 选择模板
        while True:
            try:
                choice = int(self.ia.smart_input(f"选择模板 (1-{len(templates)})", default="1"))
                if 1 <= choice <= len(templates):
                    selected_template = templates[choice - 1]
                    break
                else:
                    self.ia.colored_print("❌ 无效选择")
            except ValueError:
                self.ia.colored_print("❌ 请输入数字")
        
        # 加载模板
        try:
            with open(selected_template, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
        except Exception as e:
            self.ia.colored_print(f"❌ 加载模板失败: {e}")
            return self._configure_simple_mode(prefill)
        
        # 自定义容器名称
        default_name = template_config.get('container_name', selected_template.stem)
        container_name = self.ia.smart_input(
            "容器名称",
            default=default_name,
            validator=lambda x: bool(x and re.match(r'^[a-zA-Z0-9_-]+$', x))
        )
        
        # 构建配置
        docker_config = {
            'container_name': container_name,
            'image': template_config.get('image', 'ubuntu:20.04'),
            'ports': template_config.get('ports', []),
            'volumes': template_config.get('volumes', []),
            'environment': template_config.get('environment', {}),
            'working_directory': template_config.get('working_directory', '/workspace'),
            'shell': template_config.get('shell', 'bash'),
            'privileged': template_config.get('privileged', True),
            'network_mode': template_config.get('network_mode', 'host'),
            'restart_policy': template_config.get('restart_policy', 'always'),
            'gpus': template_config.get('gpus', ''),
            'memory_limit': template_config.get('memory_limit', ''),
            'shm_size': template_config.get('shm_size', '64g'),
            'install_packages': template_config.get('install_packages', []),
            'setup_commands': template_config.get('setup_commands', []),
            'use_existing': False,
            'template_type': template_config.get('template_type', 'custom'),
            'description': f"基于模板: {selected_template.stem}"
        }
        
        return docker_config
