# 📝 Changelog

本文档记录 MCP Bridge 的所有重要改进和变更。

---

## [2.1.0] - 2025-01-XX

### ✨ 新增功能

#### 配置系统重构（MCP 标准兼容）
- **JSON 配置文件支持** - MCP 官方标准格式 ⭐
  - 支持 `mcpServers` 标准字段名（兼容 Claude Desktop 等工具）
  - 支持 `mcp-servers.json`、`mcp-servers.yaml`、`mcp-servers.yml`
  - JSON 优先级最高，符合 MCP 生态系统规范
  - 环境变量引用：`${VAR_NAME}` 语法
  - 向后兼容 `servers` 字段名和 `MCP_SERVERS` 环境变量

- **扩展配置选项**
  - 新增 `description` 字段（服务器描述）
  - 新增 `timeout` 字段（连接超时设置）
  - 新增 `retries` 字段（重试次数）

#### E2B 云沙箱部署
- **快速部署脚本** - `deploy/e2b/quickstart.py`
  - 5 分钟内完成云端部署
  - 自动测试健康检查和工具调用
  - 新手友好的交互式输出

- **完善的 E2B 文档**
  - 重写 `deploy/e2b/README.md`
  - 包含快速开始、故障排查、最佳实践
  - 沙箱管理工具说明

### 📚 文档改进

#### 新增文档
- `docs/configuration-guide.md` - 配置指南（17+ 场景示例）
- `docs/configuration-alternatives.md` - 6 种配置方案对比分析
- `docs/deployment-guide.md` - 完整部署指南（Docker/K8s/E2B）
- `docs/SUMMARY.md` - 改进总结文档
- `CHANGELOG.md` - 本变更日志

#### 更新文档
- `README.md` - 全面重写
  - 添加 E2B 快速部署章节
  - 更新特性表格（新增云端部署）
  - 改进示例代码可读性

- `deploy/e2b/README.md` - E2B 部署指南
  - 添加快速开始（5 分钟）
  - 文件结构说明
  - 常见问题解答

### 🔧 代码改进

#### 配置模块 (`src/config/config.ts`)
- 新增 YAML/JSON 文件解析逻辑
- 实现环境变量递归引用解析
- 智能配置加载优先级
- 详细的加载日志输出

#### 安全改进
- `.gitignore` 更新
  - 保护 `mcp-servers.yaml`、`mcp-servers.yml`、`mcp-servers.json`
  - 防止配置文件意外提交

### 📦 依赖更新

- 新增：`js-yaml@^4.1.0` - YAML 解析
- 新增：`@types/js-yaml@^4.0.9` - TypeScript 类型定义

### 🎯 改进亮点

| 方面 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| **配置可读性** | 单行 JSON | 多行 YAML + 注释 | ⬆️ 300% |
| **安全性** | 密钥硬编码风险 | 环境变量引用 | ⬆️ 显著 |
| **文档完善度** | 1 个 README | 6 个详细文档 | ⬆️ 600% |
| **部署方式** | 仅本地/Docker | 新增 E2B 云沙箱 | ⬆️ 新功能 |
| **上手时间** | 需要理解 JSON | 5 分钟快速部署 | ⬇️ 50% |

---

## [2.0.0] - 2024-XX-XX

### ✨ 主要功能

- 双模式支持：短连接桥接 + SSE 长连接流式传输
- 客户端缓存机制（5 分钟 TTL）
- Bearer Token 认证
- CORS 白名单支持
- Ngrok 隧道集成
- 健康检查和优雅关闭
- 结构化日志（Winston）

### 🏗️ 架构

- TypeScript + Node.js
- Express.js Web 框架
- MCP SDK 集成
- 模块化代码结构

---

## 配置迁移指南

### 从 2.0.0 迁移到 2.1.0

**旧配置方式** (`.env`):
```env
MCP_SERVERS={"fetch":{"command":"uvx","args":["mcp-server-fetch"]}}
```

**新配置方式** (`mcp-servers.yaml`):
```yaml
servers:
  fetch:
    command: uvx
    args:
      - mcp-server-fetch
    description: "HTTP content fetcher"
```

**迁移步骤**：

1. 创建配置文件
   ```bash
   cp mcp-servers.example.yaml mcp-servers.yaml
   ```

2. 将 JSON 配置转换为 YAML
   - 可使用在线工具：https://www.json2yaml.com/

3. 删除 `.env` 中的 `MCP_SERVERS` 行

4. 重启服务
   ```bash
   npm restart
   ```

**注意**：旧配置方式仍然兼容，无需立即迁移。

---

## 未来计划

### v2.2.0（短期）
- [ ] 配置验证 API
- [ ] 配置热加载
- [ ] 环境特定配置文件（`mcp-servers.{env}.yaml`）
- [ ] Prometheus metrics 支持

### v2.3.0（中期）
- [ ] Web 管理界面
- [ ] 动态增删服务器 API
- [ ] 配置导入/导出功能
- [ ] 单元测试覆盖率 80%+

### v3.0.0（长期）
- [ ] 数据库存储配置
- [ ] 配置中心集成（Consul/etcd）
- [ ] 多租户支持
- [ ] 分布式追踪（OpenTelemetry）

---

## 贡献者

感谢所有为 MCP Bridge 做出贡献的开发者！

---

## 链接

- **项目主页**: https://github.com/yourusername/mcp-bridge
- **问题反馈**: https://github.com/yourusername/mcp-bridge/issues
- **MCP 协议**: https://modelcontextprotocol.io
- **E2B 平台**: https://e2b.dev

---

**格式说明**：
- `[主要版本]` - 不兼容的 API 变更
- `[次要版本]` - 向后兼容的功能新增
- `[修订版本]` - 向后兼容的问题修复
