# 🚀 Remote Terminal MCP 快速开始

## ✨ 三步上手，操作任意远程服务器

### 步骤1: 配置MCP
在任何支持MCP的AI Agent中（如 `~/.cursor/mcp.json`）添加：
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

### 步骤2: 重启AI Agent
重启Cursor、Claude Desktop或您使用的AI工具

### 步骤3: 自然语言操作
直接与AI对话：
- "列出所有可用的服务器"
- "连接到hg_223服务器"  
- "在服务器上执行nvidia-smi命令"
- "显示tj_041的详细信息"

**就这么简单！** 🎉

---

## 🛠️ 高级使用

### 🔧 自定义配置
```bash
npx @xuyehua/remote-terminal-mcp --config
```

### 📜 生成连接脚本（可直接在终端使用）
```bash
npx @xuyehua/remote-terminal-mcp --scripts
```

### 🐛 调试问题
```bash
npx @xuyehua/remote-terminal-mcp --debug
```

---

## 🎯 核心理念

### **让远程服务器操作像本地一样简单**

| 之前 | 现在 |
|------|------|
| 记住复杂SSH命令 | 自然语言描述需求 |
| 手动管理多个终端 | AI统一管理会话 |
| 重复输入服务器信息 | 一次配置，永久使用 |
| 特定工具绑定 | 任何AI Agent都能用 |

### **适用场景**
- 🖥️ **开发**: 多环境代码部署
- 🎮 **AI/ML**: GPU集群训练任务
- 🔧 **运维**: 服务器状态监控
- 📊 **数据**: 分布式数据处理

---

## 📁 自动配置文件

**首次使用自动创建，零手动配置！**

```
~/.remote-terminal/
├── config.yaml          # 主配置
├── servers.yaml          # 服务器列表
└── scripts/              # 连接脚本
```

---

## 🆘 支持所有MCP兼容的AI工具

- ✅ **Cursor** - 智能代码编辑器
- ✅ **Claude Desktop** - Anthropic官方应用  
- ✅ **VS Code** - 通过MCP扩展
- ✅ **任何MCP客户端** - 标准协议兼容

---

## 💡 从"复杂SSH"到"自然对话"

不再需要记住这些：
```bash
ssh -J jumper.baidu.com hg_223.bjhw
docker exec -it xyh_pytorch bash  
tmux attach -t ml_training || tmux new -s ml_training
```

只需告诉AI：
```
"在hg_223上的ml_training会话中运行我的训练脚本"
```

**这就是AI时代的远程服务器管理方式！** 🌟