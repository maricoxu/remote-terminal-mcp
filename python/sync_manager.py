#!/usr/bin/env python3
"""
同步管理器 - 处理文件同步和Git同步功能
"""

import os
import subprocess
import logging
import time
import threading
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import yaml
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """同步配置"""
    enabled: bool = False
    local_path: str = ""
    remote_path: str = ""
    ftp_port: int = 8021
    ftp_user: str = "syncuser"
    ftp_password: str = "syncpass"
    auto_sync_interval: int = 30
    sync_type: str = "rsync"  # rsync, ftp, git


class SyncManager:
    """同步管理器"""
    
    def __init__(self, config_path: str = "~/.remote-terminal/config.yaml"):
        self.config_path = Path(config_path).expanduser()
        self.sync_threads: Dict[str, threading.Thread] = {}
        self.sync_running: Dict[str, bool] = {}
        self.sync_logs: Dict[str, List[str]] = {}
        
    def load_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """加载服务器配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('servers', {}).get(server_name)
        except Exception as e:
            logger.error(f"加载服务器配置失败: {e}")
            return None
    
    def save_server_config(self, server_name: str, sync_config: SyncConfig) -> bool:
        """保存服务器同步配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'servers' not in config:
                config['servers'] = {}
            if server_name not in config['servers']:
                config['servers'][server_name] = {}
            
            config['servers'][server_name]['sync_config'] = {
                'enabled': sync_config.enabled,
                'local_path': sync_config.local_path,
                'remote_path': sync_config.remote_path,
                'ftp_port': sync_config.ftp_port,
                'ftp_user': sync_config.ftp_user,
                'ftp_password': sync_config.ftp_password,
                'auto_sync_interval': sync_config.auto_sync_interval,
                'sync_type': sync_config.sync_type
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            logger.error(f"保存服务器配置失败: {e}")
            return False
    
    def validate_paths(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """验证同步路径"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 验证本地路径
        local_path_obj = Path(local_path).expanduser()
        if not local_path_obj.exists():
            result['valid'] = False
            result['errors'].append(f"本地路径不存在: {local_path}")
        elif not local_path_obj.is_dir():
            result['valid'] = False
            result['errors'].append(f"本地路径不是目录: {local_path}")
        
        # 检查磁盘空间
        try:
            stat = local_path_obj.stat()
            free_space = os.statvfs(local_path).f_frsize * os.statvfs(local_path).f_bavail
            if free_space < 1024 * 1024 * 100:  # 100MB
                result['warnings'].append(f"本地磁盘空间不足: {free_space / (1024*1024):.1f}MB")
        except Exception as e:
            result['warnings'].append(f"无法检查磁盘空间: {e}")
        
        return result
    
    def enable_auto_sync(self, server_name: str, local_path: Optional[str] = None, 
                        remote_path: Optional[str] = None) -> Dict[str, Any]:
        """启用自动同步 - 新实现逻辑"""
        try:
            # 加载现有配置
            server_config = self.load_server_config(server_name)
            if not server_config:
                return {'success': False, 'error': f'服务器 {server_name} 配置不存在'}
            
            # 获取同步配置
            sync_config_data = server_config.get('sync_config', {})
            sync_config = SyncConfig(
                enabled=True,
                local_path=local_path or sync_config_data.get('local_path', ''),
                remote_path=remote_path or sync_config_data.get('remote_path', ''),
                ftp_port=sync_config_data.get('ftp_port', 8021),
                ftp_user=sync_config_data.get('ftp_user', 'syncuser'),
                ftp_password=sync_config_data.get('ftp_password', 'syncpass'),
                auto_sync_interval=sync_config_data.get('auto_sync_interval', 30),
                sync_type=sync_config_data.get('sync_type', 'rsync')
            )
            
            # 1. 检查远端proftpd进程
            logger.info(f"检查远端proftpd进程: {server_name}")
            proftpd_running = self._check_remote_proftpd(server_config)
            
            if not proftpd_running:
                logger.info(f"远端proftpd未运行，开始部署: {server_name}")
                # 2. 上传proftpd tar包并部署
                deploy_result = self._deploy_remote_proftpd(server_config, sync_config)
                if not deploy_result['success']:
                    return deploy_result
            
            # 3. 更新本地sftp.json配置
            logger.info(f"更新本地sftp.json配置: {server_name}")
            sftp_config_result = self._update_sftp_config(server_name, server_config, sync_config)
            if not sftp_config_result['success']:
                return sftp_config_result
            
            # 4. 保存同步配置
            if not self.save_server_config(server_name, sync_config):
                return {'success': False, 'error': '保存配置失败'}
            
            return {
                'success': True,
                'message': f'自动同步已启用: {server_name}',
                'config': {
                    'local_path': sync_config.local_path,
                    'remote_path': sync_config.remote_path,
                    'ftp_port': sync_config.ftp_port,
                    'ftp_user': sync_config.ftp_user,
                    'sync_type': sync_config.sync_type,
                    'interval': sync_config.auto_sync_interval
                },
                'deployment': {
                    'proftpd_running': proftpd_running,
                    'deployed': not proftpd_running
                }
            }
            
        except Exception as e:
            logger.error(f"启用自动同步失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def disable_auto_sync(self, server_name: str) -> Dict[str, Any]:
        """禁用自动同步 - 新实现逻辑"""
        try:
            # 加载服务器配置
            server_config = self.load_server_config(server_name)
            if not server_config:
                return {'success': False, 'error': f'服务器 {server_name} 配置不存在'}
            
            # 1. 远程执行stop.sh
            logger.info(f"远程执行stop.sh: {server_name}")
            stop_result = self._execute_remote_stop(server_config)
            if not stop_result['success']:
                return stop_result
            
            # 2. 更新配置
            sync_config_data = server_config.get('sync_config', {})
            sync_config = SyncConfig(
                enabled=False,
                local_path=sync_config_data.get('local_path', ''),
                remote_path=sync_config_data.get('remote_path', ''),
                ftp_port=sync_config_data.get('ftp_port', 8021),
                ftp_user=sync_config_data.get('ftp_user', 'syncuser'),
                ftp_password=sync_config_data.get('ftp_password', 'syncpass'),
                auto_sync_interval=sync_config_data.get('auto_sync_interval', 30),
                sync_type=sync_config_data.get('sync_type', 'rsync')
            )
            self.save_server_config(server_name, sync_config)
            
            return {
                'success': True,
                'message': f'自动同步已禁用: {server_name}',
                'remote_stop': stop_result
            }
            
        except Exception as e:
            logger.error(f"禁用自动同步失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def git_sync(self, server_name: str, commit_hash: Optional[str] = None, 
                branch: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """Git代码同步 - 新实现逻辑"""
        try:
            # 加载配置
            server_config = self.load_server_config(server_name)
            if not server_config:
                return {'success': False, 'error': f'服务器 {server_name} 配置不存在'}
            
            sync_config_data = server_config.get('sync_config', {})
            local_path = sync_config_data.get('local_path', '')
            remote_path = sync_config_data.get('remote_path', '')
            
            if not local_path:
                return {'success': False, 'error': '未配置本地路径'}
            
            if not remote_path:
                return {'success': False, 'error': '未配置远程路径'}
            
            local_path_obj = Path(local_path).expanduser()
            
            # 1. 本地git stash
            logger.info(f"执行本地git stash: {local_path}")
            stash_result = self._execute_local_git_stash(local_path_obj)
            if not stash_result['success']:
                return stash_result
            
            # 2. 远程到本地同步
            logger.info(f"远程到本地同步: {remote_path} -> {local_path}")
            sync_result = self._sync_remote_to_local(server_config, remote_path, local_path)
            if not sync_result['success']:
                return sync_result
            
            return {
                'success': True,
                'message': f'Git同步成功: {server_name}',
                'stash': stash_result,
                'sync': sync_result
            }
            
        except Exception as e:
            logger.error(f"Git同步失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_git_sync(self, repo_path: Path, commit_hash: Optional[str], 
                         branch: Optional[str], force: bool) -> Dict[str, Any]:
        """执行Git同步操作"""
        try:
            commands = []
            
            # 1. 保存当前工作
            commands.append(['git', 'stash', 'push', '-m', 'Auto sync before update'])
            
            # 2. 获取最新代码
            commands.append(['git', 'fetch', '--all'])
            
            # 3. 根据参数选择同步方式
            if commit_hash:
                commands.append(['git', 'checkout', commit_hash])
            elif branch:
                commands.append(['git', 'checkout', branch])
                commands.append(['git', 'pull', 'origin', branch])
            else:
                # 默认同步到最新
                commands.append(['git', 'pull', 'origin', 'main'])
            
            # 4. 如果强制同步，重置到指定状态
            if force and (commit_hash or branch):
                if commit_hash:
                    commands.append(['git', 'reset', '--hard', commit_hash])
                elif branch:
                    commands.append(['git', 'reset', '--hard', f'origin/{branch}'])
            
            # 执行命令
            results = []
            for cmd in commands:
                try:
                    result = subprocess.run(
                        cmd, 
                        cwd=repo_path, 
                        capture_output=True, 
                        text=True, 
                        timeout=60
                    )
                    results.append({
                        'command': ' '.join(cmd),
                        'success': result.returncode == 0,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    })
                    
                    if result.returncode != 0:
                        return {
                            'success': False,
                            'error': f'Git命令失败: {" ".join(cmd)}',
                            'details': result.stderr,
                            'results': results
                        }
                        
                except subprocess.TimeoutExpired:
                    return {
                        'success': False,
                        'error': f'Git命令超时: {" ".join(cmd)}',
                        'results': results
                    }
            
            return {
                'success': True,
                'message': 'Git同步成功',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"执行Git同步失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _start_sync_thread(self, server_name: str, sync_config: SyncConfig):
        """启动同步线程"""
        if server_name in self.sync_running and self.sync_running[server_name]:
            logger.info(f"同步线程已运行: {server_name}")
            return
        
        self.sync_running[server_name] = True
        self.sync_logs[server_name] = []
        
        def sync_worker():
            while self.sync_running.get(server_name, False):
                try:
                    if sync_config.sync_type == 'rsync':
                        self._rsync_sync(server_name, sync_config)
                    elif sync_config.sync_type == 'ftp':
                        self._ftp_sync(server_name, sync_config)
                    
                    time.sleep(sync_config.auto_sync_interval)
                except Exception as e:
                    logger.error(f"同步错误 {server_name}: {e}")
                    self.sync_logs[server_name].append(f"错误: {e}")
                    time.sleep(60)  # 错误后等待1分钟再重试
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
        self.sync_threads[server_name] = thread
        logger.info(f"同步线程已启动: {server_name}")
    
    def _stop_sync_thread(self, server_name: str):
        """停止同步线程"""
        self.sync_running[server_name] = False
        if server_name in self.sync_threads:
            self.sync_threads[server_name].join(timeout=5)
            del self.sync_threads[server_name]
        logger.info(f"同步线程已停止: {server_name}")
    
    def _rsync_sync(self, server_name: str, sync_config: SyncConfig):
        """rsync同步"""
        try:
            # 这里需要根据服务器配置构建rsync命令
            # 暂时记录日志
            self.sync_logs[server_name].append(
                f"rsync同步: {sync_config.local_path} -> {sync_config.remote_path}"
            )
        except Exception as e:
            logger.error(f"rsync同步失败: {e}")
    
    def _ftp_sync(self, server_name: str, sync_config: SyncConfig):
        """FTP同步"""
        try:
            # 这里需要实现FTP同步逻辑
            # 暂时记录日志
            self.sync_logs[server_name].append(
                f"FTP同步: {sync_config.local_path} -> {sync_config.remote_path}"
            )
        except Exception as e:
            logger.error(f"FTP同步失败: {e}")
    
    def get_sync_status(self, server_name: str) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            server_config = self.load_server_config(server_name)
            if not server_config:
                return {'success': False, 'error': f'服务器 {server_name} 配置不存在'}
            
            sync_config_data = server_config.get('sync_config', {})
            is_running = self.sync_running.get(server_name, False)
            
            return {
                'success': True,
                'server_name': server_name,
                'enabled': sync_config_data.get('enabled', False),
                'running': is_running,
                'config': sync_config_data,
                'logs': self.sync_logs.get(server_name, [])[-10:]  # 最近10条日志
            }
            
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_remote_proftpd(self, server_config: Dict[str, Any]) -> bool:
        """检查远端proftpd进程"""
        try:
            # 构建SSH命令检查proftpd进程
            ssh_command = self._build_ssh_command(server_config, "ps aux | grep proftpd | grep -v grep")
            result = subprocess.run(ssh_command, capture_output=True, text=True, timeout=30)
            
            # 如果返回码为0且有输出，说明proftpd正在运行
            return result.returncode == 0 and result.stdout.strip() != ""
            
        except Exception as e:
            logger.error(f"检查远端proftpd失败: {e}")
            return False
    
    def _deploy_remote_proftpd(self, server_config: Dict[str, Any], sync_config: SyncConfig) -> Dict[str, Any]:
        """部署远端proftpd"""
        try:
            # 1. 上传proftpd tar包
            tar_path = self._get_proftpd_tar_path()
            if not tar_path:
                return {'success': False, 'error': '找不到proftpd tar包'}
            
            upload_result = self._upload_file_to_remote(server_config, tar_path, "/tmp/")
            if not upload_result['success']:
                return upload_result
            
            # 2. 解压tar包
            extract_result = self._execute_remote_command(
                server_config, 
                f"cd /tmp && tar -xzf {tar_path.name}"
            )
            if not extract_result['success']:
                return extract_result
            
            # 3. 执行init.sh
            init_result = self._execute_remote_command(
                server_config,
                f"cd /tmp/proftpd && ./init.sh {sync_config.ftp_user} {sync_config.ftp_password} {sync_config.remote_path}"
            )
            if not init_result['success']:
                return init_result
            
            # 4. 执行start.sh
            start_result = self._execute_remote_command(
                server_config,
                "cd /tmp/proftpd && ./start.sh"
            )
            if not start_result['success']:
                return start_result
            
            return {
                'success': True,
                'message': 'proftpd部署成功',
                'upload': upload_result,
                'extract': extract_result,
                'init': init_result,
                'start': start_result
            }
            
        except Exception as e:
            logger.error(f"部署远端proftpd失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _update_sftp_config(self, server_name: str, server_config: Dict[str, Any], 
                           sync_config: SyncConfig) -> Dict[str, Any]:
        """更新本地sftp.json配置"""
        try:
            sftp_config_path = Path.home() / ".vscode" / "sftp.json"
            sftp_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有配置
            if sftp_config_path.exists():
                with open(sftp_config_path, 'r', encoding='utf-8') as f:
                    sftp_config = json.load(f)
            else:
                sftp_config = {"profiles": {}, "defaultProfile": ""}
            
            # 创建新的profile
            profile_name = f"{server_name}_sync"
            profile_config = {
                "name": profile_name,
                "host": server_config['host'],
                "port": server_config.get('port', 22),
                "username": server_config['username'],
                "password": server_config.get('password', ''),
                "remotePath": sync_config.remote_path,
                "localPath": sync_config.local_path,
                "protocol": "sftp"
            }
            
            # 更新配置
            sftp_config["profiles"][profile_name] = profile_config
            sftp_config["defaultProfile"] = profile_name
            
            # 保存配置
            with open(sftp_config_path, 'w', encoding='utf-8') as f:
                json.dump(sftp_config, f, indent=2, ensure_ascii=False)
            
            return {
                'success': True,
                'message': f'sftp.json配置已更新: {profile_name}',
                'profile_name': profile_name,
                'config_path': str(sftp_config_path)
            }
            
        except Exception as e:
            logger.error(f"更新sftp.json配置失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_remote_stop(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """远程执行stop.sh"""
        try:
            result = self._execute_remote_command(server_config, "cd /tmp/proftpd && ./stop.sh")
            return result
            
        except Exception as e:
            logger.error(f"远程执行stop.sh失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_local_git_stash(self, local_path: Path) -> Dict[str, Any]:
        """执行本地git stash"""
        try:
            if not local_path.exists():
                return {'success': False, 'error': f'本地路径不存在: {local_path}'}
            
            # 检查是否是Git仓库
            git_dir = local_path / '.git'
            if not git_dir.exists():
                return {'success': False, 'error': f'本地路径不是Git仓库: {local_path}'}
            
            # 执行git stash
            result = subprocess.run(
                ['git', 'stash', 'push', '-m', 'Auto sync before remote sync'],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'message': 'Git stash成功' if result.returncode == 0 else 'Git stash失败'
            }
            
        except Exception as e:
            logger.error(f"执行本地git stash失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _sync_remote_to_local(self, server_config: Dict[str, Any], remote_path: str, local_path: str) -> Dict[str, Any]:
        """远程到本地同步"""
        try:
            # 构建rsync命令
            rsync_command = self._build_rsync_command(server_config, remote_path, local_path)
            
            # 执行rsync
            result = subprocess.run(
                rsync_command,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'message': '远程到本地同步成功' if result.returncode == 0 else '远程到本地同步失败'
            }
            
        except Exception as e:
            logger.error(f"远程到本地同步失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_ssh_command(self, server_config: Dict[str, Any], command: str) -> List[str]:
        """构建SSH命令"""
        ssh_cmd = [
            'ssh',
            '-p', str(server_config.get('port', 22)),
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null'
        ]
        
        # 添加用户名和主机
        ssh_cmd.append(f"{server_config['username']}@{server_config['host']}")
        ssh_cmd.append(command)
        
        return ssh_cmd
    
    def _build_rsync_command(self, server_config: Dict[str, Any], remote_path: str, local_path: str) -> List[str]:
        """构建rsync命令"""
        rsync_cmd = [
            'rsync',
            '-avz',
            '-e', f"ssh -p {server_config.get('port', 22)} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
            f"{server_config['username']}@{server_config['host']}:{remote_path}/",
            f"{local_path}/"
        ]
        
        return rsync_cmd
    
    def _upload_file_to_remote(self, server_config: Dict[str, Any], local_path: Path, remote_dir: str) -> Dict[str, Any]:
        """上传文件到远程"""
        try:
            # 构建scp命令
            scp_cmd = [
                'scp',
                '-P', str(server_config.get('port', 22)),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                str(local_path),
                f"{server_config['username']}@{server_config['host']}:{remote_dir}"
            ]
            
            result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'message': '文件上传成功' if result.returncode == 0 else '文件上传失败'
            }
            
        except Exception as e:
            logger.error(f"上传文件到远程失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_remote_command(self, server_config: Dict[str, Any], command: str) -> Dict[str, Any]:
        """执行远程命令"""
        try:
            ssh_command = self._build_ssh_command(server_config, command)
            result = subprocess.run(ssh_command, capture_output=True, text=True, timeout=60)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'message': '远程命令执行成功' if result.returncode == 0 else '远程命令执行失败'
            }
            
        except Exception as e:
            logger.error(f"执行远程命令失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_proftpd_tar_path(self) -> Optional[Path]:
        """获取proftpd tar包路径"""
        # 可能的路径列表
        possible_paths = [
            Path(__file__).parent.parent / "assets" / "proftpd.tar.gz",
            Path(__file__).parent.parent / "tools" / "proftpd.tar.gz",
            Path.home() / ".remote-terminal" / "proftpd.tar.gz"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None


# 全局同步管理器实例
sync_manager = SyncManager()


def enable_auto_sync(server_name: str, local_path: Optional[str] = None, 
                    remote_path: Optional[str] = None) -> Dict[str, Any]:
    """启用自动同步 - MCP工具接口"""
    return sync_manager.enable_auto_sync(server_name, local_path, remote_path)


def disable_auto_sync(server_name: str) -> Dict[str, Any]:
    """禁用自动同步 - MCP工具接口"""
    return sync_manager.disable_auto_sync(server_name)


def git_sync(server_name: str, commit_hash: Optional[str] = None, 
            branch: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    """Git同步 - MCP工具接口"""
    return sync_manager.git_sync(server_name, commit_hash, branch, force)


def get_sync_status(server_name: str) -> Dict[str, Any]:
    """获取同步状态 - MCP工具接口"""
    return sync_manager.get_sync_status(server_name)


if __name__ == "__main__":
    # 测试代码
    print("同步管理器测试")
    
    # 测试启用同步
    result = enable_auto_sync("test_server", "/tmp/local", "/tmp/remote")
    print(f"启用同步结果: {result}")
    
    # 测试Git同步
    result = git_sync("test_server", branch="main")
    print(f"Git同步结果: {result}")
    
    # 测试获取状态
    result = get_sync_status("test_server")
    print(f"同步状态: {result}") 