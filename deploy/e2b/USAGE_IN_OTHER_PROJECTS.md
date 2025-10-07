# 在其他项目中使用 E2BSandboxManager

本指南说明如何在你的项目中引入和使用 `E2BSandboxManager` 和 `SandboxConfig`。

## 📦 安装方式

### ⚠️ 重要提示

如果你遇到 `pip install git+https://...` 安装卡住或配置错误，**强烈推荐使用方法 1（本地克隆）**，这是最快最可靠的方式。

### 方式 1: 本地克隆安装（✅ 推荐 - 最快最稳定）

```bash
# 1. 浅克隆仓库（只下载最新代码，速度快）
git clone --depth 1 --branch dev_streamable_http https://github.com/EvalsOne/MCP-bridge.git

# 2. 进入目录并安装
cd MCP-bridge/deploy/e2b
pip install -e .

# 3. 验证安装
python verify_installation.py
```

### 方式 2: requirements.txt 方式（不推荐用于 GitHub 包）

如果你一定要在 `requirements.txt` 中引用，建议使用以下格式：

```txt
# 不推荐：直接从 GitHub 安装（可能很慢或失败）
# e2b-mcp-sandbox @ git+https://github.com/EvalsOne/MCP-bridge.git@dev_streamable_http#subdirectory=deploy/e2b

# 推荐：在安装脚本中手动克隆
# 或使用本地路径引用
-e /path/to/MCP-bridge/deploy/e2b
```

安装脚本示例：

```bash
#!/bin/bash
# install_deps.sh

# 克隆 MCP-bridge（如果尚未克隆）
if [ ! -d "external/MCP-bridge" ]; then
    git clone --depth 1 --branch dev_streamable_http \
        https://github.com/EvalsOne/MCP-bridge.git external/MCP-bridge
fi

# 安装其他依赖
pip install -r requirements.txt

# 安装 e2b-mcp-sandbox
pip install -e external/MCP-bridge/deploy/e2b
```

### 方式 3: 作为 Git 子模块

如果你想更灵活地控制版本:

```bash
# 在你的项目根目录
git submodule add https://github.com/EvalsOne/MCP-bridge.git external/mcp-bridge
git submodule update --init --recursive

# 添加到 Python 路径
export PYTHONPATH="${PYTHONPATH}:${PWD}/external/mcp-bridge/deploy/e2b"
```

在代码中:

```python
import sys
sys.path.insert(0, 'external/mcp-bridge/deploy/e2b')
from sandbox_deploy import E2BSandboxManager, SandboxConfig
```

### 方式 4: 本地开发安装

```bash
# 克隆仓库（推荐使用浅克隆加速）
git clone --depth 1 --branch dev_streamable_http https://github.com/EvalsOne/MCP-bridge.git
cd MCP-bridge/deploy/e2b

# 开发模式安装（修改会立即生效）
pip install -e .
```

## 🚀 基本使用

### 1. 导入模块

```python
from sandbox_deploy import E2BSandboxManager, SandboxConfig
```

### 2. 配置沙箱

```python
import os

config = SandboxConfig(
    template_id=os.getenv("E2B_TEMPLATE_ID"),  # 必需
    auth_token="your-secure-token",
    port=3000,
    timeout=3600
)
```

### 3. 创建和管理沙箱

```python
import asyncio

async def main():
    # 创建管理器
    manager = E2BSandboxManager(config)
    
    # 创建沙箱
    result = await manager.create_sandbox(
        sandbox_id="my-sandbox",
        enable_internet=True,
        wait_for_ready=True
    )
    
    if result["success"]:
        print(f"Sandbox URL: {result['public_url']}")
        
        # 使用沙箱...
        await asyncio.sleep(60)
        
        # 停止沙箱
        await manager.stop_sandbox("my-sandbox")

asyncio.run(main())
```

## 📚 实际应用场景

### 场景 1: 自动化测试框架

```python
# my_project/tests/e2b_test_runner.py
import pytest
from sandbox_deploy import E2BSandboxManager, SandboxConfig

@pytest.fixture(scope="session")
async def e2b_sandbox():
    """提供 E2B 沙箱用于测试"""
    config = SandboxConfig(
        template_id=os.getenv("E2B_TEMPLATE_ID"),
        timeout=1800  # 30分钟测试时间
    )
    manager = E2BSandboxManager(config)
    
    result = await manager.create_sandbox(
        sandbox_id="test-sandbox",
        enable_internet=True
    )
    
    yield result
    
    await manager.stop_sandbox("test-sandbox")

@pytest.mark.asyncio
async def test_mcp_integration(e2b_sandbox):
    """测试 MCP 集成"""
    mcp_url = e2b_sandbox["services"]["mcp_connect"]["url"]
    # 你的测试逻辑...
    assert mcp_url.startswith("https://")
```

### 场景 2: Web 应用后端

```python
# my_project/app/sandbox_service.py
from fastapi import FastAPI, HTTPException
from sandbox_deploy import E2BSandboxManager, SandboxConfig

app = FastAPI()
sandbox_manager = None

@app.on_event("startup")
async def startup():
    global sandbox_manager
    config = SandboxConfig(
        template_id=os.getenv("E2B_TEMPLATE_ID"),
        auth_token=os.getenv("SANDBOX_TOKEN"),
        timeout=7200
    )
    sandbox_manager = E2BSandboxManager(config)

@app.post("/sandbox/create")
async def create_sandbox(user_id: str):
    """为用户创建沙箱"""
    result = await sandbox_manager.create_sandbox(
        sandbox_id=f"user-{user_id}",
        enable_internet=True,
        wait_for_ready=True
    )
    
    if not result["success"]:
        raise HTTPException(500, result.get("error"))
    
    return {
        "sandbox_id": result["sandbox_id"],
        "url": result["public_url"],
        "novnc_url": result["novnc_url"]
    }

@app.delete("/sandbox/{sandbox_id}")
async def stop_sandbox(sandbox_id: str):
    """停止用户沙箱"""
    result = await sandbox_manager.stop_sandbox(sandbox_id)
    return result
```

### 场景 3: 批处理作业

```python
# my_project/jobs/batch_processor.py
import asyncio
from sandbox_deploy import E2BSandboxManager, SandboxConfig

class BatchProcessor:
    def __init__(self):
        self.config = SandboxConfig(
            template_id=os.getenv("E2B_TEMPLATE_ID"),
            timeout=10800  # 3小时
        )
        self.manager = E2BSandboxManager(self.config)
    
    async def process_jobs(self, jobs):
        """并行处理多个任务"""
        tasks = []
        for i, job in enumerate(jobs):
            task = self.process_single_job(f"job-{i}", job)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def process_single_job(self, sandbox_id, job):
        """在独立沙箱中处理单个任务"""
        result = await self.manager.create_sandbox(
            sandbox_id=sandbox_id,
            enable_internet=True
        )
        
        try:
            # 处理任务...
            await asyncio.sleep(5)  # 模拟工作
            return {"job": job, "status": "success"}
        finally:
            await self.manager.stop_sandbox(sandbox_id)

# 使用
async def main():
    processor = BatchProcessor()
    jobs = ["job1", "job2", "job3"]
    results = await processor.process_jobs(jobs)
    print(results)

asyncio.run(main())
```

### 场景 4: CLI 工具

```python
# my_project/cli.py
import click
import asyncio
from sandbox_deploy import E2BSandboxManager, SandboxConfig

@click.group()
def cli():
    """My Project CLI with E2B Sandbox support"""
    pass

@cli.command()
@click.option('--template-id', required=True, help='E2B template ID')
@click.option('--timeout', default=3600, help='Sandbox timeout in seconds')
def launch(template_id, timeout):
    """Launch a sandbox"""
    async def _launch():
        config = SandboxConfig(
            template_id=template_id,
            timeout=timeout
        )
        manager = E2BSandboxManager(config)
        result = await manager.create_sandbox()
        
        if result["success"]:
            click.echo(f"✅ Sandbox ready: {result['public_url']}")
        else:
            click.echo(f"❌ Failed: {result.get('error')}", err=True)
    
    asyncio.run(_launch())

@cli.command()
@click.argument('sandbox_id')
def stop(sandbox_id):
    """Stop a sandbox"""
    # 实现停止逻辑...
    pass

if __name__ == '__main__':
    cli()
```

## 🔧 高级配置

### 自定义配置类

```python
from sandbox_deploy import SandboxConfig
from dataclasses import dataclass

@dataclass
class MyProjectSandboxConfig(SandboxConfig):
    """扩展配置以适配项目需求"""
    project_name: str = "my-project"
    debug_mode: bool = False
    custom_env_vars: dict = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.debug_mode:
            self.timeout = 7200  # 调试时更长超时
            self.keepalive_interval = 30

# 使用
config = MyProjectSandboxConfig(
    template_id="my-template",
    project_name="test-project",
    debug_mode=True
)
```

### 包装器类

```python
from sandbox_deploy import E2BSandboxManager, SandboxConfig

class MyProjectSandboxManager:
    """项目特定的沙箱管理器包装"""
    
    def __init__(self, project_config):
        self.project_config = project_config
        
        sandbox_config = SandboxConfig(
            template_id=project_config.e2b_template_id,
            auth_token=project_config.auth_token,
            port=project_config.port
        )
        self.manager = E2BSandboxManager(sandbox_config)
    
    async def create_project_sandbox(self, user_id, workspace_id):
        """创建项目特定的沙箱"""
        sandbox_id = f"{user_id}-{workspace_id}"
        
        result = await self.manager.create_sandbox(
            sandbox_id=sandbox_id,
            enable_internet=True,
            wait_for_ready=True
        )
        
        if result["success"]:
            # 添加项目特定的初始化
            await self._initialize_workspace(result, workspace_id)
        
        return result
    
    async def _initialize_workspace(self, sandbox_result, workspace_id):
        """初始化工作空间"""
        # 项目特定的初始化逻辑
        pass
```

## 🐛 错误处理最佳实践

```python
import logging
from sandbox_deploy import E2BSandboxManager, SandboxConfig

logger = logging.getLogger(__name__)

async def robust_sandbox_creation():
    """健壮的沙箱创建示例"""
    config = SandboxConfig(template_id=os.getenv("E2B_TEMPLATE_ID"))
    manager = E2BSandboxManager(config)
    sandbox_id = None
    
    try:
        result = await manager.create_sandbox(
            sandbox_id="robust-test",
            enable_internet=True,
            wait_for_ready=True
        )
        
        if not result["success"]:
            logger.error(f"Sandbox creation failed: {result.get('error')}")
            return None
        
        sandbox_id = result["sandbox_id"]
        logger.info(f"Sandbox created: {result['public_url']}")
        
        # 执行你的逻辑
        # ...
        
        return result
        
    except Exception as e:
        logger.exception("Unexpected error during sandbox operation")
        return None
        
    finally:
        # 确保清理
        if sandbox_id:
            try:
                await manager.stop_sandbox(sandbox_id)
                logger.info(f"Sandbox {sandbox_id} stopped")
            except Exception as e:
                logger.warning(f"Failed to stop sandbox: {e}")
```

## 📝 环境变量配置

在你的项目中创建 `.env` 文件:

```bash
# E2B Configuration
E2B_API_KEY=your-e2b-api-key
E2B_TEMPLATE_ID=your-template-id

# Sandbox Configuration
SANDBOX_AUTH_TOKEN=your-auth-token
SANDBOX_PORT=3000
SANDBOX_TIMEOUT=3600

# Optional
SANDBOX_KEEPALIVE_INTERVAL=60
SANDBOX_VNC_PASSWORD=your-vnc-password
```

加载配置:

```python
from dotenv import load_dotenv
load_dotenv()

config = SandboxConfig(
    template_id=os.getenv("E2B_TEMPLATE_ID"),
    auth_token=os.getenv("SANDBOX_AUTH_TOKEN"),
    port=int(os.getenv("SANDBOX_PORT", "3000")),
    timeout=int(os.getenv("SANDBOX_TIMEOUT", "3600"))
)
```

## 🔗 相关资源

- **完整示例**: 查看 `example_usage.py`
- **API 文档**: 查看 `INSTALL.md`
- **E2B 文档**: https://e2b.dev/docs
- **源代码**: https://github.com/EvalsOne/MCP-bridge

## �️ 故障排除

### 安装卡在 git checkout 步骤

**问题**: `pip install git+https://...` 卡在 "Running command git checkout..." 很久

**原因**: pip 在克隆完整的 Git 历史，仓库较大时会很慢

**解决方案**:

1. **使用浅克隆（推荐）**:
   ```bash
   # 只克隆最新的提交
   git clone --depth 1 --branch dev_streamable_http https://github.com/EvalsOne/MCP-bridge.git
   cd MCP-bridge/deploy/e2b
   pip install .
   ```

2. **取消当前安装并使用本地克隆**:
   ```bash
   # 按 Ctrl+C 取消当前安装
   
   # 使用浅克隆
   git clone --depth 1 https://github.com/EvalsOne/MCP-bridge.git
   pip install ./MCP-bridge/deploy/e2b
   ```

3. **配置 Git 使用更快的协议**:
   ```bash
   # 如果 HTTPS 慢，尝试 SSH
   git config --global url."git@github.com:".insteadOf "https://github.com/"
   ```

4. **使用 pip 的 Git 选项**:
   ```bash
   pip install --no-cache-dir "git+https://github.com/EvalsOne/MCP-bridge.git@dev_streamable_http#subdirectory=deploy/e2b&egg=e2b-mcp-sandbox"
   ```

### 导入错误: ModuleNotFoundError

**问题**: `ModuleNotFoundError: No module named 'sandbox_deploy'`

**解决方案**:
```bash
# 确认安装成功
pip show e2b-mcp-sandbox

# 如果没有，重新安装
cd /path/to/MCP-bridge/deploy/e2b
pip install -e .
```

### E2B API Key 错误

**问题**: `E2B_API_KEY environment variable not set`

**解决方案**:
```bash
# 设置环境变量
export E2B_API_KEY='your-api-key-here'

# 或在代码中设置
import os
os.environ['E2B_API_KEY'] = 'your-api-key-here'
```

### 沙箱创建超时

**问题**: 沙箱创建时间过长或超时

**解决方案**:
```python
# 增加超时时间
config = SandboxConfig(
    template_id="your-template",
    timeout=7200  # 2小时
)

# 或禁用等待就绪检查
result = await manager.create_sandbox(
    wait_for_ready=False  # 不等待健康检查
)
```

### 包依赖冲突

**问题**: 安装时出现依赖版本冲突

**解决方案**:
```bash
# 使用虚拟环境隔离
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install ./MCP-bridge/deploy/e2b

# 或使用 --ignore-installed
pip install --ignore-installed ./MCP-bridge/deploy/e2b
```

## �💡 提示

1. **始终设置超时**: 防止沙箱无限运行产生费用
2. **使用环境变量**: 不要硬编码敏感信息
3. **实现清理逻辑**: 确保在异常情况下也能停止沙箱
4. **监控资源使用**: 跟踪活跃沙箱数量和运行时间
5. **测试健康检查**: 确保服务真正就绪后再使用

## 📮 获取帮助

如有问题或建议,请在 GitHub 仓库提交 Issue:
https://github.com/EvalsOne/MCP-bridge/issues
