# MCP Connect

    ███╗   ███╗ ██████╗██████╗      ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗
    ████╗ ████║██╔════╝██╔══██╗    ██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝
    ██╔████╔██║██║     ██████╔╝    ██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   
    ██║╚██╔╝██║██║     ██╔═══╝     ██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   
    ██║ ╚═╝ ██║╚██████╗██║         ╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   
    ╚═╝     ╚═╝ ╚═════╝╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   


<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4+-blue)](https://www.typescriptlang.org/)

**将 MCP 服务器转换为 HTTP API 的轻量级桥接服务**

[English](#) • [简体中文](#)

</div>

---

## 📖 什么是 MCP Connect？

MCP Connect？ 是一个 HTTP 网关服务，让你可以通过 HTTP 方式调用使用 Stdio 通信协议的本地 MCP 服务器。

### 最新更新

- Added Streamable HTTP mode on top of the classic request/response bridge
- New quick-deploy scripts and configs under `deploy/e2b` for launching in an E2B sandbox

## 工作原理

```
+-----------------+   HTTP (JSON)               +------------------+      stdio      +------------------+
|                 |   /bridge                   |                  |                 |                  |
|  Cloud AI tools | <------------------------>  |  Node.js Bridge  | <------------>  |    MCP Server    |
|   (Remote)      |                             |    (Local)       |                 |     (Local)      |
|                 |   HTTP (SSE stream)         |                  |                 |                  |
|                 |   /mcp/:serverId            |                  |                 |                  |
+-----------------+         Tunnels (optional)  +------------------+                 +------------------+
```

**✨ 核心特性**

| 特性 | 说明 |
|------|------|
| 🚀 **双模式支持** | 可使用 Streamable HTTP 或者经典 HTTP 桥接方式调用 |
| 🔄 **Session管理** | 支持通过Session机制维护对话的连续性 |
| 🔐 **安全防护** | Bearer Token 认证 + CORS 白名单 |
| 🌐 **公网访问** | 内置 Ngrok 隧道，一键暴露外网 |
| ☁️ **云端部署** | 一键部署到 E2B 云沙箱（安全隔离） |
---

## 🚀 快速开始

### 前置要求

- Node.js >= 20.0.0
- npm 或 yarn

### 1️⃣ 安装

```bash
git clone https://github.com/EvalsOne/MCP-connect.git
cd mcp-connect
npm install
```

### 2️⃣ 配置

**步骤 A：设置环境变量**

```bash
cp .env.example .env
vim .env  # 编辑配置
```

```env
# 服务端口
PORT=3000

# 访问令牌（强烈建议设置！）
ACCESS_TOKEN=your-secret-token-here

# 可选：Ngrok 令牌（用于外网访问）
NGROK_AUTH_TOKEN=your-ngrok-token
```

**步骤 B：配置 MCP 服务器**（推荐使用 JSON 标准格式）

```bash
cp mcp-servers.example.json mcp-servers.json
vim mcp-servers.json  # 编辑配置
```

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "HTTP 内容抓取"
    }
  }
}
```

<details>
<summary>其他配置方式</summary>

**方式 2：YAML 格式**（更易读）

```bash
cp mcp-servers.example.yaml mcp-servers.yaml
```

**方式 3：环境变量**（简单场景）

在 `.env` 中添加：

```env
MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]}}
```

</details>

### 3️⃣ 启动

```bash
# 构建并启动
npm run build
npm start

# 或使用开发模式（热重载）
npm run dev

# 启用 Ngrok 隧道
npm run start:tunnel
```

看到启动横幅后，访问 http://localhost:3000/health 检查服务状态！

### 🌐 快速部署到 E2B 云沙箱

> E2B 提供隔离的云端沙箱环境，适合运行不受信任的 MCP 服务器。

#### 步骤 1️⃣：准备 E2B 环境

```bash
# 注册 E2B 账号
访问 https://e2b.dev 并获取 API Key

# 安装 E2B CLI
pip install e2b

# 设置 API Key
export E2B_API_KEY=your-e2b-api-key
```

#### 步骤 2️⃣：构建沙箱模板

```bash
cd deploy/e2b

# 开发环境
make e2b:build:dev

# 或生产环境
make e2b:build:prod
```

构建完成后会显示模板 ID，例如：`mcp-xyz123`

#### 步骤 3️⃣：在代码中使用

```python
from e2b import AsyncSandbox
import asyncio

async def main():
    # 创建沙箱（3 秒内启动）
    sandbox = await AsyncSandbox.create('mcp-xyz123')

    # 启动 MCP Bridge 服务
    await sandbox.process.start("cd /app && npm start")

    # 使用沙箱中的服务...
    # 详见 docs/deployment-guide.md

    await sandbox.kill()

asyncio.run(main())
```

**E2B 优势**：
- ✅ 完全隔离（安全运行第三方代码）
- ✅ 快速启动（< 3 秒）
- ✅ 按需扩容
- ✅ 预装 Node.js + Python + uvx

详细文档：[E2B 部署指南](docs/deployment-guide.md#e2b-沙箱部署)

---

## 📚 使用指南

### 模式一：Streamable HTTP方式

通用型更强，可以被任何支持 Steamable http 协议的 MCP 客户端调用。

#### 步骤 1：配置服务器

**推荐方式：使用 JSON 配置文件**（MCP 标准格式）⭐

创建 `mcp-servers.json`：

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "HTTP/HTTPS 内容抓取工具"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "访问 /tmp 目录"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      },
      "description": "GitHub API 集成"
    }
  }
}
```

然后在 `.env` 中设置敏感信息：

```env
GITHUB_TOKEN=ghp_your_token_here
```

<details>
<summary><b>其他配置方式</b></summary>

**方式 2：YAML 格式**（更易读，支持注释）

```yaml
mcpServers:
  fetch:
    command: uvx
    args: [mcp-server-fetch]
```

**方式 3：环境变量**（简单场景）

```env
MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]}}
```

</details>

> 💡 **提示**：
> - JSON 格式与 MCP 标准配置保持一致
> - 支持环境变量引用：`${VAR_NAME}` 语法
> - 详细配置指南：[docs/configuration-guide.md](docs/configuration-guide.md)

#### 步骤 2：创建会话并发送请求

```bash
curl -N http://localhost:3000/mcp/fetch \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '[
    {"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}
  ]'
```

**响应示例**（SSE 格式）：

```
event: message
id: 1
data: {"jsonrpc":"2.0","id":"1","result":{"tools":[...]}}
```

响应头会包含 `mcp-session-id: xxx-xxx-xxx`，用于后续请求。

#### 步骤 3：复用会话

```bash
curl -N http://localhost:3000/mcp/fetch \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "mcp-session-id: xxx-xxx-xxx" \
  -H "Accept: application/json, text/event-stream" \
  -d '[
    {"jsonrpc":"2.0","id":"2","method":"tools/call","params":{...}}
  ]'
```

#### 步骤 4：主动关闭会话（可选）

```bash
curl -X DELETE http://localhost:3000/mcp/fetch \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "mcp-session-id: xxx-xxx-xxx"
```

**💡 提示**：会话空闲 5 分钟后会自动回收（可通过 `STREAM_SESSION_TTL_MS` 配置）。

---

### 模式二：经典桥接方式

非官方标准的调用方式，需要自己实现 tools/list, tools/call 等具体的方法

#### 示例 1：列出可用工具

```bash
curl -X POST http://localhost:3000/bridge \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "serverPath": "uvx",
    "args": ["mcp-server-fetch"],
    "method": "tools/list",
    "params": {}
  }'
```

#### 示例 2：调用工具

```bash
curl -X POST http://localhost:3000/bridge \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "serverPath": "uvx",
    "args": ["mcp-server-fetch"],
    "method": "tools/call",
    "params": {
      "name": "fetch",
      "arguments": {
        "url": "https://example.com"
      }
    }
  }'
```

---

## 🔧 配置参数

### 环境变量

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PORT` | `3000` | HTTP 服务端口 |
| `AUTH_TOKEN` | - | API 访问令牌（强烈建议设置） |
| `ALLOWED_ORIGINS` | - | CORS 白名单，逗号分隔（如 `https://app.com,https://api.com`） |
| `LOG_LEVEL` | `INFO` | 日志级别（`DEBUG`、`INFO`、`WARN`、`ERROR`） |
| `STREAM_SESSION_TTL_MS` | `300000` | 流式会话空闲超时（毫秒） |
| `NGROK_AUTH_TOKEN` | - | Ngrok 认证令牌 |

### MCP 服务器配置

**推荐：使用 JSON 配置文件**（MCP 标准格式）

创建 `mcp-servers.json`（优先级最高）：

```json
{
  "mcpServers": {
    "server-name": {
      "command": "可执行命令",
      "args": ["参数1", "参数2"],
      "env": {
        "KEY": "value",
        "SECRET": "${ENV_VAR}"
      },
      "description": "服务器描述",
      "timeout": 30000,
      "retries": 3
    }
  }
}
```

**配置优先级**：
1. `mcp-servers.json` ← 最高优先级（MCP 标准）
2. `mcp-servers.yaml` ← YAML 格式（更易读）
3. `mcp-servers.yml`
4. `MCP_SERVERS` 环境变量 ← 兼容旧版本

**配置示例**：

<details>
<summary>查看完整示例</summary>

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "HTTP content fetcher"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      },
      "description": "GitHub API integration"
    },
    "database": {
      "command": "/usr/local/bin/db-mcp-server",
      "args": ["--host", "localhost"],
      "env": {
        "DATABASE_URL": "postgresql://${DB_USER}:${DB_PASS}@localhost/mydb"
      },
      "description": "PostgreSQL database access",
      "timeout": 60000,
      "retries": 3
    }
  }
}
```

**YAML 格式示例**（可选）：

```yaml
mcpServers:
  fetch:
    command: uvx
    args: [mcp-server-fetch]
  github:
    command: npx
    args: [-y, "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
```

</details>

> 📖 **详细配置指南**：[docs/configuration-guide.md](docs/configuration-guide.md)

---

## 🛠️ API 参考

### `GET /health`

健康检查端点（无需认证）

**响应**：
```json
{"status": "ok"}
```

---

### `POST /bridge`

短连接桥接模式

**请求头**：
- `Authorization: Bearer <token>`（如已设置 `ACCESS_TOKEN`）
- `Content-Type: application/json`

**请求体**：
```json
{
  "serverPath": "可执行命令或 URL（http/https/ws/wss）",
  "method": "JSON-RPC 方法名",
  "params": {},
  "args": ["可选的命令行参数"],
  "env": {"可选的环境变量": "值"}
}
```

**支持的方法**：
- `tools/list`、`tools/call`
- `prompts/list`、`prompts/get`
- `resources/list`、`resources/read`
- `resources/subscribe`、`resources/unsubscribe`
- `completion/complete`
- `logging/setLevel`

---

### `POST /mcp/:serverId`

流式会话模式

**路径参数**：
- `serverId`：在 `MCP_SERVERS` 中定义的服务器 ID

**请求头**：
- `Authorization: Bearer <token>`
- `Accept: application/json, text/event-stream`（必须）
- `mcp-session-id: <session-id>`（可选，复用已有会话）

**请求体**：
```json
[
  {"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}},
  {"jsonrpc":"2.0","method":"notifications/initialized"}
]
```

**响应**：
- 如有请求（带 `id`）：返回 SSE 流
- 仅通知（无 `id`）：返回 `202 Accepted`

---

### `DELETE /mcp/:serverId`

关闭会话

**请求头**：
- `mcp-session-id: <session-id>`（必须）

**响应**：`204 No Content`

---

## 🌐 外网访问（Ngrok）

1. 获取 Ngrok 令牌：https://dashboard.ngrok.com/get-started/your-authtoken

2. 添加到 `.env`：
   ```env
   NGROK_AUTH_TOKEN=your-token-here
   ```

3. 启动服务：
   ```bash
   npm run start:tunnel
   ```

4. 控制台会显示公网地址：
   ```
   Tunnel URL: https://abc123.ngrok.io
   MCP Bridge URL: https://abc123.ngrok.io/bridge
   ```

---

## 🔒 安全建议

1. **⚠️ 必须设置 `ACCESS_TOKEN`**
   未设置会有警告日志，生产环境禁止不设令牌

2. **配置 `ALLOWED_ORIGINS`**
   限制跨域请求来源：
   ```env
   ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

3. **使用 HTTPS**
   生产环境建议通过反向代理（Nginx、Caddy）添加 SSL

4. **定期轮换令牌**
   使用强随机令牌，定期更新

5. **审计日志**
   检查 `error.log` 和 `combined.log` 中的异常访问

---

## 📊 日志与监控

### 日志文件

- `combined.log`：所有级别日志
- `error.log`：仅错误级别

### 日志级别

通过 `LOG_LEVEL` 控制详细程度：

```env
LOG_LEVEL=DEBUG  # 开发环境
LOG_LEVEL=INFO   # 生产环境（默认）
LOG_LEVEL=WARN   # 仅警告和错误
```

### 健康检查

```bash
# 本地检查
curl http://localhost:3000/health

# 配合监控工具（如 UptimeRobot、Prometheus）
# 每 30 秒自动检查一次
```

---

## 🧪 开发指南

### 项目结构

```
src/
├── server/
│   └── http-server.ts      # HTTP 服务器和路由
├── client/
│   └── mcp-client-manager.ts  # MCP 客户端管理
├── stream/
│   ├── session-manager.ts   # 会话生命周期管理
│   └── stream-session.ts    # SSE 会话实现
├── config/
│   └── config.ts            # 配置加载和校验
├── utils/
│   ├── logger.ts            # Winston 日志器
│   └── tunnel.ts            # Ngrok 隧道管理
└── index.ts                 # 入口文件
```

### 开发命令

```bash
# 热重载开发
npm run dev

# 代码检查
npm run lint

# 运行测试
npm test

# 类型检查
npx tsc --noEmit
```

### 编码规范

- **语言**：TypeScript（严格模式）
- **缩进**：2 空格
- **命名**：
  - 函数/变量：`camelCase`
  - 类：`PascalCase`
  - 文件：`kebab-case.ts`
- **导出**：优先使用命名导出

---

## ❓ 常见问题

<details>
<summary><b>Q: 为什么返回 401 Unauthorized？</b></summary>

**A**: 检查以下几点：
1. 是否设置了 `ACCESS_TOKEN` 环境变量
2. 请求头是否包含 `Authorization: Bearer <token>`
3. Token 是否匹配（注意空格和特殊字符）
</details>

<details>
<summary><b>Q: 返回 403 Origin not allowed 怎么办？</b></summary>

**A**: 将请求来源添加到白名单：
```env
ALLOWED_ORIGINS=https://your-frontend-domain.com
```
</details>

<details>
<summary><b>Q: 404 Unknown MCP server 错误</b></summary>

**A**: 检查 `MCP_SERVERS` 配置：
1. JSON 格式是否正确（双引号、无尾随逗号）
2. `serverId` 是否存在于配置中
3. 示例：`MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]}}`
</details>

<details>
<summary><b>Q: 会话超时怎么办？</b></summary>

**A**: 会话空闲 5 分钟后自动关闭，可调整：
```env
STREAM_SESSION_TTL_MS=600000  # 改为 10 分钟
```
</details>

<details>
<summary><b>Q: 如何调试 MCP 服务器启动问题？</b></summary>

**A**:
1. 设置 `LOG_LEVEL=DEBUG` 查看详细日志
2. 检查 MCP 服务器命令是否可执行（手动运行测试）
3. 查看 `error.log` 中的错误堆栈
</details>

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [快速参考](docs/quick-reference.md) | 📋 常用命令和配置速查 |
| [配置指南](docs/configuration-guide.md) | 🔧 17+ 场景配置示例 |
| [部署指南](docs/deployment-guide.md) | 🚀 Docker/K8s/E2B 部署 |
| [配置方案对比](docs/configuration-alternatives.md) | 📊 6 种方案分析 |
| [E2B 快速开始](deploy/e2b/README.md) | ☁️ 云沙箱部署 |
| [变更日志](CHANGELOG.md) | 📝 版本更新记录 |

---

## 🗺️ 路线图

### v2.2.0（短期）
- [ ] 添加完整的单元测试和集成测试
- [ ] 配置验证 API
- [ ] 配置文件热重载
- [ ] Prometheus metrics 支持

### v2.3.0（中期）
- [ ] Web 管理界面
- [ ] 动态增删服务器 API
- [ ] OpenAPI/Swagger 文档

### v3.0.0（长期）
- [ ] 数据库存储配置
- [ ] 多租户隔离
- [ ] 分布式追踪（OpenTelemetry）

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 提交 PR 前请：

1. 运行 `npm run lint` 确保代码规范
2. 添加或更新测试用例
3. 更新相关文档
4. 在 PR 中描述改动和原因

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [Model Context Protocol](https://modelcontextprotocol.io/) - 协议规范
- [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk) - 官方 SDK
- [Ngrok](https://ngrok.com/) - 隧道服务
- [Express.js](https://expressjs.com/) - Web 框架
- [Winston](https://github.com/winstonjs/winston) - 日志库

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

Made with ❤️ by [Your Name](https://github.com/yourusername)

</div>
