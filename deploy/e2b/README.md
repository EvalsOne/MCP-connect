# 🌐 MCP Bridge - E2B 沙箱部署

将 MCP Bridge 部署到 E2B 云沙箱，获得完全隔离的运行环境。

## ⚡ 快速开始

### 1️⃣ 安装依赖

```bash
pip install e2b requests
```

### 2️⃣ 设置 API Key

注册 E2B 账号并获取 API Key：https://e2b.dev/dashboard

```bash
export E2B_API_KEY=your-api-key-here
```

### 3️⃣ 构建沙箱模板

```bash
cd deploy/e2b

# 开发环境
python build_dev.py

# 或生产环境
python build_prod.py
```

参数说明：

- `--variant`
  - 说明：模板便捷选择（自动映射到内置 Dockerfile）。
  - 可选值：`full`（GUI + noVNC）、`simple`（无 X 桌面，仅 headless Chrome）、`minimal`（最小化，无 X/Chrome/noVNC）。
  - 默认值：`full`
  - 示例：`--variant simple`

- `--dockerfile`
  - 说明：Dockerfile 的相对或绝对路径，用于构建模板镜像。若指定此项，将覆盖 `--variant` 的选择。
  - 示例：`--dockerfile e2b.Dockerfile.minimal`

- `--alias`
  - 说明：为构建的模板指定一个别名（alias）。未指定时会根据 `--variant` 自动选择：
    - `full` → `mcp-dev-gui`
    - `simple` → `mcp-dev-simple`
    - `minimal` → `mcp-dev-minimal`
  - 示例：`--alias mcp-dev-gui`

- `--cpu`
  - 说明：构建时分配的虚拟 CPU 数量（整数）。
  - 默认值：`2`
  - 示例：`--cpu 4`

- `--memory-mb`
  - 说明：构建时分配的内存大小，单位为 MB（整数）。
  - 默认值：`2048`
  - 示例：`--memory-mb 4096`

- `--skip-cache`
  - 说明：布尔开关；如果指定则在构建时跳过 Docker 缓存以强制重新构建全部层。开发环境默认使用缓存，生产环境默认不使用缓存。
  - 示例：`--skip-cache`

示例：

```bash
# 使用内置 simple 变体（无 X 桌面，无 noVNC，headless Chrome），并注册为 mcp-dev-simple
python build_dev.py --variant simple --cpu 2 --memory-mb 2048

# 使用最小化变体（无 X/Chrome/noVNC，最快启动），并注册为 mcp-dev-minimal
python build_dev.py --variant minimal --cpu 1 --memory-mb 1024 --skip-cache

# 使用默认 Dockerfile，但把 alias 设置为 mcp-dev-gui，分配 4 CPU、4GB 内存
python build_dev.py --alias mcp-dev-gui --cpu 4 --memory-mb 4096
```

---

## 💻 使用沙箱

### 方式 1：快速演示脚本（推荐新手）

运行预置的快速开始脚本：

```bash
# GUI 模式（默认）
python sandbox_deploy.py --template-id <template-id-or-alias>

# 轻量级无桌面模式（跳过 X/Chrome/VNC/noVNC）
python sandbox_deploy.py --template-id <template-id-or-alias> --headless
```

此脚本会：
1. 创建 E2B 沙箱
2. 启动 MCP Bridge 服务
3. 自动测试健康检查和工具调用
4. 显示沙箱信息

参数说明：

下面的参数对应 `deploy/e2b/sandbox_deploy.py` 的 CLI 选项（脚本将检查并回退到环境变量，必要时会退出）：

- `--template-id`
  - 说明：要使用的模板 ID 或 alias。可以通过命令行指定，也可以通过环境变量 `E2B_TEMPLATE_ID` 提供。
  - 必需性：如果既没有 `--template-id` 也没有 `E2B_TEMPLATE_ID`，脚本会报错并退出。
  - 示例：`--template-id mcp-xyz123`

- `--sandbox-id`
  - 说明：逻辑沙箱名称（用于本地管理与显示）。
  - 默认值：`mcp_test_sandbox`
  - 示例：`--sandbox-id demo1`

- `--no-internet`
  - 说明：布尔开关；如果指定则在创建的沙箱中禁用外网访问（allow_internet_access=False）。
  - 默认值：允许外网访问（除非你指定此标志）。

- `--no-wait`
  - 说明：布尔开关；如果指定则脚本在创建沙箱后不等待内部服务 `/health` 就绪，直接返回。适合快速启动但不保证服务已经准备好。
  - 默认值：等待服务就绪（会进行 /health 探测）。

- `--timeout`
  - 说明：沙箱的生命周期（秒）。该值也可以通过环境变量 `E2B_SANDBOX_TIMEOUT` 设置。
  - 默认值：`3600`（1 小时）
  - 示例：`--timeout 7200`

- `--headless`
  - 说明：轻量级无桌面模式；跳过 Xvfb/fluxbox/Chrome/VNC/noVNC 的启动，仅保留 Nginx + MCP-connect。适合对 GUI 不依赖的场景，可显著加快启动速度。
  - 默认值：关闭（GUI 模式）。

重要环境变量：

- `E2B_API_KEY`：必须设置；脚本入口检查此环境变量并在缺失时退出。示例：

```bash
export E2B_API_KEY='your-api-key-here'
```

- `E2B_TEMPLATE_ID`：可作为 `--template-id` 的替代（优先命令行参数）。
- `E2B_SANDBOX_TIMEOUT`：设置默认的超时时间（秒），等同于 `--timeout`。

使用示例：

```bash
# 指定模板并等待服务就绪
python sandbox_deploy.py --template-id mcp-xyz123 --sandbox-id demo1

# 从环境变量读取模板 ID，禁用外网，不等待就绪
export E2B_TEMPLATE_ID=mcp-xyz123
python sandbox_deploy.py --no-internet --no-wait
```



### 方式 2：自定义 Python 代码

```python
from e2b import AsyncSandbox
import asyncio

async def main():
    # 创建沙箱实例（替换为你的模板 ID）
    sandbox = await AsyncSandbox.create('mcp-xyz123')

    try:
        # 启动 MCP Bridge 服务
        process = await sandbox.process.start(
            cmd="cd /app && ACCESS_TOKEN=my-token npm start"
        )

        # 等待服务启动
        await asyncio.sleep(5)

        # 调用 API
        result = await sandbox.commands.run(
            'curl http://localhost:3000/health'
        )
        print(f'健康检查: {result.stdout}')

        # 使用你的沙箱...

    finally:
        # 清理
        await sandbox.kill()

asyncio.run(main())
```

---

## 📁 模板文件结构

| 文件 | 说明 |
|------|------|
| `template.py` | 沙箱模板配置定义 |
| `build_dev.py` | 开发环境构建脚本 |
| `build_prod.py` | 生产环境构建脚本 |
| `e2b.Dockerfile` | 完整沙箱镜像定义 |
| `e2b.Dockerfile.minimal` | 最小化镜像（仅核心功能） |
| `servers.json` | MCP 服务器配置 |
| `startup.sh` | 沙箱启动脚本 |
| `nginx.conf` | Nginx 反向代理配置 |
| `view_sandbox_logs.py` | 日志查看工具 |
| `e2b_sandbox_manager.py` | 沙箱管理工具 |

---

## 🔍 管理和调试

### 查看沙箱日志

```bash
python view_sandbox_logs.py <sandbox-id>
```

### 管理沙箱实例

新版 `e2b_sandbox_manager.py` 支持参数：

```bash
# 创建沙箱（可指定模板 ID 或 alias）
python e2b_sandbox_manager.py --template-id <template-or-alias> --sandbox-id demo1

# 禁用等待健康检查 / 禁用外网
python e2b_sandbox_manager.py --template-id <template-or-alias> --no-wait --no-internet

# 列出活跃沙箱（当前进程上下文缓存）
python e2b_sandbox_manager.py list

# 停止一个沙箱
python e2b_sandbox_manager.py stop <sandbox_id>

# 停止全部沙箱
python e2b_sandbox_manager.py stop-all
```

### 进入沙箱调试

```python
python view_sandbox_logs.py <sandbox_id> --exec "<command_to_run>"
```

---

## 📖 更多资源

- **E2B 官方文档**：https://e2b.dev/docs
- **MCP 协议规范**：https://modelcontextprotocol.io

---


**享受在云端运行 MCP Connect 的乐趣！** 🎉
