"""
Docker相关配置收集
"""
from .interaction import UserInteraction

class DockerConfigCollector:
    def __init__(self, interaction: UserInteraction):
        self.ia = interaction

    def configure_docker(self, defaults: dict = None) -> dict:
        print(">>> configure_docker called")
        prefill = defaults or {}
        # 修复：确保所有遍历和取值都安全
        if prefill is None:
            prefill = {}
        self.ia.colored_print(f"\n🐳 配置Docker设置...", )
        docker_enabled = prefill.get('enabled', False)
        default_choice = "1" if docker_enabled else "2"
        self.ia.colored_print("1. 启用Docker容器支持\n2. 不使用Docker")
        choice = self.ia.smart_input("选择", default=default_choice)
        if choice != "1":
            print(">>> 跳过docker详细配置，choice=", choice)
            return {}  # 这里直接return空dict，彻底跳过后续参数输入
        docker_config = {}
        docker_config['image'] = self.ia.smart_input("输入Docker镜像", default=prefill.get('image', '') or '')
        docker_config['container_name'] = self.ia.smart_input("为容器命名", default=prefill.get('container_name', '') or '')
        return docker_config
