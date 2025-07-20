# BOS 自动配置指南

## 概述

当用户在配置 Docker 容器时选择了 `zsh` shell，系统现在会自动执行以下流程：

1. **先用 bash 进入容器**
2. **自动配置 BOS 登录**（使用配置中的 AK/SK）
3. **从 BOS 下载配置文件到用户目录**
4. **切换到 zsh 并应用配置**

## 自动化流程详解

### 1. 检测配置

系统会检测：
- Docker 配置中的 `shell` 设置
- 是否存在有效的 BOS 配置
- BOS 凭据是否为占位符

```python
# 检测逻辑
preferred_shell = docker_config.get('shell', 'zsh')
if preferred_shell == 'zsh' and bos_config:
    # 启动自动配置流程
```

### 2. 容器进入策略

#### 情况 A: zsh + 有 BOS 配置
```bash
# 1. 先用 bash 进入容器
docker exec -it container_name bash

# 2. 在 bash 中配置 BOS
# 3. 下载配置文件
# 4. 切换到 zsh
exec zsh
```

#### 情况 B: zsh + 无 BOS 配置
```bash
# 直接用 zsh 进入
docker exec -it container_name zsh
```

#### 情况 C: 其他 shell
```bash
# 直接用配置的 shell 进入
docker exec -it container_name bash
```

### 3. BOS 配置过程

#### 3.1 创建配置目录
```bash
mkdir -p ~/.bcecmd
```

#### 3.2 生成配置文件
系统会自动创建 `~/.bcecmd/config.json`：
```json
{
  "access_key_id": "your_access_key",
  "secret_access_key": "your_secret_key",
  "region": "bj",
  "domain": "bcebos.com",
  "protocol": "https"
}
```

#### 3.3 测试连接
```bash
bcecmd bos ls > /dev/null 2>&1 && echo "BOS_CONNECTION_SUCCESS" || echo "BOS_CONNECTION_FAILED"
```

### 4. 配置文件下载

系统会尝试下载以下文件：
- `.zshrc` - zsh 主配置文件
- `.p10k.zsh` - Powerlevel10k 配置
- `.zsh_history` - 命令历史

```bash
# 下载命令示例
bcecmd bos cp bucket_name/config_path/.zshrc ~/.zshrc
bcecmd bos cp bucket_name/config_path/.p10k.zsh ~/.p10k.zsh
bcecmd bos cp bucket_name/config_path/.zsh_history ~/.zsh_history
```

### 5. 切换到 zsh

配置完成后自动切换：
```bash
exec zsh
```

如果检测到 Powerlevel10k 配置向导，会自动跳过：
```bash
# 自动按 'q' 跳过配置向导
```

## 配置要求

### BOS 配置格式

在服务器配置文件中，BOS 配置应该包含：

```yaml
servers:
  - name: "your_server"
    specs:
      bos:
        access_key: "your_real_access_key"    # 真实的 AK
        secret_key: "your_real_secret_key"    # 真实的 SK
        bucket: "your-bucket-name"            # BOS bucket 名称
        config_path: "zsh-config"             # 配置文件路径
      docker:
        shell: "zsh"                          # 触发自动配置
        container_name: "your_container"
        container_image: "your_image"
```

### BOS Bucket 结构

确保你的 BOS bucket 中有以下结构：
```
your-bucket-name/
└── zsh-config/
    ├── .zshrc
    ├── .p10k.zsh
    └── .zsh_history
```

## 错误处理

### 占位符检测

系统会检测以下占位符并跳过自动配置：
- `your_access_key`
- `your_real_access_key`
- `your_access_key_here`

### 回退机制

1. **BOS 配置失败** → 手动切换到 zsh
2. **bash 进入失败** → 尝试直接用 zsh
3. **zsh 进入失败** → 使用 bash 作为备用
4. **配置文件下载失败** → 继续使用 zsh（无自定义配置）

## 日志输出示例

```
🚪 检测到zsh配置和BOS配置，先用bash进入新容器...
✅ 成功用bash进入新容器
🔧 在bash中配置BOS和下载zsh配置文件...
📦 步骤1: 使用bash配置BOS工具...
🔑 自动配置BOS认证信息...
🔍 测试BOS连接...
✅ BOS连接成功
📥 步骤2: 从BOS下载zsh配置文件...
📥 下载 .zshrc...
✅ .zshrc 下载成功
📥 下载 .p10k.zsh...
✅ .p10k.zsh 下载成功
📥 下载 .zsh_history...
✅ .zsh_history 下载成功
✅ 至少一个配置文件下载成功
🔄 步骤3: 切换到zsh并应用配置...
🎨 检测到Powerlevel10k配置向导，自动跳过...
✅ zsh环境配置完成！
✅ BOS配置和zsh环境设置完成
```

## 手动测试

如果需要手动测试自动配置功能：

1. **准备 BOS 环境**：
   ```bash
   # 上传配置文件到 BOS
   bcecmd bos cp ~/.zshrc bos://your-bucket/zsh-config/.zshrc
   bcecmd bos cp ~/.p10k.zsh bos://your-bucket/zsh-config/.p10k.zsh
   bcecmd bos cp ~/.zsh_history bos://your-bucket/zsh-config/.zsh_history
   ```

2. **配置服务器**：
   - 在配置文件中填入真实的 BOS AK/SK
   - 设置正确的 bucket 和 config_path
   - 将 Docker shell 设置为 "zsh"

3. **连接测试**：
   ```bash
   # 使用 MCP 工具连接
   # 或使用 CLI
   python index.js connect your_server
   ```

## 优势

1. **完全自动化** - 无需手动配置 BOS 或下载文件
2. **智能检测** - 根据配置自动选择最佳流程
3. **错误恢复** - 多层回退机制确保连接成功
4. **用户友好** - 详细的日志输出和进度提示
5. **安全性** - 占位符检测避免使用无效凭据

## 注意事项

1. **网络要求** - 确保容器能访问 BOS 服务
2. **权限要求** - 确保 BOS 凭据有读取权限
3. **文件存在** - 确保 BOS 中存在所需的配置文件
4. **容器环境** - 确保容器中安装了 bcecmd 工具

## 故障排除

### 常见问题

1. **BOS 连接失败**
   - 检查 AK/SK 是否正确
   - 检查网络连接
   - 检查 bcecmd 工具是否可用

2. **配置文件下载失败**
   - 检查 bucket 和路径是否正确
   - 检查文件是否存在
   - 检查权限设置

3. **zsh 启动异常**
   - 检查 .zshrc 文件语法
   - 检查依赖是否安装
   - 查看错误日志

### 调试命令

```bash
# 检查 BOS 配置
cat ~/.bcecmd/config.json

# 测试 BOS 连接
bcecmd bos ls

# 检查下载的文件
ls -la ~/.zshrc ~/.p10k.zsh ~/.zsh_history

# 测试 zsh 配置
zsh -n ~/.zshrc
```

---

这个自动化流程大大简化了 zsh 环境的配置过程，让用户能够快速获得一个完全配置好的开发环境。 