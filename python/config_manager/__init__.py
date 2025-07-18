# config_manager 包初始化
from .main import EnhancedConfigManager
from . import main
import sys
import importlib

# 兼容 config_manager.main
# main = importlib.import_module(__name__ + '.main')
# config_manager = sys.modules[__name__]

__all__ = ["EnhancedConfigManager", "main"]
