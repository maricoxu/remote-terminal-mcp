# 全局patch，自动mock所有input和UserInteraction.smart_input，防止自动化测试卡住
import pytest
import sys, os
# 自动兼容：确保python/目录在sys.path，便于import config_manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../python')))

@pytest.fixture(autouse=True)
def patch_all_inputs(monkeypatch):
    # patch内置input，智能返回常用字段默认值
    def smart_input_patch(prompt="", *args, **kwargs):
        prompt_str = str(prompt)
        if "端口" in prompt_str or "port" in prompt_str:
            return "22"
        return ""
    monkeypatch.setattr("builtins.input", smart_input_patch)
    # patch config_manager.interaction.UserInteraction.smart_input
    try:
        from config_manager.interaction import UserInteraction
        def smart_input_patch(prompt="", *args, **kwargs):
            prompt_str = str(prompt)
            if "端口" in prompt_str or "port" in prompt_str:
                return "22"
            return ""
        monkeypatch.setattr(UserInteraction, "smart_input", smart_input_patch)
    except ImportError:
        pass
    # patch getpass.getpass，防止密码输入卡住
    import getpass
    def fake_getpass(prompt=""):
        return ""  # 返回空字符串，跳过密码输入
    monkeypatch.setattr(getpass, "getpass", fake_getpass)
    
    # patch subprocess.run，mock osascript/终端相关
    import subprocess
    def fake_run(*args, **kwargs):
        cmd = args[0] if args else []
        class Result:
            returncode = 0
            stdout = "1\n"
            stderr = ""
        if isinstance(cmd, list) and any("osascript" in str(c) for c in cmd):
            return Result()
        return Result()
    monkeypatch.setattr(subprocess, "run", fake_run)
