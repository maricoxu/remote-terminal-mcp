"""
用户交互与输入输出逻辑
"""
import sys
from colorama import init, Fore, Style
init(autoreset=True)

class UserInteraction:
    def __init__(self, force_interactive: bool = False, auto_mode: bool = False):
        self.is_mcp_mode = (not sys.stdout.isatty())
        self.auto_mode = auto_mode
        if force_interactive:
            self.is_mcp_mode = False

    def colored_print(self, text: str, color=Fore.WHITE, style=""):
        if not self.is_mcp_mode and not self.auto_mode:
            print(f"{color}{style}{text}{Style.RESET_ALL}")

    def show_progress(self, step: int, total: int, name: str):
        bar = "█" * step + "░" * (total - step)
        self.colored_print(f"\n📊 [{bar}] {step}/{total}: {name}", Fore.CYAN)

    def smart_input(self, prompt: str, validator=None, default=""):
        print(f"[smart_input] prompt: {prompt}, default: {default}")
        if self.is_mcp_mode: return default
        p_text = f"{prompt} [{default}]: " if default else f"{prompt}: "
        while True:
            try:
                val = input(p_text).strip()
                val = val or default
                print(f"[smart_input] user input: {val}")
                if validator and not validator(val):
                    self.colored_print("❌ 输入无效。", Fore.RED)
                    print("输入验证失败")
                    continue
                return val
            except KeyboardInterrupt:
                return None

    def validate_hostname(self, hostname: str) -> bool:
        # 简单校验：不能有空格，且长度大于3
        if not hostname or ' ' in hostname or len(hostname) < 4:
            return False
        return True

    def validate_port(self, port: str) -> bool:
        try:
            p = int(port)
            return 0 < p < 65536
        except Exception:
            return False

    def validate_username(self, username: str) -> bool:
        # 简单校验：不能有空格，且长度大于1
        if not username or ' ' in username or len(username) < 2:
            return False
        return True
