# Docker 优先执行策略指南

本指南提供了一个决策框架，用于优先使用 Docker 作为运行时来执行脚本，当 Docker 不可用时回退到本地执行。

## 决策流程

### 第 1 步：检测环境

运行 `detect-env.js` 获取当前环境状态：

```bash
node docker-first-runner/scripts/detect-env.js
```

这会输出一个包含环境信息的 JSON 对象：

```json
{
  "docker": {
    "available": true,
    "usable": true,
    "version": "24.0.5",
    "error": null,
    "suggestion": null
  },
  "python": {
    "available": true,
    "version": "3.9.7",
    "path": "/usr/bin/python3",
    "error": null
  },
  "node": {
    "available": true,
    "version": "18.12.1",
    "path": "/usr/bin/node",
    "error": null
  },
  "platform": "darwin"
}
```

### 第 2 步：检查 Docker 可用性

评估环境状态中的 `docker.usable`：

| 条件 | 操作 |
|------|------|
| `docker.usable === true` | **使用 Docker** → 继续执行 Docker 命令 |
| `docker.usable === false` | **检查本地环境** → 进入第 3 步 |

### 第 3 步：检查本地版本兼容性

对于本地执行，使用 `version-compare.js` 验证已安装的版本是否满足最低要求：

```bash
node docker-first-runner/scripts/version-compare.js <已安装版本> <最低要求版本>
```

示例：
```bash
node docker-first-runner/scripts/version-compare.js 3.9.7 3.8.0
# 如果兼容则返回 "true" 并退出码 0
# 如果版本不足则返回 "false" 并退出码 1
```

参考 `language-matrix.md` 中的最低版本要求：
- Python: 3.8.0
- Node.js: 16.0.0
- Ruby: 2.7.0
- Go: 1.18.0
- Bash: 4.0.0

### 第 4 步：执行

根据决策路径，使用合适的方法执行。

## Docker 命令模板

### Python

```bash
docker run --rm -v "$(pwd):/workspace" -w /workspace python:3.11-slim python script.py [参数...]
```

**选项说明：**
- `--rm`: 执行后自动删除容器
- `-v "$(pwd):/workspace"`: 将当前目录挂载到容器中的 /workspace
- `-w /workspace`: 设置工作目录为 /workspace
- `python:3.11-slim`: 轻量级 Python 3.11 镜像

### Node.js

```bash
docker run --rm -v "$(pwd):/workspace" -w /workspace node:18-alpine node script.js [参数...]
```

**替代镜像：**
- `node:16-alpine` - 用于旧版 Node.js 兼容性
- `node:20-alpine` - 用于最新特性

## 错误处理指南

### docker_not_found（Docker 未找到）

**症状：** PATH 中未找到 Docker 可执行文件

**响应：**
```
Docker 未安装在此系统上。

安装 Docker：
- macOS: brew install docker
- Ubuntu/Debian: sudo apt-get install docker.io
- Windows: 从 https://docs.docker.com/get-docker/ 下载
- 或访问: https://docs.docker.com/get-docker/
```

### docker_daemon_not_running（Docker 守护进程未运行）

**症状：** Docker 已安装但 `docker ps` 失败

**响应：**
```
Docker 守护进程未运行。

启动 Docker：
- macOS: 启动 Docker Desktop 应用程序
- Linux: sudo systemctl start docker
- Windows: 从开始菜单启动 Docker Desktop
```

### docker_permission_denied（Docker 权限被拒绝）

**症状：** 运行 docker 命令时权限被拒绝

**响应：**
```
访问 Docker 权限被拒绝。

修复方法：
1. 将用户添加到 docker 组：
   sudo usermod -aG docker $USER

2. 注销并重新登录（或重启终端）

3. 验证：docker ps
```

### version_insufficient（版本不足）

**症状：** 本地版本低于最低要求

**响应：**
```
已安装版本 {installed} 低于最低要求 {required}。

选项：
1. 改用 Docker（推荐）
2. 升级本地安装：
   - Python: 使用 pyenv 或升级系统包
   - Node.js: 使用 nvm 或从 nodejs.org 下载
   - 查看 language-matrix.md 了解推荐版本
```

## 路径转换（Windows）

在 Windows 上运行时，将 Windows 路径转换为 Unix 格式以便 Docker 使用：

### 转换规则

| Windows 路径 | Unix 等价路径 |
|--------------|---------------|
| `C:\Users\name\project` | `/c/Users/name/project` |
| `D:\workspace\code` | `/d/workspace/code` |

### 实现代码

```javascript
function convertWindowsPath(winPath) {
  // 将反斜杠替换为正斜杠
  let unixPath = winPath.replace(/\\/g, '/');
  
  // 将盘符（C:）转换为 Unix 格式（/c）
  if (/^[A-Za-z]:/.test(unixPath)) {
    const drive = unixPath[0].toLowerCase();
    unixPath = `/${drive}${unixPath.substring(2)}`;
  }
  
  return unixPath;
}

// 示例
convertWindowsPath('C:\\Users\\name\\project');
// 返回: '/c/Users/name/project'
```

### 带 Windows 路径的 Docker 命令

```bash
# Windows 命令提示符
docker run --rm -v "C:\Users\name\project:/workspace" -w /workspace python:3.11-slim python script.py

# Windows Git Bash / MSYS2
docker run --rm -v "/c/Users/name/project:/workspace" -w /workspace python:3.11-slim python script.py
```

## 快速参考

| 场景 | 决策 |
|------|------|
| Docker 可用且可用 | 使用 Docker |
| Docker 可用但未运行 | 启动 Docker 或使用本地 |
| Docker 未安装 | 如果本地版本兼容则使用本地 |
| 本地版本满足要求 | 使用本地 |
| 本地版本不足 | 使用 Docker 或升级本地 |
| 两者都不可用 | 报告错误并给出指导 |

## 决策树示例

```
开始
  │
  ▼
运行 detect-env.js
  │
  ├─► docker.usable === true ──► 使用 Docker
  │
  └─► docker.usable === false
        │
        ▼
  检查本地版本
        │
        ├─► 版本 >= 最低要求 ──► 使用本地
        │
        └─► 版本 < 最低要求
              │
              ├─► 可以升级？ ──► 升级并使用本地
              │
              └─► 无法升级？ ──► 报告错误
```
