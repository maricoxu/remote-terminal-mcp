"""
Docker相关配置收集 - 改进版
支持读取现有配置、创建新配置、不使用docker三种模式
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
        # 修改为用户目录下的配置目录
        self.configs_dir = Path.home() / '.remote-terminal-mcp' / 'docker_configs'

    def _load_existing_configs(self) -> List[Tuple[str, Dict]]:
        """加载现有的Docker配置文件"""
        existing_configs = []
        
        # 检查用户目录下的docker_configs目录
        if self.configs_dir.exists():
            for config_file in self.configs_dir.glob("*.yaml"):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    if config:
                        existing_configs.append((config_file.stem, config))
                except Exception as e:
                    self.ia.colored_print(f"⚠️ 无法读取配置文件 {config_file.name}: {e}")
        
        # 检查项目目录下的docker_configs目录（向后兼容）
        project_configs_dir = Path(__file__).resolve().parent.parent.parent / 'docker_configs'
        if project_configs_dir.exists():
            for config_file in project_configs_dir.glob("*.yaml"):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    if config:
                        existing_configs.append((f"project_{config_file.stem}", config))
                except Exception as e:
                    self.ia.colored_print(f"⚠️ 无法读取项目配置文件 {config_file.name}: {e}")
        
        # 检查docker_templates目录
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.yaml"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    if config:
                        existing_configs.append((f"template_{template_file.stem}", config))
                except Exception as e:
                    self.ia.colored_print(f"⚠️ 无法读取模板文件 {template_file.name}: {e}")
        
        return existing_configs

    def _display_config(self, name: str, config: Dict):
        """显示Docker配置信息"""
        self.ia.colored_print(f"\n📋 配置: {name}")
        self.ia.colored_print("=" * 40)
        
        # 显示关键信息
        container_name = config.get('container_name', '未设置')
        image = config.get('image', '未设置')
        description = config.get('description', '无描述')
        
        self.ia.colored_print(f"容器名称: {container_name}")
        self.ia.colored_print(f"Docker镜像: {image}")
        self.ia.colored_print(f"描述: {description}")
        
        # 显示其他重要配置
        if config.get('ports'):
            self.ia.colored_print(f"端口映射: {', '.join(config['ports'])}")
        if config.get('volumes'):
            self.ia.colored_print(f"挂载目录: {', '.join(config['volumes'])}")
        if config.get('gpus'):
            self.ia.colored_print(f"GPU配置: {config['gpus']}")
        if config.get('shell'):
            self.ia.colored_print(f"默认Shell: {config['shell']}")

    def configure_docker(self, defaults: dict = None) -> dict:
        """配置Docker设置 - 改进版"""
        prefill = defaults or {}
        if prefill is None:
            prefill = {}
            
        self.ia.colored_print(f"\n🐳 配置Docker设置...", )
        
        # 首先加载现有配置
        existing_configs = self._load_existing_configs()
        
        if existing_configs:
            self.ia.colored_print(f"\n📁 发现 {len(existing_configs)} 个现有Docker配置:")
            for i, (name, config) in enumerate(existing_configs, 1):
                self._display_config(name, config)
            
            # 询问是否使用现有配置
            self.ia.colored_print(f"\n选择配置方式:")
            self.ia.colored_print("1. 使用现有配置")
            self.ia.colored_print("2. 创建新的Docker配置")
            self.ia.colored_print("3. 不使用Docker")
            
            choice = self.ia.smart_input("选择", default="3")  # 默认不使用Docker
            
            if choice == "1":
                return self._use_existing_config(existing_configs)
            elif choice == "2":
                return self._create_new_config(prefill)
            else:
                return {}
        else:
            # 没有现有配置，直接选择创建新配置或不使用
            self.ia.colored_print(f"\n📁 未发现现有Docker配置")
            self.ia.colored_print(f"\n选择配置方式:")
            self.ia.colored_print("1. 创建新的Docker配置")
            self.ia.colored_print("2. 不使用Docker")
            
            choice = self.ia.smart_input("选择", default="2")  # 默认不使用Docker
            
            if choice == "1":
                return self._create_new_config(prefill)
            else:
                return {}

    def _use_existing_config(self, existing_configs: List[Tuple[str, Dict]]) -> dict:
        """使用现有配置"""
        self.ia.colored_print(f"\n📋 选择要使用的配置:")
        for i, (name, config) in enumerate(existing_configs, 1):
            container_name = config.get('container_name', '未设置')
            image = config.get('image', '未设置')
            self.ia.colored_print(f"{i}. {name} ({container_name} - {image})")
        
        while True:
            try:
                choice = int(self.ia.smart_input(f"选择配置 (1-{len(existing_configs)})", default="1"))
                if 1 <= choice <= len(existing_configs):
                    selected_name, selected_config = existing_configs[choice - 1]
                    self.ia.colored_print(f"✅ 已选择配置: {selected_name}")
                    
                    # 返回选中的配置
                    return {
                        'use_existing_config': True,
                        'config_name': selected_name,
                        **selected_config
                    }
                else:
                    self.ia.colored_print("❌ 无效选择")
            except ValueError:
                self.ia.colored_print("❌ 请输入数字")

    def _create_new_config(self, prefill: dict) -> dict:
        """创建新的Docker配置（简化版）"""
        self.ia.colored_print(f"\n🔧 创建新的Docker配置", )
        
        # 只需要输入容器名称和Docker镜像
        container_name = self.ia.smart_input(
            "容器名称",
            default=prefill.get('container_name', ''),
            validator=lambda x: bool(x and re.match(r'^[a-zA-Z0-9_-]+$', x))
        )
        
        image = self.ia.smart_input(
            "Docker镜像",
            default=prefill.get('image', 'ubuntu:20.04')
        )
        
        # 询问是否需要启用zsh配置
        self.ia.colored_print(f"\n🐚 zsh配置选项:")
        self.ia.colored_print("启用zsh配置将自动拷贝.zshrc和.p10k.zsh文件到容器中")
        self.ia.colored_print("这将在连接时自动完成，提供更好的终端体验")
        
        enable_zsh = self.ia.smart_input(
            "是否启用zsh配置？(y/n)",
            default=prefill.get('enable_zsh_config', 'n')
        )
        
        enable_zsh_config = enable_zsh.lower() in ['y', 'yes', '是']
        
        # 使用hardcode的详细配置
        docker_config = {
            'container_name': container_name,
            'image': image,
            'auto_create': True,
            'ports': ['8080:8080', '8888:8888', '6006:6006'],
            'volumes': ['/home:/home', '/data:/data'],
            'environment': {'PYTHONPATH': '/workspace'},
            'working_directory': '/workspace',
            'shell': 'zsh' if enable_zsh_config else 'bash',  # 如果启用zsh配置，默认使用zsh
            'privileged': True,
            'network_mode': 'host',
            'restart_policy': 'always',
            'gpus': '',
            'accelerator_type': 'none',
            'memory_limit': '',
            'shm_size': '64g',
            'install_packages': ['curl', 'wget', 'git', 'vim', 'tmux', 'zsh'] if enable_zsh_config else ['curl', 'wget', 'git', 'vim', 'tmux'],
            'setup_commands': [
                'apt update && apt install -y curl wget git vim tmux' + (' zsh' if enable_zsh_config else '')
            ],
            'template_type': 'custom',
            'description': f'自定义配置: {container_name}' + (' (启用zsh配置)' if enable_zsh_config else ''),
            'use_existing_config': False,
            'enable_zsh_config': enable_zsh_config  # 新增的zsh配置选项
        }
        
        # 询问是否保存到yaml文件
        save_choice = self.ia.smart_input("是否保存配置到yaml文件？(y/n)", default="y")
        if save_choice.lower() in ['y', 'yes', '是']:
            self._save_config_to_yaml(container_name, docker_config)
        
        return docker_config

    def _save_config_to_yaml(self, container_name: str, config: Dict):
        """保存配置到yaml文件"""
        try:
            # 确保目录存在
            self.configs_dir.mkdir(exist_ok=True)
            
            # 生成文件名
            filename = f"{container_name}_config.yaml"
            filepath = self.configs_dir / filename
            
            # 保存配置
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            self.ia.colored_print(f"✅ 配置已保存到: {filepath}")
            
        except Exception as e:
            self.ia.colored_print(f"⚠️ 保存配置失败: {e}")

    # 保留原有的方法以保持兼容性
    def _configure_simple_mode(self, prefill: dict) -> dict:
        """简单模式配置（保留兼容性）"""
        return self._create_new_config(prefill)

    def _configure_full_mode(self, prefill: dict) -> dict:
        """完整模式配置（保留兼容性）"""
        return self._create_new_config(prefill)

    def _configure_from_template(self, prefill: dict) -> dict:
        """从模板配置（保留兼容性）"""
        return self._create_new_config(prefill)
