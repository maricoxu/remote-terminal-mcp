# 高级模式默认化设计方案

## 设计理念

将当前的"快速模式 + 高级模式"双轨制改为"统一高级模式 + 智能默认值"的单轨制，既保持功能完整性，又提供优秀的用户体验。

## 核心原则

### 1. 渐进式复杂度披露 (Progressive Disclosure)
- **默认简单**：首次显示最常用的配置项
- **按需展开**：用户可以选择查看更多选项
- **智能推荐**：根据用户选择自动调整显示内容

### 2. 智能默认值系统
- **上下文感知**：根据连接类型提供相应默认值
- **用户学习**：记住用户的常用配置模式
- **环境适配**：根据系统环境自动调整默认值

### 3. 配置模板化
- **场景模板**：为常见使用场景提供预设模板
- **一键应用**：快速应用模板并允许微调
- **自定义模板**：用户可以保存自己的配置模板

## 界面设计

### 主配置流程

```
🚀 Remote Terminal 配置向导
==================================================

📋 基本信息
┌─────────────────────────────────────────────────┐
│ 服务器名称: [my-server          ] 💡 用于识别  │
│ 服务器地址: [192.168.1.100      ] 💡 IP或域名  │
│ 用户名:     [username           ] 💡 登录用户  │
│ 端口:       [22                 ] 💡 SSH端口   │
└─────────────────────────────────────────────────┘

🔗 连接方式 (选择一种)
┌─────────────────────────────────────────────────┐
│ ○ 直接SSH连接     (适用于公网/局域网服务器)      │
│ ● 跳板机连接      (适用于内网服务器)            │
│ ○ 二级跳板机      (适用于复杂网络环境)          │
└─────────────────────────────────────────────────┘

📦 高级选项 (可选) [展开 ▼]
┌─────────────────────────────────────────────────┐
│ 🐳 Docker配置                                   │
│   ☑ 启用Docker支持                             │
│   容器名: [dev-container        ]               │
│   镜像:   [ubuntu:20.04         ]               │
│                                                 │
│ 🌐 环境配置                                     │
│   存储桶: [bos://bucket/user/... ] (可选)       │
│   会话名: [myserver_dev         ]               │
│                                                 │
│ 🔧 连接选项                                     │
│   超时:   [30                   ] 秒            │
│   重试:   [3                    ] 次            │
└─────────────────────────────────────────────────┘

[< 上一步]  [预览配置]  [保存并测试 >]
```

### 智能默认值示例

#### 场景1: 选择"直接SSH连接"
```
自动填充:
- 端口: 22
- 超时: 30秒
- 重试: 3次
- Docker: 关闭
- 会话名: {服务器名}_dev
```

#### 场景2: 选择"跳板机连接"
```
自动显示:
- 跳板机配置区域
- 目标服务器配置
- relay-cli相关选项

自动填充:
- 跳板机端口: 22
- 连接工具: relay-cli
- 存储桶: bos://default-bucket/{用户名}/template
```

#### 场景3: 启用Docker支持
```
自动显示:
- 容器管理选项
- 镜像配置
- 工作目录设置

自动填充:
- 容器名: {服务器名}_container
- 镜像: ubuntu:20.04
- 工作目录: /workspace
```

## 技术实现

### 1. 配置模板系统

```python
class ConfigTemplate:
    """配置模板类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.defaults = {}
        self.required_fields = []
        self.optional_fields = []
        self.conditional_fields = {}
    
    def apply_defaults(self, user_input: dict) -> dict:
        """应用默认值"""
        config = self.defaults.copy()
        config.update(user_input)
        return config
    
    def get_fields_for_context(self, context: dict) -> list:
        """根据上下文获取需要显示的字段"""
        fields = self.required_fields.copy()
        
        # 根据条件添加字段
        for condition, field_list in self.conditional_fields.items():
            if self._evaluate_condition(condition, context):
                fields.extend(field_list)
        
        return fields

# 预定义模板
TEMPLATES = {
    "ssh_direct": ConfigTemplate(
        name="直接SSH连接",
        description="适用于公网或局域网服务器"
    ),
    "ssh_relay": ConfigTemplate(
        name="跳板机连接", 
        description="适用于内网服务器"
    ),
    "docker_dev": ConfigTemplate(
        name="Docker开发环境",
        description="容器化开发环境"
    )
}
```

### 2. 智能默认值生成器

```python
class SmartDefaultsGenerator:
    """智能默认值生成器"""
    
    def __init__(self):
        self.user_preferences = self._load_user_preferences()
        self.system_info = self._get_system_info()
    
    def generate_defaults(self, context: dict) -> dict:
        """生成智能默认值"""
        defaults = {}
        
        # 基于连接类型
        if context.get('connection_type') == 'relay':
            defaults.update(self._get_relay_defaults())
        elif context.get('connection_type') == 'ssh':
            defaults.update(self._get_ssh_defaults())
        
        # 基于用户历史
        defaults.update(self._get_user_preference_defaults())
        
        # 基于系统环境
        defaults.update(self._get_system_defaults())
        
        return defaults
    
    def _get_relay_defaults(self) -> dict:
        """获取跳板机连接的默认值"""
        return {
            'port': 22,
            'connection_tool': 'relay-cli',
            'bos_bucket': f'bos://default-bucket/{getpass.getuser()}/template',
            'tmux_session_prefix': 'relay_dev'
        }
    
    def _get_user_preference_defaults(self) -> dict:
        """基于用户偏好的默认值"""
        # 分析用户历史配置，提取常用模式
        return self.user_preferences.get('common_patterns', {})
```

### 3. 渐进式界面控制器

```python
class ProgressiveUIController:
    """渐进式界面控制器"""
    
    def __init__(self):
        self.current_step = 1
        self.total_steps = 6
        self.expanded_sections = set()
        self.user_context = {}
    
    def render_step(self, step: int) -> str:
        """渲染当前步骤"""
        if step == 1:
            return self._render_basic_info()
        elif step == 2:
            return self._render_connection_type()
        elif step == 3:
            return self._render_advanced_options()
        # ... 其他步骤
    
    def _render_advanced_options(self) -> str:
        """渲染高级选项（可展开）"""
        if 'advanced' not in self.expanded_sections:
            return self._render_collapsed_advanced()
        else:
            return self._render_expanded_advanced()
    
    def handle_user_input(self, input_data: dict):
        """处理用户输入并更新上下文"""
        self.user_context.update(input_data)
        
        # 根据输入调整界面
        if input_data.get('connection_type') == 'relay':
            self.expanded_sections.add('relay_config')
        
        if input_data.get('enable_docker'):
            self.expanded_sections.add('docker_config')
```

## 用户体验流程

### 新手用户流程
1. **基本信息填写** - 只显示必要字段，提供清晰的帮助文本
2. **连接方式选择** - 图形化选择，自动应用相应默认值
3. **一键完成** - 大部分用户可以直接保存，无需进入高级选项
4. **可选微调** - 需要时可以展开高级选项进行调整

### 高级用户流程
1. **快速识别** - 通过界面提示快速定位到需要的配置项
2. **批量配置** - 支持同时配置多个相关选项
3. **模板应用** - 可以基于已有配置创建新的配置
4. **专家模式** - 可以直接编辑YAML配置文件

### 配置复用流程
1. **模板保存** - 将常用配置保存为个人模板
2. **快速应用** - 新建配置时可以选择已有模板
3. **批量创建** - 基于模板批量创建相似配置
4. **团队共享** - 导出模板供团队成员使用

## 实现计划

### Phase 1: 核心框架 (1周)
- [ ] 配置模板系统
- [ ] 智能默认值生成器
- [ ] 渐进式界面控制器
- [ ] 基础UI重构

### Phase 2: 智能化功能 (1周)
- [ ] 用户偏好学习
- [ ] 上下文感知配置
- [ ] 自动配置验证
- [ ] 智能错误提示

### Phase 3: 高级功能 (1周)
- [ ] 配置模板管理
- [ ] 批量操作支持
- [ ] 配置导入导出增强
- [ ] 团队协作功能

### Phase 4: 优化完善 (1周)
- [ ] 性能优化
- [ ] 用户体验测试
- [ ] 文档更新
- [ ] 向后兼容性确保

## 兼容性考虑

### 向后兼容
- 保持现有配置文件格式兼容
- 提供配置迁移工具
- 保留命令行参数支持

### 渐进迁移
- 新用户默认使用新界面
- 老用户可以选择升级
- 提供并行使用期

### 配置共享
- 新旧格式互相转换
- 团队配置标准化
- 版本控制友好

## 成功指标

### 用户体验指标
- 配置完成时间 < 2分钟
- 新手成功率 > 95%
- 用户满意度 > 4.5/5

### 技术指标
- 配置验证准确率 > 99%
- 默认值命中率 > 80%
- 错误恢复成功率 > 90%

### 采用指标
- 新界面使用率 > 80%
- 模板使用率 > 60%
- 配置错误率 < 5%

---

**总结**：通过统一高级模式 + 智能默认值的设计，我们可以为用户提供既强大又易用的配置体验，满足从新手到专家的各种需求。 