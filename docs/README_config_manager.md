# config_manager 重构说明

## 目录结构

- python/config_manager/io.py           # 配置文件读写与合并
- python/config_manager/interaction.py  # 用户交互与输入输出
- python/config_manager/server_info.py  # 服务器信息收集与校验
- python/config_manager/docker_config.py# Docker相关配置收集
- python/config_manager/sync_config.py  # 自动同步相关配置收集
- python/config_manager/main.py         # 主流程调度
- python/create_server_config.py        # 新建服务器配置入口
- python/update_server_config.py        # 更新服务器配置入口

## 主要变更点

1. **功能解耦**：将原有大类拆分为多个小模块，每个模块只负责一类功能，提升可维护性和可测试性。
2. **交互体验**：支持 --force-interactive 参数，任何环境下都能弹出交互式表单。
3. **入口清晰**：create_server_config.py 和 update_server_config.py 分别对应新建和更新，均默认走交互式向导。
4. **更新模式**：update_server_config.py 支持 --server 参数，自动带入被更新服务器信息。

## 使用方法

- 新建服务器：
  ```bash
  python python/create_server_config.py --force-interactive
  ```
- 更新服务器：
  ```bash
  python python/update_server_config.py --server 服务器名 --force-interactive
  ```

## 后续建议
- 可继续细化每个子模块的单元测试
- 进一步抽象通用交互逻辑
- 支持更多高级配置（如多级跳板机、模板批量导入等）
