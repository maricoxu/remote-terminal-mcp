#!/bin/bash

# 创建用户配置文件
echo "🔧 创建真实的用户配置文件..."

cat > ~/.remote-terminal/config.yaml << 'EOF'
# 用户自定义配置文件
# 这是我的真实服务器配置，不应该被覆盖
# 创建时间: $(date)

servers:
  my-production-server:
    type: script_based
    host: production.example.com
    port: 22
    username: deploy
    description: "生产环境服务器"
    session:
      name: "prod_deploy"
    specs:
      connection:
        type: ssh
        timeout: 30
      environment_setup:
        shell: bash
        working_directory: "/var/www"
        
  my-dev-server:
    type: script_based  
    host: dev.example.com
    port: 2222
    username: developer
    description: "开发环境服务器"
    session:
      name: "dev_work"
    specs:
      connection:
        type: ssh
        timeout: 30
      environment_setup:
        shell: zsh
        working_directory: "/home/developer/projects"

global_settings:
  default_timeout: 60
  auto_recovery: true
  log_level: DEBUG
  default_shell: zsh

security_settings:
  strict_host_key_checking: false
  connection_timeout: 45
  max_retry_attempts: 5

# 重要的用户数据
user_notes: |
  这个配置文件包含了我的重要服务器信息
  请不要自动覆盖这个文件
  最后更新: $(date)
EOF

echo "✅ 用户配置文件已创建"
echo "📄 文件路径: ~/.remote-terminal/config.yaml"
echo "📊 文件信息:"
ls -la ~/.remote-terminal/config.yaml
echo ""
echo "📝 文件内容预览:"
head -10 ~/.remote-terminal/config.yaml 