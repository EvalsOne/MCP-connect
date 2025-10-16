# MCP Connect

    ███╗   ███╗ ██████╗██████╗      ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗
    ████╗ ████║██╔════╝██╔══██╗    ██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝
    ██╔████╔██║██║     ██████╔╝    ██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   
    ██║╚██╔╝██║██║     ██╔═══╝     ██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   
    ██║ ╚═╝ ██║╚██████╗██║         ╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   
    ╚═╝     ╚═╝ ╚═════╝╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   


<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D20.0.0-brightgreen)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4+-blue)](https://www.typescriptlang.org/)

**将 MCP 服务器转换为 HTTP API 的轻量级桥接服务**

[English](../README.md) • [简体中文](README.zh-CN.md)

</div>

---

## 📖 什么是 MCP Connect？

MCP Connect 是一个 HTTP 网关服务，让你可以通过Streamable HTTP 方式调用使用 Stdio 通信协议的本地 MCP 服务器。

### 最新更新

- 在经典请求/响应桥接之上新增 Streamable HTTP 模式
- 在 `deploy/e2b` 下新增快速部署脚本与配置，用于在 E2B 沙箱中启动

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
| 🚀 **双模式支持** | 可使用 Streamable HTTP 或者经典 HTTP 桥接方式调用本地Stdio协议的MCP服务器 |
| 🔄 **Session管理** | 支持通过Session机制维护对话的连续性 |
| 🔐 **安全防护** | Bearer Token 认证 + CORS 白名单 |
| 🌐 **公网访问** | 内置 Ngrok 隧道，一键暴露外网 |
| ☁️ **云端部署** | 一键部署到 E2B 云沙箱 |
---

## 🚀 快速开始

### 前置要求

- Node.js >= 22.0.0 (推荐)
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

**步骤 B：配置 MCP 服务器**（推荐使用 YAML）

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
    "description": "HTTP/HTTPS 内容抓取器"
    }
  },
  ......
}
```

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


---

## 📚 使用指南

### 模式一：Streamable HTTP方式

通用型更强，可以被任何支持 Steamable http 协议的 MCP 客户端调用。如：Claude Code, Cursor, Codex, Github Copilot等。

Streamable HTTP方式中，每个MCP Server都将通过路由机制分配唯一的URL地址可供调用。例如：

在 mcp-servers.json 中增加对于fetch MCP server的支持。

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "HTTP/HTTPS 内容抓取器"
    }
  }
}
```

启动成功后，即可通过以下地址访问fetch MCP server：

```
http://localhost:3000/mcp/fetch
```

⚠️ 注意：必须在启动前通过mcp-servers.json进行配置，否则将无法使用。

---

### 模式二：经典桥接方式 (兼容之前的旧方式)

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

### 加密与安全

#### 认证（Authentication）
MCP Connect 使用简单的令牌认证机制。令牌存储在 `.env` 文件中。设置令牌后，MCP Connect 将使用该令牌校验请求。

```bash
Authorization: Bearer <your_auth_token>
```

#### 允许的来源（Allowed Origins）
在生产环境下，建议在环境变量中配置 `ALLOWED_ORIGINS`，限制跨域请求的来源：

```env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

如果设置了 ALLOWED_ORIGINS，不匹配的访问源将被拒绝。

---

## 🛠️ API 参考

### `GET /health`

健康检查端点（无需认证）

**响应**：
```json
{"status": "ok"}
```

---


### `POST /mcp/:serverId`

流式会话模式

**路径参数**：
- `serverId`：在 `MCP_SERVERS` 中定义的服务器 ID

**请求头**：
- `Authorization: Bearer <token>`（如已设置 `ACCESS_TOKEN`）
- `Accept: application/json, text/event-stream`（必须）
- `mcp-session-id: <session-id>`（可选，复用已有会话）

**请求体**：
```json
[
  {"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}},
  {"jsonrpc":"2.0","method":"notifications/initialized"}
]
```

---

### `POST /bridge`

原桥接模式

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

## 🌐 通过Ngrok提供外网访问隧道

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

## 🌐 快速部署到 E2B 云沙箱

> E2B 提供隔离的云端沙箱环境，适合在安全环境中运行不受信任的 MCP 服务器。

### 步骤 1️⃣：准备 E2B 环境

```bash
# 注册 E2B 账号
访问 https://e2b.dev 并获取 API Key

# 安装 E2B CLI
pip install e2b

# 设置 API Key
export E2B_API_KEY=your-e2b-api-key
```

### 步骤 2️⃣：构建沙箱模板

```bash
cd deploy/e2b

# 开发环境
python build_dev.py

# 或生产环境
python build_prod.py
```

### 步骤 3️⃣：从模版启动沙盒

```bash
python sandbox_deploy.py --template-id mcp-dev-gui
```

详细文档：[E2B 部署指南](docs/deployment-guide.md#e2b-沙箱部署)

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

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

</div>
