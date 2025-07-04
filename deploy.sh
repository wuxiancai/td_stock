#!/bin/bash
# -*- coding: utf-8 -*-
# A股九转序列识别系统 - Ubuntu 22.04 一键部署脚本
# 作者: AI Assistant
# 版本: 1.0
# 适用系统: Ubuntu 22.04 Server

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本！"
        log_info "建议创建普通用户: sudo adduser tduser && sudo usermod -aG sudo tduser"
        exit 1
    fi
}

# 检查Python版本
check_python_version() {
    log_step "检查Python版本..."
    
    # 检查Python3是否可用
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装或不在PATH中"
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

# 预检查项目文件
check_project_files() {
    log_step "检查项目文件完整性..."
    
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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

# 检查系统版本
check_system() {
    log_step "检查系统版本..."
    
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测系统版本"
        exit 1
    fi
    
    source /etc/os-release
    
    if [[ "$ID" != "ubuntu" ]]; then
        log_error "此脚本仅支持Ubuntu系统，当前系统: $ID"
        exit 1
    fi
    
    if [[ "$VERSION_ID" != "22.04" ]]; then
        log_warn "此脚本针对Ubuntu 22.04优化，当前版本: $VERSION_ID"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_info "系统检查通过: Ubuntu $VERSION_ID"
}

# 更新系统
update_system() {
    log_step "更新系统包..."
    sudo apt update
    sudo apt upgrade -y
    log_info "系统更新完成"
}

# 安装基础依赖
install_dependencies() {
    log_step "安装基础依赖..."
    
    # 安装系统依赖
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        wget \
        unzip \
        supervisor \
        nginx \
        ufw \
        htop \
        tree \
        vim
    
    log_info "基础依赖安装完成"
}

# 配置Python环境
setup_python_env() {
    log_step "配置Python虚拟环境..."
    
    # 创建项目目录
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    
    if [[ -d "$PROJECT_DIR" ]]; then
        log_warn "项目目录已存在: $PROJECT_DIR"
        read -p "是否删除重新创建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$PROJECT_DIR"
        else
            log_error "部署中止"
            exit 1
        fi
    fi
    
    # 复制项目文件
    log_info "复制项目文件..."
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    
    # 检查源目录是否存在文件
    if ! ls "$SCRIPT_DIR"/* >/dev/null 2>&1; then
        log_error "源目录 $SCRIPT_DIR 中没有找到文件"
        exit 1
    fi
    
    # 检查关键文件是否存在于源目录
    REQUIRED_FILES=("requirements.txt" "config.py" "run_daily.py")
    REQUIRED_DIRS=("core" "utils" "web")
    
    log_info "检查源目录中的关键文件..."
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$file" ]]; then
            log_error "关键文件 $file 不存在于源目录 $SCRIPT_DIR"
            log_error "请确保在项目根目录运行此脚本"
            exit 1
        fi
    done
    
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [[ ! -d "$SCRIPT_DIR/$dir" ]]; then
            log_error "关键目录 $dir 不存在于源目录 $SCRIPT_DIR"
            log_error "请确保在项目根目录运行此脚本"
            exit 1
        fi
    done
    
    log_info "源目录文件检查通过"
    
    # 创建项目目录并复制文件
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # 复制所有文件
    cp -r "$SCRIPT_DIR"/* .
    log_info "项目文件复制完成"
    
    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装项目依赖
    log_info "安装Python依赖包..."
    pip install -r requirements.txt
    
    # 创建必要目录
    mkdir -p data/raw data/processed html_charts logs
    
    log_info "Python环境配置完成"
}

# 配置Supervisor服务
setup_supervisor() {
    log_step "配置Supervisor服务..."
    
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    USER=$(whoami)
    
    # 创建Supervisor配置文件
    sudo tee /etc/supervisor/conf.d/td_analysis.conf > /dev/null <<EOF
[program:td_analysis_web]
command=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/web/app.py
directory=$PROJECT_DIR
user=$USER
autostart=true
autorestart=true
stderr_logfile=$PROJECT_DIR/logs/web_error.log
stdout_logfile=$PROJECT_DIR/logs/web_access.log
environment=FLASK_ENV=production

[program:td_analysis_scheduler]
command=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/run_daily.py
directory=$PROJECT_DIR
user=$USER
autostart=true
autorestart=true
stderr_logfile=$PROJECT_DIR/logs/scheduler_error.log
stdout_logfile=$PROJECT_DIR/logs/scheduler_access.log
EOF
    
    # 重新加载Supervisor配置
    sudo supervisorctl reread
    sudo supervisorctl update
    
    log_info "Supervisor服务配置完成"
}

# 配置Nginx反向代理
setup_nginx() {
    log_step "配置Nginx反向代理..."
    
    # 创建Nginx配置文件
    sudo tee /etc/nginx/sites-available/td_analysis > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    # 静态文件
    location /static/ {
        alias /home/$(whoami)/td_analysis/web/static/;
        expires 30d;
    }
    
    # 图表文件
    location /charts/ {
        alias /home/$(whoami)/td_analysis/html_charts/;
        expires 1d;
    }
    
    # 主应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 日志配置
    access_log /var/log/nginx/td_analysis_access.log;
    error_log /var/log/nginx/td_analysis_error.log;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
EOF
    
    # 启用站点
    sudo ln -sf /etc/nginx/sites-available/td_analysis /etc/nginx/sites-enabled/
    
    # 删除默认站点
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # 测试Nginx配置
    sudo nginx -t
    
    # 重启Nginx
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    log_info "Nginx配置完成"
}

# 配置防火墙
setup_firewall() {
    log_step "配置防火墙..."
    
    # 重置UFW规则
    sudo ufw --force reset
    
    # 允许SSH
    sudo ufw allow ssh
    
    # 允许HTTP和HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # 启用防火墙
    sudo ufw --force enable
    
    log_info "防火墙配置完成"
}

# 创建系统服务脚本
create_service_scripts() {
    log_step "创建系统服务脚本..."
    
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    
    # 创建启动脚本
    cat > "$PROJECT_DIR/start_services.sh" <<EOF
#!/bin/bash
# 启动所有服务

echo "启动TD分析系统服务..."

# 启动Supervisor服务
sudo supervisorctl start td_analysis_web
sudo supervisorctl start td_analysis_scheduler

# 启动Nginx
sudo systemctl start nginx

echo "所有服务已启动"
echo "Web访问地址: http://\$(hostname -I | awk '{print \$1}')"
EOF
    
    # 创建停止脚本
    cat > "$PROJECT_DIR/stop_services.sh" <<EOF
#!/bin/bash
# 停止所有服务

echo "停止TD分析系统服务..."

# 停止Supervisor服务
sudo supervisorctl stop td_analysis_web
sudo supervisorctl stop td_analysis_scheduler

echo "所有服务已停止"
EOF
    
    # 创建重启脚本
    cat > "$PROJECT_DIR/restart_services.sh" <<EOF
#!/bin/bash
# 重启所有服务

echo "重启TD分析系统服务..."

# 重启Supervisor服务
sudo supervisorctl restart td_analysis_web
sudo supervisorctl restart td_analysis_scheduler

# 重启Nginx
sudo systemctl restart nginx

echo "所有服务已重启"
echo "Web访问地址: http://\$(hostname -I | awk '{print \$1}')"
EOF
    
    # 创建状态检查脚本
    cat > "$PROJECT_DIR/check_status.sh" <<EOF
#!/bin/bash
# 检查服务状态

echo "=== TD分析系统服务状态 ==="
echo

echo "Supervisor服务状态:"
sudo supervisorctl status
echo

echo "Nginx服务状态:"
sudo systemctl status nginx --no-pager -l
echo

echo "系统资源使用:"
free -h
echo
df -h
echo

echo "网络端口监听:"
sudo netstat -tlnp | grep -E ':(80|5000)\s'
EOF
    
    # 设置执行权限
    chmod +x "$PROJECT_DIR"/*.sh
    
    log_info "服务脚本创建完成"
}

# 创建日志轮转配置
setup_log_rotation() {
    log_step "配置日志轮转..."
    
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    
    sudo tee /etc/logrotate.d/td_analysis > /dev/null <<EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    su $(whoami) $(whoami)
}
EOF
    
    log_info "日志轮转配置完成"
}

# 创建备份脚本
create_backup_script() {
    log_step "创建备份脚本..."
    
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    
    cat > "$PROJECT_DIR/backup.sh" <<EOF
#!/bin/bash
# 数据备份脚本

BACKUP_DIR="\$HOME/td_analysis_backup"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/td_analysis_\$DATE.tar.gz"

mkdir -p "\$BACKUP_DIR"

echo "开始备份TD分析系统数据..."

# 备份数据和配置
tar -czf "\$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs/*.log' \
    -C "\$(dirname \"$PROJECT_DIR\")" \
    "\$(basename \"$PROJECT_DIR\")"

echo "备份完成: \$BACKUP_FILE"
echo "备份大小: \$(du -h \"\$BACKUP_FILE\" | cut -f1)"

# 清理30天前的备份
find "\$BACKUP_DIR" -name "td_analysis_*.tar.gz" -mtime +30 -delete

echo "旧备份清理完成"
EOF
    
    chmod +x "$PROJECT_DIR/backup.sh"
    
    # 添加到crontab（每天凌晨2点备份）
    (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | crontab -
    
    log_info "备份脚本创建完成"
}

# 性能优化
optimize_system() {
    log_step "系统性能优化..."
    
    # 调整系统参数
    sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# TD分析系统优化
net.core.somaxconn = 1024
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 1024
vm.swappiness = 10
EOF
    
    # 应用系统参数
    sudo sysctl -p
    
    log_info "系统优化完成"
}

# 启动服务
start_services() {
    log_step "启动系统服务..."
    
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    
    # 启动Supervisor服务
    sudo supervisorctl start td_analysis_web
    sudo supervisorctl start td_analysis_scheduler
    
    # 等待服务启动
    sleep 5
    
    # 检查服务状态
    if sudo supervisorctl status td_analysis_web | grep -q RUNNING; then
        log_info "Web服务启动成功"
    else
        log_error "Web服务启动失败"
    fi
    
    if sudo supervisorctl status td_analysis_scheduler | grep -q RUNNING; then
        log_info "调度服务启动成功"
    else
        log_error "调度服务启动失败"
    fi
}

# 运行测试
run_tests() {
    log_step "运行系统测试..."
    
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    cd "$PROJECT_DIR"
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 运行测试
    python test_system.py
    
    log_info "系统测试完成"
}

# 显示部署信息
show_deployment_info() {
    log_step "部署完成信息"
    
    SERVER_IP=$(hostname -I | awk '{print $1}')
    PROJECT_DIR="/home/$(whoami)/td_analysis"
    
    echo
    echo "======================================"
    echo "    TD分析系统部署完成！"
    echo "======================================"
    echo
    echo "🌐 Web访问地址: http://$SERVER_IP"
    echo "📁 项目目录: $PROJECT_DIR"
    echo "👤 运行用户: $(whoami)"
    echo
    echo "🔧 管理命令:"
    echo "  启动服务: $PROJECT_DIR/start_services.sh"
    echo "  停止服务: $PROJECT_DIR/stop_services.sh"
    echo "  重启服务: $PROJECT_DIR/restart_services.sh"
    echo "  检查状态: $PROJECT_DIR/check_status.sh"
    echo "  数据备份: $PROJECT_DIR/backup.sh"
    echo
    echo "📋 服务管理:"
    echo "  查看日志: sudo supervisorctl tail -f td_analysis_web"
    echo "  重启Web: sudo supervisorctl restart td_analysis_web"
    echo "  重启调度: sudo supervisorctl restart td_analysis_scheduler"
    echo
    echo "📊 监控命令:"
    echo "  系统状态: htop"
    echo "  磁盘使用: df -h"
    echo "  内存使用: free -h"
    echo "  网络连接: sudo netstat -tlnp"
    echo
    echo "🔒 安全提醒:"
    echo "  - 定期更新系统: sudo apt update && sudo apt upgrade"
    echo "  - 监控日志文件: tail -f $PROJECT_DIR/logs/*.log"
    echo "  - 定期备份数据: $PROJECT_DIR/backup.sh"
    echo
    echo "======================================"
}

# 主函数
main() {
    echo "======================================"
    echo "  A股九转序列识别系统 - 自动部署脚本"
    echo "  适用系统: Ubuntu 22.04 Server"
    echo "  版本: 1.0"
    echo "======================================"
    echo
    
    # 检查运行权限
    check_root
    
    # 检查Python版本
    check_python_version
    
    # 预检查项目文件
    check_project_files
    
    # 检查系统
    check_system
    
    # 确认部署
    echo
    log_warn "即将开始自动部署，此过程将:"
    echo "  1. 更新系统包"
    echo "  2. 安装Python、Nginx、Supervisor等依赖"
    echo "  3. 配置虚拟环境和项目文件"
    echo "  4. 设置系统服务和反向代理"
    echo "  5. 配置防火墙和安全设置"
    echo "  6. 启动所有服务"
    echo
    read -p "确认继续部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    echo
    log_info "开始自动部署..."
    echo
    
    # 执行部署步骤
    update_system
    install_dependencies
    setup_python_env
    setup_supervisor
    setup_nginx
    setup_firewall
    create_service_scripts
    setup_log_rotation
    create_backup_script
    optimize_system
    start_services
    run_tests
    
    # 显示部署信息
    show_deployment_info
    
    log_info "部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@"