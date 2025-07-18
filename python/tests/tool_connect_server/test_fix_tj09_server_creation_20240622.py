#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回归测试：tj09服务器配置创建验证
测试目标：验证tj09服务器配置成功创建并包含正确的配置信息
创建日期：2024-06-22
修复问题：确保服务器配置创建功能正常工作

测试内容：
1. 验证tj09服务器在服务器列表中存在
2. 验证服务器配置信息正确
3. 验证Docker配置正确设置
4. 验证连接类型为relay
"""

import unittest
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.mcp_testing_utils import MCPTestClient

class TJ09ServerCreationTest(unittest.TestCase):
    """tj09服务器配置创建测试"""
    
    def setUp(self):
        """测试初始化"""
        self.test_results = []
        
    def log_result(self, test_name, success, message):
        """记录测试结果"""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        self.test_results.append((test_name, success, message))
        
    async def test_tj09_server_exists(self):
        """测试1：验证tj09服务器在列表中存在"""
        print("🧪 测试tj09服务器存在性...")
        
        try:
            client = MCPTestClient()
            
            # 获取服务器列表
            result = await client.call_tool("list_servers", {
                "random_string": "test_tj09_exists"
            })
            
            if not result:
                self.log_result("tj09_exists", False, "获取服务器列表失败")
                return
                
            result_text = str(result)
            
            # 验证tj09服务器存在
            if "tj09" in result_text:
                self.log_result("tj09_exists", True, "tj09服务器在列表中存在")
            else:
                self.log_result("tj09_exists", False, "tj09服务器不在列表中")
                
        except Exception as e:
            self.log_result("tj09_exists", False, f"测试异常: {str(e)}")
            
    async def test_tj09_server_config(self):
        """测试2：验证tj09服务器配置信息"""
        print("🧪 测试tj09服务器配置信息...")
        
        try:
            client = MCPTestClient()
            
            # 获取tj09服务器详细信息
            result = await client.call_tool("get_server_info", {
                "server_name": "tj09"
            })
            
            if not result:
                self.log_result("tj09_config", False, "获取服务器信息失败")
                return
                
            # 验证基本配置信息
            expected_config = {
                "host": "tjdm-isa-ai-p800node09.tjdm",
                "username": "xuyehua",
                "port": 22,
                "description": "天津P800节点09服务器",
                "connection_type": "relay"
            }
            
            config_checks = []
            for key, expected_value in expected_config.items():
                if key in result and result[key] == expected_value:
                    config_checks.append(f"✅ {key}: {expected_value}")
                else:
                    actual_value = result.get(key, "未设置")
                    config_checks.append(f"❌ {key}: 期望 {expected_value}, 实际 {actual_value}")
            
            # 检查是否所有配置都正确
            failed_checks = [check for check in config_checks if check.startswith("❌")]
            
            if not failed_checks:
                self.log_result("tj09_config", True, 
                    f"服务器基本配置正确: {len(config_checks)}项全部通过")
            else:
                self.log_result("tj09_config", False, 
                    f"配置验证失败: {failed_checks}")
                
        except Exception as e:
            self.log_result("tj09_config", False, f"测试异常: {str(e)}")
            
    async def test_tj09_docker_config(self):
        """测试3：验证tj09 Docker配置"""
        print("🧪 测试tj09 Docker配置...")
        
        try:
            client = MCPTestClient()
            
            # 获取tj09服务器详细信息
            result = await client.call_tool("get_server_info", {
                "server_name": "tj09"
            })
            
            if not result:
                self.log_result("tj09_docker", False, "获取服务器信息失败")
                return
                
            # 验证Docker配置
            if "specs" not in result or "docker" not in result["specs"]:
                self.log_result("tj09_docker", False, "缺少Docker配置")
                return
                
            docker_config = result["specs"]["docker"]
            
            # 验证Docker配置项
            expected_docker = {
                "auto_create": True,
                "container_name": "xyh_pytorch",
                "image": "iregistry.baidu-int.com/xmlir/xmlir_ubuntu_2004_x86_64:v0.32"
            }
            
            docker_checks = []
            for key, expected_value in expected_docker.items():
                if key in docker_config and docker_config[key] == expected_value:
                    docker_checks.append(f"✅ {key}: {expected_value}")
                else:
                    actual_value = docker_config.get(key, "未设置")
                    docker_checks.append(f"❌ {key}: 期望 {expected_value}, 实际 {actual_value}")
            
            # 验证端口映射
            if "ports" in docker_config:
                expected_ports = ["8080:8080", "8888:8888", "6006:6006"]
                actual_ports = docker_config["ports"]
                missing_ports = [port for port in expected_ports if port not in actual_ports]
                
                if not missing_ports:
                    docker_checks.append("✅ 端口映射: 正确配置")
                else:
                    docker_checks.append(f"❌ 端口映射: 缺少 {missing_ports}")
            else:
                docker_checks.append("❌ 端口映射: 未配置")
            
            # 验证卷挂载
            if "volumes" in docker_config:
                expected_volumes = ["/home:/home", "/data:/data"]
                actual_volumes = docker_config["volumes"]
                missing_volumes = [vol for vol in expected_volumes if vol not in actual_volumes]
                
                if not missing_volumes:
                    docker_checks.append("✅ 卷挂载: 正确配置")
                else:
                    docker_checks.append(f"❌ 卷挂载: 缺少 {missing_volumes}")
            else:
                docker_checks.append("❌ 卷挂载: 未配置")
            
            # 检查Docker配置结果
            failed_docker = [check for check in docker_checks if check.startswith("❌")]
            
            if not failed_docker:
                self.log_result("tj09_docker", True, 
                    f"Docker配置正确: {len(docker_checks)}项全部通过")
            else:
                self.log_result("tj09_docker", False, 
                    f"Docker配置验证失败: {failed_docker}")
                
        except Exception as e:
            self.log_result("tj09_docker", False, f"测试异常: {str(e)}")
            
    async def test_tj09_connection_type(self):
        """测试4：验证tj09连接类型为relay"""
        print("🧪 测试tj09连接类型...")
        
        try:
            client = MCPTestClient()
            
            # 获取tj09服务器详细信息
            result = await client.call_tool("get_server_info", {
                "server_name": "tj09"
            })
            
            if not result:
                self.log_result("tj09_connection", False, "获取服务器信息失败")
                return
                
            # 验证连接类型
            if result.get("connection_type") == "relay":
                self.log_result("tj09_connection", True, "连接类型正确设置为relay")
            else:
                actual_type = result.get("connection_type", "未设置")
                self.log_result("tj09_connection", False, 
                    f"连接类型错误: 期望 relay, 实际 {actual_type}")
            
            # 验证relay配置
            if "specs" in result and "connection" in result["specs"]:
                connection_spec = result["specs"]["connection"]
                
                checks = []
                if connection_spec.get("tool") == "relay-cli":
                    checks.append("✅ relay工具配置正确")
                else:
                    checks.append(f"❌ relay工具: {connection_spec.get('tool')}")
                
                if "target" in connection_spec and "host" in connection_spec["target"]:
                    target_host = connection_spec["target"]["host"]
                    if target_host == "tjdm-isa-ai-p800node09.tjdm":
                        checks.append("✅ 目标主机配置正确")
                    else:
                        checks.append(f"❌ 目标主机: {target_host}")
                else:
                    checks.append("❌ 缺少目标主机配置")
                
                failed_relay = [check for check in checks if check.startswith("❌")]
                if not failed_relay:
                    self.log_result("tj09_relay_config", True, 
                        "relay连接配置正确")
                else:
                    self.log_result("tj09_relay_config", False, 
                        f"relay配置问题: {failed_relay}")
            else:
                self.log_result("tj09_relay_config", False, "缺少relay连接配置")
                
        except Exception as e:
            self.log_result("tj09_connection", False, f"测试异常: {str(e)}")
            
    async def test_tj09_status_check(self):
        """测试5：验证tj09服务器状态检查"""
        print("🧪 测试tj09服务器状态...")
        
        try:
            client = MCPTestClient()
            
            # 获取tj09服务器状态
            result = await client.call_tool("get_server_status", {
                "server_name": "tj09"
            })
            
            if not result:
                self.log_result("tj09_status", False, "获取服务器状态失败")
                return
                
            # 验证状态响应结构
            required_fields = ["server_name", "status", "message", "server_config"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                self.log_result("tj09_status", False, 
                    f"状态响应缺少字段: {missing_fields}")
            else:
                # 验证服务器名称正确
                if result["server_name"] == "tj09":
                    self.log_result("tj09_status", True, 
                        f"状态检查正常，当前状态: {result['status']}")
                else:
                    self.log_result("tj09_status", False, 
                        f"服务器名称不匹配: {result['server_name']}")
                
        except Exception as e:
            self.log_result("tj09_status", False, f"测试异常: {str(e)}")

async def run_all_tests():
    """运行所有测试"""
    test_instance = TJ09ServerCreationTest()
    
    test_methods = [
        ("tj09服务器存在性", test_instance.test_tj09_server_exists),
        ("tj09基本配置", test_instance.test_tj09_server_config),
        ("tj09 Docker配置", test_instance.test_tj09_docker_config),
        ("tj09连接类型", test_instance.test_tj09_connection_type),
        ("tj09状态检查", test_instance.test_tj09_status_check)
    ]
    
    for test_name, test_method in test_methods:
        print(f"\n🧪 开始测试: {test_name}")
        await test_method()
    
    # 统计测试结果
    total_tests = len(test_instance.test_results)
    passed_tests = sum(1 for _, success, _ in test_instance.test_results if success)
    failed_tests = total_tests - passed_tests
    
    print(f"\n📊 测试结果统计:")
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\n❌ 失败的测试:")
        for test_name, success, message in test_instance.test_results:
            if not success:
                print(f"  • {test_name}: {message}")
    
    return failed_tests == 0

def main():
    """运行tj09服务器配置创建验证测试"""
    print("🎯 开始tj09服务器配置创建验证测试")
    print("=" * 60)
    
    try:
        success = asyncio.run(run_all_tests())
        
        print("=" * 60)
        if success:
            print("🎉 所有测试通过！tj09服务器配置创建成功")
            print("✅ 服务器基本信息配置正确")
            print("✅ Docker配置完整且正确")
            print("✅ Relay连接配置正确")
            print("✅ 服务器状态检查正常")
            return 0
        else:
            print("❌ 部分测试失败！需要检查配置")
            return 1
            
    except Exception as e:
        print(f"❌ 测试执行异常: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 