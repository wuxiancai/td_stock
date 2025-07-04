#!/bin/bash
# -*- coding: utf-8 -*-
# A股九转序列识别系统 - 依赖安装脚本
# 快速安装Python依赖包

set -e  # 遇到错误立即退出

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

# 检查Python版本
check_python() {
    log_step "检查Python版本..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python版本: $PYTHON_VERSION"
    
    # 检查版本是否满足要求（3.8+）
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_info "Python版本检查通过"
    else
        log_error "Python版本过低，需要3.8或更高版本"
        exit 1
    fi
}

# 检查pip
check_pip() {
    log_step "检查pip..."
    
    if ! command -v pip3 &> /dev/null; then
        log_warn "pip3未找到，尝试安装..."
        python3 -m ensurepip --upgrade
    fi
    
    # 升级pip
    log_info "升级pip..."
    python3 -m pip install --upgrade pip
    
    PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
    log_info "pip版本: $PIP_VERSION"
}

# 安装系统依赖（Ubuntu/Debian）
install_system_deps() {
    log_step "安装系统依赖..."
    
    if command -v apt-get &> /dev/null; then
        log_info "检测到apt包管理器，安装系统依赖..."
        sudo apt-get update
        sudo apt-get install -y \
            python3-dev \
            python3-pip \
            python3-venv \
            build-essential \
            libffi-dev \
            libssl-dev \
            libjpeg-dev \
            libpng-dev \
            libfreetype6-dev \
            pkg-config \
            gcc \
            g++
    elif command -v yum &> /dev/null; then
        log_info "检测到yum包管理器，安装系统依赖..."
        sudo yum update -y
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y \
            python3-devel \
            python3-pip \
            libffi-devel \
            openssl-devel \
            libjpeg-devel \
            libpng-devel \
            freetype-devel
    elif command -v brew &> /dev/null; then
        log_info "检测到brew包管理器（macOS），安装系统依赖..."
        brew install \
            python3 \
            libffi \
            openssl \
            jpeg \
            libpng \
            freetype \
            pkg-config
    else
        log_warn "未检测到支持的包管理器，跳过系统依赖安装"
    fi
}

# 创建虚拟环境
setup_venv() {
    log_step "设置Python虚拟环境..."
    
    VENV_DIR="venv"
    
    if [[ -d "$VENV_DIR" ]]; then
        log_warn "虚拟环境已存在: $VENV_DIR"
        read -p "是否删除重新创建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            log_info "使用现有虚拟环境"
            return 0
        fi
    fi
    
    # 创建虚拟环境
    python3 -m venv "$VENV_DIR"
    log_info "虚拟环境创建完成: $VENV_DIR"
}

# 激活虚拟环境
activate_venv() {
    log_step "激活虚拟环境..."
    
    VENV_DIR="venv"
    
    if [[ ! -d "$VENV_DIR" ]]; then
        log_error "虚拟环境不存在: $VENV_DIR"
        exit 1
    fi
    
    source "$VENV_DIR/bin/activate"
    log_info "虚拟环境已激活"
    
    # 验证虚拟环境
    PYTHON_PATH=$(which python)
    log_info "Python路径: $PYTHON_PATH"
}

# 安装Python依赖
install_python_deps() {
    log_step "安装Python依赖包..."
    
    # 检查requirements.txt文件
    if [[ ! -f "requirements.txt" ]]; then
        log_error "requirements.txt文件不存在"
        exit 1
    fi
    
    log_info "从requirements.txt安装依赖..."
    
    # 升级pip、setuptools、wheel
    pip install --upgrade pip setuptools wheel
    
    # 安装依赖包
    pip install -r requirements.txt
    
    log_info "Python依赖安装完成"
}

# 安装可选依赖
install_optional_deps() {
    log_step "安装可选依赖..."
    
    echo "以下是可选的依赖包，可以根据需要安装："
    echo "1. TA-Lib (技术分析库) - 需要编译"
    echo "2. 机器学习包 (scikit-learn等)"
    echo "3. 深度学习包 (tensorflow, torch等)"
    echo "4. 数据库驱动 (psycopg2, pymysql等)"
    echo
    
    read -p "是否安装TA-Lib? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_talib
    fi
    
    read -p "是否安装机器学习包? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install scikit-learn xgboost lightgbm
        log_info "机器学习包安装完成"
    fi
}

# 安装TA-Lib
install_talib() {
    log_info "安装TA-Lib..."
    
    # 检查系统类型
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y libta-lib-dev
        elif command -v yum &> /dev/null; then
            sudo yum install -y ta-lib-devel
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ta-lib
        fi
    fi
    
    # 安装Python包
    pip install TA-Lib
    log_info "TA-Lib安装完成"
}

# 验证安装
verify_installation() {
    log_step "验证安装..."
    
    # 测试核心包导入
    python -c "
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import flask
import akshare as ak
from apscheduler.schedulers.blocking import BlockingScheduler
print('核心依赖包导入成功')
"
    
    if [[ $? -eq 0 ]]; then
        log_info "核心依赖验证通过"
    else
        log_error "核心依赖验证失败"
        exit 1
    fi
    
    # 测试可选包
    python -c "
try:
    import talib
    print('TA-Lib可用')
except ImportError:
    print('TA-Lib不可用（可选）')

try:
    import sklearn
    print('scikit-learn可用')
except ImportError:
    print('scikit-learn不可用（可选）')
"
}

# 生成激活脚本
generate_activate_script() {
    log_step "生成激活脚本..."
    
    cat > activate_env.sh << 'EOF'
#!/bin/bash
# 激活TD分析系统虚拟环境

if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
    echo "虚拟环境已激活"
    echo "Python路径: $(which python)"
    echo "pip路径: $(which pip)"
else
    echo "错误: 虚拟环境不存在，请先运行 ./install_dependencies.sh"
    exit 1
fi
EOF
    
    chmod +x activate_env.sh
    log_info "激活脚本已创建: activate_env.sh"
}

# 显示安装信息
show_installation_info() {
    log_step "安装完成信息"
    
    echo
    echo "======================================"
    echo "    依赖安装完成！"
    echo "======================================"
    echo
    echo "📦 已安装的主要包:"
    pip list | grep -E "(pandas|numpy|plotly|flask|akshare|apscheduler|gunicorn)"
    echo
    echo "🔧 使用方法:"
    echo "  激活环境: source venv/bin/activate"
    echo "  或使用脚本: ./activate_env.sh"
    echo "  退出环境: deactivate"
    echo
    echo "📋 验证安装:"
    echo "  python -c 'import pandas, numpy, plotly, flask, akshare'"
    echo
    echo "🚀 下一步:"
    echo "  1. 激活虚拟环境"
    echo "  2. 运行测试: python test_system.py"
    echo "  3. 启动应用: python web/app.py"
    echo
    echo "======================================"
}

# 主函数
main() {
    echo "======================================"
    echo "  A股九转序列识别系统 - 依赖安装脚本"
    echo "  版本: 1.0"
    echo "======================================"
    echo
    
    # 检查当前目录
    if [[ ! -f "requirements.txt" ]]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 执行安装步骤
    check_python
    check_pip
    
    # 询问是否安装系统依赖
    read -p "是否安装系统依赖? (推荐) (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        install_system_deps
    fi
    
    setup_venv
    activate_venv
    install_python_deps
    
    # 询问是否安装可选依赖
    read -p "是否安装可选依赖? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_optional_deps
    fi
    
    verify_installation
    generate_activate_script
    show_installation_info
    
    log_info "依赖安装完成！"
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@"