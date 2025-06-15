# Bash配置文件 - Remote Terminal 默认模板
# 你可以修改此文件或复制到 ~/.remote-terminal/configs/bash/ 进行个性化定制

# 如果不是交互式shell，直接返回
[[ $- != *i* ]] && return

# 历史配置
HISTCONTROL=ignoreboth
HISTSIZE=1000
HISTFILESIZE=2000
shopt -s histappend

# 检查窗口大小
shopt -s checkwinsize

# 设置彩色提示符
if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='\u@\h:\w\$ '
fi

# 启用颜色支持
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# 常用别名
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'

# Git别名
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline'

# Docker别名
alias d='docker'
alias dc='docker-compose'
alias dps='docker ps'
alias di='docker images'

# 自定义环境变量
export EDITOR=vim
export LANG=en_US.UTF-8

# 自定义函数
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# 启动消息
echo "🐚 Bash环境已加载！"
echo "💡 这是Remote Terminal的默认bash配置"
echo "📝 你可以在 ~/.remote-terminal/configs/bash/ 中自定义配置"