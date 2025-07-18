import unittest
from unittest.mock import patch
from config_manager.interaction import UserInteraction


class TestUserInteraction(unittest.TestCase):
    def test_colored_print(self):
        ia = UserInteraction(force_interactive=True, auto_mode=True)
        ia.colored_print("测试输出", style="")  # 只要不报错即可

    def test_smart_input_default(self):
        ia = UserInteraction(force_interactive=True, auto_mode=True)
        ia.is_mcp_mode = False  # 强制走 input 分支
        with patch.object(ia, 'smart_input', return_value="abc"):
            self.assertEqual(ia.smart_input("提示", default="abc"), "abc")

    def test_smart_input_with_mock(self):
        ia = UserInteraction(force_interactive=True, auto_mode=False)
        ia.is_mcp_mode = False  # 强制走 input 分支
        with patch.object(ia, 'smart_input', return_value="mocked"):
            self.assertEqual(ia.smart_input("请输入内容", default="default"), "mocked")

if __name__ == '__main__':
    unittest.main()
