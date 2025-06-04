# 🖥️ Remote Terminal MCP - 配置步骤

## ⚡ 3分钟快速上手

### 第1步：配置Cursor（1分钟）

在 `~/.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "remote-terminal": {
      "command": "node",
      "args": ["/Users/xuyehua/Code/remote-terminal-mcp/index.js"],
      "disabled": false,
      "autoApprove": true,
      "description": "🖥️ Remote Terminal MCP"
    }
  }
}
```

> 💡 **提示**：将路径改为你的实际项目路径

### 第2步：配置服务器（1分钟）

创建配置文件 `~/.remote-terminal-mcp/config.yaml`，复制以下示例并修改：

```yaml
servers:
  # 本地开发环境
  local-dev:
    type: "local_tmux"
    description: "本地开发会话"
    session:
      name: "dev-session"
      working_directory: "~/Code"        # 📍 改为你的代码目录
      shell: "/bin/zsh"

  # 远程服务器示例
  my-server:
    type: "script_based"
    description: "我的GPU服务器"
    connection:
      tool: "ssh"                       # 或 "relay-cli"
      mode: "direct"
      target:
        host: "gpu.company.com"         # 📍 改为你的服务器地址
        user: "admin"                   # 📍 改为你的用户名
    docker:                             # 📍 可选：Docker配置
      container_name: "dev_env"
      auto_create: true
    session:
      name: "gpu_dev"                   # 📍 改为你想要的会话名
      working_directory: "/workspace"

# 全局设置
global_settings:
  default_server: "local-dev"
  connection_timeout: 30
```

**只需修改带 📍 标记的字段即可！**

### 第3步：开始使用（1分钟）

重启Cursor后，直接和AI对话：

```
"列出所有远程服务器"
"连接到my-server" 
"在服务器上执行 nvidia-smi"
"启动服务器的开发环境"
```

---

## 📋 更多配置示例

### 🌐 百度内网服务器
```yaml
baidu-server:
  type: "script_based"
  description: "百度内网服务器"
  connection:
    tool: "relay-cli"
    mode: "direct"
    target:
      host: "server.domain.baidu"       # 📍 修改
      user: "root"
  session:
    name: "baidu_dev"
  bos:                                  # 📍 可选：BOS配置
    access_key: "your_access_key"
    secret_key: "your_secret_key"
    bucket: "bos://bucket/path"
```

### 🌊 跳板机服务器
```yaml
jump-server:
  type: "script_based"
  description: "通过跳板机访问的服务器"
  connection:
    tool: "ssh"
    mode: "jump_host"
    jump_host:
      host: "user@jump.company.com"     # 📍 修改跳板机
      password: "password"              # 📍 修改密码
    target:
      host: "private-gpu-01"            # 📍 修改目标服务器
      user: "root"
  session:
    name: "private_dev"
```

## 🛠️ 故障排除

### Cursor连接失败？
1. 检查项目路径是否正确
2. 确认 `index.js` 文件存在  
3. 重启Cursor重新加载配置

### 配置文件错误？
1. 检查YAML缩进是否正确（使用空格，不用Tab）
2. 确认所有必填字段都已填写
3. 在Cursor中问AI："检查我的服务器配置"

---

## 🎉 为什么这样更好？

| 传统方式 | 新方式 |
|---------|-------|
| 📦 需要npm安装 | 🚀 直接使用本地项目 |
| 📝 复杂配置语法 | 📋 简单示例复制修改 |
| 🔍 需要查阅文档 | ⚡ 3分钟快速上手 |
| 🐛 容易配置出错 | ✅ 标准模板保证正确 |

**无需安装，配置简单，让远程服务器管理变得高效便捷！** 🚀 