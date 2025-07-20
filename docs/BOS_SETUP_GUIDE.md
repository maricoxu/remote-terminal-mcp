# BOS 自动配置指南

## 概述

我们已经为 Docker 容器环境创建了完整的 BOS (Baidu Object Storage) 自动配置功能。这个功能可以自动配置 `bcecmd` 工具并从 BOS 下载个人配置文件。

## 🎯 功能特性

1. **自动 bcecmd 配置**: 使用 JSON 配置文件直接配置 BOS 凭据
2. **配置文件下载**: 自动从 BOS 下载 `.zshrc`, `.p10k.zsh`, `.zsh_history` 等配置文件
3. **智能检测**: 检测 bcecmd 工具可用性和 BOS 连接状态
4. **错误处理**: 完整的错误处理和用户友好的提示信息

## 📁 相关文件

### 在容器中创建的文件：
- `~/.bcecmd/config.json.example` - BOS 配置模板文件
- `/tmp/setup_bos_complete.sh` - 完整的 BOS 配置和下载脚本
- `/tmp/apply_bos_config.sh` - 简单的配置应用脚本

### 在项目中创建的文件：
- `configure_bos.py` - Python 版本的 BOS 配置脚本
- `bos_config.yaml.example` - YAML 格式的配置示例

## 🚀 使用方法

### 方法 1: 手动配置（推荐）

1. **编辑配置文件**:
   ```bash
   # 在容器中编辑配置模板
   nano ~/.bcecmd/config.json.example
   ```

2. **填入真实的 BOS 凭据**:
   ```json
   {
     "access_key_id": "your_real_access_key",
     "secret_access_key": "your_real_secret_key",
     "region": "bj",
     "domain": "bcebos.com",
     "protocol": "https"
   }
   ```

3. **应用配置**:
   ```bash
   cp ~/.bcecmd/config.json.example ~/.bcecmd/config.json
   ```

4. **运行完整配置脚本**:
   ```bash
   /tmp/setup_bos_complete.sh
   ```

### 方法 2: 环境变量配置

1. **设置环境变量**:
   ```bash
   export BOS_ACCESS_KEY="your_real_access_key"
   export BOS_SECRET_KEY="your_real_secret_key"
   export BOS_BUCKET="bos://klx-pytorch-work-bd-bj"
   export BOS_CONFIG_PATH="xuyehua/template"
   ```

2. **运行 Python 配置脚本**:
   ```bash
   python3 /tmp/configure_bos.py
   ```

### 方法 3: 自动化配置（通过 MCP）

当使用 MCP 远程终端工具连接到配置了 BOS 的 Docker 容器时，系统会自动：

1. 检测 `bcecmd` 工具的可用性
2. 读取配置中的 BOS 凭据
3. 自动配置 `bcecmd`
4. 下载个人配置文件
5. 设置 zsh 环境

## 📋 配置文件结构

### bcecmd 配置文件 (`~/.bcecmd/config.json`)
```json
{
  "access_key_id": "your_access_key",
  "secret_access_key": "your_secret_key",
  "region": "bj",
  "domain": "bcebos.com",
  "protocol": "https"
}
```

### MCP 服务器配置中的 BOS 部分
```yaml
specs:
  bos:
    access_key: "your_real_access_key"
    secret_key: "your_real_secret_key"
    bucket: "bos://klx-pytorch-work-bd-bj"
    config_path: "xuyehua/template"
```

## 🔧 脚本功能说明

### `/tmp/setup_bos_complete.sh`
- 检查 BOS 配置文件是否存在
- 测试 BOS 连接
- 下载配置文件 (`.zshrc`, `.p10k.zsh`, `.zsh_history`)
- 提供完整的状态反馈

### `configure_bos.py`
- 支持从环境变量或配置文件读取 BOS 凭据
- 自动创建 bcecmd 配置文件
- 测试 BOS 连接
- 下载配置文件

## 🎯 下载的配置文件

从 BOS 路径 `bos://klx-pytorch-work-bd-bj/xuyehua/template/` 下载：

1. **`.zshrc`** - zsh 配置文件
2. **`.p10k.zsh`** - Powerlevel10k 主题配置
3. **`.zsh_history`** - zsh 历史记录

## ⚠️ 注意事项

1. **安全性**: 
   - 不要在代码中硬编码 BOS 凭据
   - 使用环境变量或安全的配置文件
   - 确保配置文件权限正确 (`chmod 600 ~/.bcecmd/config.json`)

2. **网络要求**:
   - 确保容器可以访问 BOS 服务
   - 检查防火墙和网络策略

3. **工具依赖**:
   - 确保 `bcecmd` 工具已安装
   - 确保 `jq` 工具可用（用于 JSON 处理）

## 🔍 故障排除

### 常见问题

1. **bcecmd 未找到**:
   ```bash
   # 检查 bcecmd 安装
   which bcecmd
   # 或者查找 bcecmd
   find / -name "bcecmd" 2>/dev/null
   ```

2. **BOS 连接失败**:
   ```bash
   # 测试 BOS 连接
   bcecmd bos ls
   # 检查配置
   cat ~/.bcecmd/config.json
   ```

3. **配置文件下载失败**:
   ```bash
   # 手动测试下载
   bcecmd bos cp bos://klx-pytorch-work-bd-bj/xuyehua/template/.zshrc ~/.zshrc
   ```

### 调试命令

```bash
# 检查 BOS 配置
cat ~/.bcecmd/config.json

# 测试 BOS 连接
bcecmd bos ls

# 查看可用的 bucket
bcecmd bos ls bos://

# 查看特定路径内容
bcecmd bos ls bos://klx-pytorch-work-bd-bj/xuyehua/template/
```

## 🎉 成功标志

配置成功后，你应该看到：

1. ✅ BOS 连接测试成功
2. ✅ 配置文件下载完成
3. ✅ zsh 环境配置完整
4. ✅ Powerlevel10k 主题正常显示

## 📞 支持

如果遇到问题，请检查：
1. BOS 凭据是否正确
2. 网络连接是否正常
3. bcecmd 工具是否正确安装
4. 配置文件路径是否存在

---

*此文档描述了完整的 BOS 自动配置流程，确保开发环境的一致性和便利性。* 