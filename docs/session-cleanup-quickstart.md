# Session Cleanup 快速参考

## 🚀 快速开始

### 默认配置（推荐）

什么都不用做！新的清理机制已经自动优化：

```bash
# 启动服务
npm start

# 自动启用的功能：
# ✅ 每 ~100 秒清理一次过期 session
# ✅ 空闲超过 5 分钟的 session 会被清理
# ✅ 正在使用的 session 不会被误杀
```

### 禁用清理（长期任务）

如果你的任务运行时间很长，可以完全禁用清理：

```bash
# .env
DISABLE_BRIDGE_CLEANUP=true
DISABLE_STREAM_CLEANUP=true

# 启动
npm start
```

⚠️ **警告**：禁用清理后，session 永不过期，需要手动管理！

## 📊 配置对比

| 场景 | 配置 | 优点 | 缺点 |
|------|------|------|------|
| **默认** | 不设置任何变量 | 自动管理，无需关心 | Session 可能在 5 分钟后过期 |
| **长 TTL** | `STREAM_SESSION_TTL_MS=1800000` | 30 分钟后才过期 | 占用更多内存 |
| **完全禁用** | `DISABLE_*_CLEANUP=true` | 永不过期 | 需要手动清理，内存可能泄漏 |

## 🛠️ 常用命令

### 启动时查看清理配置

```bash
npm start

# 输出示例：
# [INFO] Bridge session cleanup enabled (interval: 100000ms, TTL: 300000ms)
# [INFO] Streamable session cleanup enabled (interval: 100000ms, TTL: 300000ms)
```

### 查看清理日志

```bash
# 实时查看清理活动
tail -f logs/*.log | grep -i cleanup

# 输出示例：
# [INFO] Cleaning up 2 expired bridge client(s)
# [DEBUG] Closing bridge client client_123 (idle for 320s)
```

### 临时禁用清理（不修改 .env）

```bash
# 仅当前会话禁用
DISABLE_BRIDGE_CLEANUP=true DISABLE_STREAM_CLEANUP=true npm start
```

## 🔍 故障排查

### 症状：Session 被意外关闭

```bash
Error: Session not found (404)
```

**解决方案 1**：延长 TTL
```bash
# .env
STREAM_SESSION_TTL_MS=1800000  # 30 分钟
```

**解决方案 2**：禁用清理
```bash
# .env
DISABLE_BRIDGE_CLEANUP=true
DISABLE_STREAM_CLEANUP=true
```

**解决方案 3**：客户端发送心跳
```javascript
// 每 2 分钟 ping 一次保持 session 活跃
setInterval(async () => {
  await fetch('/mcp/server', {
    method: 'POST',
    headers: { 'mcp-session-id': sessionId },
    body: JSON.stringify({ method: 'ping' })
  });
}, 2 * 60 * 1000);
```

### 症状：内存占用持续增长

**原因**：清理被禁用，session 累积过多

**解决方案**：重新启用清理
```bash
# 删除或注释掉 .env 中的：
# DISABLE_BRIDGE_CLEANUP=true
# DISABLE_STREAM_CLEANUP=true

# 重启服务
npm restart
```

## 📝 最佳实践

### 1. 开发环境

```bash
# .env.development
STREAM_SESSION_TTL_MS=600000  # 10 分钟，方便调试
LOG_LEVEL=debug  # 看到详细的清理日志
```

### 2. 生产环境

```bash
# .env.production
STREAM_SESSION_TTL_MS=300000  # 5 分钟，默认值
LOG_LEVEL=info  # 适度的日志级别
# 不禁用清理，让服务器自动管理
```

### 3. 长期任务环境

```bash
# .env.production
STREAM_SESSION_TTL_MS=3600000  # 1 小时
DISABLE_BRIDGE_CLEANUP=true  # 完全由客户端控制
DISABLE_STREAM_CLEANUP=true
```

## 🎯 改进总结

| 改进点 | 旧行为 | 新行为 |
|--------|--------|--------|
| **清理频率** | 每 5 分钟 | 每 ~1.67 分钟 (TTL/3) |
| **配置灵活性** | 无法禁用 | 可通过环境变量禁用 |
| **日志信息** | 基本信息 | 详细的清理统计和时间 |
| **误杀风险** | 较高 | 显著降低 |

## 📚 更多信息

详细文档请参考：[Session Cleanup 完整说明](./session-cleanup.md)
