# NPM包启动方式调试日志 (2025-06-12)

## 核心目标

将 `remote-terminal` MCP服务的启动方式，从本地Python脚本直接执行，切换为通过NPM包（`npx`）启动，以实现更标准化的分发和版本管理。

## 调试全过程回顾

我们遇到了一个极其顽固的 `Permission denied` 错误，并在解决它的过程中，排除了一系列关于 `npx` 和 `npm` 的错误假设。

### 阶段一：初步尝试与 `Permission denied`

- **尝试**: 使用简单的 `npx @xuyehua/remote-terminal-mcp` 命令。
- **问题**: `sh: /opt/homebrew/bin/remote-terminal-mcp: Permission denied`。
- **初步诊断**: `npm` 在通过 `bin` 字段创建可执行文件时，未能赋予它 `+x` (可执行) 权限。

### 阶段二：解决权限问题的多种尝试 (全部失败)

这是我们投入精力最多的阶段，我们尝试了所有标准和非标准的解决方案，但 **`Permission denied`** 问题依然存在。

1.  **假设：`git`权限未设置**
    - **验证**: `git ls-files --stage bin/cli.js` 返回 `100755`，证明 `git` 中的文件权限是正确的。
    - **结论**: 此假设错误。

2.  **假设：`npm publish`过程丢失权限**
    - **修复方案A (v0.4.56)**: 使用 `postinstall` 钩子运行 `chmod +x bin/cli.js`。
    - **结果**: 失败，权限问题依旧。
    - **修复方案B (v0.4.57)**: 使用Node.js脚本 (`scripts/postinstall.js`) 和 `fs.chmodSync` 来执行权限修改，以排除对外部 `chmod` 命令的依赖。
    - **结果**: 依然失败，权限问题顽固如初。

### 阶段三：绕过 `bin` 命令，探索其他 `npx` 模式

在意识到直接执行 `bin` 命令存在无法解决的权限问题后，我们试图寻找其他 `npx` 的执行方式。

1.  **尝试：`npx --package <pkg> -c "node bin/cli.js"`**
    - **问题**: `EUSAGE` 错误，日志显示 `npx` 收到的参数是 `node` 和 `bin/cli.js` 两个，而不是一个。
    - **诊断**: Cursor的Supervisor进程启动器会自动按空格分割 `args` 数组中的字符串。

2.  **尝试：`npx --package <pkg> -c "sh -c 'node bin/cli.js'"`**
    - **目的**: 使用 `sh -c` 将命令封装为单个参数，防止被Supervisor分割。
    - **问题**: 仍然是 `EUSAGE` 错误。
    - **诊断**: 通过详细日志发现，`npx` 执行命令时的当前工作目录 (`cwd`) 是根目录 `/`，而不是包所在的临时目录。因此 `sh` 找不到 `node` 或 `bin/cli.js`。

3.  **尝试：`npx --package <pkg> -- node bin/cli.js`**
    - **目的**: 使用 `npx` 的参数透传模式 (`--`)。
    - **问题**: `Error: Cannot find module '/bin/cli.js'` 或 `.../tmp-mcp-local-test/bin/cli.js`。
    - **诊断**: 在本地测试后，我们最终确认，`npx` 的透传模式并 **不会** 将工作目录切换到下载的包内，而是在当前 `cwd` 执行命令，导致 `node` 找不到脚本。

## 最终结论与未来方向

- **核心障碍**: 在Cursor的执行环境中，我们似乎无法通过任何 `postinstall` 或 `npx` 的已知机制，来解决 `npm` 安装的 `bin` 脚本的 `Permission denied` 问题。这强烈暗示问题可能源于Cursor环境自身的安全策略或限制，而非我们的包或 `npm` 的通用行为。

- **短期方案**: 已回归到直接执行Python脚本的模式，保证工具的可用性。

- **长期建议**:
    1.  向Cursor官方寻求支持，提供我们这份详细的日志，询问在他们的环境中通过 `npx` 运行自定义 `bin` 命令的最佳实践，以及是否存在已知的权限限制。
    2.  如果无法解决，可以考虑放弃 `bin` 的方式，转而设计一个纯粹的、作为库被调用的Node.js模块，然后用一个简单的、无需特殊权限的包装脚本来启动它。

---
这份日志记录了我们严谨的、基于证据的、但最终未果的探索。这是一次宝贵的学习经历。 