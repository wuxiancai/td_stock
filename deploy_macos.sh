#!/bin/bash
# -*- coding: utf-8 -*-
# A股九转序列识别系统 - macOS 部署脚本
# 作者: AI Assistant
# 版本: 1.0
# 适用系统: macOS

set -e  # 遇到错误立即退出

# 设置字符编码
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$SCRIPT_DIR" || "$SCRIPT_DIR" == "/" ]]; then
    echo "错误: 无法确定脚本所在目录"
    echo "当前工作目录: $(pwd)"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查macOS版本
check_macos() {
    log_step "检查macOS版本..."
    
    if [[ "$(uname)" != "Darwin" ]]; then
        log_error "此脚本仅适用于macOS系统"
        exit 1
    fi
    
    MACOS_VERSION=$(sw_vers -productVersion)
    log_info "当前macOS版本: $MACOS_VERSION"
    
    # 检查是否安装了Homebrew
    if ! command -v brew &> /dev/null; then
        log_warn "未检测到Homebrew，建议安装以便管理依赖"
        log_info "安装命令: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    else
        log_info "Homebrew已安装: $(brew --version | head -n1)"
    fi
}

# 检查Python版本
check_python_version() {
    log_step "检查Python版本..."
    
    # 检查Python3是否可用
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装或不在PATH中"
        log_info "建议通过Homebrew安装: brew install python"
        exit 1
    fi
    
    # 获取Python版本
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    log_info "当前Python版本: $PYTHON_VERSION"
    
    # 检查版本要求（建议Python 3.8+）
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
        log_warn "当前Python版本 $PYTHON_VERSION 可能存在兼容性问题"
        log_warn "建议使用Python 3.8或更高版本"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_info "Python版本检查通过"
}

# 检查项目文件
check_project_files() {
    log_step "检查项目文件完整性..."
    
    cd "$SCRIPT_DIR"
    
    # 检查关键文件
    REQUIRED_FILES=("requirements.txt" "config.py" "run_daily.py" "test_system.py")
    REQUIRED_DIRS=("core" "utils" "web")
    
    log_info "检查关键文件..."
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "关键文件 $file 不存在"
            log_error "当前目录: $SCRIPT_DIR"
            log_error "请确保在项目根目录运行此脚本"
            exit 1
        fi
        log_info "✓ $file"
    done
    
    log_info "检查关键目录..."
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_error "关键目录 $dir 不存在"
            log_error "当前目录: $SCRIPT_DIR"
            log_error "请确保在项目根目录运行此脚本"
            exit 1
        fi
        log_info "✓ $dir/"
    done
    
    log_info "项目文件完整性检查通过"
}

# 设置Python虚拟环境
setup_python_env() {
    log_step "设置Python虚拟环境..."
    
    cd "$SCRIPT_DIR"
    
    # 创建虚拟环境
    if [[ ! -d "venv" ]]; then
        log_info "创建Python虚拟环境..."
        python3 -m venv venv
    else
        log_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    log_info "升级pip..."
    pip install --upgrade pip
    
    # 安装依赖
    log_info "安装Python依赖包..."
    
    # 先尝试安装TA-Lib（可能失败）
    if pip install TA-Lib; then
        log_info "TA-Lib安装成功"
    else
        log_warn "TA-Lib安装失败，将跳过技术指标功能"
        log_warn "如需使用技术指标，请参考以下方法手动安装:"
        log_warn "1. 通过Homebrew安装: brew install ta-lib"
        log_warn "2. 然后安装Python包: pip install TA-Lib"
    fi
    
    # 安装其他依赖（排除TA-Lib）
    log_info "安装其他依赖包..."
    pip install -r requirements.txt || {
        log_warn "部分依赖包安装失败，尝试跳过问题包..."
        # 创建临时requirements文件，排除可能有问题的包
        grep -v "^TA-Lib" requirements.txt > temp_requirements.txt
        pip install -r temp_requirements.txt
        rm temp_requirements.txt
    }
    
    log_info "Python环境配置完成"
}

# 创建必要目录
create_directories() {
    log_step "创建必要目录..."
    
    cd "$SCRIPT_DIR"
    
    # 创建数据目录
    mkdir -p data/raw data/processed
    mkdir -p logs
    mkdir -p html_charts
    
    log_info "目录创建完成"
}

# 运行测试
run_tests() {
    log_step "运行系统测试..."
    
    cd "$SCRIPT_DIR"
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 运行测试
    if python test_system.py; then
        log_info "系统测试通过"
    else
        log_error "系统测试失败，请检查错误信息"
        return 1
    fi
}

# 启动Web服务
start_web_service() {
    log_step "启动Web服务..."
    
    cd "$SCRIPT_DIR"
    
    # 激活虚拟环境
    source venv/bin/activate
    
    log_info "启动Flask Web服务..."
    log_info "访问地址: http://localhost:5000"
    log_info "按 Ctrl+C 停止服务"
    
    # 启动Web服务
    cd web
    python app.py
}

# 显示部署信息
show_deployment_info() {
    log_step "部署完成信息"
    
    echo
    echo "======================================"
    echo "    TD分析系统部署完成！"
    echo "======================================"
    echo
    echo "🌐 Web访问地址: http://localhost:5000"
    echo "📁 项目目录: $SCRIPT_DIR"
    echo "👤 运行用户: $(whoami)"
    echo
    echo "🔧 启动命令:"
    echo "  cd $SCRIPT_DIR"
    echo "  source venv/bin/activate"
    echo "  cd web && python app.py"
    echo
    echo "📋 其他命令:"
    echo "  运行测试: python test_system.py"
    echo "  每日分析: python run_daily.py"
    echo "  查看日志: tail -f logs/td_analysis.log"
    echo
    echo "💡 提示:"
    echo "  - 如需使用技术指标功能，请手动安装TA-Lib"
    echo "  - 建议在虚拟环境中运行所有Python命令"
    echo "  - 数据文件保存在 data/ 目录下"
    echo "  - 图表文件保存在 html_charts/ 目录下"
    echo
    echo "======================================"
}

# 主函数
main() {
    echo "======================================"
    echo "  A股九转序列识别系统 - macOS部署脚本"
    echo "  适用系统: macOS"
    echo "  版本: 1.0"
    echo "======================================"
    echo
    
    # 显示基本信息
    log_info "脚本执行信息:"
    log_info "  脚本路径: ${BASH_SOURCE[0]}"
    log_info "  项目目录: $SCRIPT_DIR"
    log_info "  当前用户: $(whoami)"
    log_info "  工作目录: $(pwd)"
    echo
    
    # 检查系统
    check_macos
    
    # 检查Python版本
    check_python_version
    
    # 预检查项目文件
    check_project_files
    
    # 确认部署
    echo
    log_warn "即将开始部署，此过程将:"
    echo "  1. 创建Python虚拟环境"
    echo "  2. 安装项目依赖包"
    echo "  3. 创建必要目录"
    echo "  4. 运行系统测试"
    echo "  5. 提供启动说明"
    echo
    read -p "确认继续部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    echo
    log_info "开始部署..."
    echo
    
    # 执行部署步骤
    setup_python_env
    create_directories
    run_tests
    
    # 显示部署信息
    show_deployment_info
    
    # 询问是否立即启动Web服务
    echo
    read -p "是否立即启动Web服务? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_web_service
    else
        log_info "部署完成！请按照上述说明手动启动服务。"
    fi
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@"