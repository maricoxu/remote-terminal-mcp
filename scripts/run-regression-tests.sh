#!/bin/bash
# Remote Terminal MCP 回归测试运行脚本
# 确保所有修复的问题不会回归

set -e  # 遇到错误立即退出

echo "🧪 Remote Terminal MCP 回归测试套件"
echo "=================================="
echo "日期: $(date)"
echo "Python版本: $(python3 --version)"
echo ""

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试结果数组
declare -a TEST_RESULTS

# 运行单个测试的函数
run_test() {
    local test_name="$1"
    local test_file="$2"
    local test_description="$3"
    
    echo "📋 运行测试: $test_name"
    echo "   描述: $test_description"
    echo "   文件: $test_file"
    echo ""
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if python3 "$test_file"; then
        echo "✅ $test_name - 通过"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("✅ $test_name - 通过")
    else
        echo "❌ $test_name - 失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("❌ $test_name - 失败")
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
}

# 检查依赖
echo "🔍 检查测试依赖..."
if ! python3 -c "import psutil" >/dev/null 2>&1; then
    echo "⚠️  安装缺失的依赖: psutil"
    pip3 install psutil
fi

if ! python3 -c "import pexpect" >/dev/null 2>&1; then
    echo "⚠️  安装缺失的依赖: pexpect (可选)"
    pip3 install pexpect || echo "   pexpect安装失败，将跳过相关测试"
fi

echo "✅ 依赖检查完成"
echo ""

# 运行回归测试
echo "🚀 开始运行回归测试..."
echo ""

# 1. 预填充参数功能测试
run_test \
    "预填充参数功能" \
    "tests/tool_add_server_config/test_fix_save_config_parameter_mismatch_20250615.py" \
    "测试MCP工具的预填充参数功能，确保参数正确传递和显示"

# 2. 交互界面启动机制测试
run_test \
    "交互界面启动机制" \
    "python/tests/tool_connect_server/test_fix_interactive_interface_startup_20241222.py" \
    "测试交互界面启动机制，确保不启动后台进程而是提供用户指导"

# 2.1. 🔧 新增：交互启动要求测试
run_test \
    "交互启动要求" \
    "python/tests/tool_connect_server/test_fix_interactive_startup_requirement_20241222.py" \
    "测试create_server_config工具必须启动交互配置界面，验证强制交互模式修复"

# 2.2. 🔧 新增：用户可见交互界面测试
run_test \
    "用户可见交互界面" \
    "python/tests/tool_connect_server/test_fix_user_visible_interaction_20241222.py" \
    "测试用户是否真的能看到交互配置界面，验证用户体验修复"

# 3. 🔧 新增：完整交互序列和进程管理测试
run_test \
    "完整交互序列和进程管理" \
    "python/tests/tool_connect_server/test_fix_complete_interaction_and_process_management_20241222.py" \
    "测试完整的交互序列包括文件同步设置，以及进程生命周期管理"

# 4. 🔧 新增：终端清理Bug修复测试
run_test \
    "终端清理Bug修复" \
    "tests/tool_disconnect_server/test_fix_terminal_cleanup_bug_20241222.py" \
    "测试修复后的终端清理逻辑，确保AppleScript不再使用有问题的pwd命令"

# 5. 🔧 新增：Docker配置保存和显示功能测试
run_test \
    "Docker配置保存和显示功能" \
    "tests/tool_add_server_config/test_fix_config_auto_creation_removal_20241222.py" \
    "测试Docker配置的保存、显示和格式兼容性，确保预填充参数正确应用"

# 6. 🔧 新增：Docker配置自动化功能测试
run_test \
    "Docker配置自动化功能" \
    "tests/tool_add_server_config/test_docker_config_enhanced.py" \
    "测试Docker配置的完整自动化保存流程，包括端到端测试和边界情况验证"

# 7. 🔧 新增：MCP服务器重启和新代码加载测试
run_test \
    "MCP服务器重启和新代码加载" \
    "python/tests/tool_connect_server/test_fix_mcp_timeout_issue_20240622.py" \
    "测试MCP服务器重启后新代码能正确加载，修复语法错误并验证update_server_config新逻辑"

# 8. 🔧 新增：连接功能回归测试
run_test \
    "连接功能回归测试" \
    "python/tests/tool_connect_server/test_regression_prevention.py" \
    "测试连接功能的回归预防，确保新功能不影响现有功能"

# 9. 🔧 新增：端到端连接测试
run_test \
    "端到端连接测试" \
    "python/tests/tool_connect_server/test_end_to_end.py" \
    "测试完整的端到端连接流程，包括Docker环境配置"

# JavaScript语法回归测试
echo "🔍 运行JavaScript语法回归测试..."
echo ""

# 检查关键JavaScript文件的语法
js_files=(
    "index.js"
    "node_mcp_server.js" 
    "scripts/check-dependencies.js"
    "scripts/post-install.js"
)

for js_file in "${js_files[@]}"; do
    if [ -f "$js_file" ]; then
        echo "📋 检查JavaScript语法: $js_file"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        
        if node -c "$js_file" 2>/dev/null; then
            echo "✅ $js_file - 语法正确"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            TEST_RESULTS+=("✅ $js_file - 语法正确")
        else
            echo "❌ $js_file - 语法错误"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            TEST_RESULTS+=("❌ $js_file - 语法错误")
        fi
        echo ""
    fi
done

# 🔧 新增：进程清理验证
echo "🧹 进程清理验证..."
echo ""

# 检查是否有残留的测试进程
echo "📋 检查残留测试进程"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

remaining_processes=$(ps aux | grep -E "(enhanced_config_manager|test.*server)" | grep -v grep | wc -l)
if [ "$remaining_processes" -eq 0 ]; then
    echo "✅ 无残留测试进程"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TEST_RESULTS+=("✅ 无残留测试进程")
else
    echo "❌ 发现 $remaining_processes 个残留测试进程"
    echo "   残留进程列表:"
    ps aux | grep -E "(enhanced_config_manager|test.*server)" | grep -v grep | while read line; do
        echo "   $line"
    done
    FAILED_TESTS=$((FAILED_TESTS + 1))
    TEST_RESULTS+=("❌ 发现残留测试进程")
fi
echo ""

# 🔧 新增：配置文件完整性检查
echo "📁 配置文件完整性检查..."
echo ""

echo "📋 检查配置模板文件"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

template_files=(
    "templates/ssh_server.yaml"
    "templates/relay_server.yaml"
    "templates/docker_server.yaml"
    "templates/complex_server.yaml"
)

template_check_passed=true
for template in "${template_files[@]}"; do
    if [ ! -f "$template" ]; then
        echo "❌ 缺失模板文件: $template"
        template_check_passed=false
    fi
done

if $template_check_passed; then
    echo "✅ 所有配置模板文件存在"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TEST_RESULTS+=("✅ 配置模板文件完整")
else
    echo "❌ 配置模板文件不完整"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    TEST_RESULTS+=("❌ 配置模板文件不完整")
fi
echo ""

# 输出测试总结
echo "=========================================="
echo "📊 回归测试总结"
echo "=========================================="
echo "总测试数: $TOTAL_TESTS"
echo "通过: $PASSED_TESTS"
echo "失败: $FAILED_TESTS"
echo "通过率: $(python3 -c "print(f'{$PASSED_TESTS/$TOTAL_TESTS*100:.1f}%')")"
echo ""

echo "详细结果:"
for result in "${TEST_RESULTS[@]}"; do
    echo "  $result"
done
echo ""

# 🔧 新增：测试环境信息
echo "🔧 测试环境信息:"
echo "   操作系统: $(uname -s)"
echo "   Python路径: $(which python3)"
echo "   工作目录: $(pwd)"
echo "   用户: $(whoami)"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 所有回归测试通过！代码质量良好，可以安全发布。"
    exit 0
else
    echo "💥 有 $FAILED_TESTS 个测试失败！请修复问题后重新运行测试。"
    echo ""
    echo "🔧 调试建议:"
    echo "1. 检查失败的测试详细输出"
    echo "2. 确保所有依赖已正确安装"
    echo "3. 验证代码修改是否引入了回归问题"
    echo "4. 检查是否有进程或文件资源未正确清理"
    exit 1
fi 