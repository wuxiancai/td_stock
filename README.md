# A股九转序列识别系统

一个基于Python的A股技术分析系统，专门用于识别和分析九转序列信号，提供自动化数据采集、技术指标计算、可视化图表生成和Web界面展示功能。

## 🌟 主要特性

- **九转序列识别**: 自动识别TD Sequential买卖信号
- **实时数据采集**: 支持多种数据源（AKShare、YFinance等）
- **可视化图表**: 交互式K线图和技术指标展示
- **Web界面**: 现代化的Web用户界面
- **自动化调度**: 定时数据更新和分析
- **多种部署方式**: 支持传统部署和Docker容器化部署
- **完整监控**: 日志记录、性能监控、异常处理
- **高可扩展性**: 模块化设计，易于扩展新功能

## 📋 系统要求

### 最低要求
- **操作系统**: Ubuntu 22.04 LTS / macOS 10.15+ / Windows 10+
- **Python**: 3.8+
- **内存**: 4GB RAM
- **存储**: 10GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **操作系统**: Ubuntu 22.04 LTS Server
- **Python**: 3.10+
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **CPU**: 4核心

## 📁 项目结构

```
九转指标选股法/
├── core/                   # 核心功能模块
│   ├── fetch_data.py      # 数据获取
│   ├── td_sequential.py   # 九转序列计算
│   └── plot_kline.py      # K线图绘制
├── web/                   # Web应用
│   ├── app.py            # Flask应用主文件
│   ├── static/           # 静态资源
│   └── templates/        # HTML模板
├── utils/                 # 工具模块
│   ├── logger.py         # 日志管理
│   ├── cache.py          # 缓存管理
│   ├── exceptions.py     # 异常处理
│   └── __init__.py       # 工具函数
├── data/                  # 数据目录
│   ├── raw/              # 原始数据
│   └── processed/        # 处理后数据
├── html_charts/           # 生成的图表
├── logs/                  # 日志文件
├── docker/                # Docker配置
├── config.yaml            # 配置文件
├── requirements.txt       # Python依赖
├── deploy.sh             # 一键部署脚本
├── deploy_docker.sh      # Docker部署脚本
├── install_dependencies.sh # 依赖安装脚本
├── run_daily.py          # 主程序
├── test_system.py        # 系统测试
├── Dockerfile            # Docker镜像配置
├── docker-compose.yml    # Docker编排配置
├── DEPLOYMENT.md         # 详细部署指南
└── README.md             # 项目说明
```

## 🚀 快速开始

### 方式一：一键部署（推荐）

适用于Ubuntu 22.04服务器：

```bash
# 1. 下载项目
git clone <repository-url>
cd 九转指标选股法

# 2. 运行一键部署脚本
chmod +x deploy.sh
./deploy.sh

# 3. 访问系统
# 浏览器打开: http://your-server-ip
```

### 方式二：Docker部署

适用于支持Docker的系统：

```bash
# 1. 确保Docker已安装
docker --version
docker-compose --version

# 2. 运行Docker部署脚本
chmod +x deploy_docker.sh
./deploy_docker.sh

# 3. 访问系统
# 浏览器打开: http://localhost
```

### 方式三：手动安装

适用于开发环境或自定义部署：

```bash
# 1. 安装Python依赖
chmod +x install_dependencies.sh
./install_dependencies.sh

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 运行测试
python test_system.py

# 4. 启动Web应用
python web/app.py

# 5. 启动调度器（新终端）
python run_daily.py
```

## 🔧 配置说明

### 主配置文件 (config.yaml)

```yaml
# 数据源配置
data_source:
  provider: "akshare"  # 数据提供商
  request_delay: 1     # 请求延迟（秒）
  timeout: 30          # 超时时间（秒）

# 调度配置
scheduler:
  trigger_time: "09:30"  # 触发时间
  timezone: "Asia/Shanghai"

# 目录配置
directories:
  data_dir: "data"
  processed_dir: "data/processed"
  charts_dir: "html_charts"
  logs_dir: "logs"

# Web服务配置
web:
  host: "0.0.0.0"
  port: 5000
  debug: false

# 日志配置
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_file_size: "10MB"
  backup_count: 5
```

### 环境变量

```bash
# Flask配置
export FLASK_ENV=production
export FLASK_APP=web/app.py

# Python路径
export PYTHONPATH=/path/to/project

# 时区设置
export TZ=Asia/Shanghai
```

## 📊 功能模块

### 1. 数据获取模块 (core/fetch_data.py)

- 支持多种数据源（AKShare、YFinance等）
- 自动重试和错误处理
- 数据缓存和增量更新
- 数据质量验证

### 2. 九转序列计算 (core/td_sequential.py)

- TD Sequential算法实现
- 买卖信号识别
- 信号强度评估
- 历史信号统计

### 3. 图表生成 (core/plot_kline.py)

- 交互式K线图
- 技术指标叠加
- 信号标注
- 批量图表生成

### 4. Web界面 (web/app.py)

- 股票列表展示
- 图表查看
- 信号筛选
- 实时数据更新

### 5. 任务调度 (run_daily.py)

- 定时数据更新
- 自动分析执行
- 报告生成
- 异常监控

## 🛠️ 开发指南

### 本地开发环境搭建

```bash
# 1. 克隆项目
git clone <repository-url>
cd 九转指标选股法

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发依赖
pip install pytest pytest-cov black isort flake8

# 5. 运行测试
pytest tests/

# 6. 代码格式化
black .
isort .
flake8 .
```

### 添加新功能

1. **创建新模块**：在相应目录下创建Python文件
2. **编写测试**：在`tests/`目录下添加测试用例
3. **更新配置**：如需要，更新`config.yaml`
4. **更新文档**：更新相关文档和README

### 代码规范

- 使用Black进行代码格式化
- 使用isort进行导入排序
- 使用flake8进行代码检查
- 编写单元测试，保持测试覆盖率>80%
- 添加类型注解
- 编写详细的文档字符串

## 🐳 Docker使用

### 基础使用

```bash
# 构建镜像
docker build -t td-analysis .

# 运行容器
docker run -d -p 80:80 --name td-analysis td-analysis

# 查看日志
docker logs -f td-analysis

# 进入容器
docker exec -it td-analysis bash
```

### Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f td-analysis

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

### 部署模式

1. **基础模式**：主应用 + Redis
2. **完整模式**：基础模式 + PostgreSQL
3. **监控模式**：完整模式 + Prometheus + Grafana
4. **日志模式**：完整模式 + ELK Stack
5. **生产模式**：所有服务 + SSL

## 📈 监控和维护

### 日志管理

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看访问日志
tail -f logs/access.log

# 日志轮转（自动配置）
logrotate /etc/logrotate.d/td_analysis
```

### 性能监控

```bash
# 系统资源
htop
free -h
df -h

# 应用性能
python -m memory_profiler script.py
python -m cProfile script.py

# 网络监控
netstat -tlnp
ss -tlnp
```

### 数据备份

```bash
# 手动备份
./backup.sh

# 自动备份（已配置cron）
crontab -l

# 恢复备份
tar -xzf backup_file.tar.gz
```

## 🔒 安全配置

### 系统安全

1. **防火墙配置**
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

2. **SSH安全**
   ```bash
   # 禁用root登录
   sudo nano /etc/ssh/sshd_config
   # PermitRootLogin no
   
   # 使用密钥认证
   ssh-keygen -t rsa -b 4096
   ssh-copy-id user@server
   ```

3. **应用安全**
   - 定期更新依赖包
   - 使用HTTPS（配置SSL证书）
   - 设置访问限制
   - 监控异常访问

### SSL证书配置

```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🚨 故障排除

### 常见问题

1. **Web服务无法访问**
   ```bash
   # 检查服务状态
   sudo supervisorctl status
   sudo systemctl status nginx
   
   # 检查端口
   sudo netstat -tlnp | grep :80
   
   # 查看日志
   tail -f logs/web_error.log
   ```

2. **数据获取失败**
   ```bash
   # 检查网络连接
   ping baidu.com
   
   # 测试API
   python -c "import akshare as ak; print(ak.stock_zh_a_hist('000001'))"
   
   # 查看日志
   tail -f logs/data_error.log
   ```

3. **内存不足**
   ```bash
   # 检查内存使用
   free -h
   
   # 增加swap
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### 紧急恢复

```bash
# 重启所有服务
sudo systemctl restart supervisor nginx

# 重新部署
./deploy.sh

# 从备份恢复
tar -xzf latest_backup.tar.gz
./start_services.sh
```

## 📚 API文档

### REST API端点

- `GET /` - 主页
- `GET /api/stocks` - 获取股票列表
- `GET /chart/<stock_code>` - 查看股票图表
- `GET /summary` - 查看汇总图表
- `GET /health` - 健康检查

### 响应格式

```json
{
  "status": "success",
  "data": {
    "stocks": [
      {
        "code": "000001",
        "name": "平安银行",
        "signal": "buy",
        "strength": 8
      }
    ]
  },
  "message": "操作成功"
}
```

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 贡献规范

- 遵循现有代码风格
- 添加适当的测试
- 更新相关文档
- 确保所有测试通过

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 支持

- **文档**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **问题反馈**: 创建GitHub Issue
- **功能请求**: 创建GitHub Issue
- **安全问题**: 发送邮件至 security@example.com

## 🙏 致谢

- [AKShare](https://github.com/akfamily/akshare) - 数据源
- [Plotly](https://plotly.com/) - 图表库
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [APScheduler](https://apscheduler.readthedocs.io/) - 任务调度

## 📊 项目统计

![GitHub stars](https://img.shields.io/github/stars/username/repo)
![GitHub forks](https://img.shields.io/github/forks/username/repo)
![GitHub issues](https://img.shields.io/github/issues/username/repo)
![GitHub license](https://img.shields.io/github/license/username/repo)

---

**注意**: 本系统仅用于技术分析和学习目的，不构成投资建议。投资有风险，入市需谨慎。
            "close_price": 12.34,
            "signal_type": "buy",
            "setup_count": 3
        }
    ],
    "summary": {
        "total": 10,
        "buy_signals": 6,
        "sell_signals": 4,
        "date": "20240115"
    }
}
```

## 注意事项

1. **数据源**: 使用AkShare获取A股数据，请确保网络连接稳定
2. **请求频率**: 系统已内置请求延时，避免频率限制
3. **存储空间**: 长期运行需要定期清理历史数据文件
4. **市场时间**: 建议在交易日收盘后运行，数据更完整

## 故障排除

### 常见问题

1. **数据获取失败**
   - 检查网络连接
   - 确认AkShare版本是否最新

2. **图表显示异常**
   - 检查Plotly版本
   - 确认浏览器支持JavaScript

3. **Web服务无法访问**
   - 检查端口是否被占用
   - 确认防火墙设置

### 日志查看

```bash
# 查看运行日志
tail -f td_analysis.log

# 查看Web服务日志
python web/app.py  # 开发模式会显示详细日志
```

## 技术支持

如有问题或建议，请检查：
1. 确认Python版本和依赖包版本
2. 查看日志文件中的错误信息
3. 验证数据文件是否正常生成

## 许可证

本项目仅供学习和研究使用，不构成投资建议。使用者需自行承担投资风险。