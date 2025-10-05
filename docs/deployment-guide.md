# 🚀 MCP Bridge 部署指南

## 部署方式概览

| 方式 | 复杂度 | 适用场景 | 优点 |
|------|--------|----------|------|
| [本地运行](#本地运行) | ⭐ 简单 | 开发、测试 | 快速启动 |
| [Docker](#docker-部署) | ⭐⭐ 中等 | 生产环境 | 隔离、可移植 |
| [E2B Sandbox](#e2b-沙箱部署) | ⭐⭐⭐ 高级 | 云端隔离环境 | 动态扩容、安全隔离 |
| [PM2](#pm2-进程管理) | ⭐⭐ 中等 | 生产环境 | 自动重启、负载均衡 |
| [Kubernetes](#kubernetes-部署) | ⭐⭐⭐⭐ 复杂 | 大规模集群 | 高可用、自动扩展 |

---

## 本地运行

### 开发模式（热重载）

```bash
# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
vim .env

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000/health

### 生产模式

```bash
# 构建
npm run build

# 启动
npm start

# 或带 Ngrok 隧道
npm run start:tunnel
```

---

## Docker 部署

### 方式一：使用 Docker Compose（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mcp-bridge:
    build: .
    ports:
      - "3000:3000"
    env_file:
      - .env
    volumes:
      # 挂载配置文件
      - ./mcp-servers.yaml:/app/mcp-servers.yaml:ro
      # 挂载日志目录
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

启动：

```bash
docker-compose up -d
```

### 方式二：手动 Docker 命令

#### 1. 创建 Dockerfile

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制源码
COPY . .

# 编译 TypeScript
RUN npm run build

# 暴露端口
EXPOSE 3000

# 启动服务
CMD ["node", "dist/index.js"]
```

#### 2. 构建镜像

```bash
docker build -t mcp-bridge:latest .
```

#### 3. 运行容器

```bash
docker run -d \
  --name mcp-bridge \
  -p 3000:3000 \
  -v $(pwd)/mcp-servers.yaml:/app/mcp-servers.yaml:ro \
  -e ACCESS_TOKEN=your-secret-token \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  mcp-bridge:latest
```

#### 4. 查看日志

```bash
docker logs -f mcp-bridge
```

---

## E2B 沙箱部署

> E2B (Environment as a Service) 提供云端隔离的沙箱环境，适合运行不受信任的代码。

### 什么是 E2B？

E2B 是一个云端沙箱平台，提供：
- ✅ 完全隔离的运行环境
- ✅ 快速启动（< 3 秒）
- ✅ 按需扩容
- ✅ 内置安全防护

**适用场景**：
- 需要运行第三方 MCP 服务器
- 代码执行隔离要求高
- 动态创建/销毁环境

### 前置要求

1. 注册 E2B 账号：https://e2b.dev
2. 获取 API Key：https://e2b.dev/dashboard
3. 安装 Python（用于构建模板）

```bash
pip install e2b
```

### 步骤 1：配置 E2B

在 `.env` 中添加：

```env
E2B_API_KEY=your-e2b-api-key
```

### 步骤 2：构建沙箱模板

MCP Bridge 提供了预配置的 E2B 模板（位于 `deploy/e2b/`）：

```bash
cd deploy/e2b

# 开发环境构建
make e2b:build:dev

# 或生产环境构建
make e2b:build:prod
```

构建完成后会显示模板 ID，例如：`mcp-bridge-template-xyz123`

### 步骤 3：配置 MCP 服务器

E2B 沙箱内的服务器配置通过 `servers.json` 管理：

```json
{
  "servers": {
    "chrome-devtools": {
      "command": "/home/user/chrome-devtools-wrapper.sh",
      "args": [],
      "env": {
        "CHROME_REMOTE_DEBUGGING_URL": "http://127.0.0.1:9222"
      }
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "env": {}
    }
  }
}
```

### 步骤 4：在代码中使用 E2B 沙箱

```python
from e2b import AsyncSandbox
import asyncio
import json

async def run_mcp_in_sandbox():
    # 创建沙箱实例
    sandbox = await AsyncSandbox.create('mcp-bridge-template-xyz123')

    try:
        # 启动 MCP Bridge 服务
        proc = await sandbox.process.start(
            cmd="cd /app && npm start",
            env={"ACCESS_TOKEN": "sandbox-token"}
        )

        # 等待服务启动
        await asyncio.sleep(5)

        # 调用 MCP 接口
        result = await sandbox.commands.run(
            f'curl -X POST http://localhost:3000/bridge \
              -H "Authorization: Bearer sandbox-token" \
              -H "Content-Type: application/json" \
              -d \'{json.dumps({
                  "serverPath": "uvx",
                  "args": ["mcp-server-fetch"],
                  "method": "tools/list",
                  "params": {}
              })}\''
        )

        print(result.stdout)

    finally:
        await sandbox.kill()

asyncio.run(run_mcp_in_sandbox())
```

### E2B 模板内容

模板包含以下预装软件：

- ✅ Node.js 18+
- ✅ Python 3
- ✅ uv/uvx 工具链
- ✅ Chrome DevTools
- ✅ Nginx（可选）
- ✅ MCP Bridge 服务

### E2B 管理工具

#### 查看沙箱日志

```bash
cd deploy/e2b
python view_sandbox_logs.py <sandbox-id>
```

#### 管理沙箱实例

```python
# e2b_sandbox_manager.py 提供的功能：
# - 列出所有活跃沙箱
# - 停止指定沙箱
# - 查看沙箱状态
# - 清理过期沙箱
```

### E2B 配置文件说明

| 文件 | 说明 |
|------|------|
| `e2b.Dockerfile` | 完整沙箱镜像定义 |
| `e2b.Dockerfile.minimal` | 最小化镜像（仅核心功能） |
| `template.py` | 沙箱模板配置 |
| `servers.json` | MCP 服务器定义 |
| `startup.sh` | 沙箱启动脚本 |
| `nginx.conf` | Nginx 反向代理配置 |

---

## PM2 进程管理

### 安装 PM2

```bash
npm install -g pm2
```

### 创建 PM2 配置

`ecosystem.config.js`：

```javascript
module.exports = {
  apps: [{
    name: 'mcp-bridge',
    script: 'dist/index.js',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    env_production: {
      NODE_ENV: 'production',
      LOG_LEVEL: 'INFO'
    }
  }]
};
```

### 启动服务

```bash
# 启动
pm2 start ecosystem.config.js

# 查看状态
pm2 status

# 查看日志
pm2 logs mcp-bridge

# 监控
pm2 monit

# 重启
pm2 restart mcp-bridge

# 开机自启
pm2 startup
pm2 save
```

---

## Kubernetes 部署

### 1. 创建 ConfigMap（配置）

`k8s/configmap.yaml`：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-bridge-config
data:
  mcp-servers.yaml: |
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

### 2. 创建 Secret（敏感信息）

```bash
kubectl create secret generic mcp-bridge-secrets \
  --from-literal=ACCESS_TOKEN=your-secret-token \
  --from-literal=GITHUB_TOKEN=ghp_xxxxxxxxxx
```

### 3. 创建 Deployment

`k8s/deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-bridge
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-bridge
  template:
    metadata:
      labels:
        app: mcp-bridge
    spec:
      containers:
      - name: mcp-bridge
        image: mcp-bridge:latest
        ports:
        - containerPort: 3000
        env:
        - name: ACCESS_TOKEN
          valueFrom:
            secretKeyRef:
              name: mcp-bridge-secrets
              key: ACCESS_TOKEN
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: mcp-bridge-secrets
              key: GITHUB_TOKEN
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: config
          mountPath: /app/mcp-servers.yaml
          subPath: mcp-servers.yaml
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: mcp-bridge-config
```

### 4. 创建 Service

`k8s/service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-bridge
spec:
  selector:
    app: mcp-bridge
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: LoadBalancer
```

### 5. 部署

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 查看状态
kubectl get pods
kubectl get svc mcp-bridge

# 查看日志
kubectl logs -f deployment/mcp-bridge
```

---

## 反向代理配置

### Nginx

```nginx
upstream mcp_bridge {
    server localhost:3000;
}

server {
    listen 80;
    server_name api.example.com;

    # HTTPS 重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # 日志
    access_log /var/log/nginx/mcp-bridge-access.log;
    error_log /var/log/nginx/mcp-bridge-error.log;

    location / {
        proxy_pass http://mcp_bridge;
        proxy_http_version 1.1;

        # SSE 支持
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;

        # 通用代理头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
}
```

### Caddy（自动 HTTPS）

```caddyfile
api.example.com {
    reverse_proxy localhost:3000 {
        # SSE 支持
        flush_interval -1
    }

    log {
        output file /var/log/caddy/mcp-bridge.log
    }
}
```

---

## 环境变量最佳实践

### 开发环境

`.env.development`：

```env
PORT=3000
NODE_ENV=development
ACCESS_TOKEN=dev-token-only
LOG_LEVEL=DEBUG
STREAM_SESSION_TTL_MS=600000
```

### 生产环境

`.env.production`：

```env
PORT=3000
NODE_ENV=production
ACCESS_TOKEN=${SECURE_TOKEN_FROM_SECRET_MANAGER}
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
LOG_LEVEL=INFO
STREAM_SESSION_TTL_MS=300000
NGROK_AUTH_TOKEN=
```

**安全建议**：
- 使用密钥管理服务（AWS Secrets Manager、HashiCorp Vault）
- 定期轮换 `ACCESS_TOKEN`
- 限制 `ALLOWED_ORIGINS`
- 生产环境禁用 DEBUG 日志

---

## 监控与日志

### Prometheus Metrics（未来功能）

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-bridge'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/metrics'
```

### 日志聚合

#### ELK Stack

```bash
# Filebeat 配置
filebeat.inputs:
  - type: log
    paths:
      - /app/logs/combined.log
      - /app/logs/error.log
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

#### Loki + Grafana

```yaml
# promtail-config.yaml
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: mcp-bridge
    static_configs:
      - targets:
          - localhost
        labels:
          job: mcp-bridge
          __path__: /app/logs/*.log
```

---

## 性能优化

### 1. 启用集群模式

```javascript
// cluster.js
import cluster from 'cluster';
import os from 'os';

if (cluster.isPrimary) {
  const cpuCount = os.cpus().length;
  for (let i = 0; i < cpuCount; i++) {
    cluster.fork();
  }
  cluster.on('exit', (worker) => {
    console.log(`Worker ${worker.id} died, starting new worker`);
    cluster.fork();
  });
} else {
  import('./dist/index.js');
}
```

### 2. 缓存优化

调整客户端缓存 TTL：

```typescript
// src/server/http-server.ts
private readonly CLIENT_CACHE_TTL = 10 * 60 * 1000; // 改为 10 分钟
```

### 3. 限流

```bash
npm install express-rate-limit
```

```typescript
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 分钟
  max: 100 // 限制每 IP 100 次请求
});

this.app.use('/bridge', limiter);
```

---

## 故障排查

### 容器无法启动

```bash
# 查看容器日志
docker logs mcp-bridge

# 进入容器调试
docker exec -it mcp-bridge sh
```

### 健康检查失败

```bash
# 手动测试
curl http://localhost:3000/health

# 查看端口占用
lsof -i :3000
netstat -tuln | grep 3000
```

### E2B 沙箱连接超时

```python
# 增加超时时间
sandbox = await AsyncSandbox.create('template-id', timeout=120)
```

---

## 总结

| 场景 | 推荐方式 |
|------|----------|
| 本地开发 | `npm run dev` |
| 个人项目 | Docker Compose |
| 生产环境 | PM2 + Nginx |
| 云端隔离 | E2B Sandbox |
| 大规模集群 | Kubernetes |

根据实际需求选择合适的部署方式！
