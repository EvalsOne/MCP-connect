# 🔧 MCP Connect 配置指南

## 配置方式对比

MCP Connect 支持三种配置方式，按优先级从高到低：

| 方式 | 优先级 | 适用场景 | 优点 | 缺点 |
|------|--------|----------|------|------|
| **JSON 文件** | ⭐⭐⭐ 最高 | 生产环境、MCP 标准 | MCP 标准格式、工具支持好、严格验证 | 不支持注释 |
| **YAML 文件** | ⭐⭐ 中 | 需要注释、复杂配置 | 可读性强、支持注释、版本控制友好 | 非 MCP 标准 |
| **环境变量** | ⭐ 最低 | 简单场景、容器环境 | 部署简单、12-factor 兼容 | 复杂配置难以维护 |

---

## 方式一：JSON 配置文件（推荐 ⭐ MCP 标准）

### 基础示例

创建 `mcp-servers.json`：

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "HTTP/HTTPS content fetcher"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "Read/write access to /tmp directory"
    }
  }
}
```

### 环境变量引用

在配置中引用 `.env` 的变量：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      },
      "description": "GitHub API integration"
    },
    "database": {
      "command": "node",
      "args": ["/path/to/db-server.js"],
      "env": {
        "DATABASE_URL": "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/mydb"
      }
    }
  }
}
```

对应的 `.env`：

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
DB_USER=admin
DB_PASS=secret123
DB_HOST=localhost
```

### 完整示例（包含所有选项）

```json
{
  "mcpServers": {
    "production-api": {
      "command": "/usr/local/bin/my-mcp-server",
      "args": ["--config", "/etc/mcp/config.json", "--verbose"],
      "env": {
        "NODE_ENV": "production",
        "API_KEY": "${PRODUCTION_API_KEY}",
        "LOG_LEVEL": "info"
      },
      "description": "Production API gateway with authentication",
      "timeout": 30000,
      "retries": 3
    }
  }
}
```

---

## 方式二：YAML 配置文件（可选，易读）

### 基础示例

创建 `mcp-servers.yaml`：

```yaml
mcpServers:
  # Web 内容抓取服务
  fetch:
    command: uvx
    args:
      - mcp-server-fetch
    description: "HTTP/HTTPS content fetcher"

  # 本地文件系统访问
  filesystem:
    command: npx
    args:
      - -y
      - "@modelcontextprotocol/server-filesystem"
      - /tmp
    description: "Read/write access to /tmp directory"
```

### 环境变量引用

在配置中引用 `.env` 的变量：

```yaml
servers:
  github:
    command: npx
    args:
      - -y
      - "@modelcontextprotocol/server-github"
    env:
      # 使用 ${VAR_NAME} 语法引用环境变量
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
    description: "GitHub API integration"

  database:
    command: node
    args:
      - /path/to/db-server.js
    env:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/mydb
```

对应的 `.env`：

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
DB_USER=admin
DB_PASS=secret123
DB_HOST=localhost
```

### 完整示例（包含所有选项）

```yaml
servers:
  production-api:
    # 必填：可执行命令
    command: /usr/local/bin/my-mcp-server

    # 可选：命令行参数
    args:
      - --config
      - /etc/mcp/config.json
      - --verbose

    # 可选：环境变量
    env:
      NODE_ENV: production
      API_KEY: ${PRODUCTION_API_KEY}
      LOG_LEVEL: info

    # 可选：描述（用于文档和日志）
    description: "Production API gateway with authentication"

    # 可选：连接超时（毫秒）
    timeout: 30000

    # 可选：重试次数
    retries: 3
```

### 多环境配置

**开发环境** (`mcp-servers.dev.yaml`):

```yaml
servers:
  api:
    command: npm
    args: [run, dev:mcp-server]
    env:
      NODE_ENV: development
      DEBUG: "*"
```

**生产环境** (`mcp-servers.prod.yaml`):

```yaml
servers:
  api:
    command: /opt/mcp/server
    args: [--production]
    env:
      NODE_ENV: production
      LOG_LEVEL: warn
```

然后在启动时指定：

```bash
# 开发
cp mcp-servers.dev.yaml mcp-servers.yaml
npm run dev

# 生产
cp mcp-servers.prod.yaml mcp-servers.yaml
npm start
```

---

## 方式二：JSON 配置文件

创建 `mcp-servers.json`：

```json
{
  "servers": {
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
      }
    }
  }
}
```

**优点**：
- 可以通过脚本动态生成
- 严格的语法检查

**缺点**：
- 不支持注释（可使用 JSON5 库扩展）
- 可读性不如 YAML

---

## 方式三：环境变量（遗留方式）

在 `.env` 文件中：

```env
MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]}}
```

**仅推荐用于**：
- 单个简单服务器
- 容器环境的临时覆盖
- 向后兼容旧配置

---

## 配置加载优先级

系统按以下顺序查找配置：

```
1. mcp-servers.yaml      ← 最高优先级
2. mcp-servers.yml       ← YAML 的备用后缀
3. mcp-servers.json      ← JSON 格式
4. MCP_SERVERS 环境变量  ← 遗留方式
5. 空配置（无服务器）    ← 仅 /bridge 端点可用
```

---

## 高级配置场景

### 场景 1：Docker 容器中的服务

```yaml
servers:
  postgres-mcp:
    command: docker
    args:
      - run
      - --rm
      - -i
      - --network=host
      - my-postgres-mcp-image
    env:
      DATABASE_URL: ${DATABASE_URL}
    timeout: 60000  # Docker 启动较慢
```

### 场景 2：远程 HTTP/WebSocket 服务

```yaml
servers:
  remote-api:
    # 对于 HTTP/HTTPS，command 可以是 URL
    command: https://api.example.com/mcp
    description: "Remote MCP server over HTTPS"

  remote-ws:
    command: wss://api.example.com/mcp
    description: "Remote MCP server over WebSocket"
```

### 场景 3：带认证的服务

```yaml
servers:
  authenticated-service:
    command: /usr/local/bin/secure-mcp-server
    env:
      AUTH_METHOD: jwt
      JWT_SECRET: ${JWT_SECRET}
      ALLOWED_USERS: ${ALLOWED_USERS}
```

### 场景 4：资源受限环境

```yaml
servers:
  memory-constrained:
    command: node
    args:
      - --max-old-space-size=512
      - /path/to/server.js
    env:
      NODE_OPTIONS: --max-old-space-size=512
```

---

## 配置验证

### 手动验证

```bash
# 使用 yamllint（需先安装）
yamllint mcp-servers.yaml

# 使用 jq 验证 JSON
cat mcp-servers.json | jq .
```

### 自动验证（启动时）

MCP Bridge 会在启动时验证配置：

```
✓ Loaded MCP servers from mcp-servers.yaml
  - fetch: HTTP content fetcher
  - github: GitHub API integration
  - filesystem: Read/write access to /tmp directory
```

错误示例：

```
✗ Failed to parse mcp-servers.yaml: Missing command for server "invalid"
```

---

## 配置热加载（未来功能）

当前版本需要重启服务才能应用配置更改。计划中的热加载功能：

```bash
# 发送信号触发重载
kill -HUP <pid>

# 或通过 API
curl -X POST http://localhost:3000/admin/reload \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 安全最佳实践

### ✅ 推荐做法

1. **敏感信息使用环境变量引用**
   ```yaml
   env:
     API_KEY: ${SECRET_API_KEY}  # ✓ 从 .env 读取
   ```

2. **配置文件加入 `.gitignore`**
   ```bash
   echo "mcp-servers.yaml" >> .gitignore
   ```

3. **使用示例文件作为模板**
   ```bash
   cp mcp-servers.example.yaml mcp-servers.yaml
   # 编辑 mcp-servers.yaml，不提交到 git
   ```

4. **限制文件权限**
   ```bash
   chmod 600 mcp-servers.yaml
   ```

### ❌ 避免的做法

1. **直接写死密钥**
   ```yaml
   env:
     API_KEY: sk-1234567890abcdef  # ✗ 危险！
   ```

2. **提交真实配置到版本控制**
   ```bash
   git add mcp-servers.yaml  # ✗ 不要这样做
   ```

---

## 故障排查

### 问题 1：找不到配置文件

**错误**：
```
⚠ No MCP server configuration found
```

**解决**：
```bash
# 检查文件是否存在
ls -la mcp-servers.yaml

# 确认文件名和扩展名正确
ls mcp-servers.*

# 确认在项目根目录运行
pwd
```

### 问题 2：YAML 语法错误

**错误**：
```
Failed to parse mcp-servers.yaml: bad indentation
```

**解决**：
- 使用 2 空格缩进（不要用 Tab）
- 检查冒号后是否有空格
- 使用 YAML 在线验证器

### 问题 3：环境变量未解析

**错误**：
配置中 `${GITHUB_TOKEN}` 显示为空字符串

**解决**：
```bash
# 确认环境变量已设置
echo $GITHUB_TOKEN

# 确认 .env 文件已加载
cat .env | grep GITHUB_TOKEN

# 重启服务
npm restart
```

---

## 迁移指南

### 从环境变量迁移到 YAML

**旧配置** (`.env`):
```env
MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]},"github":{"command":"npx","args":["-y","@modelcontextprotocol/server-github"],"env":{"GITHUB_PERSONAL_ACCESS_TOKEN":"ghp_xxx"}}}
```

**新配置** (`mcp-servers.yaml`):
```yaml
servers:
  fetch:
    command: uvx
    args:
      - mcp-server-fetch

  github:
    command: npx
    args:
      - -y
      - "@modelcontextprotocol/server-github"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
```

**`.env` 中只保留**：
```env
GITHUB_TOKEN=ghp_xxx
```

---

## 总结

| 需求 | 推荐方式 |
|------|----------|
| 1-2 个简单服务器 | 环境变量 |
| 3+ 个服务器 | YAML 文件 |
| 需要注释和文档 | YAML 文件 |
| 程序化生成配置 | JSON 文件 |
| 容器化部署 | YAML 文件 + 环境变量引用 |
| 多环境管理 | 多个 YAML 文件 + 符号链接 |

**最佳实践**：使用 `mcp-servers.yaml` + `.env` 组合，既保证可读性，又安全管理敏感信息。
