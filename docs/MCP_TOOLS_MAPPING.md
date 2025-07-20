# MCP工具与Python脚本映射关系

## 🎯 工具映射概览

### 1. `create_server_config` 工具

#### **MCP工具定义**
- **工具名称**: `create_server_config`
- **描述**: 🚀 智能服务器配置创建工具 - 支持关键词识别和参数化配置
- **触发方式**: 通过MCP客户端调用

#### **对应的Python脚本**
- **脚本路径**: `python/create_server_config.py`
- **执行方式**: `python create_server_config.py [--force-interactive]`
- **核心方法**: `EnhancedConfigManager.guided_setup()`

#### **触发Prompt示例**
```
"创建一个新的服务器配置"
"我想添加一台服务器"
"添加服务器配置"
"新建服务器"
"配置服务器连接"
```

#### **MCP工具实现**
```python
# 在 mcp_server.py 中的实现
elif tool_name == "create_server_config":
    try:
        manager = EnhancedConfigManager()
        server_info = tool_arguments.copy()
        
        # 使用guided_setup方法创建服务器配置
        result = manager.guided_setup(prefill=server_info)
        
        if result:
            content = f"✅ 服务器配置创建成功\n配置: {json.dumps(result, ensure_ascii=False, indent=2)}"
        else:
            content = "❌ 服务器配置创建失败"
    except Exception as e:
        debug_log(f"create_server_config error: {str(e)}")
        content = json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
```

#### **独立脚本实现**
```python
# create_server_config.py
def main():
    parser = argparse.ArgumentParser(description='通过交互式向导创建新服务器配置')
    parser.add_argument('--force-interactive', action='store_true', help='强制进入交互式配置模式')
    args = parser.parse_args()
    manager = EnhancedConfigManager(force_interactive=args.force_interactive)
    manager.guided_setup()
```

---

### 2. `update_server_config` 工具

#### **MCP工具定义**
- **工具名称**: `update_server_config`
- **描述**: Update an existing server configuration with new parameters
- **触发方式**: 通过MCP客户端调用

#### **对应的Python脚本**
- **脚本路径**: `python/update_server_config.py`
- **执行方式**: `python update_server_config.py [--force-interactive] [--server SERVER_NAME]`
- **核心方法**: `EnhancedConfigManager.guided_setup(prefill_params=prefill, update_mode=True)`

#### **触发Prompt示例**
```
"更新服务器配置"
"修改服务器设置"
"编辑服务器配置"
"更新现有服务器"
"修改连接参数"
```

#### **MCP工具实现**
```python
# 在 mcp_server.py 中的实现
elif tool_name == "update_server_config":
    try:
        manager = EnhancedConfigManager()
        name = tool_arguments.get("name")
        update_info = tool_arguments.copy()
        update_info.pop("name", None)
        
        # 使用update_server_config方法更新服务器配置
        result = manager.update_server_config(name, **update_info)
        
        if result:
            content = f"✅ 服务器 {name} 已更新\n配置: {json.dumps(result, ensure_ascii=False, indent=2)}"
        else:
            content = f"❌ 服务器 {name} 更新失败"
    except Exception as e:
        debug_log(f"update_server_config error: {str(e)}")
        content = json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
```

#### **独立脚本实现**
```python
# update_server_config.py
def main():
    parser = argparse.ArgumentParser(description='通过交互式向导更新已有服务器配置')
    parser.add_argument('--force-interactive', action='store_true', help='强制进入交互式配置模式')
    parser.add_argument('--server', type=str, help='要更新的服务器名称')
    args = parser.parse_args()
    manager = EnhancedConfigManager(force_interactive=args.force_interactive)
    prefill = {'name': args.server} if args.server else {}
    manager.guided_setup(prefill_params=prefill, update_mode=True)
```

---

## 🔄 执行流程对比

### MCP工具执行流程
1. **用户触发**: 通过MCP客户端调用工具
2. **参数传递**: 工具参数通过JSON-RPC传递
3. **MCP服务器处理**: `mcp_server.py` 中的 `handle_request()` 函数
4. **配置管理器调用**: 调用 `EnhancedConfigManager` 的相应方法
5. **结果返回**: 通过JSON-RPC返回结果

### 独立脚本执行流程
1. **命令行调用**: 直接执行Python脚本
2. **参数解析**: 使用 `argparse` 解析命令行参数
3. **配置管理器调用**: 直接调用 `EnhancedConfigManager` 方法
4. **交互式界面**: 在终端中显示交互式配置界面
5. **结果输出**: 直接在终端输出结果

---

## 📋 参数映射关系

### create_server_config 参数

| MCP参数 | 独立脚本参数 | 说明 |
|---------|-------------|------|
| `prompt` | 无 | 用户需求描述 |
| `name` | 无 | 服务器名称 |
| `host` | 无 | 服务器主机名 |
| `username` | 无 | SSH用户名 |
| `port` | 无 | SSH端口 |
| `connection_type` | 无 | 连接类型 |
| `--force-interactive` | `--force-interactive` | 强制交互模式 |

### update_server_config 参数

| MCP参数 | 独立脚本参数 | 说明 |
|---------|-------------|------|
| `server_name` | `--server` | 服务器名称 |
| `host` | 无 | 服务器主机名 |
| `username` | 无 | SSH用户名 |
| `port` | 无 | SSH端口 |
| `--force-interactive` | `--force-interactive` | 强制交互模式 |

---

## 🎯 使用建议

### 开发调试
- **使用独立脚本**: 便于调试和测试
- **命令行参数**: 支持 `--force-interactive` 强制交互模式
- **直接调用**: 不依赖MCP服务器

### 生产环境
- **使用MCP工具**: 集成在AI助手中
- **参数化配置**: 支持预填充参数
- **交互式界面**: 提供友好的用户界面

### 测试验证
- **回归测试**: 使用 `tests/` 目录下的测试
- **功能验证**: 确保MCP工具和独立脚本行为一致
- **参数测试**: 验证各种参数组合的正确性

---

## 📝 注意事项

1. **路径一致性**: MCP工具和独立脚本使用相同的核心方法
2. **参数兼容**: 确保参数格式和类型一致
3. **错误处理**: 统一的错误处理和返回格式
4. **交互模式**: 都支持交互式和参数化两种模式
5. **配置存储**: 使用相同的配置文件格式和存储位置 