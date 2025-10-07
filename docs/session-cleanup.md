# Session Cleanup 机制说明

## 问题背景

原有的 session 清理机制存在以下问题：
1. **清理间隔过长**：每 5 分钟清理一次，容易误杀正在使用的 session
2. **时间窗口问题**：session 可能在即将被使用前的瞬间被清理
3. **无法禁用**：某些场景需要长期保持 session，但无法禁用清理

## 改进方案

### 1. 优化清理间隔

**原来**：
```
清理间隔 = TTL (5分钟)
每 5 分钟清理一次，清理超过 5 分钟未使用的 session
```

**现在**：
```
清理间隔 = TTL / 3 (约 1分40秒)
每 1 分 40 秒清理一次，清理超过 5 分钟未使用的 session
```

**优势**：
- ✅ 更频繁地检查，减少过期 session 存活时间
- ✅ 减少误杀窗口：session 刚过期就能被快速清理
- ✅ 对正在使用的 session 影响更小

### 2. 支持禁用清理

通过环境变量控制是否启用清理：

```bash
# 禁用 Bridge 方式的清理
DISABLE_BRIDGE_CLEANUP=true

# 禁用 Streamable 方式的清理
DISABLE_STREAM_CLEANUP=true
```

### 3. 改进日志输出

**启动时**：
```
Bridge session cleanup enabled (interval: 100000ms, TTL: 300000ms)
Streamable session cleanup enabled (interval: 100000ms, TTL: 300000ms)
```

**清理时**：
```
Cleaning up 2 expired bridge client(s)
Closing bridge client client_123 (idle for 320s)
```

## 使用建议

### 场景 1：频繁的短期请求（推荐默认配置）

```bash
# .env
STREAM_SESSION_TTL_MS=300000  # 5 分钟
# 不设置 DISABLE_*_CLEANUP，使用默认清理机制
```

**特点**：
- 自动清理空闲 session
- 减少资源占用
- 适合大多数场景

### 场景 2：长期运行的任务

```bash
# .env
STREAM_SESSION_TTL_MS=1800000  # 30 分钟
# 或者直接禁用清理
DISABLE_BRIDGE_CLEANUP=true
DISABLE_STREAM_CLEANUP=true
```

**特点**：
- Session 可以长期保持
- 需要客户端主动管理 session 生命周期
- 适合长时间运行的工作流

### 场景 3：高频低延迟调用

```bash
# .env
STREAM_SESSION_TTL_MS=600000  # 10 分钟
# 启用清理，但延长 TTL
```

**特点**：
- 平衡资源管理和可用性
- 减少因 session 过期导致的重连

## 客户端最佳实践

### 1. 实现心跳保活

对于长期任务，定期发送请求更新 `lastUsed`：

```javascript
// 每 2 分钟发送一次心跳
setInterval(async () => {
  try {
    await fetch('http://localhost:3000/mcp/filesystem', {
      method: 'POST',
      headers: {
        'mcp-session-id': sessionId,
        'Accept': 'application/json, text/event-stream',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'ping',
        params: {}
      })
    });
  } catch (error) {
    console.error('Heartbeat failed:', error);
  }
}, 2 * 60 * 1000);
```

### 2. 处理 Session 过期

实现重试逻辑，自动创建新 session：

```javascript
async function callMCP(sessionId, method, params) {
  try {
    const response = await fetch('http://localhost:3000/mcp/filesystem', {
      method: 'POST',
      headers: {
        'mcp-session-id': sessionId,
        'Accept': 'application/json, text/event-stream'
      },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
    });

    if (response.status === 404) {
      // Session 过期，创建新的
      console.log('Session expired, creating new session...');
      const newResponse = await fetch('http://localhost:3000/mcp/filesystem', {
        method: 'POST',
        headers: { 'Accept': 'application/json, text/event-stream' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
      });
      const newSessionId = newResponse.headers.get('mcp-session-id');
      return { response: newResponse, sessionId: newSessionId };
    }

    return { response, sessionId };
  } catch (error) {
    console.error('MCP call failed:', error);
    throw error;
  }
}
```

### 3. 主动关闭 Session

任务完成后，主动释放资源：

```javascript
async function cleanup(sessionId) {
  try {
    await fetch(`http://localhost:3000/mcp/filesystem`, {
      method: 'DELETE',
      headers: {
        'mcp-session-id': sessionId,
        'Authorization': 'Bearer your-token'
      }
    });
    console.log('Session closed successfully');
  } catch (error) {
    console.error('Failed to close session:', error);
  }
}
```

## 监控建议

### 查看 Session 状态

```bash
# 查看日志中的清理信息
tail -f logs/*.log | grep -i "cleanup\|session"

# 输出示例：
# [INFO] Bridge session cleanup enabled (interval: 100000ms, TTL: 300000ms)
# [INFO] Streamable session cleanup enabled (interval: 100000ms, TTL: 300000ms)
# [INFO] Cleaning up 3 expired bridge client(s)
# [DEBUG] Closing bridge client client_123 (idle for 320s)
```

### 性能指标

如果遇到性能问题，可以考虑：
1. 增加 TTL 值，减少清理频率
2. 禁用清理，由客户端全权管理
3. 实现连接池限制（未来功能）

## 配置参考

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `STREAM_SESSION_TTL_MS` | `300000` (5分钟) | Session 空闲超时时间 |
| `DISABLE_BRIDGE_CLEANUP` | `false` | 是否禁用 Bridge 清理 |
| `DISABLE_STREAM_CLEANUP` | `false` | 是否禁用 Streamable 清理 |

## 故障排查

### 问题：Session 被意外关闭

**症状**：
```
Error: Session not found
或
Connection reset by peer
```

**可能原因**：
1. Session 空闲时间超过 TTL
2. 清理机制误杀了正在使用的 session

**解决方案**：
```bash
# 方案 1：延长 TTL
STREAM_SESSION_TTL_MS=1800000  # 30 分钟

# 方案 2：完全禁用清理
DISABLE_BRIDGE_CLEANUP=true
DISABLE_STREAM_CLEANUP=true

# 方案 3：客户端实现心跳保活
```

### 问题：内存占用持续增长

**症状**：
服务器内存不断增长，不释放

**可能原因**：
清理被禁用，session 累积过多

**解决方案**：
```bash
# 1. 重新启用清理
unset DISABLE_BRIDGE_CLEANUP
unset DISABLE_STREAM_CLEANUP

# 2. 或者实现客户端主动关闭
# 使用 DELETE /mcp/:serverId 端点
```

## 未来改进

计划中的功能：
- [ ] 每个 server 独立的 TTL 配置
- [ ] Session 持久化（重启不丢失）
- [ ] 连接池管理和限制
- [ ] Session 监控 API (`GET /sessions`)
- [ ] 自适应清理策略（基于系统负载）
