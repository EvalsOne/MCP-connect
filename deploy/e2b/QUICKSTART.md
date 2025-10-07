# 🚀 快速开始 - E2B MCP Sandbox Manager

## 最快安装方式（推荐）

### 方法 1: 本地克隆安装（最快最稳定）

```bash
# 1. 浅克隆仓库（只下载最新代码，速度快）
git clone --depth 1 --branch dev_streamable_http https://github.com/EvalsOne/MCP-bridge.git

# 2. 进入目录并安装
cd MCP-bridge/deploy/e2b
pip install -e .

# 3. 验证安装
python -c "from sandbox_deploy import E2BSandboxManager, SandboxConfig; print('✅ 安装成功!')"
```

### 方法 2: 使用快速安装脚本

```bash
# 下载并运行快速安装脚本
curl -O https://raw.githubusercontent.com/EvalsOne/MCP-bridge/dev_streamable_http/deploy/e2b/quick_install.sh
chmod +x quick_install.sh
./quick_install.sh dev_streamable_http
```

### 方法 3: pip 直接安装（可能较慢）

```bash
# 从 GitHub 安装（克隆完整仓库，可能需要几分钟）
pip install git+https://github.com/EvalsOne/MCP-bridge.git@dev_streamable_http#subdirectory=deploy/e2b
```

**注意**: 方法 3 会克隆完整的 Git 历史，如果网络慢可能会卡在 `git checkout` 步骤。建议使用方法 1。

## 🎯 快速测试

安装完成后，测试是否工作：

```python
import asyncio
from sandbox_deploy import E2BSandboxManager, SandboxConfig

async def quick_test():
    config = SandboxConfig(
        template_id="your-template-id",  # 替换为你的模板 ID
        timeout=600
    )
    manager = E2BSandboxManager(config)
    print("✅ E2BSandboxManager 已就绪!")

# 运行测试
asyncio.run(quick_test())
```

## 📝 设置环境变量

```bash
# 在你的 shell 配置文件中添加（~/.bashrc 或 ~/.zshrc）
export E2B_API_KEY='your-e2b-api-key'
export E2B_TEMPLATE_ID='your-template-id'

# 重新加载配置
source ~/.bashrc  # 或 source ~/.zshrc
```

或创建 `.env` 文件：

```bash
# 在你的项目目录创建 .env 文件
cat > .env << EOF
E2B_API_KEY=your-e2b-api-key
E2B_TEMPLATE_ID=your-template-id
EOF
```

## 🎉 运行示例

```bash
# 进入 e2b 目录
cd MCP-bridge/deploy/e2b

# 运行示例程序
python example_usage.py
```

## 📚 下一步

- **详细文档**: 查看 [USAGE_IN_OTHER_PROJECTS.md](./USAGE_IN_OTHER_PROJECTS.md)
- **API 参考**: 查看 [INSTALL.md](./INSTALL.md)
- **完整示例**: 查看 [example_usage.py](./example_usage.py)

## 🆘 遇到问题？

### 问题 1: pip 安装卡住

**症状**: `Running command git checkout -b dev_streamable_http` 很久没反应

**解决**: 使用方法 1（本地克隆）代替 pip 直接安装

### 问题 2: 导入错误

**症状**: `ModuleNotFoundError: No module named 'sandbox_deploy'`

**解决**:
```bash
# 检查安装
pip show e2b-mcp-sandbox

# 如果未安装，重新安装
cd /path/to/MCP-bridge/deploy/e2b
pip install -e .
```

### 问题 3: E2B API Key 错误

**症状**: `E2B_API_KEY environment variable not set`

**解决**:
```bash
export E2B_API_KEY='your-key-here'
```

## 💡 提示

- ✅ 使用虚拟环境以避免依赖冲突
- ✅ 使用浅克隆（`--depth 1`）加快下载速度
- ✅ 优先使用本地克隆而不是 pip 直接安装
- ✅ 保持 E2B API Key 在环境变量中

## 🔗 有用链接

- **GitHub 仓库**: https://github.com/EvalsOne/MCP-bridge
- **E2B 官网**: https://e2b.dev
- **获取 API Key**: https://e2b.dev/dashboard
