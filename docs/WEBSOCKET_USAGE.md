# noVNC WebSocket 使用指南

本指南说明如何使用 `sandbox_deploy.py` 返回的 `websocket_url` 进行实时桌面访问。

## 返回字段说明

创建沙箱后新增字段：

```json
{
  "public_url": "https://xxxxx.e2b.dev",
  "novnc_url": "https://xxxxx.e2b.dev/novnc/vnc.html",
  "websocket_url": "wss://xxxxx.e2b.dev/websockify",
  "services": {
    "novnc": {
      "url": "https://xxxxx.e2b.dev/novnc/vnc.html",
      "websocket_url": "wss://xxxxx.e2b.dev/websockify",
      "requires_password": true,
      "password_hint": "auth_token"
    }
  }
}
```

## 使用场景

| 字段 | 适用场景 | 说明 |
|------|----------|------|
| `novnc_url` | 人工交互 | 浏览器打开完整 noVNC UI |
| `websocket_url` | 程序化/自定义客户端 | 直接 WebSocket (RFB) 通道 |

## 认证方式

VNC 密码默认使用 `SandboxConfig.auth_token`，若设置了 `vnc_password` 则使用自定义密码。

## JavaScript 直接嵌入

```html
<script type="module">
import RFB from 'https://cdn.jsdelivr.net/npm/@novnc/novnc@1.4.0/core/rfb.js';
const wsUrl = 'wss://xxxxx.e2b.dev/websockify';
const password = 'demo#e2b';
const rfb = new RFB(document.getElementById('screen'), wsUrl, { credentials: { password } });
rfb.scaleViewport = true;
rfb.resizeSession = true;
</script>
<div id="screen" style="width:100vw;height:100vh;background:#000"></div>
```

## Python 连接 (仅握手验证)

```python
import asyncio, os
import websockets

async def test(ws_url):
    async with websockets.connect(ws_url) as ws:
        greeting = await ws.recv()
        print('Server greeting:', greeting)

asyncio.run(test('wss://xxxxx.e2b.dev/websockify'))
```

## WebSocket 健康检查 (curl + wscat)

```bash
# 升级握手探测
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" https://xxxxx.e2b.dev/websockify

# 交互 (需安装 wscat)
wscat -c wss://xxxxx.e2b.dev/websockify
```

## Nginx 关键配置

已内置：
```nginx
location /websockify {
  proxy_pass http://127.0.0.1:6080/websockify;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_read_timeout 7d;
  proxy_send_timeout 7d;
  proxy_buffering off;
}
```

## 性能调优建议

- 降低分辨率：启动前设置 `SandboxConfig.xvfb_resolution = '1366x768x24'`
- 减少刷新：可在 `startup.sh` 里为 `x11vnc` 加 `-wait 50 -defer 200`
- 浏览器端启用自适应缩放：`rfb.scaleViewport = true`

## 故障排查

| 问题 | 可能原因 | 解决 |
|------|----------|------|
| 连接失败 | nginx 未启动 | 查看 `/var/log/nginx/error.log` |
| 无密码提示 | 使用默认 token | 用 `result['services']['mcp_connect']['auth_token']` |
| 频繁断开 | 长时间无操作 | 增加 keepalive 或降低分辨率 |

## 获取密码

```python
password = (lambda novnc: novnc['password_hint'] == 'auth_token' and result['services']['mcp_connect']['auth_token'] or 'custom-password')(result['services']['novnc'])
```

---
如需更高级的嵌入或多路流复用，可扩展一个自定义 websocket 中继层。欢迎提交 PR 改进。
