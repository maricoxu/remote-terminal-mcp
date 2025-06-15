#!/usr/bin/env python3
"""
修复enhanced_config_manager.py中的删除逻辑问题
"""
import re

def fix_enhanced_config_manager():
    """修复enhanced_config_manager.py中的save_config方法"""
    
    # 读取原文件
    with open('enhanced_config_manager_fixed.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复save_config方法的签名
    content = re.sub(
        r'def save_config\(self, config: Dict\):',
        'def save_config(self, config: Dict, merge_mode: bool = True):',
        content
    )
    
    # 修复save_config方法的实现
    old_save_method = '''    def save_config(self, config: Dict, merge_mode: bool = True):
        """保存配置 - 合并到现有配置而不是覆盖"""
        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 确保servers节点存在
            if 'servers' not in existing_config:
                existing_config['servers'] = {}
            
            # 合并新的服务器配置到现有配置
            if 'servers' in config:
                existing_config['servers'].update(config['servers'])
            
            # 合并其他配置项
            for key, value in config.items():
                if key != 'servers':
                    existing_config[key] = value
            
            # 保存合并后的配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 保存配置失败: {e}", Fore.RED)'''
    
    new_save_method = '''    def save_config(self, config: Dict, merge_mode: bool = True):
        """保存配置 - 支持合并模式和覆盖模式"""
        try:
            if merge_mode:
                # 合并模式：读取现有配置并合并（用于添加新配置）
                existing_config = {}
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        existing_config = yaml.safe_load(f) or {}
                
                # 确保servers节点存在
                if 'servers' not in existing_config:
                    existing_config['servers'] = {}
                
                # 合并新的服务器配置到现有配置
                if 'servers' in config:
                    existing_config['servers'].update(config['servers'])
                
                # 合并其他配置项
                for key, value in config.items():
                    if key != 'servers':
                        existing_config[key] = value
                
                final_config = existing_config
            else:
                # 覆盖模式：直接使用传入的配置（用于删除操作）
                final_config = config
            
            # 创建备份
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup_{int(__import__('time').time())}"
                import shutil
                shutil.copy2(self.config_path, backup_path)
                self.colored_print(f"📋 已创建配置备份: {backup_path}", Fore.CYAN)
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(final_config, f, default_flow_style=False, allow_unicode=True)
                
            self.colored_print(f"✅ 配置已保存到: {self.config_path}", Fore.GREEN)
                
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 保存配置失败: {e}", Fore.RED)'''
    
    # 替换save_config方法
    content = re.sub(
        r'    def save_config\(self, config: Dict, merge_mode: bool = True\):\s*"""保存配置 - 合并到现有配置而不是覆盖""".*?(?=\n    def|\nclass|\n\n\nclass|\Z)',
        new_save_method,
        content,
        flags=re.DOTALL
    )
    
    # 修复删除服务器的调用，使用覆盖模式
    content = re.sub(
        r'(del config\[\'servers\'\]\[server_name\]\s*\n\s*)(self\.save_config\(config\))',
        r'\1\2  # 使用覆盖模式保存，确保删除生效\n                    self.save_config(config, merge_mode=False)',
        content
    )
    
    # 保存修复后的文件
    with open('enhanced_config_manager_fixed.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ enhanced_config_manager.py 修复完成！")
    print("🔧 主要修复内容：")
    print("   1. save_config方法支持merge_mode参数")
    print("   2. 删除操作使用覆盖模式(merge_mode=False)")
    print("   3. 添加配置备份机制")
    print("   4. 改进日志输出")

if __name__ == "__main__":
    fix_enhanced_config_manager() 