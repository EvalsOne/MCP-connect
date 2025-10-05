# 🚀 MCP Connect 快速参考

## 📋 5 分钟快速开始

```bash
# 1. 克隆项目
git clone https://github.com/EvalsOne/MCP-connect.git
cd mcp-connect

# 2. 安装依赖
npm install

# 3. 配置环境变量
cp .env.example .env
echo "ACCESS_TOKEN=my-secret-token" >> .env

# 4. 配置 MCP 服务器
cp mcp-servers.example.yaml mcp-servers.yaml

# 5. 启动服务
npm run build && npm start
```

访问 http://localhost:3000/health 检查服务状态！

---

## 🔧 配置方式速查

### JSON 配置（推荐）⭐

**文件**：`mcp-servers.json`

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "工具描述"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**优点**：
- ✅ MCP 标准格式
- ✅ 环境变量引用
- ✅ 严格的语法验证
- ✅ 工具支持好

### YAML 配置（可选）

**文件**：`mcp-servers.yaml`

```yaml
mcpServers:
  fetch:
    command: uvx
    args: [mcp-server-fetch]
```

**优点**：更易读、支持注释

### 环境变量配置（简单场景）

**文件**：`.env`

```env
MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]}}
```

**适用于**：单个服务器、快速测试

---

## 📡 API 快速参考

### Streamable HTTP 模式

```bash
# 创建会话并调用
curl -N http://localhost:3000/mcp/fetch \
  -H "Authorization: Bearer token" \
  -H "Accept: application/json, text/event-stream" \
  -d '[{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}]'
```

### 经典桥接模式

```bash
# 列出工具
curl -X POST http://localhost:3000/bridge \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "serverPath": "uvx",
    "args": ["mcp-server-fetch"],
    "method": "tools/list",
    "params": {}
  }'
```

---

## 🌐 部署方式速查

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| **本地** | `npm start` | 开发、测试 |
| **Docker** | `docker-compose up -d` | 生产环境 |
| **E2B** | `cd deploy/e2b && python quickstart.py` | 云端隔离 |
| **PM2** | `pm2 start ecosystem.config.js` | 生产环境 |

---

## 🔑 环境变量速查

| 变量 | 默认值 | 必须 | 说明 |
|------|--------|------|------|
| `PORT` | `3000` | ❌ | 服务端口 |
| `ACCESS_TOKEN` | - | ✅ | API 令牌 |
| `LOG_LEVEL` | `INFO` | ❌ | 日志级别 |
| `STREAM_SESSION_TTL_MS` | `300000` | ❌ | 会话超时 |
| `ALLOWED_ORIGINS` | - | ❌ | CORS 白名单 |
| `NGROK_AUTH_TOKEN` | - | ❌ | Ngrok 令牌 |

---

## 📖 配置优先级

```
1. mcp-servers.json   ← 最高优先级（MCP 标准）
2. mcp-servers.yaml   ← YAML 格式（易读）
3. mcp-servers.yml
4. MCP_SERVERS 环境变量 ← 兼容旧版
5. 空配置（无服务器）
```

---

## 🛠️ 常用命令

```bash
# 开发（热重载）
npm run dev

# 构建
npm run build

# 启动
npm start

# 启动并开启 Ngrok
npm run start:tunnel

# 查看日志
tail -f combined.log
tail -f error.log
```

---

## 🐛 常见问题速查

### 401 Unauthorized

```bash
# 检查令牌是否设置
echo $ACCESS_TOKEN

# 确认请求头
-H "Authorization: Bearer your-token"
```

### 404 Unknown MCP server

```bash
# 检查配置文件是否存在
ls mcp-servers.yaml

# 查看配置加载日志
npm start | grep "Loaded MCP servers"
```

### 服务无法启动

```bash
# 检查端口占用
lsof -i :3000

# 查看错误日志
cat error.log
```

---

## 📚 文档导航

- **完整文档**：[README.md](../README.md)
- **配置指南**：[docs/configuration-guide.md](./configuration-guide.md)
- **部署指南**：[docs/deployment-guide.md](./deployment-guide.md)
- **配置方案对比**：[docs/configuration-alternatives.md](./configuration-alternatives.md)
- **E2B 部署**：[deploy/e2b/README.md](../deploy/e2b/README.md)

---

## 💡 最佳实践

### ✅ 推荐做法

```yaml
# mcp-servers.yaml
servers:
  github:
    command: npx
    args: [-y, "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}  # ✅ 引用环境变量
```

```env
# .env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # ✅ 敏感信息放这里
```

### ❌ 不推荐做法

```yaml
# ❌ 直接硬编码密钥
servers:
  github:
    env:
      GITHUB_TOKEN: ghp_xxxxxxxxxxxx  # 危险！
```

---

## 🔗 快速链接

- **MCP 协议**：https://modelcontextprotocol.io
- **E2B 平台**：https://e2b.dev
- **问题反馈**：https://github.com/EvalsOne/MCP-connect/issues
- **配置示例**：[mcp-servers.example.yaml](../mcp-servers.example.yaml)

---

**提示**：将本文档加入书签，随时查阅！ 📌
