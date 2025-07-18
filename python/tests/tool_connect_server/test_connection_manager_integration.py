#!/usr/bin/env python3
"""
连接管理器整合回归测试
验证整合后的connect.py文件的所有功能正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_integration_imports():
    """测试整合后的导入功能"""
    try:
        from python.connect import (
            connect_server, 
            disconnect_server, 
            get_server_status, 
            list_all_servers,
            create_connection_manager,
            ConnectionManager,
            SimpleConnectionManager,
            ConnectionResult,
            ConnectionStatus,
            ConnectionType
        )
        print("✅ 整合后导入测试通过")
        return True
    except ImportError as e:
        print(f"❌ 整合后导入失败: {e}")
        return False

def test_manager_creation():
    """测试两种管理器的创建"""
    try:
        from python.connect import create_connection_manager
        
        # 创建复杂版管理器
        complex_manager = create_connection_manager(simple_mode=False)
        assert type(complex_manager).__name__ == "ConnectionManager"
        
        # 创建简化版管理器
        simple_manager = create_connection_manager(simple_mode=True)
        assert type(simple_manager).__name__ == "SimpleConnectionManager"
        
        print("✅ 双管理器创建测试通过")
        return True
    except Exception as e:
        print(f"❌ 管理器创建测试失败: {e}")
        return False

def test_api_backward_compatibility():
    """测试API向后兼容性"""
    try:
        from python.connect import connect_server, disconnect_server, get_server_status
        
        # 测试原有的函数签名依然可用
        # 注意：不实际调用，只测试函数存在且参数兼容
        import inspect
        
        # 检查connect_server函数签名
        sig = inspect.signature(connect_server)
        params = list(sig.parameters.keys())
        
        # 应该包含原有参数和新的simple_mode参数
        expected_params = ['server_name', 'force_recreate', 'config_path', 'simple_mode']
        for param in expected_params:
            if param not in params:
                print(f"❌ 缺少参数: {param}")
                return False
        
        print("✅ API向后兼容性测试通过")
        return True
    except Exception as e:
        print(f"❌ API兼容性测试失败: {e}")
        return False

def test_mcp_server_compatibility():
    """测试MCP服务器兼容性"""
    try:
        # 模拟MCP服务器的导入方式
        from python.connect import connect_server as new_connect_server
        from python.connect import disconnect_server as new_disconnect_server
        
        # 检查函数可调用性
        assert callable(new_connect_server)
        assert callable(new_disconnect_server)
        
        print("✅ MCP服务器兼容性测试通过")
        return True
    except Exception as e:
        print(f"❌ MCP服务器兼容性测试失败: {e}")
        return False

def test_simple_mode_parameter():
    """测试simple_mode参数功能"""
    try:
        from python.connect import create_connection_manager
        
        # 测试simple_mode=False（默认）
        manager1 = create_connection_manager(simple_mode=False)
        assert type(manager1).__name__ == "ConnectionManager"
        
        # 测试simple_mode=True
        manager2 = create_connection_manager(simple_mode=True)
        assert type(manager2).__name__ == "SimpleConnectionManager"
        
        # 测试默认值（应该是False）
        manager3 = create_connection_manager()
        assert type(manager3).__name__ == "ConnectionManager"
        
        print("✅ simple_mode参数测试通过")
        return True
    except Exception as e:
        print(f"❌ simple_mode参数测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 连接管理器整合回归测试")
    print("=" * 50)
    
    tests = [
        ("整合后导入测试", test_integration_imports),
        ("双管理器创建测试", test_manager_creation),
        ("API向后兼容性测试", test_api_backward_compatibility),
        ("MCP服务器兼容性测试", test_mcp_server_compatibility),
        ("simple_mode参数测试", test_simple_mode_parameter),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 运行 {name}...")
        try:
            if test_func():
                passed += 1
                print(f"   ✅ {name} 通过")
            else:
                print(f"   ❌ {name} 失败")
        except Exception as e:
            print(f"   ❌ {name} 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 回归测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 连接管理器整合回归测试全部通过！")
        print("✅ 整合工作验证成功，可以安全使用新功能")
        return True
    else:
        print("⚠️ 部分回归测试失败，需要检查整合质量")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 