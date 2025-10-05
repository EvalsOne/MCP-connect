# 📋 JSON 配置格式迁移指南

## 🎯 为什么使用 JSON 格式？

### MCP 标准兼容性

JSON 格式是 Model Context Protocol 的**官方标准配置格式**，与以下工具保持一致：

- ✅ Claude Desktop（官方客户端）
- ✅ MCP Inspector（调试工具）
- ✅ 其他 MCP 实现（Go、Python 等）

### 标准字段名

使用 `mcpServers` 作为顶层字段名，符合 MCP 规范：

```json
{
  "mcpServers": {
    "server-id": {
      "command": "...",
      "args": [],
      "env": {}
    }
  }
}
```

---

## 🔄 配置格式对比

### ❌ 旧格式（YAML 优先）

```yaml
# mcp-servers.yaml
servers:  # 非标准字段名
  fetch:
    command: uvx
    args: [mcp-server-fetch]
```

**优先级**：
1. `mcp-servers.yaml`
2. `mcp-servers.yml`
3. `mcp-servers.json`

### ✅ 新格式（JSON 优先，MCP 标准）

```json
// mcp-servers.json
{
  "mcpServers": {  // MCP 标准字段名
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}
```

**优先级**：
1. `mcp-servers.json` ← **MCP 标准**
2. `mcp-servers.yaml`
3. `mcp-servers.yml`

---

## 🛠️ 迁移步骤

### 步骤 1：创建 JSON 配置文件

```bash
cp mcp-servers.example.json mcp-servers.json
```

### 步骤 2：转换现有 YAML 配置

**YAML 转 JSON 工具**：
- 在线工具：https://www.json2yaml.com/convert-yaml-to-json
- 命令行：`yq eval -o=json mcp-servers.yaml > mcp-servers.json`

**手动转换示例**：

```yaml
# 旧格式 (mcp-servers.yaml)
servers:  # 改为 mcpServers
  github:
    command: npx
    args: [-y, "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

转换为：

```json
// 新格式 (mcp-servers.json)
{
  "mcpServers": {
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

### 步骤 3：验证配置

```bash
# 启动服务，查看日志
npm start

# 看到以下输出表示成功
✓ Loaded MCP servers from /path/to/mcp-servers.json
```

### 步骤 4：删除旧 YAML 文件（可选）

```bash
rm mcp-servers.yaml mcp-servers.yml
```

---

## 📊 兼容性说明

### 向后兼容

✅ **保留了所有旧格式支持**：
- YAML 文件仍然有效（优先级降低）
- `servers` 和 `mcpServers` 字段名都支持
- 环境变量 `MCP_SERVERS` 仍可用

### 推荐做法

| 场景 | 推荐格式 | 原因 |
|------|----------|------|
| **新项目** | JSON (`mcpServers`) | MCP 标准，工具兼容性最好 |
| **现有项目** | 迁移到 JSON | 长期维护性更好 |
| **需要注释** | YAML (`mcpServers`) | 可选方案，但非标准 |
| **快速测试** | 环境变量 | 临时方案 |

---

## 🔍 配置字段对比

### 标准字段 vs 遗留字段

| 字段类型 | MCP 标准 | 遗留支持 | 说明 |
|---------|---------|---------|------|
| **顶层字段** | `mcpServers` | `servers` | 建议使用 `mcpServers` |
| **命令** | `command` | `command` | 相同 |
| **参数** | `args` | `args` | 相同 |
| **环境变量** | `env` | `env` | 相同 |
| **描述** | - | `description` | 扩展字段（非标准） |
| **超时** | - | `timeout` | 扩展字段（非标准） |
| **重试** | - | `retries` | 扩展字段（非标准） |

---

## 💡 最佳实践

### ✅ 推荐做法

```json
{
  "mcpServers": {
    "production-service": {
      "command": "npx",
      "args": ["-y", "my-mcp-server"],
      "env": {
        "API_KEY": "${PROD_API_KEY}"  // 引用环境变量
      }
    }
  }
}
```

**要点**：
1. 使用 `mcpServers` 字段名
2. 敏感信息用 `${VAR}` 引用 `.env`
3. 使用标准 JSON 格式化工具

### ❌ 不推荐做法

```json
{
  "servers": {  // ❌ 旧字段名
    "service": {
      "command": "node",
      "env": {
        "API_KEY": "hardcoded-secret-123"  // ❌ 硬编码密钥
      }
    }
  }
}
```

---

## 🔧 工具支持

### JSON Schema 验证

创建 `mcp-servers.schema.json`：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "mcpServers": {
      "type": "object",
      "patternProperties": {
        "^[a-zA-Z0-9_-]+$": {
          "type": "object",
          "required": ["command"],
          "properties": {
            "command": { "type": "string" },
            "args": { "type": "array", "items": { "type": "string" } },
            "env": { "type": "object" },
            "description": { "type": "string" },
            "timeout": { "type": "number" },
            "retries": { "type": "number" }
          }
        }
      }
    }
  },
  "required": ["mcpServers"]
}
```

在 `mcp-servers.json` 顶部添加：

```json
{
  "$schema": "./mcp-servers.schema.json",
  "mcpServers": {
    ...
  }
}
```

### VSCode 自动补全

创建 `.vscode/settings.json`：

```json
{
  "json.schemas": [
    {
      "fileMatch": ["mcp-servers.json"],
      "url": "./mcp-servers.schema.json"
    }
  ]
}
```

---

## 📚 参考资源

- **MCP 官方文档**：https://modelcontextprotocol.io
- **Claude Desktop 配置**：使用相同的 `mcpServers` 格式
- **配置指南**：[docs/configuration-guide.md](./configuration-guide.md)
- **快速参考**：[docs/quick-reference.md](./quick-reference.md)

---

## ❓ 常见问题

### Q: 必须立即迁移到 JSON 吗？

**A**: 不必须，但强烈建议：
- YAML 配置仍然有效
- 但 JSON 是 MCP 标准，长期兼容性更好
- 新项目应直接使用 JSON

### Q: `mcpServers` 和 `servers` 有什么区别？

**A**:
- `mcpServers` 是 MCP 官方标准字段名
- `servers` 是旧版遗留字段名，仍然支持
- 两者功能完全相同，建议使用 `mcpServers`

### Q: JSON 不支持注释怎么办？

**A**: 有三种方案：
1. 使用 `description` 字段记录说明
2. 保留 YAML 配置（降级为第二优先级）
3. 使用 JSONC（带注释的 JSON，部分工具支持）

### Q: 如何批量转换多个服务器配置？

**A**: 使用自动化工具：

```bash
# 使用 yq（推荐）
yq eval -o=json mcp-servers.yaml > mcp-servers.json

# 使用 Python
python -c "import yaml, json; print(json.dumps(yaml.safe_load(open('mcp-servers.yaml')), indent=2))" > mcp-servers.json
```

---

## ✅ 迁移检查清单

- [ ] 创建 `mcp-servers.json` 文件
- [ ] 使用 `mcpServers` 字段名
- [ ] 转换所有服务器配置
- [ ] 环境变量引用正确（`${VAR}`）
- [ ] 验证 JSON 语法正确
- [ ] 启动服务测试
- [ ] 查看日志确认加载成功
- [ ] （可选）删除旧 YAML 文件
- [ ] （可选）添加 JSON Schema

---

**总结**：迁移到 JSON 格式是与 MCP 生态系统保持一致的最佳选择！
