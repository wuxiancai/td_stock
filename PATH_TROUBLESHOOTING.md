# 路径问题故障排除指南

## 🚨 问题描述

在运行部署脚本时遇到以下错误：
```
[ERROR] 源目录 / 中没有找到文件
```

这个错误表明脚本无法正确识别项目根目录，导致文件复制失败。

## 🔍 问题原因

### 1. 脚本路径解析失败
- `$(dirname "$0")` 在某些环境下可能返回不正确的路径
- 使用软链接或特殊方式执行脚本时路径解析异常
- 在某些shell环境下 `$0` 变量可能不准确

### 2. 执行环境问题
- 脚本不在项目根目录中执行
- 通过管道或重定向方式执行脚本
- 在Docker容器或特殊环境中运行

### 3. 文件系统权限问题
- 当前用户没有访问脚本所在目录的权限
- 脚本文件被移动或删除

## ✅ 解决方案

### 1. 脚本改进（已实施）

**使用更可靠的路径获取方法：**
```bash
# 使用 BASH_SOURCE 而不是 $0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

**添加路径验证：**
```bash
# 检查路径是否为根目录（异常情况）
if [[ "$SCRIPT_DIR" == "/" ]]; then
    log_error "检测到异常的源目录路径: $SCRIPT_DIR"
    exit 1
fi
```

**增强调试信息：**
```bash
# 显示详细的路径信息
log_info "脚本路径: ${BASH_SOURCE[0]}"
log_info "项目目录: $SCRIPT_DIR"
log_info "当前用户: $(whoami)"
log_info "工作目录: $(pwd)"
```

### 2. 正确的执行方式

**推荐方式：**
```bash
# 进入项目根目录
cd /path/to/td_stock

# 直接执行脚本
./deploy.sh

# 或者使用bash执行
bash deploy.sh
```

**避免的方式：**
```bash
# 不要使用绝对路径在其他目录执行
cd /tmp
/path/to/td_stock/deploy.sh  # 可能导致路径问题

# 不要通过管道执行
cat deploy.sh | bash  # 会丢失脚本路径信息
```

### 3. 环境检查

**验证项目结构：**
```bash
# 确保在正确的目录
ls -la
# 应该看到：deploy.sh, requirements.txt, config.py 等文件

# 检查脚本权限
ls -l deploy.sh
# 应该有执行权限 (-rwxr-xr-x)
```

**设置执行权限：**
```bash
chmod +x deploy.sh
```

## 🔧 故障排除步骤

### 步骤1：验证当前位置
```bash
pwd
ls -la
```
确保在项目根目录，能看到 `deploy.sh` 文件。

### 步骤2：检查脚本权限
```bash
ls -l deploy.sh
```
确保脚本有执行权限。

### 步骤3：手动测试路径获取
```bash
# 测试路径获取命令
echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

### 步骤4：使用调试模式
```bash
# 启用bash调试模式
bash -x deploy.sh
```
这会显示每个命令的执行过程。

### 步骤5：检查系统环境
```bash
# 检查shell类型
echo $SHELL

# 检查bash版本
bash --version

# 检查当前用户
whoami
id
```

## 🛡️ 预防措施

### 1. 标准化执行流程
```bash
# 创建标准执行脚本
cat > run_deploy.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./deploy.sh
EOF
chmod +x run_deploy.sh
```

### 2. 添加环境检查
在脚本开头添加更多检查：
```bash
# 检查必要文件
if [[ ! -f "requirements.txt" ]]; then
    echo "错误：未在项目根目录执行脚本"
    echo "当前目录：$(pwd)"
    exit 1
fi
```

### 3. 使用绝对路径
如果需要从其他位置执行：
```bash
# 设置项目根目录
PROJECT_ROOT="/home/user/td_stock"
cd "$PROJECT_ROOT"
./deploy.sh
```

## 📋 常见问题解答

### Q: 为什么会出现源目录是 `/` 的情况？
A: 这通常发生在以下情况：
- 脚本通过软链接执行
- 在容器环境中执行
- `dirname` 命令无法正确解析路径
- 脚本被移动或重命名

### Q: 如何确保脚本在正确的目录执行？
A: 最佳实践：
1. 始终在项目根目录执行脚本
2. 使用 `./deploy.sh` 而不是绝对路径
3. 检查脚本输出的路径信息

### Q: 脚本修改后还是有问题怎么办？
A: 尝试以下步骤：
1. 重新下载或克隆项目
2. 检查文件权限和所有权
3. 在不同的shell环境中测试
4. 联系技术支持并提供详细的错误日志

## 🔍 调试技巧

### 1. 启用详细日志
```bash
# 在脚本开头添加
set -x  # 显示执行的命令
set -v  # 显示读取的行
```

### 2. 手动验证路径
```bash
# 测试各种路径获取方法
echo "方法1: $(dirname "$0")"
echo "方法2: $(dirname "${BASH_SOURCE[0]}")"
echo "方法3: $(readlink -f "$0")"
echo "方法4: $(realpath "$0")"
```

### 3. 检查环境变量
```bash
# 显示相关环境变量
echo "PWD: $PWD"
echo "HOME: $HOME"
echo "USER: $USER"
echo "SHELL: $SHELL"
```

## 📞 获取帮助

如果问题仍然存在，请提供以下信息：
1. 完整的错误日志
2. 系统信息 (`uname -a`)
3. 执行环境描述
4. 项目目录结构 (`ls -la`)
5. 脚本执行方式

通过这些改进，路径解析问题应该得到彻底解决。