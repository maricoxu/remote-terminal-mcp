"""
AutoSyncManager - 自动同步管理器

负责处理远程服务器的自动同步功能，包括：
1. 部署proftpd服务器到远程Docker容器
2. 配置并启动FTP服务
3. 设置本地SFTP连接
4. 提供文件同步功能
"""

import os
import time
import base64
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

def log_output(message: str, level: str = "INFO"):
    """日志输出函数"""
    import sys
    levels = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌"
    }
    prefix = levels.get(level, "ℹ️")
    print(f"{prefix} {message}")
    sys.stdout.flush()

@dataclass
class SyncConfig:
    """同步配置"""
    remote_workspace: str = "/home/Code"
    ftp_port: int = 8021
    ftp_user: str = "ftpuser"
    ftp_password: str = "sync_password"
    local_workspace: str = ""
    auto_sync: bool = True
    sync_patterns: list = None
    exclude_patterns: list = None

    def __post_init__(self):
        if self.sync_patterns is None:
            self.sync_patterns = ["*.py", "*.js", "*.ts", "*.json", "*.md", "*.txt"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["*.pyc", "__pycache__", ".git", "node_modules", ".DS_Store"]

class AutoSyncManager:
    """自动同步管理器"""
    
    def __init__(self, session_name: str):
        """
        初始化AutoSyncManager
        
        Args:
            session_name: tmux会话名称
        """
        self.session_name = session_name
        self.proftpd_source = Path.home() / ".remote-terminal" / "templates" / "proftpd.tar.gz"
        self.is_deployed = False
        self.is_running = False
        self.sync_config = None
        
    def setup_auto_sync(self, sync_config: SyncConfig) -> Tuple[bool, str]:
        """
        设置自动同步环境
        
        Args:
            sync_config: 同步配置
            
        Returns:
            Tuple[bool, str]: (是否成功, 结果消息)
        """
        try:
            self.sync_config = sync_config
            log_output("🚀 开始设置自动同步环境...", "INFO")
            log_output(f"   远程工作目录: {sync_config.remote_workspace}", "INFO")
            log_output(f"   FTP端口: {sync_config.ftp_port}", "INFO")
            log_output(f"   FTP用户: {sync_config.ftp_user}", "INFO")
            
            # 步骤1: 检查proftpd.tar.gz文件
            if not self._validate_proftpd_source():
                return False, "proftpd.tar.gz文件不存在"
            
            # 步骤2: 创建远程工作目录
            success, msg = self._create_remote_workspace(sync_config.remote_workspace)
            if not success:
                return False, f"创建远程工作目录失败: {msg}"
            
            # 步骤3: 部署proftpd
            success, msg = self._deploy_proftpd(sync_config.remote_workspace)
            if not success:
                return False, f"部署proftpd失败: {msg}"
            
            # 步骤4: 配置并启动proftpd
            success, msg = self._configure_and_start_proftpd(sync_config)
            if not success:
                return False, f"配置proftpd失败: {msg}"
            
            # 步骤5: 配置本地SFTP
            success, msg = self._configure_local_sftp(sync_config)
            if not success:
                log_output(f"⚠️ 本地SFTP配置失败: {msg}", "WARNING")
                log_output("💡 请手动配置SFTP客户端", "INFO")
            
            self.is_deployed = True
            self.is_running = True
            log_output("✅ 自动同步环境设置完成", "SUCCESS")
            return True, "自动同步环境设置成功"
            
        except Exception as e:
            log_output(f"设置自动同步环境异常: {str(e)}", "ERROR")
            return False, f"设置自动同步环境异常: {str(e)}"
    
    def _validate_proftpd_source(self) -> bool:
        """验证proftpd.tar.gz文件是否存在"""
        if not self.proftpd_source.exists():
            log_output(f"❌ 未找到proftpd.tar.gz: {self.proftpd_source}", "ERROR")
            return False
        
        # 检查文件大小
        file_size = self.proftpd_source.stat().st_size
        log_output(f"📦 找到proftpd.tar.gz, 大小: {file_size / 1024:.1f}KB", "INFO")
        return True
    
    def _create_remote_workspace(self, remote_workspace: str) -> Tuple[bool, str]:
        """创建远程工作目录"""
        try:
            log_output(f"📁 创建远程工作目录: {remote_workspace}", "INFO")
            
            # 创建目录命令
            create_cmd = f"mkdir -p {remote_workspace}"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, create_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 验证目录创建
            check_cmd = f"ls -la {remote_workspace} && echo 'WORKSPACE_CREATED'"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'WORKSPACE_CREATED' in result.stdout:
                log_output("✅ 远程工作目录创建成功", "SUCCESS")
                return True, "远程工作目录创建成功"
            else:
                return False, "远程工作目录创建失败"
                
        except Exception as e:
            return False, f"创建远程工作目录异常: {str(e)}"
    
    def _deploy_proftpd(self, remote_workspace: str) -> Tuple[bool, str]:
        """部署proftpd到远程服务器"""
        try:
            log_output("📦 部署proftpd到远程服务器...", "INFO")
            
            # 切换到远程工作目录
            cd_cmd = f"cd {remote_workspace}"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, cd_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 使用base64编码传输proftpd.tar.gz
            log_output("📤 使用base64编码传输proftpd.tar.gz...", "INFO")
            
            # 读取文件并base64编码
            with open(self.proftpd_source, 'rb') as f:
                file_content = f.read()
            
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # 分块传输（避免命令行长度限制）
            chunk_size = 1000
            chunks = [encoded_content[i:i+chunk_size] for i in range(0, len(encoded_content), chunk_size)]
            
            log_output(f"📤 分{len(chunks)}块传输文件...", "INFO")
            
            # 清空目标文件
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'rm -f proftpd.tar.gz.b64', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 逐块写入
            for i, chunk in enumerate(chunks):
                if i == 0:
                    cmd = f"echo '{chunk}' > proftpd.tar.gz.b64"
                else:
                    cmd = f"echo '{chunk}' >> proftpd.tar.gz.b64"
                
                subprocess.run(['tmux', 'send-keys', '-t', self.session_name, cmd, 'Enter'],
                             capture_output=True)
                time.sleep(0.1)
                
                # 显示进度
                if i % 100 == 0:
                    progress = int((i + 1) / len(chunks) * 100)
                    log_output(f"📤 传输进度: {progress}%", "INFO")
            
            # 解码文件
            log_output("🔄 解码文件...", "INFO")
            decode_cmd = "base64 -d proftpd.tar.gz.b64 > proftpd.tar.gz && rm proftpd.tar.gz.b64"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, decode_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 验证文件传输
            check_cmd = "ls -la proftpd.tar.gz && echo 'PROFTPD_UPLOADED'"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'PROFTPD_UPLOADED' in result.stdout:
                log_output("✅ proftpd.tar.gz上传成功", "SUCCESS")
                
                # 解压文件
                log_output("📦 解压proftpd.tar.gz...", "INFO")
                extract_cmd = "tar -xzf proftpd.tar.gz && echo 'PROFTPD_EXTRACTED'"
                subprocess.run(['tmux', 'send-keys', '-t', self.session_name, extract_cmd, 'Enter'],
                             capture_output=True)
                time.sleep(3)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                      capture_output=True, text=True)
                
                if 'PROFTPD_EXTRACTED' in result.stdout:
                    log_output("✅ proftpd解压成功", "SUCCESS")
                    return True, "proftpd部署成功"
                else:
                    return False, "proftpd解压失败"
            else:
                return False, "proftpd.tar.gz上传失败"
                
        except Exception as e:
            return False, f"部署proftpd异常: {str(e)}"
    
    def _configure_and_start_proftpd(self, sync_config: SyncConfig) -> Tuple[bool, str]:
        """配置并启动proftpd服务"""
        try:
            log_output("⚙️ 配置并启动proftpd服务...", "INFO")
            
            # 进入proftpd目录
            cd_cmd = "cd proftpd"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, cd_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 执行初始化脚本
            log_output("🔧 执行初始化脚本...", "INFO")
            init_cmd = f"bash ./init.sh {sync_config.remote_workspace}"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, init_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(5)
            
            # 检查初始化结果
            result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                  capture_output=True, text=True)
            
            log_output("📋 初始化脚本输出:", "INFO")
            # 显示最后几行输出
            output_lines = result.stdout.split('\n')[-10:]
            for line in output_lines:
                if line.strip():
                    log_output(f"   {line.strip()}", "DEBUG")
            
            # 启动proftpd服务
            log_output("🚀 启动proftpd服务...", "INFO")
            start_cmd = f"bash ./start.sh"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, start_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 验证服务启动
            check_cmd = f"netstat -tlnp | grep {sync_config.ftp_port} && echo 'PROFTPD_RUNNING'"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'PROFTPD_RUNNING' in result.stdout or str(sync_config.ftp_port) in result.stdout:
                log_output(f"✅ proftpd服务已启动，监听端口: {sync_config.ftp_port}", "SUCCESS")
                log_output(f"   FTP用户: {sync_config.ftp_user}", "INFO")
                log_output(f"   工作目录: {sync_config.remote_workspace}", "INFO")
                return True, "proftpd服务启动成功"
            else:
                return False, "proftpd服务启动失败"
                
        except Exception as e:
            return False, f"配置proftpd异常: {str(e)}"
    
    def _configure_local_sftp(self, sync_config: SyncConfig) -> Tuple[bool, str]:
        """配置本地SFTP连接"""
        try:
            log_output("🔧 配置本地SFTP...", "INFO")
            
            # 创建SFTP配置目录
            sftp_config_dir = Path.home() / ".remote-terminal" / "sftp_configs"
            sftp_config_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成SFTP配置文件
            sftp_config = {
                "host": "localhost",
                "port": sync_config.ftp_port,
                "username": sync_config.ftp_user,
                "password": sync_config.ftp_password,
                "remotePath": sync_config.remote_workspace,
                "localPath": sync_config.local_workspace or os.getcwd(),
                "uploadOnSave": True,
                "syncMode": "full",
                "ignore": sync_config.exclude_patterns
            }
            
            # 保存配置文件
            config_file = sftp_config_dir / f"sftp_config_{self.session_name}.json"
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(sftp_config, f, indent=2, ensure_ascii=False)
            
            log_output(f"✅ SFTP配置已保存到: {config_file}", "SUCCESS")
            log_output("💡 配置信息:", "INFO")
            log_output(f"   主机: localhost:{sync_config.ftp_port}", "INFO")
            log_output(f"   用户: {sync_config.ftp_user}", "INFO")
            log_output(f"   远程路径: {sync_config.remote_workspace}", "INFO")
            log_output(f"   本地路径: {sync_config.local_workspace or os.getcwd()}", "INFO")
            
            return True, "SFTP配置成功"
            
        except Exception as e:
            return False, f"配置SFTP异常: {str(e)}"
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            "is_deployed": self.is_deployed,
            "is_running": self.is_running,
            "session_name": self.session_name,
            "proftpd_source": str(self.proftpd_source),
            "sync_config": self.sync_config.__dict__ if self.sync_config else None
        }
    
    def stop_sync_service(self) -> Tuple[bool, str]:
        """停止同步服务"""
        try:
            if not self.is_running:
                return True, "同步服务未运行"
            
            log_output("🛑 停止proftpd服务...", "INFO")
            
            # 查找并停止proftpd进程
            stop_cmd = "pkill -f proftpd"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, stop_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            # 验证服务停止
            check_cmd = f"netstat -tlnp | grep {self.sync_config.ftp_port} || echo 'PROFTPD_STOPPED'"
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'PROFTPD_STOPPED' in result.stdout:
                log_output("✅ proftpd服务已停止", "SUCCESS")
                self.is_running = False
                return True, "同步服务停止成功"
            else:
                return False, "同步服务停止失败"
                
        except Exception as e:
            return False, f"停止同步服务异常: {str(e)}"

def create_auto_sync_manager(session_name: str) -> AutoSyncManager:
    """创建AutoSyncManager实例"""
    return AutoSyncManager(session_name) 