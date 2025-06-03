# @xuyehua/remote-terminal-mcp

> 🖥️ 统一远程终端管理的MCP服务 - 让多服务器操作如本地一样简单

将复杂的远程服务器连接和管理包装成简单的NPM包，适用于任何支持MCP协议的AI Agent。

## ✨ 核心价值

- 🔗 **一键连接** - 简化复杂的SSH连接流程
- 🖥️ **统一终端** - 多个远程服务器的统一管理界面
- 📋 **会话管理** - 智能tmux会话管理
- 🛠️ **便捷操作** - 在任意服务器上执行命令
- 🔧 **零配置** - 开箱即用，自动创建默认配置
- 🚀 **通用兼容** - 适用于Cursor、Claude Desktop等所有MCP客户端

## 🎯 适用场景

### 服务器类型 ✅
- **GPU服务器** - Tesla A100、V100等
- **CPU服务器** - 高性能计算节点
- **开发服务器** - 日常开发环境
- **云主机** - AWS、阿里云、腾讯云等
- **任何SSH可达的远程机器**

### AI Agent兼容性 ✅
- **Cursor** - 智能代码编辑器
- **Claude Desktop** - Anthropic官方应用
- **VS Code** - 通过MCP扩展
- **其他MCP客户端** - 标准协议兼容

## 🚀 快速开始

### 1. 在任何MCP客户端中配置

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "npx",
      "args": ["-y", "@xuyehua/remote-terminal-mcp"],
      "disabled": false,
      "autoApprove": true
    }
  }
}
```

### 2. 重启您的AI Agent

### 3. 开始使用自然语言操作

```
"列出所有服务器"
"连接到服务器hg_223"
"在default会话中执行nvidia-smi"
"显示服务器详细信息"
```

**就是这么简单！** 🎉

---

## 🛠️ 可用功能

### 远程连接管理
- **list_servers** - 列出所有配置的服务器
- **get_server_info** - 获取服务器详细信息
- **connect_to_server** - 生成连接指令和脚本

### 终端会话管理
- **execute_command** - 在远程tmux会话中执行命令
- **list_tmux_sessions** - 列出所有可用的tmux会话

### 系统监控
- **monitor_gpu** - GPU使用情况监控（适用于GPU服务器）

### 预配置服务器示例
- **HG系列**: Tesla A100 GPU服务器 (hg_223, hg_224, hg_225, hg_226)
- **TJ系列**: Tesla V100 GPU服务器 (tj_041, tj_042, tj_043, tj_044)
- **CPU系列**: CPU计算服务器 (cpu_221)

---

## 📋 高级功能

### 🔧 个性化配置
```bash
npx @xuyehua/remote-terminal-mcp --config
```

### 📜 生成连接脚本
```bash
npx @xuyehua/remote-terminal-mcp --scripts
```
自动为所有服务器生成可执行的连接脚本，支持多种模式：
- `connect` - 直接SSH连接
- `docker` - Docker环境管理
- `tmux` - tmux会话管理
- `full` - 完整设置流程

### 🐛 调试模式
```bash
npx @xuyehua/remote-terminal-mcp --debug
```

### 🧪 功能测试
```bash
npx @xuyehua/remote-terminal-mcp --test
```

---

## 📁 配置文件

### 自动生成，无需手动配置！

```
~/.remote-terminal/
├── config.yaml          # 主配置文件
├── servers.yaml          # 服务器配置
└── scripts/              # 生成的连接脚本
    ├── connect_hg_223.sh
    ├── connect_tj_041.sh
    └── ...
```

### 添加自定义服务器
编辑 `~/.remote-terminal/servers.yaml`：
```yaml
servers:
  my_server:
    name: '我的开发服务器'
    host: 'dev.mycompany.com'
    container_name: 'my_container'
    gpu_type: 'RTX 4090'
    gpu_count: 1
    series: 'DEV'
    status: 'active'
```

---

## 🌟 设计理念

### 从复杂到简单
| 传统SSH方式 | Remote Terminal MCP |
|------------|-------------------|
| 记住多个SSH命令 | 自然语言操作 |
| 手动管理密钥 | 统一认证管理 |
| 复杂的跳板机配置 | 一键连接 |
| 各自为政的会话 | 统一会话管理 |
| 重复的环境设置 | 自动化脚本 |

### 通用兼容性
- ✅ **协议标准**: 基于MCP 2024-11-05标准
- ✅ **Agent无关**: 不绑定特定编辑器或AI工具
- ✅ **跨平台**: 支持macOS、Linux、Windows
- ✅ **扩展友好**: 易于添加新功能和服务器类型

---

## 🎯 使用案例

### 场景1: AI开发者
```
用户: "在hg_223上运行我的PyTorch训练脚本"
AI: "好的，我来帮您在HG-223 GPU服务器上执行训练脚本..."
```

### 场景2: DevOps工程师
```
用户: "检查所有TJ系列服务器的GPU使用情况"
AI: "正在检查TJ系列服务器状态..."
```

### 场景3: 数据科学家
```
用户: "在CPU服务器上运行数据预处理任务"
AI: "已在CPU-221服务器的tmux会话中启动预处理任务..."
```

---

## 🔧 环境要求

- **Node.js**: 14.0.0+
- **Python**: 3.8+ (用于MCP服务器)
- **tmux**: 2.0+ (推荐，用于会话管理)
- **SSH**: 用于远程连接

---

## 🆘 常见问题

### Q: 支持哪些AI Agent？
A: 所有支持MCP协议的AI工具，包括Cursor、Claude Desktop、VS Code等

### Q: 如何添加新服务器？
A: 编辑 `~/.remote-terminal/servers.yaml` 或运行配置向导

### Q: 是否支持密钥认证？
A: 支持，使用系统SSH配置，包括密钥文件和ssh-agent

### Q: 如何重置配置？
A: 删除 `~/.remote-terminal/` 目录，重启AI Agent

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🌟 为什么选择Remote Terminal MCP？

### 对比传统方案
| 特性 | 传统SSH | 远程桌面 | Remote Terminal MCP |
|------|---------|----------|-------------------|
| 设置复杂度 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| 资源占用 | 低 | 高 | 极低 |
| AI集成 | 无 | 无 | 原生支持 |
| 多服务器管理 | 困难 | 困难 | 简单 |
| 自动化程度 | 低 | 低 | 高 |

### 核心优势
- 🎯 **专为AI时代设计** - 原生支持自然语言操作
- 🔒 **安全可靠** - 基于标准SSH协议，无额外安全风险
- ⚡ **轻量高效** - 低资源占用，高响应速度
- 🔗 **无缝集成** - 与AI Agent深度集成，操作流畅
- 🌐 **社区驱动** - 开源项目，持续改进

---

## 📞 支持

- 📖 [文档](https://github.com/xuyehua/remote-terminal-mcp/wiki)
- 🐛 [问题反馈](https://github.com/xuyehua/remote-terminal-mcp/issues)
- 💬 [讨论](https://github.com/xuyehua/remote-terminal-mcp/discussions)
- 📧 Email: your-email@example.com

---

<p align="center">
  <strong>让远程服务器管理像本地操作一样简单</strong><br/>
  Made with ❤️ by <a href="https://github.com/xuyehua">xuyehua</a>
</p>