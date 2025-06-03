# 🚀 Cursor-Bridge MCP 快速设置指南

## 📋 完整设置流程

### 第1步: 安装并配置MCP
在 `~/.cursor/mcp.json` 中添加：
```json
{
  "mcpServers": {
    "cursor-bridge": {
      "command": "npx",
      "args": ["-y", "@xuyehua/cursor-bridge-mcp"],
      "disabled": false,
      "autoApprove": true
    }
  }
}
```

### 第2步: 首次启动配置 (自动)
重启Cursor后，cursor-bridge会自动：
- ✅ 创建配置目录 `~/.cursor-bridge/`
- ✅ 生成默认配置文件
- ✅ 设置9台服务器信息

**无需手动配置！** 🎉

### 第3步: 个性化配置 (可选)
```bash
# 运行配置向导
npx @xuyehua/cursor-bridge-mcp --config
```

---

## 📁 配置文件说明

### 主配置文件: `~/.cursor-bridge/config.yaml`
```yaml
version: '0.1.0'
settings:
  default_tmux_session: 'default'    # 默认会话名
  auto_create_session: true          # 自动创建会话
  debug_mode: false                  # 调试模式
  bos_bucket: 'bos:/klx-pytorch-work-bd-bj/xuyehua/template'
  connection_timeout: 30             # 连接超时(秒)
  retry_attempts: 3                  # 重试次数

preferences:
  show_gpu_info: true                # 显示GPU信息
  auto_attach_tmux: false           # 自动连接tmux
  preferred_shell: 'zsh'            # 首选Shell
```

### 服务器配置: `~/.cursor-bridge/servers.yaml`
已预配置9台服务器：
- **HG系列** (Tesla A100): hg_223, hg_224, hg_225, hg_226
- **TJ系列** (Tesla V100): tj_041, tj_042, tj_043, tj_044  
- **CPU系列**: cpu_221

---

## 🎯 使用场景

### 场景1: 查看服务器状态
```
在Cursor中问: "列出所有HG系列服务器"
```

### 场景2: 执行命令
```  
在Cursor中说: "在default会话中执行 nvidia-smi"
```

### 场景3: 服务器连接
```
在Cursor中说: "连接到hg_223服务器"
```

---

## 🔧 高级配置

### 自定义服务器
编辑 `~/.cursor-bridge/servers.yaml`：
```yaml
servers:
  my_server:
    name: '我的GPU服务器'
    host: 'my-gpu-server.com'
    container_name: 'my_container'
    gpu_type: 'RTX 4090'
    gpu_count: 2
    series: 'CUSTOM'
    status: 'active'
```

### 调试模式
```bash
# 查看详细日志
npx @xuyehua/cursor-bridge-mcp --debug
```

### 功能测试
```bash
# 验证所有功能
npx @xuyehua/cursor-bridge-mcp --test
```

---

## 🆘 常见问题

### Q: 配置文件在哪里？
A: `~/.cursor-bridge/` 目录下，首次启动自动创建

### Q: 如何添加新服务器？
A: 编辑 `~/.cursor-bridge/servers.yaml` 或运行配置向导

### Q: tmux命令失败怎么办？
A: 确保tmux已安装: `brew install tmux` (macOS)

### Q: 如何重置配置？
A: 删除 `~/.cursor-bridge/` 目录，重启Cursor

---

## 💡 设计哲学

**零配置原则**: 开箱即用，高级用户可深度定制
**渐进增强**: 从简单使用到专业配置的平滑过渡