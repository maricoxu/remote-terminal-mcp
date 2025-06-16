#!/bin/bash
# Docker容器数据备份脚本
# 自动备份重要数据到指定位置

set -e

# 配置
BACKUP_DIR="/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="container_backup_${TIMESTAMP}"
LOG_FILE="/var/log/backup.log"

# 需要备份的目录
BACKUP_SOURCES=(
    "/home"
    "/workspace"
    "/data"
    "~/.config"
    "~/.ssh"
)

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"

log "开始数据备份: $BACKUP_NAME"

# 创建备份归档
BACKUP_FILE="$BACKUP_DIR/$BACKUP_NAME.tar.gz"

# 备份数据
tar -czf "$BACKUP_FILE" \
    --exclude="*.tmp" \
    --exclude="*.log" \
    --exclude=".cache" \
    --exclude="node_modules" \
    --exclude="__pycache__" \
    "${BACKUP_SOURCES[@]}" 2>/dev/null || true

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "备份完成: $BACKUP_FILE (大小: $BACKUP_SIZE)"
    
    # 清理旧备份（保留最近7天）
    if [ "${AUTO_CLEANUP:-false}" = "true" ]; then
        find "$BACKUP_DIR" -name "container_backup_*.tar.gz" -mtime +7 -delete
        log "清理完成: 删除7天前的备份文件"
    fi
    
    # 上传到BOS（如果配置了）
    if [ ! -z "$BOS_ACCESS_KEY" ] && [ ! -z "$BOS_SECRET_KEY" ] && [ ! -z "$BOS_BUCKET" ]; then
        python3 -c "
import bos
import os
bos.upload('$BOS_BUCKET', 'backups/$BACKUP_NAME.tar.gz', '$BACKUP_FILE')
print('备份已上传到BOS')
" 2>/dev/null || log "BOS上传失败"
    fi
else
    log "备份失败: 无法创建备份文件"
    exit 1
fi

log "备份流程完成" 