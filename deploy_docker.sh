#!/bin/bash
# -*- coding: utf-8 -*-
# A股九转序列识别系统 - Docker一键部署脚本
# 适用于支持Docker的系统

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

# 检查Docker
check_docker() {
    log_step "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        echo "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    log_info "Docker版本: $DOCKER_VERSION"
}

# 检查Docker Compose
check_docker_compose() {
    log_step "检查Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        COMPOSE_VERSION=$(docker compose version --short)
    else
        log_error "Docker Compose未安装"
        echo "请安装Docker Compose或使用较新版本的Docker"
        exit 1
    fi
    
    log_info "Docker Compose版本: $COMPOSE_VERSION"
    log_info "使用命令: $COMPOSE_CMD"
}

# 检查系统资源
check_resources() {
    log_step "检查系统资源..."
    
    # 检查内存
    if command -v free &> /dev/null; then
        TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
        if [[ $TOTAL_MEM -lt 2048 ]]; then
            log_warn "系统内存较少 (${TOTAL_MEM}MB)，建议至少4GB内存"
        else
            log_info "系统内存: ${TOTAL_MEM}MB"
        fi
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df . | awk 'NR==2 {print $4}')
    AVAILABLE_GB=$((AVAILABLE_SPACE / 1024 / 1024))
    if [[ $AVAILABLE_GB -lt 5 ]]; then
        log_warn "可用磁盘空间较少 (${AVAILABLE_GB}GB)，建议至少10GB空间"
    else
        log_info "可用磁盘空间: ${AVAILABLE_GB}GB"
    fi
}

# 选择部署模式
select_deployment_mode() {
    log_step "选择部署模式..."
    
    echo "请选择部署模式:"
    echo "1. 基础模式 (仅主应用 + Redis)"
    echo "2. 完整模式 (主应用 + Redis + PostgreSQL)"
    echo "3. 监控模式 (完整模式 + Prometheus + Grafana)"
    echo "4. 日志模式 (完整模式 + ELK Stack)"
    echo "5. 生产模式 (所有服务 + SSL)"
    echo
    
    read -p "请输入选择 (1-5): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            DEPLOYMENT_MODE="basic"
            COMPOSE_PROFILES=""
            ;;
        2)
            DEPLOYMENT_MODE="full"
            COMPOSE_PROFILES=""
            ;;
        3)
            DEPLOYMENT_MODE="monitoring"
            COMPOSE_PROFILES="--profile monitoring"
            ;;
        4)
            DEPLOYMENT_MODE="logging"
            COMPOSE_PROFILES="--profile logging"
            ;;
        5)
            DEPLOYMENT_MODE="production"
            COMPOSE_PROFILES="--profile production --profile monitoring"
            ;;
        *)
            log_warn "无效选择，使用基础模式"
            DEPLOYMENT_MODE="basic"
            COMPOSE_PROFILES=""
            ;;
    esac
    
    log_info "选择的部署模式: $DEPLOYMENT_MODE"
}

# 配置环境变量
setup_environment() {
    log_step "配置环境变量..."
    
    # 创建.env文件
    cat > .env << EOF
# TD分析系统环境配置

# 应用配置
FLASK_ENV=production
PYTHONPATH=/app
TZ=Asia/Shanghai

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# 数据库配置
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=td_analysis
DATABASE_USER=tduser
DATABASE_PASSWORD=td_password_2024

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin123

# 日志配置
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601

# 安全配置
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "your-secret-key-here")
JWT_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "your-jwt-secret-here")
EOF
    
    log_info "环境配置文件已创建: .env"
}

# 构建镜像
build_images() {
    log_step "构建Docker镜像..."
    
    # 检查Dockerfile
    if [[ ! -f "Dockerfile" ]]; then
        log_error "Dockerfile不存在"
        exit 1
    fi
    
    # 构建主应用镜像
    log_info "构建主应用镜像..."
    docker build -t td-analysis:latest .
    
    log_info "镜像构建完成"
}

# 启动服务
start_services() {
    log_step "启动Docker服务..."
    
    # 停止现有服务
    log_info "停止现有服务..."
    $COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    
    # 启动服务
    log_info "启动新服务..."
    if [[ -n "$COMPOSE_PROFILES" ]]; then
        $COMPOSE_CMD $COMPOSE_PROFILES up -d
    else
        $COMPOSE_CMD up -d td-analysis redis
        if [[ "$DEPLOYMENT_MODE" == "full" ]]; then
            $COMPOSE_CMD up -d postgres
        fi
    fi
    
    log_info "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_step "等待服务就绪..."
    
    # 等待主应用
    log_info "等待主应用启动..."
    for i in {1..60}; do
        if curl -f http://localhost/health &>/dev/null; then
            log_info "主应用已就绪"
            break
        fi
        if [[ $i -eq 60 ]]; then
            log_warn "主应用启动超时，请检查日志"
        fi
        sleep 2
    done
    
    # 等待其他服务
    if [[ "$DEPLOYMENT_MODE" =~ ^(monitoring|production)$ ]]; then
        log_info "等待监控服务..."
        sleep 10
    fi
}

# 显示服务状态
show_status() {
    log_step "服务状态检查..."
    
    echo
    echo "=== Docker容器状态 ==="
    $COMPOSE_CMD ps
    
    echo
    echo "=== 服务健康检查 ==="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# 显示访问信息
show_access_info() {
    log_step "部署完成信息"
    
    SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo
    echo "======================================"
    echo "    TD分析系统Docker部署完成！"
    echo "======================================"
    echo
    echo "🌐 访问地址:"
    echo "  主应用: http://$SERVER_IP"
    echo "  健康检查: http://$SERVER_IP/health"
    
    if [[ "$DEPLOYMENT_MODE" =~ ^(monitoring|production)$ ]]; then
        echo "  Prometheus: http://$SERVER_IP:9090"
        echo "  Grafana: http://$SERVER_IP:3000 (admin/admin123)"
    fi
    
    if [[ "$DEPLOYMENT_MODE" == "logging" ]]; then
        echo "  Elasticsearch: http://$SERVER_IP:9200"
        echo "  Kibana: http://$SERVER_IP:5601"
    fi
    
    echo
    echo "🔧 管理命令:"
    echo "  查看状态: $COMPOSE_CMD ps"
    echo "  查看日志: $COMPOSE_CMD logs -f td-analysis"
    echo "  重启服务: $COMPOSE_CMD restart"
    echo "  停止服务: $COMPOSE_CMD down"
    echo "  更新服务: $COMPOSE_CMD pull && $COMPOSE_CMD up -d"
    
    echo
    echo "📋 容器管理:"
    echo "  进入容器: docker exec -it td_analysis_app bash"
    echo "  查看日志: docker logs td_analysis_app"
    echo "  重启容器: docker restart td_analysis_app"
    
    echo
    echo "📊 监控命令:"
    echo "  资源使用: docker stats"
    echo "  磁盘使用: docker system df"
    echo "  清理资源: docker system prune"
    
    echo
    echo "🔒 安全提醒:"
    echo "  - 修改默认密码: 编辑 .env 文件"
    echo "  - 配置防火墙: 限制端口访问"
    echo "  - 定期更新: docker pull 最新镜像"
    echo "  - 备份数据: 定期备份 volumes"
    
    echo
    echo "======================================"
}

# 创建管理脚本
create_management_scripts() {
    log_step "创建管理脚本..."
    
    # 启动脚本
    cat > start_docker.sh << EOF
#!/bin/bash
# 启动TD分析系统Docker服务
echo "启动Docker服务..."
$COMPOSE_CMD $COMPOSE_PROFILES up -d
echo "服务已启动"
echo "访问地址: http://\$(hostname -I | awk '{print \$1}')"
EOF
    
    # 停止脚本
    cat > stop_docker.sh << EOF
#!/bin/bash
# 停止TD分析系统Docker服务
echo "停止Docker服务..."
$COMPOSE_CMD down
echo "服务已停止"
EOF
    
    # 重启脚本
    cat > restart_docker.sh << EOF
#!/bin/bash
# 重启TD分析系统Docker服务
echo "重启Docker服务..."
$COMPOSE_CMD restart
echo "服务已重启"
echo "访问地址: http://\$(hostname -I | awk '{print \$1}')"
EOF
    
    # 状态检查脚本
    cat > status_docker.sh << EOF
#!/bin/bash
# 检查TD分析系统Docker服务状态
echo "=== 容器状态 ==="
$COMPOSE_CMD ps
echo
echo "=== 资源使用 ==="
docker stats --no-stream
echo
echo "=== 健康检查 ==="
curl -f http://localhost/health && echo "主应用正常" || echo "主应用异常"
EOF
    
    # 日志查看脚本
    cat > logs_docker.sh << EOF
#!/bin/bash
# 查看TD分析系统Docker日志
if [[ \$1 ]]; then
    $COMPOSE_CMD logs -f \$1
else
    echo "可用服务:"
    $COMPOSE_CMD ps --services
    echo
    echo "使用方法: \$0 <service_name>"
    echo "例如: \$0 td-analysis"
fi
EOF
    
    # 设置执行权限
    chmod +x *.sh
    
    log_info "管理脚本已创建"
}

# 主函数
main() {
    echo "======================================"
    echo "  A股九转序列识别系统 - Docker部署脚本"
    echo "  版本: 1.0"
    echo "======================================"
    echo
    
    # 检查环境
    check_docker
    check_docker_compose
    check_resources
    
    # 选择部署模式
    select_deployment_mode
    
    # 确认部署
    echo
    log_warn "即将开始Docker部署，此过程将:"
    echo "  1. 配置环境变量"
    echo "  2. 构建Docker镜像"
    echo "  3. 启动Docker服务"
    echo "  4. 等待服务就绪"
    echo "  5. 创建管理脚本"
    echo
    read -p "确认继续部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    echo
    log_info "开始Docker部署..."
    echo
    
    # 执行部署步骤
    setup_environment
    build_images
    start_services
    wait_for_services
    show_status
    create_management_scripts
    
    # 显示部署信息
    show_access_info
    
    log_info "Docker部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@"