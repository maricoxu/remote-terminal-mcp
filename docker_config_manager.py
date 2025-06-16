#!/usr/bin/env python3
"""
Docker Configuration Manager

独立的Docker环境配置管理器，为MCP Remote Terminal提供详细的Docker配置功能
支持模板、自定义配置、环境验证等功能
"""

import os
import re
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
# 添加颜色支持
try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # 如果没有colorama，使用简单的颜色代码
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
    
    class Back:
        BLACK = '\033[40m'
        RED = '\033[41m'
        GREEN = '\033[42m'
        YELLOW = '\033[43m'
        BLUE = '\033[44m'
        MAGENTA = '\033[45m'
        CYAN = '\033[46m'
        WHITE = '\033[47m'
    
    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        NORMAL = '\033[22m'
        RESET_ALL = '\033[0m'
    
    HAS_COLOR = True

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
    xpu_config: Dict[str, str] = field(default_factory=dict)  # XPU配置
    accelerator_type: str = "none"  # none, nvidia, xpu, custom
    memory_limit: str = ""  # "8g", "16g"
    shm_size: str = "64g"
    
    # 开发环境特定
    install_packages: List[str] = field(default_factory=list)  # ["python3", "git", "vim"]
    setup_commands: List[str] = field(default_factory=list)  # 容器创建后执行的命令
    
    # BOS配置（用于下载配置文件）
    bos_access_key: str = ""
    bos_secret_key: str = ""
    bos_bucket: str = ""
    bos_config_path: str = ""
    
    # 存储配置增强
    persistent_volumes: List[str] = field(default_factory=list)  # 持久化存储卷
    tmpfs_mounts: List[str] = field(default_factory=list)  # 临时文件系统挂载
    bind_mounts: Dict[str, str] = field(default_factory=dict)  # 绑定挂载 {host_path: container_path}
    
    # 数据管理
    data_backup_enabled: bool = False
    backup_schedule: str = ""  # cron格式
    auto_cleanup: bool = False
    
    # 模板信息
    template_type: str = "custom"  # development, ml, web, custom
    description: str = ""

    def to_yaml_dict(self) -> Dict:
        """转换为YAML配置格式"""
        config = {
            "container_name": self.container_name,
            "image": self.image,
            "auto_create": self.auto_create,
            "working_directory": self.working_directory,
            "shell": self.shell,
            "privileged": self.privileged,
            "network_mode": self.network_mode,
            "restart_policy": self.restart_policy
        }
        
        # 添加端口映射
        if self.ports:
            config["ports"] = self.ports
            
        # 添加挂载
        if self.volumes:
            config["volumes"] = self.volumes
            
        # 添加环境变量
        if self.environment:
            config["environment"] = self.environment
            
        # 添加硬件加速器支持
        if self.accelerator_type != "none":
            config["accelerator"] = {
                "type": self.accelerator_type
            }
            if self.gpus and self.gpus != "none":
                config["accelerator"]["gpus"] = self.gpus
            if self.xpu_config:
                config["accelerator"]["xpu"] = self.xpu_config
            
        # 添加资源限制
        if self.memory_limit:
            config["memory_limit"] = self.memory_limit
            
        if self.shm_size:
            config["shm_size"] = self.shm_size
            
        # 添加初始化配置
        if self.install_packages:
            config["install_packages"] = self.install_packages
            
        if self.setup_commands:
            config["setup_commands"] = self.setup_commands
            
        # 添加BOS配置
        if self.bos_access_key or self.bos_secret_key or self.bos_bucket or self.bos_config_path:
            config["bos"] = {}
            if self.bos_access_key:
                config["bos"]["access_key"] = self.bos_access_key
            if self.bos_secret_key:
                config["bos"]["secret_key"] = self.bos_secret_key
            if self.bos_bucket:
                config["bos"]["bucket"] = self.bos_bucket
            if self.bos_config_path:
                config["bos"]["config_path"] = self.bos_config_path
        
        # 添加存储配置增强
        if self.persistent_volumes or self.tmpfs_mounts or self.bind_mounts:
            config["storage"] = {}
            if self.persistent_volumes:
                config["storage"]["persistent_volumes"] = self.persistent_volumes
            if self.tmpfs_mounts:
                config["storage"]["tmpfs_mounts"] = self.tmpfs_mounts
            if self.bind_mounts:
                config["storage"]["bind_mounts"] = self.bind_mounts
        
        # 添加数据管理
        if self.data_backup_enabled or self.backup_schedule or self.auto_cleanup:
            config["data_management"] = {}
            if self.data_backup_enabled:
                config["data_management"]["enabled"] = self.data_backup_enabled
            if self.backup_schedule:
                config["data_management"]["backup_schedule"] = self.backup_schedule
            if self.auto_cleanup:
                config["data_management"]["auto_cleanup"] = self.auto_cleanup
        
        # 添加元信息
        if self.template_type != "custom":
            config["template_type"] = self.template_type
            
        if self.description:
            config["description"] = self.description
            
        return config

    def build_docker_run_command(self) -> str:
        """构建Docker run命令"""
        cmd_parts = ["docker", "run"]
        
        # 基础参数
        cmd_parts.extend(["--name", self.container_name])
        
        if self.privileged:
            cmd_parts.append("--privileged")
            
        # 网络模式
        if self.network_mode:
            cmd_parts.extend(["--net", self.network_mode])
            
        # 重启策略
        if self.restart_policy:
            cmd_parts.extend(["--restart", self.restart_policy])
            
        # 端口映射
        for port in self.ports:
            cmd_parts.extend(["-p", port])
            
        # 挂载
        for volume in self.volumes:
            cmd_parts.extend(["-v", volume])
            
        # 环境变量
        for key, value in self.environment.items():
            cmd_parts.extend(["-e", f"{key}={value}"])
            
        # 硬件加速器支持
        if self.accelerator_type == "nvidia" and self.gpus:
            if self.gpus == "all":
                cmd_parts.append("--gpus all")
            else:
                cmd_parts.extend(["--gpus", f'"{self.gpus}"'])
        elif self.accelerator_type == "xpu" and self.xpu_config:
            # XPU可能需要特殊的运行时配置
            if "runtime" in self.xpu_config:
                cmd_parts.extend(["--runtime", self.xpu_config["runtime"]])
        elif self.accelerator_type == "custom" and self.gpus:
            if self.gpus == "all":
                cmd_parts.append("--gpus all")
            else:
                cmd_parts.extend(["--gpus", f'"{self.gpus}"'])
                
        # 内存限制
        if self.memory_limit:
            cmd_parts.extend(["-m", self.memory_limit])
            
        # 共享内存
        if self.shm_size:
            cmd_parts.extend(["--shm-size", self.shm_size])
            
        # 工作目录
        if self.working_directory:
            cmd_parts.extend(["-w", self.working_directory])
            
        # 交互模式
        cmd_parts.extend(["-dit"])
        
        # 镜像
        cmd_parts.append(self.image)
        
        return " ".join(cmd_parts)

class DockerConfigManager:
    """Docker配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """初始化Docker配置管理器"""
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".remote-terminal"
            
        self.docker_templates_dir = self.config_dir / "docker_templates"
        self.docker_configs_dir = self.config_dir / "docker_configs"
        
        # 确保目录存在
        self.ensure_directories()
        
        # 创建默认模板
        self.create_default_templates()
        
    def ensure_directories(self):
        """确保必要目录存在"""
        self.config_dir.mkdir(exist_ok=True)
        self.docker_templates_dir.mkdir(exist_ok=True)
        self.docker_configs_dir.mkdir(exist_ok=True)
        
    def create_default_templates(self):
        """创建默认Docker模板"""
        templates = {
            "development.yaml": {
                "template_type": "development",
                "description": "通用开发环境",
                "container_name": "dev_environment",
                "image": "ubuntu:20.04",
                "auto_create": True,
                "working_directory": "/workspace",
                "privileged": True,
                "network_mode": "host",
                "restart_policy": "always",
                "volumes": [
                    "/home:/home",
                    "/tmp:/tmp"
                ],
                "install_packages": [
                    "curl", "wget", "git", "vim", "tmux", "zsh"
                ],
                "setup_commands": [
                    "apt update && apt install -y curl wget git vim tmux zsh",
                    "echo 'Development environment ready!'"
                ]
            },
            
            "ml_pytorch.yaml": {
                "template_type": "ml",
                "description": "PyTorch机器学习环境",
                "container_name": "pytorch_ml",
                "image": "pytorch/pytorch:1.12.0-cuda11.3-cudnn8-devel",
                "auto_create": True,
                "working_directory": "/workspace",
                "privileged": True,
                "network_mode": "host",
                "restart_policy": "always",
                "gpus": "all",
                "shm_size": "64g",
                "volumes": [
                    "/data:/data",
                    "/home:/home",
                    "/workspace:/workspace"
                ],
                "environment": {
                    "CUDA_VISIBLE_DEVICES": "0,1,2,3",
                    "PYTHONPATH": "/workspace"
                },
                "ports": [
                    "8888:8888",  # Jupyter
                    "6006:6006"   # TensorBoard
                ],
                "install_packages": [
                    "jupyter", "tensorboard", "wandb", "matplotlib", "seaborn"
                ],
                "setup_commands": [
                    "pip install jupyter tensorboard wandb matplotlib seaborn",
                    "conda install -c conda-forge nodejs",
                    "jupyter lab --generate-config",
                    "echo 'PyTorch ML environment ready!'"
                ]
            },
            
            "web_development.yaml": {
                "template_type": "web",
                "description": "Web开发环境",
                "container_name": "web_dev",
                "image": "node:16-alpine",
                "auto_create": True,
                "working_directory": "/app",
                "privileged": False,
                "network_mode": "bridge",
                "restart_policy": "unless-stopped",
                "ports": [
                    "3000:3000",
                    "8080:8080",
                    "9000:9000"
                ],
                "volumes": [
                    "/workspace:/app",
                    "/home:/home"
                ],
                "environment": {
                    "NODE_ENV": "development",
                    "PORT": "3000"
                },
                "install_packages": [
                    "yarn", "git", "curl"
                ],
                "setup_commands": [
                    "npm install -g yarn @vue/cli create-react-app",
                    "echo 'Web development environment ready!'"
                ]
            },
            
            "gpu_compute.yaml": {
                "template_type": "ml",
                "description": "GPU计算环境",
                "container_name": "gpu_compute",
                "image": "nvidia/cuda:11.3-devel-ubuntu20.04",
                "auto_create": True,
                "working_directory": "/workspace",
                "privileged": True,
                "network_mode": "host",
                "restart_policy": "always",
                "gpus": "all",
                "memory_limit": "32g",
                "shm_size": "16g",
                "volumes": [
                    "/data:/data",
                    "/home:/home",
                    "/workspace:/workspace"
                ],
                "environment": {
                    "CUDA_VISIBLE_DEVICES": "all",
                    "NVIDIA_VISIBLE_DEVICES": "all"
                },
                "install_packages": [
                    "python3", "python3-pip", "git", "vim"
                ],
                "setup_commands": [
                    "apt update && apt install -y python3 python3-pip git vim",
                    "pip3 install numpy torch torchvision",
                    "nvidia-smi",
                    "echo 'GPU compute environment ready!'"
                ]
            }
        }
        
        for template_name, config in templates.items():
            template_path = self.docker_templates_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    def colored_print(self, text: str, color=Fore.WHITE, style=Style.NORMAL):
        """彩色打印"""
        print(f"{style}{color}{text}{Style.RESET_ALL}")
        
    def smart_input(self, prompt: str, default: str = "", suggestions: List[str] = None, 
                   validator=None, show_suggestions: bool = True, allow_empty: bool = False) -> str:
        """智能输入"""
        if suggestions and show_suggestions:
            self.colored_print(f"💡 建议: {', '.join(suggestions[:3])}", Fore.YELLOW)
            
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "
            
        while True:
            user_input = input(full_prompt).strip()
            if not user_input and default:
                return default
            if not user_input and allow_empty:
                return ""
            if not user_input:
                continue
                
            if validator and not validator(user_input):
                self.colored_print("❌ 输入格式不正确，请重新输入", Fore.RED)
                continue
                
            return user_input
    
    def show_progress(self, current: int, total: int, message: str):
        """显示进度"""
        progress = int(current / total * 20)
        bar = "█" * progress + "░" * (20 - progress)
        percentage = int(current / total * 100)
        self.colored_print(f"⏳ [{bar}] {percentage}% - {message}", Fore.CYAN)
    
    def main_menu(self):
        """Docker配置主菜单"""
        while True:
            self.colored_print("\n" + "="*50, Fore.CYAN)
            self.colored_print("🐳 Docker环境配置管理器", Fore.CYAN, Style.BRIGHT)
            self.colored_print("="*50, Fore.CYAN)
            self.colored_print("1. 🚀 创建新Docker环境", Fore.GREEN)
            self.colored_print("2. 📋 使用Docker模板", Fore.BLUE)
            self.colored_print("3. ✏️ 编辑Docker环境", Fore.YELLOW)
            self.colored_print("4. 📂 管理Docker环境", Fore.MAGENTA)
            self.colored_print("5. 🔍 预览Docker命令", Fore.CYAN)
            self.colored_print("6. 🔙 返回", Fore.WHITE)
            
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == "1":
                self.create_custom_environment()
            elif choice == "2":
                self.create_from_template()
            elif choice == "3":
                self.edit_environment()
            elif choice == "4":
                self.manage_environments()
            elif choice == "5":
                self.preview_docker_command()
            elif choice == "6":
                break
            else:
                self.colored_print("❌ 无效选择，请重新输入", Fore.RED)
    
    def create_custom_environment(self):
        """创建自定义Docker环境"""
        self.colored_print("\n🚀 创建自定义Docker环境", Fore.GREEN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.GREEN)
        
        try:
            # 基础配置
            self.show_progress(1, 4, "基础配置")
            container_name = self.smart_input(
                "容器名称",
                suggestions=["dev_env", "ml_workspace", "web_app"],
                validator=lambda x: bool(x and re.match(r'^[a-zA-Z0-9_-]+$', x))
            )
            
            image = self.smart_input(
                "Docker镜像",
                default="ubuntu:20.04",
                suggestions=["ubuntu:20.04", "pytorch/pytorch:latest", "node:16-alpine"]
            )
            
            # 高级配置
            self.show_progress(2, 4, "高级配置")
            self.colored_print("\n📡 端口映射 (格式: host:container，多个用逗号分隔)")
            ports_input = self.smart_input(
                "端口映射",
                suggestions=["8080:80", "3000:3000,8888:8888", "无端口映射直接回车"],
                allow_empty=True
            )
            ports = [p.strip() for p in ports_input.split(",") if p.strip()] if ports_input else []
            
            self.colored_print("\n📁 挂载目录 (格式: host:container，多个用逗号分隔)")
            volumes_input = self.smart_input(
                "挂载目录",
                default="/home:/home",
                suggestions=["/home:/home", "/data:/data,/workspace:/workspace", "无挂载直接回车清空"],
                allow_empty=True
            )
            volumes = [v.strip() for v in volumes_input.split(",") if v.strip()] if volumes_input else []
            
            # 使用默认配置，跳过环境变量和硬件加速器配置
            self.show_progress(3, 4, "应用默认配置")
            environment = {}  # 空环境变量
            gpus = ""  # 不使用GPU
            xpu_config = {}  # 不使用XPU
            accelerator_choice = "1"  # 默认无加速器
            
            memory_limit = self.smart_input(
                "内存限制 (如: 8g, 16g，直接回车跳过)",
                suggestions=["8g", "16g", "32g", "直接回车跳过"],
                allow_empty=True
            )
            
            # 初始化配置
            self.show_progress(4, 4, "完成配置")
            
            # Shell选择
            self.colored_print("\n🐚 Shell配置")
            shell = self.smart_input(
                "默认Shell",
                default="bash",
                suggestions=["bash", "zsh", "sh"],
                validator=lambda x: x in ['bash', 'zsh', 'sh']
            )
            
            self.colored_print("\n📦 安装包 (用逗号分隔，直接回车跳过)")
            packages_input = self.smart_input(
                "安装包",
                suggestions=["git,vim,curl", "python3,pip", "nodejs,npm", "直接回车跳过"],
                allow_empty=True
            )
            install_packages = [p.strip() for p in packages_input.split(",") if p.strip()] if packages_input else []
            
            # BOS配置（仅在使用zsh时询问）
            bos_access_key = ""
            bos_secret_key = ""
            bos_bucket = ""
            bos_config_path = ""
            
            if shell == "zsh":
                self.colored_print("\n☁️ BOS配置 (用于自动下载zsh配置文件)")
                configure_bos = self.smart_input(
                    "是否配置BOS自动下载zsh配置 (y/n)",
                    default="n",
                    validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
                ).lower() in ['y', 'yes']
                
                if configure_bos:
                    bos_access_key = self.smart_input(
                        "BOS Access Key",
                        validator=lambda x: bool(x.strip())
                    )
                    bos_secret_key = self.smart_input(
                        "BOS Secret Key",
                        validator=lambda x: bool(x.strip())
                    )
                    bos_bucket = self.smart_input(
                        "BOS Bucket",
                        default="bos://klx-pytorch-work-bd-bj",
                        suggestions=["bos://klx-pytorch-work-bd-bj"]
                    )
                    bos_config_path = self.smart_input(
                        "配置文件路径",
                        default="xuyehua/template",
                        suggestions=["xuyehua/template", "username/config"]
                    )
            
            # 存储配置增强
            persistent_volumes = []
            tmpfs_mounts = []
            bind_mounts = {}
            
            self.colored_print("\n📁 存储配置增强")
            self.colored_print("1. 添加持久化存储卷")
            self.colored_print("2. 添加临时文件系统挂载")
            self.colored_print("3. 添加绑定挂载")
            self.colored_print("4. 跳过存储配置")
            self.colored_print("5. 回车结束")
            
            while True:
                choice = self.smart_input(
                    "选择存储配置增强选项 (1-5)",
                    default="4",
                    validator=lambda x: x in ['1', '2', '3', '4', '5']
                )
                if choice == "1":
                    self.colored_print("\n📁 添加持久化存储卷 (格式: host:container，多个用逗号分隔)")
                    volumes_input = self.smart_input(
                        "持久化存储卷",
                        default="/home:/home",
                        suggestions=["/home:/home", "/data:/data,/workspace:/workspace"]
                    )
                    persistent_volumes = [v.strip() for v in volumes_input.split(",") if v.strip()] if volumes_input else []
                elif choice == "2":
                    self.colored_print("\n📁 添加临时文件系统挂载 (格式: host:container，多个用逗号分隔)")
                    volumes_input = self.smart_input(
                        "临时文件系统挂载",
                        default="/home:/home",
                        suggestions=["/home:/home", "/data:/data,/workspace:/workspace"]
                    )
                    tmpfs_mounts = [v.strip() for v in volumes_input.split(",") if v.strip()] if volumes_input else []
                elif choice == "3":
                    self.colored_print("\n📁 添加绑定挂载 (格式: host_path:container_path，多个用逗号分隔)")
                    self.colored_print("例如: /home:/home, /data:/data")
                    volumes_input = self.smart_input(
                        "绑定挂载",
                        default="/home:/home",
                        suggestions=["/home:/home", "/data:/data,/workspace:/workspace"]
                    )
                    bind_mounts = {k.strip(): v.strip() for k, v in (m.split(':') for m in volumes_input.split(','))} if volumes_input else {}
                elif choice == "4":
                    break
                else:
                    self.colored_print("❌ 无效选择", Fore.RED)
            
            # 数据管理
            data_backup_enabled = self.smart_input(
                "是否启用数据备份 (y/n)",
                default="n",
                validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
            ).lower() in ['y', 'yes']
            
            backup_schedule = self.smart_input(
                "数据备份计划 (cron格式)",
                default="0 0 * * *",
                validator=lambda x: bool(x.strip())
            )
            
            auto_cleanup = self.smart_input(
                "是否启用自动清理 (y/n)",
                default="n",
                validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
            ).lower() in ['y', 'yes']
            
            # 确定加速器类型
            accelerator_type_map = {
                "1": "none",
                "2": "nvidia", 
                "3": "xpu",
                "4": "custom"
            }
            accelerator_type = accelerator_type_map.get(accelerator_choice, "none")
            
            # 创建配置对象
            docker_config = DockerEnvironmentConfig(
                container_name=container_name,
                image=image,
                ports=ports,
                volumes=volumes,
                environment=environment,
                shell=shell,
                gpus=gpus,
                xpu_config=xpu_config,
                accelerator_type=accelerator_type,
                memory_limit=memory_limit,
                install_packages=install_packages,
                bos_access_key=bos_access_key,
                bos_secret_key=bos_secret_key,
                bos_bucket=bos_bucket,
                bos_config_path=bos_config_path,
                persistent_volumes=persistent_volumes,
                tmpfs_mounts=tmpfs_mounts,
                bind_mounts=bind_mounts,
                data_backup_enabled=data_backup_enabled,
                backup_schedule=backup_schedule,
                auto_cleanup=auto_cleanup,
                template_type="custom",
                description=f"自定义Docker环境: {container_name}"
            )
            
            # 应用高级存储配置
            docker_config = self.setup_advanced_storage(docker_config)
            
            # 应用BOS存储配置
            if shell == "zsh" or bos_access_key:
                docker_config = self.setup_bos_storage(docker_config)
            
            # 保存配置
            self.save_docker_config(container_name, docker_config)
            
            self.colored_print(f"\n✅ Docker环境 '{container_name}' 创建成功！", Fore.GREEN, Style.BRIGHT)
            self.preview_config(docker_config)
            
        except KeyboardInterrupt:
            self.colored_print("\n❌ 配置被取消", Fore.YELLOW)
        except Exception as e:
            self.colored_print(f"\n❌ 创建失败: {e}", Fore.RED)
    
    def create_from_template(self):
        """从模板创建Docker环境"""
        self.colored_print("\n📋 使用Docker模板", Fore.BLUE, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.BLUE)
        
        # 列出可用模板
        templates = list(self.docker_templates_dir.glob("*.yaml"))
        if not templates:
            self.colored_print("❌ 没有找到Docker模板", Fore.RED)
            return
        
        self.colored_print("📋 可用模板:", Fore.CYAN)
        for i, template in enumerate(templates, 1):
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                template_type = config.get('template_type', 'unknown')
                description = config.get('description', '无描述')
                self.colored_print(f"  {i}. {template.stem} ({template_type}) - {description}", Fore.WHITE)
            except Exception:
                self.colored_print(f"  {i}. {template.stem} (读取失败)", Fore.RED)
        
        # 选择模板
        while True:
            try:
                choice = int(input(f"\n选择模板 (1-{len(templates)}): "))
                if 1 <= choice <= len(templates):
                    selected_template = templates[choice - 1]
                    break
                else:
                    self.colored_print("❌ 无效选择", Fore.RED)
            except ValueError:
                self.colored_print("❌ 请输入数字", Fore.RED)
        
        # 加载模板
        try:
            with open(selected_template, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
        except Exception as e:
            self.colored_print(f"❌ 加载模板失败: {e}", Fore.RED)
            return
        
        # 自定义容器名称
        default_name = template_config.get('container_name', selected_template.stem)
        container_name = self.smart_input(
            "容器名称",
            default=default_name,
            validator=lambda x: bool(x and re.match(r'^[a-zA-Z0-9_-]+$', x))
        )
        
        # 获取BOS配置
        bos_config = template_config.get('bos', {})
        
        # 创建Docker配置对象
        docker_config = DockerEnvironmentConfig(
            container_name=container_name,
            image=template_config.get('image', 'ubuntu:20.04'),
            auto_create=template_config.get('auto_create', True),
            ports=template_config.get('ports', []),
            volumes=template_config.get('volumes', []),
            environment=template_config.get('environment', {}),
            working_directory=template_config.get('working_directory', '/workspace'),
            shell=template_config.get('shell', 'bash'),
            privileged=template_config.get('privileged', True),
            network_mode=template_config.get('network_mode', 'host'),
            restart_policy=template_config.get('restart_policy', 'always'),
            gpus=template_config.get('gpus', ''),
            memory_limit=template_config.get('memory_limit', ''),
            shm_size=template_config.get('shm_size', '64g'),
            install_packages=template_config.get('install_packages', []),
            setup_commands=template_config.get('setup_commands', []),
            bos_access_key=bos_config.get('access_key', ''),
            bos_secret_key=bos_config.get('secret_key', ''),
            bos_bucket=bos_config.get('bucket', ''),
            bos_config_path=bos_config.get('config_path', ''),
            persistent_volumes=template_config.get('persistent_volumes', []),
            tmpfs_mounts=template_config.get('tmpfs_mounts', []),
            bind_mounts=template_config.get('bind_mounts', {}),
            data_backup_enabled=template_config.get('data_backup_enabled', False),
            backup_schedule=template_config.get('backup_schedule', '0 0 * * *'),
            auto_cleanup=template_config.get('auto_cleanup', False),
            template_type=template_config.get('template_type', 'custom'),
            description=template_config.get('description', f"基于模板: {selected_template.stem}")
        )
        
        # 保存配置
        self.save_docker_config(container_name, docker_config)
        
        self.colored_print(f"\n✅ 基于模板创建Docker环境 '{container_name}' 成功！", Fore.GREEN, Style.BRIGHT)
        self.preview_config(docker_config)
    
    def edit_environment(self):
        """编辑Docker环境"""
        # TODO: 实现编辑功能
        self.colored_print("🚧 编辑功能正在开发中...", Fore.YELLOW)
    
    def manage_environments(self):
        """管理Docker环境"""
        # 实现环境管理功能
        pass
    
    def setup_bos_storage(self, config: DockerEnvironmentConfig) -> DockerEnvironmentConfig:
        """设置BOS存储配置"""
        self.colored_print("\n☁️ BOS存储配置", Fore.CYAN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.CYAN)
        
        try:
            # BOS基础配置
            configure_bos = self.smart_input(
                "是否配置BOS自动下载配置文件 (y/n)",
                default="n",
                validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
            ).lower() in ['y', 'yes']
            
            if not configure_bos:
                return config
            
            # BOS认证信息
            self.colored_print("\n🔑 BOS认证配置")
            bos_access_key = self.smart_input(
                "BOS Access Key",
                validator=lambda x: bool(x.strip())
            )
            bos_secret_key = self.smart_input(
                "BOS Secret Key",
                validator=lambda x: bool(x.strip())
            )
            
            # BOS存储桶配置
            self.colored_print("\n🪣 BOS存储桶配置")
            bos_bucket = self.smart_input(
                "BOS Bucket",
                default="bos://klx-pytorch-work-bd-bj",
                suggestions=["bos://klx-pytorch-work-bd-bj", "bos://your-bucket-name"]
            )
            bos_config_path = self.smart_input(
                "配置文件路径",
                default="xuyehua/template",
                suggestions=["xuyehua/template", "username/config", "shared/configs"]
            )
            
            # 更新配置
            config.bos_access_key = bos_access_key
            config.bos_secret_key = bos_secret_key
            config.bos_bucket = bos_bucket
            config.bos_config_path = bos_config_path
            
            # 添加BOS下载命令到setup_commands
            bos_setup_commands = [
                "# BOS配置文件下载",
                f"export BOS_ACCESS_KEY={bos_access_key}",
                f"export BOS_SECRET_KEY={bos_secret_key}",
                "pip install bos-python-sdk",
                f"python3 -c \"import bos; bos.download('{bos_bucket}', '{bos_config_path}', '/tmp/configs')\"",
                "cp -r /tmp/configs/* ~/",
                "rm -rf /tmp/configs"
            ]
            
            config.setup_commands.extend(bos_setup_commands)
            
            self.colored_print("✅ BOS存储配置完成", Fore.GREEN)
            return config
            
        except Exception as e:
            self.colored_print(f"❌ BOS配置失败: {e}", Fore.RED)
            return config
    
    def setup_advanced_storage(self, config: DockerEnvironmentConfig) -> DockerEnvironmentConfig:
        """设置高级存储配置"""
        self.colored_print("\n📁 高级存储配置", Fore.BLUE, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.BLUE)
        
        try:
            # 持久化存储
            self.colored_print("\n💾 持久化存储配置")
            setup_persistent = self.smart_input(
                "是否配置持久化存储 (y/n)",
                default="y",
                validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
            ).lower() in ['y', 'yes']
            
            if setup_persistent:
                self.colored_print("推荐的持久化存储配置:")
                self.colored_print("  • /home - 用户主目录")
                self.colored_print("  • /data - 数据目录")
                self.colored_print("  • /workspace - 工作空间")
                self.colored_print("  • /models - 模型文件")
                
                volumes_input = self.smart_input(
                    "持久化存储卷 (格式: host:container，多个用逗号分隔)",
                    default="/home:/home,/data:/data,/workspace:/workspace",
                    suggestions=["/home:/home,/data:/data", "/workspace:/workspace,/models:/models"]
                )
                
                if volumes_input:
                    persistent_volumes = [v.strip() for v in volumes_input.split(",") if v.strip()]
                    config.persistent_volumes = persistent_volumes
                    # 同时添加到常规volumes中
                    config.volumes.extend(persistent_volumes)
            
            # 临时存储
            self.colored_print("\n🗂️ 临时存储配置")
            setup_tmpfs = self.smart_input(
                "是否配置临时文件系统 (y/n)",
                default="n",
                validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
            ).lower() in ['y', 'yes']
            
            if setup_tmpfs:
                self.colored_print("推荐的临时存储配置:")
                self.colored_print("  • /tmp - 临时文件")
                self.colored_print("  • /var/tmp - 变量临时文件")
                
                tmpfs_input = self.smart_input(
                    "临时文件系统挂载 (格式: path:size，多个用逗号分隔)",
                    default="/tmp:1g,/var/tmp:512m",
                    suggestions=["/tmp:1g", "/tmp:1g,/var/tmp:512m"]
                )
                
                if tmpfs_input:
                    tmpfs_mounts = [t.strip() for t in tmpfs_input.split(",") if t.strip()]
                    config.tmpfs_mounts = tmpfs_mounts
            
            # 数据备份
            self.colored_print("\n💾 数据备份配置")
            setup_backup = self.smart_input(
                "是否启用数据备份 (y/n)",
                default="n",
                validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
            ).lower() in ['y', 'yes']
            
            if setup_backup:
                config.data_backup_enabled = True
                config.backup_schedule = self.smart_input(
                    "备份计划 (cron格式)",
                    default="0 2 * * *",  # 每天凌晨2点
                    suggestions=["0 2 * * *", "0 */6 * * *", "0 0 * * 0"]
                )
                
                config.auto_cleanup = self.smart_input(
                    "是否启用自动清理旧备份 (y/n)",
                    default="y",
                    validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no']
                ).lower() in ['y', 'yes']
            
            self.colored_print("✅ 高级存储配置完成", Fore.GREEN)
            return config
            
        except Exception as e:
            self.colored_print(f"❌ 高级存储配置失败: {e}", Fore.RED)
            return config
    
    def preview_docker_command(self):
        """预览Docker命令"""
        configs = list(self.docker_configs_dir.glob("*.yaml"))
        if not configs:
            self.colored_print("❌ 没有找到Docker配置", Fore.RED)
            return
        
        self.colored_print("📋 选择要预览的配置:", Fore.CYAN)
        for i, config in enumerate(configs, 1):
            self.colored_print(f"  {i}. {config.stem}", Fore.WHITE)
        
        try:
            choice = int(input(f"\n选择配置 (1-{len(configs)}): "))
            if 1 <= choice <= len(configs):
                selected_config = configs[choice - 1]
                with open(selected_config, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                docker_config = DockerEnvironmentConfig(**config_data)
                docker_cmd = docker_config.build_docker_run_command()
                
                self.colored_print(f"\n🔍 Docker运行命令预览:", Fore.CYAN, Style.BRIGHT)
                self.colored_print(f"{docker_cmd}", Fore.GREEN)
                
        except (ValueError, IndexError):
            self.colored_print("❌ 无效选择", Fore.RED)
        except Exception as e:
            self.colored_print(f"❌ 预览失败: {e}", Fore.RED)
    
    def save_docker_config(self, name: str, config: DockerEnvironmentConfig):
        """保存Docker配置"""
        config_path = self.docker_configs_dir / f"{name}.yaml"
        config_data = config.to_yaml_dict()
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            self.colored_print(f"💾 配置已保存到: {config_path}", Fore.GREEN)
        except Exception as e:
            self.colored_print(f"❌ 保存失败: {e}", Fore.RED)
            raise
    
    def preview_config(self, config: DockerEnvironmentConfig):
        """预览配置"""
        self.colored_print("\n📋 配置预览:", Fore.CYAN)
        self.colored_print(f"  容器名称: {config.container_name}", Fore.WHITE)
        self.colored_print(f"  镜像: {config.image}", Fore.WHITE)
        self.colored_print(f"  模板类型: {config.template_type}", Fore.WHITE)
        
        if config.ports:
            self.colored_print(f"  端口映射: {', '.join(config.ports)}", Fore.WHITE)
        if config.volumes:
            self.colored_print(f"  挂载目录: {', '.join(config.volumes)}", Fore.WHITE)
        if config.environment:
            env_str = ', '.join([f"{k}={v}" for k, v in config.environment.items()])
            self.colored_print(f"  环境变量: {env_str}", Fore.WHITE)
        if config.gpus:
            self.colored_print(f"  GPU支持: {config.gpus}", Fore.WHITE)
        if config.install_packages:
            self.colored_print(f"  安装包: {', '.join(config.install_packages)}", Fore.WHITE)
    
    def get_docker_config(self, name: str) -> Optional[DockerEnvironmentConfig]:
        """获取Docker配置"""
        config_path = self.docker_configs_dir / f"{name}.yaml"
        if not config_path.exists():
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            return DockerEnvironmentConfig(**config_data)
        except Exception:
            return None
    
    def list_docker_configs(self) -> List[str]:
        """列出所有Docker配置"""
        configs = []
        for config_file in self.docker_configs_dir.glob("*.yaml"):
            configs.append(config_file.stem)
        return configs

def main():
    """主函数"""
    docker_manager = DockerConfigManager()
    docker_manager.main_menu()

if __name__ == "__main__":
    main()