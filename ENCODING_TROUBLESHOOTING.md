# 字符编码问题故障排除指南

## 问题描述

在部署过程中可能遇到以下字符编码问题：
- 日志输出显示为问号 `???` 或乱码
- 中文字符无法正确显示
- `UnicodeDecodeError` 或 `UnicodeEncodeError` 错误
- 终端显示 `[INFO] ??????...` 等乱码信息

## 常见原因

1. **系统locale设置不正确**
2. **缺少UTF-8语言包**
3. **终端编码设置问题**
4. **Python环境编码配置错误**
5. **SSH连接编码设置问题**

## 解决方案

### 1. 检查当前编码设置

```bash
# 查看当前locale设置
locale

# 查看可用的locale
locale -a

# 查看环境变量
echo $LANG
echo $LC_ALL
```

### 2. 安装和配置UTF-8支持

```bash
# 更新包列表
sudo apt update

# 安装locale包
sudo apt install -y locales language-pack-en language-pack-zh-hans

# 生成UTF-8 locale
sudo locale-gen en_US.UTF-8
sudo locale-gen zh_CN.UTF-8

# 更新系统locale
sudo update-locale LANG=en_US.UTF-8

# 重新配置locales（可选）
sudo dpkg-reconfigure locales
```

### 3. 设置环境变量

**临时设置（当前会话）：**
```bash
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8
```

**永久设置（添加到 ~/.bashrc）：**
```bash
echo 'export LANG=C.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=C.UTF-8' >> ~/.bashrc
echo 'export PYTHONIOENCODING=utf-8' >> ~/.bashrc
source ~/.bashrc
```

**系统级设置：**
```bash
# 编辑系统环境文件
sudo nano /etc/environment

# 添加以下内容：
LANG=C.UTF-8
LC_ALL=C.UTF-8
PYTHONIOENCODING=utf-8
```

### 4. SSH连接编码设置

**客户端设置（本地终端）：**
```bash
# 对于macOS Terminal
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# SSH连接时指定编码
ssh -o "SendEnv LANG LC_*" user@server
```

**服务器端设置：**
```bash
# 编辑SSH配置
sudo nano /etc/ssh/sshd_config

# 确保包含以下设置：
AcceptEnv LANG LC_*

# 重启SSH服务
sudo systemctl restart sshd
```

### 5. Python编码设置

**在Python脚本中：**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 设置默认编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 确保stdout使用UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
```

**环境变量设置：**
```bash
export PYTHONIOENCODING=utf-8
export PYTHONLEGACYWINDOWSSTDIO=utf-8
```

## 验证修复

### 1. 测试基本字符显示

```bash
# 测试中文字符
echo "测试中文字符显示"

# 测试特殊字符
echo "✓ ✗ → ← ↑ ↓"

# 测试emoji（如果支持）
echo "🚀 🎉 ⚠️ ❌"
```

### 2. 测试Python编码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("测试中文输出")
print("当前编码:", sys.stdout.encoding)
print("文件系统编码:", sys.getfilesystemencoding())

# 测试文件读写
with open('test_utf8.txt', 'w', encoding='utf-8') as f:
    f.write('测试UTF-8文件写入\n')

with open('test_utf8.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    print("文件内容:", content.strip())

os.remove('test_utf8.txt')
print("UTF-8测试完成")
```

### 3. 测试部署脚本

```bash
# 运行部署脚本的编码测试部分
bash -c '
source deploy.sh
check_locale
'
```

## 特定问题解决

### 问题1：终端显示 `[INFO] ??????...`

**原因：** 终端不支持UTF-8或locale设置错误

**解决：**
```bash
# 1. 设置终端编码
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# 2. 重新运行脚本
./deploy.sh
```

### 问题2：Python UnicodeDecodeError

**原因：** Python读取文件时编码不匹配

**解决：**
```bash
# 设置Python编码环境变量
export PYTHONIOENCODING=utf-8

# 或在Python代码中明确指定编码
# with open('file.txt', 'r', encoding='utf-8') as f:
```

### 问题3：Web界面中文乱码

**原因：** Web服务器或浏览器编码设置问题

**解决：**
```python
# 在Flask应用中设置
app.config['JSON_AS_ASCII'] = False

# 在HTML模板中添加
# <meta charset="UTF-8">
```

### 问题4：数据库中文乱码

**原因：** 数据库字符集设置不正确

**解决：**
```sql
-- MySQL
CREATE DATABASE td_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- PostgreSQL
CREATE DATABASE td_analysis WITH ENCODING 'UTF8';
```

## 预防措施

### 1. 系统初始化时设置编码

```bash
# 在新系统上首先执行
sudo apt update
sudo apt install -y locales language-pack-en
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
```

### 2. 在脚本开头设置编码

```bash
#!/bin/bash
# -*- coding: utf-8 -*-

# 设置编码环境变量
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8
```

### 3. 在Python项目中使用编码声明

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 在文件开头明确声明编码
```

### 4. 配置开发环境

**VS Code设置：**
```json
{
    "files.encoding": "utf8",
    "terminal.integrated.env.linux": {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8"
    }
}
```

**Git设置：**
```bash
git config --global core.quotepath false
git config --global gui.encoding utf-8
git config --global i18n.commit.encoding utf-8
```

## 常用命令参考

```bash
# 查看系统编码信息
locale
locale -a
echo $LANG
echo $LC_ALL

# 测试字符显示
echo "测试中文"
python3 -c "print('Python中文测试')"

# 重新生成locale
sudo locale-gen
sudo update-locale

# 重启相关服务
sudo systemctl restart ssh
sudo systemctl restart nginx

# 查看文件编码
file -bi filename

# 转换文件编码
iconv -f GBK -t UTF-8 input.txt > output.txt
```

## 联系支持

如果按照以上步骤仍无法解决编码问题，请提供以下信息：

1. 系统版本：`lsb_release -a`
2. 当前locale：`locale`
3. 环境变量：`env | grep -E '(LANG|LC_|PYTHON)'`
4. 终端类型和版本
5. 具体错误信息和截图

---

**更新时间：** 2024年7月  
**适用版本：** Ubuntu 20.04+  
**维护者：** TD Analysis Team