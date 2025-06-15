# Remote Terminal 配置模板

这个目录包含了Remote Terminal的默认配置文件模板，在创建Docker容器时会自动使用。

## 目录结构

```
templates/configs/
├── bash/
│   └── .bashrc          # Bash默认配置模板
├── zsh/
│   └── .zshrc           # Zsh默认配置模板
└── README.md            # 本说明文件
```

## 配置优先级

系统会按以下优先级查找配置文件：

1. **用户配置** (最高优先级)
   - 位置: `~/.remote-terminal/configs/`
   - 用于个人定制配置

2. **项目模板** (中等优先级)
   - 位置: `项目根目录/templates/configs/`
   - 随npm包分发的默认配置

3. **系统默认** (最低优先级)
   - 当以上两个都不存在时使用

## 使用方法

### 方法1: 直接修改项目模板
直接编辑 `templates/configs/` 中的配置文件，适合团队共享配置。

### 方法2: 创建个人配置
```bash
# 创建个人配置目录
mkdir -p ~/.remote-terminal/configs/zsh

# 复制模板到个人配置目录
cp templates/configs/zsh/.zshrc ~/.remote-terminal/configs/zsh/

# 编辑个人配置
vim ~/.remote-terminal/configs/zsh/.zshrc
```

### 方法3: 使用现有配置
如果你已经有完善的shell配置，直接复制到对应目录：
```bash
# 复制现有的zsh配置
cp ~/.zshrc ~/.remote-terminal/configs/zsh/
cp ~/.p10k.zsh ~/.remote-terminal/configs/zsh/  # 如果使用powerlevel10k
```

## 配置文件说明

### Bash配置 (.bashrc)
- 基本的bash环境配置
- 常用别名和函数
- 彩色提示符
- 历史记录优化

### Zsh配置 (.zshrc)
- 基本的zsh环境配置
- 自动补全功能
- 常用别名和函数
- 历史记录优化
- 简洁的提示符

## 高级配置

### 添加更多配置文件
你可以在对应目录中添加更多配置文件，例如：
- `.vimrc` - Vim编辑器配置
- `.tmux.conf` - Tmux终端复用器配置
- `.gitconfig` - Git配置

### Zsh主题和插件
如果你想使用Oh My Zsh和主题，可以在.zshrc中添加：
```bash
# 安装Oh My Zsh (在容器启动脚本中)
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# 在.zshrc中配置
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"  # 或其他主题
plugins=(git docker kubectl)
source $ZSH/oh-my-zsh.sh
```

## 注意事项

- 配置文件会在Docker容器启动时复制到用户目录
- 修改配置文件后需要重新创建容器才能生效
- 建议先在本地测试配置文件的正确性
- 大型配置文件可能会影响容器启动速度