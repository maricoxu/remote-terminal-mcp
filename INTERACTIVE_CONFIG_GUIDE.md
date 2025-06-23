# Remote Terminal 交互式配置指南

## 概述

Remote Terminal MCP 提供了两种配置方式：
1. **快速配置向导** - 适合新手用户，提供预设模板
2. **完整配置管理器** - 适合高级用户，提供全面控制

## 快速配置向导

### 启动方式
```bash
python3 config-helper.py --quick
```

### 服务器类型选择

#### 🖥️ 普通Linux服务器
适用于：可以直接SSH连接的服务器
- 简单配置，快速上手

#### 🌉 内网服务器
适用于：需要通过relay-cli连接的内网服务器
- 自动配置relay连接
- 支持跳板机模式

#### 🐳 Docker开发服务器
适用于：需要在Docker容器中开发的场景
- 自动容器管理
- 开发环境隔离

#### 🎯 自定义配置
适用于：有特殊需求的高级用户
- 跳转到完整配置管理器
- 支持所有高级选项

## 完整配置管理器

### 启动方式
```bash
python3 config-helper.py
```

### 功能菜单

1. **📝 创建新服务器配置**
   - 交互式配置创建
   - 支持所有连接类型
   - 配置验证和预览

2. **📋 查看现有配置**
   - 列出所有服务器
   - 显示连接状态
   - 配置详情查看

3. **✏️ 编辑服务器配置**
   - 修改现有配置
   - 增量更新
   - 配置备份

4. **🗑️ 删除服务器配置**
   - 安全删除
   - 确认提示
   - 批量操作

5. **🧪 测试服务器连接**
   - 连接验证
   - 网络测试
   - 故障诊断

6. **📤 导出配置**
   - 配置备份
   - 团队共享
   - 版本控制

7. **📥 导入配置**
   - 配置恢复
   - 批量导入
   - 格式验证

## 使用示例

### 示例1: 配置SSH服务器

**场景**：连接一台可以直接SSH访问的Linux服务器

```bash
python3 config-helper.py --quick

请选择您的服务器类型:
1. 🖥️  普通Linux服务器 (直接SSH)
2. 🌉 内网服务器 (通过relay-cli)
3. 🐳 带Docker环境的开发服务器
4. 🎯 自定义配置

请选择 (1-4): 1

🖥️ 配置普通SSH服务器
------------------------------
服务器名称 (如: dev-server): my-server
服务器地址: 192.168.1.100
用户名 [username]: 
✅ SSH服务器 'my-server' 配置完成
```

### 示例2: 配置内网服务器

**场景**：需要连接公司内网的开发服务器

```bash
python3 config-helper.py --quick

请选择您的服务器类型:
1. 🖥️  普通Linux服务器 (直接SSH)
2. 🌉 内网服务器 (通过relay-cli)
3. 🐳 带Docker环境的开发服务器
4. 🎯 自定义配置

请选择 (1-4): 2

🌉 配置内网服务器 (Relay)
------------------------------
服务器名称 (如: cpu-221): dev-server
目标服务器地址 (如: internal-server.company.com): internal-server.company.com
用户名 [username]: 
✅ 配置已保存到: /Users/username/.remote-terminal/config.yaml
✅ Relay服务器 'dev-server' 配置完成
```

**生成的配置预览**：
```yaml
dev-server:
  description: 内网服务器
  host: relay.example.com
  port: 22
  specs:
    connection:
      target:
        host: internal-server.company.com
      tool: relay
    environment:
      BOS_BUCKET: bos://bucket-name/username/template
      TMUX_SESSION_PREFIX: devserver_dev
  username: username
```

**连接测试结果**：
```
🧪 测试连接: dev-server
⏳ 正在测试连接...
✅ 服务器 internal-server.company.com 网络连通性正常
💡 完整连接测试需要使用 remote-terminal 工具
```

### 示例3: 配置Docker开发环境

**场景**：在远程服务器的Docker容器中进行开发

```bash
python3 config-helper.py --quick

请选择您的服务器类型:
1. 🖥️  普通Linux服务器 (直接SSH)
2. 🌉 内网服务器 (通过relay-cli)
3. 🐳 带Docker环境的开发服务器
4. 🎯 自定义配置

请选择 (1-4): 3

🐳 配置Docker开发服务器
------------------------------
服务器名称 (如: gpu-dev): docker-dev
服务器地址: 192.168.1.200
用户名 [username]: 
Docker容器名 [dev_container]: 
✅ Docker服务器 'docker-dev' 配置完成
```

## 高级配置选项

### 连接方式配置

1. **直接SSH连接**
   - 适用于公网或局域网服务器
   - 配置简单，连接稳定

2. **Relay跳板机连接**
   - 适用于内网服务器
   - 支持relay-cli工具
   - 自动处理认证

3. **二级跳板机连接**
   - 适用于复杂网络环境
   - 支持多级跳转
   - 灵活的路由配置

### Docker环境配置

- **容器名称**：指定要连接的容器
- **镜像名称**：容器不存在时自动创建
- **工作目录**：容器内的默认目录
- **自动创建**：智能容器管理

### 环境变量配置

- **存储桶路径**：文件同步配置
- **会话前缀**：tmux会话命名
- **自定义环境**：开发环境变量

## 配置文件位置

- **用户配置**：`~/.remote-terminal/config.yaml`
- **项目配置**：`./config/servers.yaml`
- **模板配置**：`./templates/`

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连通性
   - 验证服务器地址
   - 确认端口开放

2. **认证失败**
   - 检查用户名密码
   - 验证SSH密钥
   - 确认权限设置

3. **配置错误**
   - 使用配置验证功能
   - 检查YAML格式
   - 参考示例配置

### 调试技巧

- 使用测试连接功能
- 查看详细错误信息
- 启用调试日志
- 逐步配置验证

## 最佳实践

1. **配置管理**
   - 定期备份配置
   - 使用版本控制
   - 团队配置共享

2. **安全考虑**
   - 避免明文密码
   - 使用SSH密钥
   - 定期更新凭据

3. **性能优化**
   - 合理设置超时
   - 使用连接复用
   - 优化网络配置

---

**提示**：首次使用建议从快速配置向导开始，熟悉后再使用完整配置管理器进行高级配置。