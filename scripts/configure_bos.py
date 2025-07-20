#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOS 自动配置脚本

这个脚本可以自动配置 bcecmd 工具，支持从环境变量或配置文件读取 BOS 凭据
"""

import os
import sys
import time
import subprocess
import yaml
from pathlib import Path


def log_output(message):
    """输出日志信息"""
    print(f"🔧 {message}")


def read_bos_config():
    """从配置文件或环境变量读取 BOS 配置"""
    bos_config = {}
    
    # 1. 尝试从环境变量读取
    access_key = os.getenv('BOS_ACCESS_KEY')
    secret_key = os.getenv('BOS_SECRET_KEY')
    bucket = os.getenv('BOS_BUCKET')
    config_path = os.getenv('BOS_CONFIG_PATH')
    
    if access_key and secret_key:
        log_output("从环境变量读取 BOS 配置")
        bos_config = {
            'access_key': access_key,
            'secret_key': secret_key,
            'bucket': bucket or 'bos://klx-pytorch-work-bd-bj',
            'config_path': config_path or 'xuyehua/template'
        }
        return bos_config
    
    # 2. 尝试从配置文件读取
    config_files = [
        '/Users/xuyehua/.remote-terminal/config.yaml',
        '/Users/xuyehua/.remote-terminal/bos_config.yaml',
        './bos_config.yaml'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 查找 BOS 配置
                if 'servers' in config:
                    for server_name, server_config in config['servers'].items():
                        if 'bos' in server_config.get('specs', {}):
                            bos_config = server_config['specs']['bos']
                            if bos_config.get('access_key') and bos_config.get('access_key') != 'your_access_key':
                                log_output(f"从配置文件读取 BOS 配置: {config_file}")
                                return bos_config
                
                # 直接的 BOS 配置
                if 'bos' in config:
                    bos_config = config['bos']
                    if bos_config.get('access_key') and bos_config.get('access_key') != 'your_access_key':
                        log_output(f"从配置文件读取 BOS 配置: {config_file}")
                        return bos_config
                        
            except Exception as e:
                log_output(f"读取配置文件失败 {config_file}: {e}")
                continue
    
    return None


def configure_bcecmd_interactive():
    """交互式配置 bcecmd"""
    log_output("开始交互式 BOS 配置...")
    
    print("\n请输入 BOS 配置信息:")
    access_key = input("Access Key ID: ").strip()
    secret_key = input("Secret Access Key: ").strip()
    
    if not access_key or not secret_key:
        log_output("❌ Access Key 和 Secret Key 不能为空")
        return False
    
    return configure_bcecmd_with_keys(access_key, secret_key)


def configure_bcecmd_with_keys(access_key, secret_key, region='bj', domain='bcebos.com'):
    """使用提供的密钥配置 bcecmd"""
    try:
        log_output("配置 bcecmd...")
        
        # 检查 bcecmd 是否存在
        result = subprocess.run(['which', 'bcecmd'], capture_output=True, text=True)
        if result.returncode != 0:
            log_output("❌ bcecmd 工具未找到，请先安装 bcecmd")
            return False
        
        bcecmd_path = result.stdout.strip()
        log_output(f"找到 bcecmd: {bcecmd_path}")
        
        # 创建配置过程
        log_output("启动 bcecmd 配置...")
        
        # 使用 pexpect 或者直接写配置文件
        config_dir = Path.home() / '.bcecmd'
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / 'config.json'
        config_content = {
            "access_key_id": access_key,
            "secret_access_key": secret_key,
            "region": region,
            "domain": domain,
            "protocol": "https"
        }
        
        import json
        with open(config_file, 'w') as f:
            json.dump(config_content, f, indent=2)
        
        log_output(f"✅ BOS 配置已写入: {config_file}")
        
        # 测试配置
        log_output("测试 BOS 连接...")
        test_result = subprocess.run([bcecmd_path, 'bos', 'ls'], 
                                   capture_output=True, text=True, timeout=10)
        
        if test_result.returncode == 0:
            log_output("✅ BOS 连接测试成功！")
            return True
        else:
            log_output(f"⚠️ BOS 连接测试失败: {test_result.stderr}")
            return False
            
    except Exception as e:
        log_output(f"❌ 配置 bcecmd 失败: {e}")
        return False


def download_bos_configs(bucket, config_path):
    """从 BOS 下载配置文件"""
    try:
        log_output(f"从 BOS 下载配置文件...")
        log_output(f"源路径: {bucket}/{config_path}")
        
        # 下载配置文件
        files_to_download = [
            '.zshrc',
            '.p10k.zsh',
            '.zsh_history',
            '.oh-my-zsh'
        ]
        
        for file_name in files_to_download:
            source_path = f"{bucket}/{config_path}/{file_name}"
            target_path = f"~/{file_name}"
            
            log_output(f"下载 {file_name}...")
            result = subprocess.run(['bcecmd', 'bos', 'cp', '-r', source_path, target_path],
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                log_output(f"✅ {file_name} 下载成功")
            else:
                log_output(f"⚠️ {file_name} 下载失败: {result.stderr}")
        
        log_output("✅ 配置文件下载完成")
        return True
        
    except Exception as e:
        log_output(f"❌ 下载配置文件失败: {e}")
        return False


def main():
    """主函数"""
    log_output("BOS 自动配置工具启动")
    
    # 读取 BOS 配置
    bos_config = read_bos_config()
    
    if bos_config:
        log_output("找到 BOS 配置，开始自动配置...")
        access_key = bos_config['access_key']
        secret_key = bos_config['secret_key']
        bucket = bos_config.get('bucket', '')
        config_path = bos_config.get('config_path', '')
        
        # 配置 bcecmd
        if configure_bcecmd_with_keys(access_key, secret_key):
            # 下载配置文件
            if bucket and config_path:
                download_bos_configs(bucket, config_path)
            
            log_output("🎉 BOS 配置完成！")
            log_output("💡 建议重新启动 zsh 以应用新配置: exec zsh")
        else:
            log_output("❌ BOS 配置失败")
            return 1
    else:
        log_output("未找到 BOS 配置，启动交互式配置...")
        if not configure_bcecmd_interactive():
            log_output("❌ 交互式配置失败")
            return 1
        
        log_output("🎉 BOS 配置完成！")
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 