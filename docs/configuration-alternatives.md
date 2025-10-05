# 🔀 配置方案完整对比

## 已实现：YAML/JSON 文件配置

**状态**：✅ 已支持

**实现位置**：`src/config/config.ts:79-146`

### 优点
- ✅ 可读性强，支持注释
- ✅ 多行编辑，无需转义
- ✅ 版本控制友好（易于 diff）
- ✅ 支持环境变量引用 `${VAR}`
- ✅ 类型安全（启动时验证）
- ✅ 向后兼容环境变量方式

### 缺点
- ⚠️ 需要额外的依赖（js-yaml）
- ⚠️ 文件需要手动管理（但可用示例文件）

### 适用场景
- 生产环境部署
- 管理 3+ 个 MCP 服务器
- 团队协作项目
- 需要注释和文档的配置

---

## 方案二：动态 API 管理（推荐实现）

**状态**：💡 建议添加

### 设计方案

添加管理端点，运行时动态增删服务器：

```typescript
// POST /admin/servers
{
  "id": "new-server",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-fetch"]
}

// GET /admin/servers
// DELETE /admin/servers/:id
// PUT /admin/servers/:id
```

### 实现示例

```typescript
// src/server/admin-routes.ts
export class AdminRoutes {
  private serverRegistry: Map<string, StreamableServerConfig>;

  async addServer(req: Request, res: Response) {
    const { id, command, args, env } = req.body;

    // 验证配置
    if (!command) {
      return res.status(400).json({ error: 'command is required' });
    }

    // 测试启动
    try {
      const testSession = await this.sessionManager.createSession(id, {
        command, args, env
      });
      await testSession.close();
    } catch (error) {
      return res.status(400).json({
        error: 'Failed to start server',
        details: error.message
      });
    }

    // 保存到配置
    this.serverRegistry.set(id, { command, args, env });
    await this.persistConfig();

    res.json({ success: true, id });
  }

  private async persistConfig() {
    const config = {
      servers: Object.fromEntries(this.serverRegistry)
    };
    await fs.promises.writeFile(
      'mcp-servers.yaml',
      yaml.dump(config),
      'utf8'
    );
  }
}
```

### 优点
- ✅ 无需重启服务
- ✅ 适合 SaaS 模式（多租户）
- ✅ 配合 Web UI 使用体验好
- ✅ 可以预检测配置有效性

### 缺点
- ⚠️ 需要额外的安全控制（管理员权限）
- ⚠️ 增加代码复杂度
- ⚠️ 需要考虑并发修改问题

### 适用场景
- 需要频繁增删服务器
- 多租户 SaaS 平台
- 配合 Web 管理界面

---

## 方案三：数据库存储配置

**状态**：💡 可选实现

### 设计方案

使用 SQLite/PostgreSQL 存储服务器配置：

```sql
CREATE TABLE mcp_servers (
  id VARCHAR(255) PRIMARY KEY,
  command VARCHAR(255) NOT NULL,
  args JSON,
  env JSON,
  description TEXT,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE server_usage_stats (
  server_id VARCHAR(255),
  request_count INTEGER,
  last_used TIMESTAMP,
  FOREIGN KEY (server_id) REFERENCES mcp_servers(id)
);
```

### 实现示例

```typescript
// src/config/database-config.ts
import Database from 'better-sqlite3';

export class DatabaseConfig {
  private db: Database.Database;

  constructor(dbPath: string = 'mcp-bridge.db') {
    this.db = new Database(dbPath);
    this.initSchema();
  }

  loadServers(): Record<string, StreamableServerConfig> {
    const rows = this.db.prepare(`
      SELECT id, command, args, env, description
      FROM mcp_servers
      WHERE enabled = true
    `).all();

    return rows.reduce((acc, row) => {
      acc[row.id] = {
        command: row.command,
        args: JSON.parse(row.args),
        env: JSON.parse(row.env),
        description: row.description,
      };
      return acc;
    }, {});
  }

  trackUsage(serverId: string) {
    this.db.prepare(`
      INSERT INTO server_usage_stats (server_id, request_count, last_used)
      VALUES (?, 1, CURRENT_TIMESTAMP)
      ON CONFLICT(server_id) DO UPDATE SET
        request_count = request_count + 1,
        last_used = CURRENT_TIMESTAMP
    `).run(serverId);
  }
}
```

### 优点
- ✅ 支持复杂查询（按使用频率排序）
- ✅ 内置审计日志
- ✅ 多实例共享配置
- ✅ 可以关联用户/租户信息

### 缺点
- ⚠️ 增加外部依赖
- ⚠️ 需要迁移和备份策略
- ⚠️ 对简单场景过度设计

### 适用场景
- 企业级部署
- 需要审计和统计
- 多实例负载均衡
- 配合权限系统

---

## 方案四：远程配置中心

**状态**：💡 企业功能

### 设计方案

集成 Consul、etcd 或 AWS Systems Manager：

```typescript
// src/config/consul-config.ts
import Consul from 'consul';

export class ConsulConfig {
  private consul: Consul.Consul;

  constructor() {
    this.consul = new Consul({
      host: process.env.CONSUL_HOST || 'localhost',
      port: process.env.CONSUL_PORT || '8500',
    });
  }

  async loadServers(): Promise<Record<string, StreamableServerConfig>> {
    const result = await this.consul.kv.get({
      key: 'mcp-bridge/servers',
      recurse: true
    });

    const servers: Record<string, StreamableServerConfig> = {};
    for (const item of result) {
      const serverId = item.Key.split('/').pop();
      servers[serverId] = JSON.parse(item.Value);
    }
    return servers;
  }

  async watchChanges(callback: (servers: Record<string, StreamableServerConfig>) => void) {
    const watcher = this.consul.watch({
      method: this.consul.kv.get,
      options: { key: 'mcp-bridge/servers', recurse: true }
    });

    watcher.on('change', async () => {
      const servers = await this.loadServers();
      callback(servers);
    });
  }
}
```

### 优点
- ✅ 支持配置热加载
- ✅ 分布式一致性
- ✅ 多环境管理（dev/staging/prod）
- ✅ 集成服务发现

### 缺点
- ⚠️ 需要运维配置中心
- ⚠️ 增加系统复杂度
- ⚠️ 单点依赖风险

### 适用场景
- 微服务架构
- 多区域部署
- 需要配置审计和回滚
- Kubernetes 集群

---

## 方案五：Git 作为配置源

**状态**：💡 DevOps 模式

### 设计方案

从 Git 仓库拉取配置，实现 GitOps：

```typescript
// src/config/git-config.ts
import simpleGit from 'simple-git';

export class GitConfig {
  private git = simpleGit();
  private repoPath = '/tmp/mcp-config-repo';

  async syncConfig() {
    if (!fs.existsSync(this.repoPath)) {
      await this.git.clone(
        process.env.CONFIG_REPO_URL!,
        this.repoPath
      );
    } else {
      await this.git.cwd(this.repoPath).pull();
    }

    const configPath = path.join(this.repoPath, 'mcp-servers.yaml');
    return yaml.load(fs.readFileSync(configPath, 'utf8'));
  }

  async watchChanges(interval = 60000) {
    setInterval(async () => {
      const beforeHash = await this.git.cwd(this.repoPath).revparse(['HEAD']);
      await this.git.cwd(this.repoPath).pull();
      const afterHash = await this.git.cwd(this.repoPath).revparse(['HEAD']);

      if (beforeHash !== afterHash) {
        console.log('Config updated, reloading...');
        const newConfig = await this.syncConfig();
        this.emit('config-changed', newConfig);
      }
    }, interval);
  }
}
```

### 优点
- ✅ 配置即代码（Infrastructure as Code）
- ✅ 完整的变更历史
- ✅ Pull Request 审核流程
- ✅ 自动化 CI/CD 集成

### 缺点
- ⚠️ 需要 Git 服务器
- ⚠️ 同步延迟
- ⚠️ 需要处理认证

### 适用场景
- GitOps 工作流
- 严格的变更审批
- 多环境配置管理
- 团队协作

---

## 方案六：环境特定配置文件

**状态**：✅ 简单实现

### 设计方案

按环境后缀自动选择配置文件：

```typescript
// src/config/config.ts
function getConfigPath(): string {
  const env = process.env.NODE_ENV || 'development';

  const candidates = [
    `mcp-servers.${env}.yaml`,      // 环境特定
    `mcp-servers.${env}.yml`,
    `mcp-servers.yaml`,              // 通用
    `mcp-servers.yml`,
  ];

  for (const file of candidates) {
    const fullPath = path.resolve(process.cwd(), file);
    if (fs.existsSync(fullPath)) {
      return fullPath;
    }
  }

  throw new Error('No configuration file found');
}
```

### 使用示例

```bash
# 开发环境
NODE_ENV=development npm start
# → 加载 mcp-servers.development.yaml

# 生产环境
NODE_ENV=production npm start
# → 加载 mcp-servers.production.yaml
```

### 优点
- ✅ 实现简单
- ✅ 环境隔离清晰
- ✅ 无需额外依赖

### 缺点
- ⚠️ 需要维护多个文件
- ⚠️ 配置重复度高

### 适用场景
- 开发/测试/生产环境差异大
- Docker Compose 多环境部署
- 简单的多环境需求

---

## 对比总结

| 方案 | 复杂度 | 灵活性 | 安全性 | 推荐场景 |
|------|--------|--------|--------|----------|
| **YAML 文件** | 低 ⭐ | 中 ⭐⭐ | 中 ⭐⭐ | 大多数场景 |
| **动态 API** | 中 ⭐⭐ | 高 ⭐⭐⭐ | 低 ⭐ | SaaS 平台 |
| **数据库** | 高 ⭐⭐⭐ | 高 ⭐⭐⭐ | 高 ⭐⭐⭐ | 企业级 |
| **配置中心** | 高 ⭐⭐⭐ | 高 ⭐⭐⭐ | 高 ⭐⭐⭐ | 微服务 |
| **Git 同步** | 中 ⭐⭐ | 中 ⭐⭐ | 高 ⭐⭐⭐ | DevOps |
| **环境文件** | 低 ⭐ | 低 ⭐ | 中 ⭐⭐ | 多环境 |

---

## 推荐实现路线

### Phase 1：当前版本（已完成）
- ✅ YAML/JSON 文件支持
- ✅ 环境变量引用
- ✅ 向后兼容

### Phase 2：短期增强
- 🔄 环境特定配置文件
- 🔄 配置验证和测试端点
- 🔄 配置导出/导入 API

### Phase 3：中期功能
- 📅 动态 API 管理
- 📅 配置热加载
- 📅 Web 管理界面

### Phase 4：企业功能
- 🔮 数据库存储
- 🔮 配置中心集成
- 🔮 多租户支持

---

## 快速决策指南

**如果你的项目是...**

- **个人项目/小团队** → 使用 YAML 文件
- **需要频繁修改配置** → 考虑动态 API
- **企业级部署** → 考虑数据库或配置中心
- **严格变更审批** → 使用 Git 同步
- **多环境部署** → 使用环境特定文件
- **容器化部署** → YAML + 环境变量引用

---

## 实现建议

对于当前项目，建议：

1. **保持 YAML 文件为主要方式**（已实现）
2. **添加环境特定配置**（简单增强）
3. **未来可选添加动态 API**（按需实现）

这样既保持简单性，又为未来扩展留有空间。
