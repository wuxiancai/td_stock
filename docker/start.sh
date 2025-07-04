#!/bin/bash
# Docker容器启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 等待依赖服务
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local timeout=${4:-30}
    
    log_info "等待 $service 服务启动..."
    
    for i in $(seq 1 $timeout); do
        if nc -z $host $port 2>/dev/null; then
            log_info "$service 服务已就绪"
            return 0
        fi
        sleep 1
    done
    
    log_warn "$service 服务未在 $timeout 秒内启动"
    return 1
}

# 初始化应用
init_app() {
    log_step "初始化应用..."
    
    # 创建必要目录
    mkdir -p /app/data/raw /app/data/processed /app/html_charts /app/logs
    
    # 设置权限
    chown -R tduser:tduser /app/data /app/html_charts /app/logs
    
    # 检查配置文件
    if [[ ! -f "/app/config.yaml" ]]; then
        log_warn "配置文件不存在，使用默认配置"
        cp /app/config.yaml.example /app/config.yaml 2>/dev/null || true
    fi
    
    log_info "应用初始化完成"
}

# 健康检查
health_check() {
    log_step "执行健康检查..."
    
    # 检查Python环境
    python3 -c "import sys; print(f'Python版本: {sys.version}')" || {
        log_error "Python环境检查失败"
        exit 1
    }
    
    # 检查核心依赖
    python3 -c "
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import flask
import akshare as ak
from apscheduler.schedulers.blocking import BlockingScheduler
print('核心依赖检查通过')
" || {
        log_error "依赖包检查失败"
        exit 1
    }
    
    log_info "健康检查通过"
}

# 启动服务
start_services() {
    log_step "启动服务..."
    
    # 等待Redis（如果配置了）
    if [[ -n "$REDIS_HOST" ]]; then
        wait_for_service "$REDIS_HOST" "${REDIS_PORT:-6379}" "Redis" 30
    fi
    
    # 等待数据库（如果配置了）
    if [[ -n "$DATABASE_HOST" ]]; then
        wait_for_service "$DATABASE_HOST" "${DATABASE_PORT:-5432}" "Database" 60
    fi
    
    # 启动Supervisor
    log_info "启动Supervisor..."
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/td_analysis.conf
}

# 信号处理
handle_signal() {
    log_info "接收到停止信号，正在关闭服务..."
    
    # 停止Supervisor管理的进程
    if [[ -f /tmp/supervisord.pid ]]; then
        supervisorctl stop all
        kill -TERM $(cat /tmp/supervisord.pid) 2>/dev/null || true
    fi
    
    log_info "服务已停止"
    exit 0
}

# 设置信号处理
trap handle_signal SIGTERM SIGINT

# 主函数
main() {
    log_info "启动TD分析系统容器..."
    
    # 显示环境信息
    log_info "容器信息:"
    echo "  主机名: $(hostname)"
    echo "  用户: $(whoami)"
    echo "  工作目录: $(pwd)"
    echo "  Python版本: $(python3 --version)"
    echo "  时区: $(date +%Z)"
    echo
    
    # 执行初始化
    init_app
    health_check
    start_services
}

# 运行主函数
main "$@"