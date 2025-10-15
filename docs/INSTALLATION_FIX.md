# 安装问题修复说明

## 问题描述

在使用 `pip install git+https://github.com/...` 安装时遇到以下错误：

```
ValueError: invalid pyproject.toml config: `tool.setuptools.packages`.
configuration error: `tool.setuptools.packages` must be valid exactly by one definition
```

## 根本原因

`pyproject.toml` 中的配置错误：

```toml
[tool.setuptools]
packages = ["."]  # ❌ 错误：'.' 不是有效的 Python 模块名
```

## 修复方案

### 1. 修复 pyproject.toml

将 `packages` 改为 `py-modules`，因为这个项目是单文件模块而不是包：

```toml
[tool.setuptools]
py-modules = ["sandbox_deploy"]  # ✅ 正确：指定单个模块文件

[tool.setuptools.package-data]
"*" = ["startup.sh", "chrome-devtools-wrapper.sh", "servers.json", "nginx.conf"]
```

### 2. 简化 setup.py

由于已经有了 `pyproject.toml`，简化 `setup.py` 避免配置冲突：

```python
from setuptools import setup
setup()  # 所有配置在 pyproject.toml 中
```

### 3. 更新 MANIFEST.in

确保所有必要的文件都被包含：

```
include README.md
include INSTALL.md
include LICENSE
include startup.sh
include chrome-devtools-wrapper.sh
include servers.json
include nginx.conf
```

## 推荐的安装方式

### ✅ 方式 1: 本地克隆（最推荐）

```bash
git clone --depth 1 --branch dev_streamable_http https://github.com/EvalsOne/MCP-bridge.git
cd MCP-bridge/deploy/e2b
pip install -e .
```

**优点**:
- 速度快（浅克隆只下载最新代码）
- 可靠（不依赖 pip 的 Git 集成）
- 可编辑（`-e` 模式方便开发）
- 包含所有配套文件

### ⚠️ 方式 2: pip 直接安装（可能慢）

```bash
pip install git+https://github.com/EvalsOne/MCP-bridge.git@dev_streamable_http#subdirectory=deploy/e2b
```

**缺点**:
- 克隆完整 Git 历史（较慢）
- 可能卡在 `git checkout` 步骤
- 网络问题可能导致失败

## 验证安装

运行验证脚本：

```bash
python verify_installation.py
```

或手动验证：

```python
from sandbox_deploy import E2BSandboxManager, SandboxConfig
print("✅ 安装成功!")
```

## 常见问题

### Q1: pip 安装卡在 git checkout 很久？

**A**: 这是因为 pip 在克隆完整的 Git 历史。解决方案：
1. 按 `Ctrl+C` 取消
2. 使用方式 1（本地克隆）

### Q2: 出现 "invalid pyproject.toml" 错误？

**A**: 确保你使用的是修复后的版本：
```bash
git pull origin dev_streamable_http
```

### Q3: 导入模块失败？

**A**: 检查安装：
```bash
pip show e2b-mcp-sandbox
python -c "from sandbox_deploy import E2BSandboxManager"
```

## 技术细节

### py-modules vs packages

- **`py-modules`**: 用于单个 `.py` 文件（如 `sandbox_deploy.py`）
- **`packages`**: 用于包含 `__init__.py` 的目录结构

本项目使用 `py-modules` 因为：
- 主要代码在单个文件 `sandbox_deploy.py` 中
- 配套文件通过 `package-data` 包含
- 简单直接，易于分发

### 文件结构

```
deploy/e2b/
├── sandbox_deploy.py          # 主模块
├── pyproject.toml             # 项目配置（主要）
├── setup.py                   # 构建脚本（简化）
├── MANIFEST.in                # 文件清单
├── __init__.py                # 包初始化（可选）
├── startup.sh                 # 配套脚本
├── chrome-devtools-wrapper.sh # 配套脚本
├── servers.json               # 配套配置
├── nginx.conf                 # 配套配置
└── *.md                       # 文档
```

## 更新日志

- ✅ 修复 `pyproject.toml` 中的 `packages` 配置
- ✅ 简化 `setup.py` 避免配置冲突
- ✅ 更新 `MANIFEST.in` 包含所有必要文件
- ✅ 添加安装验证脚本
- ✅ 更新文档说明推荐的安装方式
- ✅ 添加快速开始指南

## 参考链接

- [Setuptools 文档](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)
- [PEP 621 - pyproject.toml](https://peps.python.org/pep-0621/)
- [Python Packaging Guide](https://packaging.python.org/)
