#!/usr/bin/env python3
"""
通过交互式向导创建新服务器配置（新版主入口）
"""
import argparse
import json
import os
from config_manager.main import EnhancedConfigManager

def main():
    parser = argparse.ArgumentParser(description='通过交互式向导创建新服务器配置')
    parser.add_argument('--force-interactive', action='store_true', help='强制进入交互式配置模式')
    parser.add_argument('--prefill-file', type=str, help='预填充参数文件路径')
    args = parser.parse_args()
    
    # 加载预填充参数
    prefill_params = {}
    if args.prefill_file and os.path.exists(args.prefill_file):
        try:
            with open(args.prefill_file, 'r', encoding='utf-8') as f:
                prefill_params = json.load(f)
            # 清理临时文件
            os.unlink(args.prefill_file)
        except Exception as e:
            print(f"警告：无法加载预填充参数文件: {e}")
    
    manager = EnhancedConfigManager(force_interactive=args.force_interactive)
    manager.guided_setup(prefill=prefill_params)

if __name__ == "__main__":
    main()
