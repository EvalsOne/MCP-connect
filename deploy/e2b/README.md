# 🌐 MCP Bridge - E2B 沙箱部署

将 MCP Bridge 部署到 E2B 云沙箱，获得完全隔离的运行环境。

## ⚡ 快速开始（5 分钟）

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

# 开发环境（快速构建）
make e2b:build:dev

# 或生产环境（完整功能）
make e2b:build:prod
```

### 4️⃣ 运行快速演示

```bash
python quickstart.py
```

看到 `🎉 MCP Bridge 已在 E2B 沙箱中运行！` 即表示成功！

---

## 📋 前置要求

在开始之前，请确保：
- ✅ 拥有 E2B 账号（注册：[e2b.dev](https://e2b.dev)）
- ✅ 获取了 E2B API Key（获取：[E2B Dashboard](https://e2b.dev/dashboard)）
- ✅ 安装了 Python 3.8+

E2B 沙箱镜像预装：

- ✅ Python 3 运行时
- ✅ Node.js 18+
- ✅ uv 工具链（`uv` 和 `uvx` 命令）
- ✅ MCP Bridge 服务
- ✅ Chrome DevTools（可选）

---

## 🔧 详细配置

### 构建沙箱模板

**开发环境**（快速构建，适合测试）：

```bash
make e2b:build:dev
# 或使用脚本并选择 Dockerfile / alias：
python build_dev.py \
  --dockerfile e2b.Dockerfile \
  --alias mcp-dev-gui \
  --cpu 2 \
  --memory-mb 2048

# 使用最小镜像：
python build_dev.py --dockerfile e2b.Dockerfile.minimal --alias mcp-dev-mini
```

**生产环境**（完整功能，包含所有依赖）：

```bash
make e2b:build:prod
# 或通过脚本（可自定义 Dockerfile / alias）
python build_prod.py \
  --dockerfile e2b.Dockerfile \
  --alias mcp-prod-gui --cpu 2 --memory-mb 2048

# 跳过缓存（默认已开启 skip cache，可显式指定）
python build_prod.py --skip-cache --alias mcp-prod-gui
```

构建完成后会显示模板 ID，例如：`mcp-xyz123`

---

## 💻 使用沙箱

### 方式 1：快速演示脚本（推荐新手）

运行预置的快速开始脚本：

```bash
python quickstart.py  # 仍然使用默认模板 ID

# 或直接创建沙箱并指定模板 ID：
python e2b_sandbox_manager.py --template-id <template-or-alias> --sandbox-id my_sandbox
```

此脚本会：
1. 创建 E2B 沙箱
2. 启动 MCP Bridge 服务
3. 自动测试健康检查和工具调用
4. 显示沙箱信息

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
| `quickstart.py` | 快速演示脚本（新手友好） |
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

## 🛠️ 沙箱内可用工具

E2B 沙箱预装了以下工具：

### Python 和 uvx

```bash
# 运行 Python 脚本
python3 -c "print('hello from sandbox')"

# 通过 uvx 执行 Python CLI
uvx some-python-cli --help

# 启动 MCP 服务器
uvx mcp-server-fetch
```

### Node.js 和 npm

```bash
# 运行 Node.js 脚本
node -e "console.log('hello')"

# 使用 npm 包
npx @modelcontextprotocol/server-github
```

### MCP Bridge API

```bash
# 健康检查
curl http://localhost:3000/health

# 调用桥接端点
curl -X POST http://localhost:3000/bridge \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"serverPath":"uvx","args":["mcp-server-fetch"],"method":"tools/list","params":{}}'
```

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

参数说明：

| 参数 | 说明 |
|------|------|
| `--template-id` | 使用 `build_dev.py` 或 `build_prod.py` 生成的模板 ID 或 alias |
| `--sandbox-id` | 逻辑沙箱名（默认 `mcp_test_sandbox`） |
| `--no-internet` | 关闭沙箱外网访问 |
| `--no-wait` | 不等待服务 `/health` 就绪，直接返回结果 |
| `--timeout` | 设置沙箱生命周期（秒） |

### 进入沙箱调试

```python
# 在 Python 代码中
process = await sandbox.process.start("bash", on_stdout=print, on_stderr=print)
await process.send_stdin("ls -la /app\n")
```

---

## ⚙️ 配置 MCP 服务器

编辑 `servers.json` 添加自定义 MCP 服务器：

```json
{
  "servers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## 📖 更多资源

- **完整部署指南**：[../../docs/deployment-guide.md](../../docs/deployment-guide.md)
- **配置说明**：[../../docs/configuration-guide.md](../../docs/configuration-guide.md)
- **E2B 官方文档**：https://e2b.dev/docs
- **MCP 协议规范**：https://modelcontextprotocol.io

---

## 🐛 常见问题

### 沙箱创建失败

```
❌ Error: Failed to create sandbox
```

**解决方案**：
1. 检查 E2B API Key 是否正确
2. 确认模板已构建成功
3. 查看账户配额是否用尽

### 服务启动超时

```
❌ 超时：等待服务启动
```

**解决方案**：
1. 增加 `wait_for_server` 的 `max_retries`
2. 检查沙箱日志：`python view_sandbox_logs.py <id>`
3. 确认镜像包含所有依赖

### 无法调用 MCP 工具

```
❌ 401 Unauthorized
```

**解决方案**：
1. 检查 `ACCESS_TOKEN` 是否正确传递
2. 确认请求头包含 `Authorization: Bearer <token>`

---

## 🚀 下一步

1. ✅ 运行 `python quickstart.py` 体验沙箱
2. ✅ 自定义 `servers.json` 添加你的 MCP 服务器
3. ✅ 阅读完整部署指南了解高级功能
4. ✅ 查看 E2B 文档探索更多可能性

**享受在云端运行 MCP Bridge 的乐趣！** 🎉