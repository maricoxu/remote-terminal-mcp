"""
服务器信息收集与校验
"""
from typing import Tuple, Optional
from .interaction import UserInteraction

class ServerInfoCollector:
    def __init__(self, interaction: UserInteraction):
        self.ia = interaction

    def parse_user_host(self, user_host: str) -> Optional[Tuple[str, str]]:
        if '@' in user_host and len(user_host.split('@')) == 2:
            user, host = user_host.split('@', 1)
            if user and host:
                return user, host
        return None

    def validate_port(self, port: str) -> bool:
        return port.isdigit() and 1 <= int(port) <= 65535

    def get_user_host(self, prefill: dict) -> Tuple[Optional[str], Optional[str]]:
        default_uh = f"{prefill.get('username','')}@{prefill.get('host','')}" if prefill.get('username') and prefill.get('host') else ""
        while True:
            user_host_str = self.ia.smart_input("输入服务器地址 (格式: user@host)", default=default_uh)
            if not user_host_str: return None, None
            parsed = self.parse_user_host(user_host_str)
            if parsed:
                return parsed
            self.ia.colored_print("❌ 格式错误，请使用 'user@host' 格式。")

    def get_port(self, prefill: dict) -> Optional[str]:
        return self.ia.smart_input("输入SSH端口", default=str(prefill.get("port", "22")), validator=self.validate_port)

    def get_server_name(self, prefill: dict) -> Optional[str]:
        return self.ia.smart_input("为这个连接设置一个唯一的名称", default=prefill.get('name', ''))
