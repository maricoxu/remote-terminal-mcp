"""
主配置管理器，负责流程调度
"""
from .io import ConfigIO
from .interaction import UserInteraction
from .server_info import ServerInfoCollector
from .docker_config import DockerConfigCollector
from .sync_config import SyncConfigCollector

class EnhancedConfigManager:
    def __init__(self, config_path: str = None, force_interactive: bool = False):
        self.io = ConfigIO(config_path)
        self.ia = UserInteraction(force_interactive)
        self.server = ServerInfoCollector(self.ia)
        self.docker = DockerConfigCollector(self.ia)
        self.sync = SyncConfigCollector(self.ia)

    def launch_cursor_terminal_config(self, prefill_params: dict = None, update_mode: bool = False):
        """
        兼容老API：用于回归测试，内部直接调用新版 guided_setup
        """
        return self.guided_setup(prefill_params=prefill_params, update_mode=update_mode)

    def guided_setup(self, prefill: dict = None, edit_server: str = None):
        """
        交互式配置主入口，支持参数预填充
        :param prefill: 预填参数字典
        :param edit_server: 编辑模式下指定服务器名
        """
        prefill = prefill or {}
        self.ia.colored_print("\n==================================================")
        self.ia.colored_print("欢迎使用远程终端配置向导")
        self.ia.colored_print("==================================================\n")
        # 只加载一次配置
        config = self.io.load_config()
        if edit_server:
            self.ia.colored_print(f"\n✨ 正在编辑服务器: {edit_server}")
            name = edit_server
            server_defaults = config.get('servers', {}).get(name, {})
            merged_defaults = {**server_defaults, **prefill}
        else:
            name = prefill.get('name') or self.ia.smart_input("为这个连接设置一个唯一的名称")
            merged_defaults = prefill
        # 服务器地址
        host = merged_defaults.get('host') or self.ia.smart_input("输入服务器地址 (格式: user@host)")
        # 用户名
        username = merged_defaults.get('username')
        if not username:
            username = host.split('@')[0] if '@' in host else ''
        # 端口
        port = merged_defaults.get('port') or self.ia.smart_input("输入SSH端口", default="22")
        # docker配置
        docker_config = self.docker.configure_docker(merged_defaults.get('docker_config', {}))
        docker_enabled = bool(docker_config)
        # 自动同步配置
        sync_config = self.sync.configure_sync(merged_defaults.get('sync_config', {}))
        auto_sync_enabled = bool(sync_config)
        # 保存配置
        if 'servers' not in config:
            config['servers'] = {}
        config['servers'][name] = {
            'host': host.split('@')[1] if '@' in host else host,
            'username': username,
            'port': int(port),
            'docker_enabled': docker_enabled,
            'docker_config': docker_config,
            'auto_sync_enabled': auto_sync_enabled,
            'sync_config': sync_config,
        }
        self.io.save_config({'servers': config['servers']})
        self.ia.colored_print(f"\n✅ 配置已保存至 {self.io.config_path}")
        return name, config['servers'][name]
