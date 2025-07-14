#!/usr/bin/env python3
"""
通过交互式向导创建新服务器配置（新版主入口）
"""
import argparse
from config_manager.main import EnhancedConfigManager

def main():
    parser = argparse.ArgumentParser(description='通过交互式向导创建新服务器配置')
    parser.add_argument('--force-interactive', action='store_true', help='强制进入交互式配置模式')
    args = parser.parse_args()
    manager = EnhancedConfigManager(force_interactive=args.force_interactive)
    manager.guided_setup()

if __name__ == "__main__":
    main()
