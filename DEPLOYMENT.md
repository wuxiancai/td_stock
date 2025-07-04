# A股九转序列识别系统 - 部署指南

## 概述

本文档提供了在Ubuntu 22.04服务器上部署A股九转序列识别系统的完整指南。系统采用Flask Web框架，使用Nginx作为反向代理，Supervisor管理进程，支持自动化数据分析和Web可视化。

## 系统要求

### 硬件要求
- **CPU**: 2核心以上
- **内存**: 4GB以上（推荐8GB）
- **存储**: 20GB以上可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Ubuntu 22.04 Server LTS
- **Python**: 3.10+
- **权限**: sudo权限的普通用户账户

## 部署前准备

### 1. 创建部署用户

```bash
# 创建专用用户（如果使用root，请先创建普通用户）
sudo adduser tduser
sudo usermod -aG sudo tduser

# 切换到新用户
su - tduser
```

### 2. 上传项目文件

将项目文件上传到服务器，可以使用以下方法之一：

**方法1: 使用scp**
```bash
# 在本地执行
scp -r /path/to/九转指标选股法 username@server_ip:/home/username/
```

**方法2: 使用git**
```bash
# 在服务器执行
git clone <your_repository_url>
```

**方法3: 使用rsync**
```bash
# 在本地执行
rsync -avz /path/to/九转指标选股法/ username@server_ip:/home/username/九转指标选股法/
```

### 3. 设置SSH密钥（推荐）

```bash
# 在本地生成SSH密钥
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 复制公钥到服务器
ssh-copy-id username@server_ip
```

## 一键部署

### 1. 运行部署脚本

```bash
# 进入项目目录
cd /path/to/九转指标选股法

# 给部署脚本执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

### 2. 部署过程

部署脚本将自动执行以下步骤：

1. **系统检查**: 验证Ubuntu版本和用户权限
2. **系统更新**: 更新包管理器和系统包
3. **依赖安装**: 安装Python、Nginx、Supervisor等
4. **环境配置**: 创建虚拟环境，安装Python依赖
5. **服务配置**: 配置Supervisor和Nginx
6. **防火墙设置**: 配置UFW防火墙规则
7. **服务启动**: 启动所有系统服务
8. **测试验证**: 运行系统测试

### 3. 部署完成

部署成功后，系统将显示访问信息：

```
======================================
    TD分析系统部署完成！
======================================

🌐 Web访问地址: http://YOUR_SERVER_IP
📁 项目目录: /home/username/td_analysis
👤 运行用户: username
```

## 手动部署（可选）

如果自动部署失败，可以按照以下步骤手动部署：

### 1. 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. 安装依赖

```bash
sudo apt install -y python3 python3-pip python3-venv git curl wget unzip supervisor nginx ufw htop tree vim
```

### 3. 配置Python环境

```bash
# 创建项目目录
mkdir -p ~/td_analysis
cd ~/td_analysis

# 复制项目文件
cp -r /path/to/source/* .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建目录
mkdir -p data/raw data/processed html_charts logs
```

### 4. 配置Supervisor

```bash
sudo nano /etc/supervisor/conf.d/td_analysis.conf
```

添加以下内容：

```ini
[program:td_analysis_web]
command=/home/username/td_analysis/venv/bin/python /home/username/td_analysis/web/app.py
directory=/home/username/td_analysis
user=username
autostart=true
autorestart=true
stderr_logfile=/home/username/td_analysis/logs/web_error.log
stdout_logfile=/home/username/td_analysis/logs/web_access.log
environment=FLASK_ENV=production

[program:td_analysis_scheduler]
command=/home/username/td_analysis/venv/bin/python /home/username/td_analysis/run_daily.py
directory=/home/username/td_analysis
user=username
autostart=true
autorestart=true
stderr_logfile=/home/username/td_analysis/logs/scheduler_error.log
stdout_logfile=/home/username/td_analysis/logs/scheduler_access.log
```

```bash
# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update
```

### 5. 配置Nginx

```bash
sudo nano /etc/nginx/sites-available/td_analysis
```

添加以下内容：

```nginx
server {
    listen 80;
    server_name _;
    
    location /static/ {
        alias /home/username/td_analysis/web/static/;
        expires 30d;
    }
    
    location /charts/ {
        alias /home/username/td_analysis/html_charts/;
        expires 1d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/td_analysis /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启服务
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 6. 配置防火墙

```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 服务管理

### 启动服务

```bash
# 使用管理脚本
~/td_analysis/start_services.sh

# 或手动启动
sudo supervisorctl start td_analysis_web
sudo supervisorctl start td_analysis_scheduler
sudo systemctl start nginx
```

### 停止服务

```bash
# 使用管理脚本
~/td_analysis/stop_services.sh

# 或手动停止
sudo supervisorctl stop td_analysis_web
sudo supervisorctl stop td_analysis_scheduler
```

### 重启服务

```bash
# 使用管理脚本
~/td_analysis/restart_services.sh

# 或手动重启
sudo supervisorctl restart td_analysis_web
sudo supervisorctl restart td_analysis_scheduler
sudo systemctl restart nginx
```

### 检查状态

```bash
# 使用管理脚本
~/td_analysis/check_status.sh

# 或手动检查
sudo supervisorctl status
sudo systemctl status nginx
sudo netstat -tlnp | grep -E ':(80|5000)'
```

## 日志管理

### 查看日志

```bash
# Web应用日志
sudo supervisorctl tail -f td_analysis_web

# 调度器日志
sudo supervisorctl tail -f td_analysis_scheduler

# Nginx日志
sudo tail -f /var/log/nginx/td_analysis_access.log
sudo tail -f /var/log/nginx/td_analysis_error.log

# 应用日志文件
tail -f ~/td_analysis/logs/*.log
```

### 日志轮转

系统已自动配置日志轮转，日志文件将：
- 每天轮转一次
- 保留30天
- 自动压缩旧日志

## 数据备份

### 自动备份

系统已配置每日自动备份（凌晨2点）：

```bash
# 查看备份任务
crontab -l

# 手动执行备份
~/td_analysis/backup.sh
```

### 手动备份

```bash
# 创建备份
tar -czf td_analysis_backup_$(date +%Y%m%d).tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs/*.log' \
    ~/td_analysis
```

### 恢复备份

```bash
# 停止服务
~/td_analysis/stop_services.sh

# 恢复数据
tar -xzf td_analysis_backup_YYYYMMDD.tar.gz -C ~/

# 重新安装依赖
cd ~/td_analysis
source venv/bin/activate
pip install -r requirements.txt

# 启动服务
~/td_analysis/start_services.sh
```

## 监控和维护

### 系统监控

```bash
# 系统资源
htop
free -h
df -h

# 网络连接
sudo netstat -tlnp
sudo ss -tlnp

# 进程状态
ps aux | grep python
ps aux | grep nginx
```

### 性能优化

1. **调整Nginx配置**
   ```bash
   sudo nano /etc/nginx/nginx.conf
   ```
   
2. **优化Python应用**
   - 增加worker进程数
   - 调整内存限制
   - 优化数据库查询

3. **系统调优**
   ```bash
   # 查看当前设置
   sysctl -a | grep -E '(net.core|vm.swappiness)'
   
   # 应用优化参数
   sudo sysctl -p
   ```

### 定期维护

1. **系统更新**（每月）
   ```bash
   sudo apt update
   sudo apt upgrade
   sudo apt autoremove
   ```

2. **日志清理**（每周）
   ```bash
   # 清理旧日志
   find ~/td_analysis/logs -name "*.log" -mtime +7 -delete
   
   # 清理系统日志
   sudo journalctl --vacuum-time=7d
   ```

3. **依赖更新**（每季度）
   ```bash
   cd ~/td_analysis
   source venv/bin/activate
   pip list --outdated
   pip install --upgrade package_name
   ```

## 故障排除

### 常见问题

#### 1. Web服务无法访问

**症状**: 浏览器无法打开网站

**排查步骤**:
```bash
# 检查服务状态
sudo supervisorctl status td_analysis_web
sudo systemctl status nginx

# 检查端口监听
sudo netstat -tlnp | grep -E ':(80|5000)'

# 检查防火墙
sudo ufw status

# 查看日志
sudo supervisorctl tail td_analysis_web
sudo tail -f /var/log/nginx/td_analysis_error.log
```

**解决方案**:
```bash
# 重启服务
sudo supervisorctl restart td_analysis_web
sudo systemctl restart nginx

# 检查配置文件
sudo nginx -t
```

#### 2. Python依赖错误

**症状**: 导入模块失败

**解决方案**:
```bash
cd ~/td_analysis
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

#### 3. 数据获取失败

**症状**: 无法获取股票数据

**排查步骤**:
```bash
# 检查网络连接
ping baidu.com

# 测试API接口
curl -I "https://api.example.com"

# 查看应用日志
tail -f ~/td_analysis/logs/app.log
```

#### 4. 磁盘空间不足

**症状**: 系统运行缓慢或错误

**解决方案**:
```bash
# 检查磁盘使用
df -h

# 清理日志文件
sudo journalctl --vacuum-size=100M
find ~/td_analysis/logs -name "*.log" -mtime +7 -delete

# 清理缓存
sudo apt autoremove
sudo apt autoclean
```

#### 5. 内存不足

**症状**: 进程被杀死或系统卡顿

**解决方案**:
```bash
# 检查内存使用
free -h

# 增加swap空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 紧急恢复

如果系统完全无法访问：

1. **重启所有服务**
   ```bash
   sudo systemctl restart supervisor
   sudo systemctl restart nginx
   sudo supervisorctl restart all
   ```

2. **重新部署**
   ```bash
   cd ~/td_analysis
   ./deploy.sh
   ```

3. **从备份恢复**
   ```bash
   # 参考备份恢复章节
   ```

## 安全建议

### 1. 系统安全

```bash
# 禁用root登录
sudo nano /etc/ssh/sshd_config
# 设置: PermitRootLogin no

# 更改SSH端口
# 设置: Port 2222

# 重启SSH服务
sudo systemctl restart ssh

# 更新防火墙规则
sudo ufw allow 2222/tcp
sudo ufw delete allow ssh
```

### 2. 应用安全

- 定期更新依赖包
- 使用HTTPS（配置SSL证书）
- 设置访问限制
- 监控异常访问

### 3. 数据安全

- 定期备份数据
- 加密敏感信息
- 限制文件权限
- 监控文件变化

## SSL证书配置（可选）

### 使用Let's Encrypt

```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 手动配置SSL

```bash
# 修改Nginx配置
sudo nano /etc/nginx/sites-available/td_analysis
```

添加SSL配置：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # 其他配置...
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## 联系支持

如果遇到无法解决的问题，请：

1. 收集错误日志
2. 记录重现步骤
3. 提供系统信息
4. 联系技术支持

---

**部署完成后，请及时修改默认密码和配置，确保系统安全！**