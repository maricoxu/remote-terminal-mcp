"""
配置文件读写与合并逻辑
"""
import yaml
from pathlib import Path
from typing import Dict, Optional

class ConfigIO:
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path.home() / '.remote-terminal' / 'config.yaml'

    def load_config(self) -> Dict:
        if not self.config_path.exists():
            return {}
        with self.config_path.open('r', encoding='utf-8') as f:
            content = f.read()
        try:
            return yaml.safe_load(content) if content and content.strip() else {}
        except Exception as e:
            print(f"⚠️ 配置文件解析失败: {e}")
            return {}

    def save_config(self, config: dict, merge: bool = True):
        final_cfg = config
        if merge and self.config_path.exists():
            existing = self.load_config().get('servers', {})
            existing.update(config.get('servers', {}))
            final_cfg = {'servers': existing}
        # 确保父目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open('w', encoding='utf-8') as f:
            yaml.dump(final_cfg, f, allow_unicode=True)
        print(f"\n✅ 配置已保存至 {self.config_path}")
