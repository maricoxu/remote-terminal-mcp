#!/usr/bin/env python3
"""
通过交互式向导更新已有服务器配置（新版主入口）
"""
import argparse
from config_manager.main import EnhancedConfigManager

def main():
    parser = argparse.ArgumentParser(description='通过交互式向导更新已有服务器配置')
    parser.add_argument('--force-interactive', action='store_true', help='强制进入交互式配置模式')
    parser.add_argument('--server', type=str, help='要更新的服务器名称')
    args = parser.parse_args()
    manager = EnhancedConfigManager(force_interactive=args.force_interactive)
    prefill = {'name': args.server} if args.server else {}
    manager.guided_setup(prefill=prefill, edit_server=args.server)

if __name__ == "__main__":
    main()
