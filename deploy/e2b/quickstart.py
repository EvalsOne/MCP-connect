#!/usr/bin/env python3
"""
MCP Bridge E2B 快速部署示例
运行此脚本快速体验 E2B 沙箱中的 MCP Bridge

使用方法：
    python quickstart.py

前置要求：
    pip install e2b requests
    export E2B_API_KEY=your-e2b-api-key
"""

import asyncio
import os
import sys
import json
import time
from typing import Optional

try:
    from e2b import AsyncSandbox
except ImportError:
    print("❌ 请先安装 E2B: pip install e2b")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ 请先安装 requests: pip install requests")
    sys.exit(1)


# E2B 模板 ID（需要先构建模板）
# 运行 `make e2b:build:dev` 获取模板 ID
TEMPLATE_ID = os.getenv("E2B_TEMPLATE_ID", "mcp")

# MCP Bridge 配置
ACCESS_TOKEN = "quickstart-demo-token"
PORT = 3000


async def wait_for_server(sandbox: AsyncSandbox, max_retries: int = 30) -> bool:
    """等待 MCP Bridge 服务启动"""
    print("⏳ 等待服务启动...", end="", flush=True)

    for i in range(max_retries):
        try:
            result = await sandbox.commands.run(
                f"curl -s http://localhost:{PORT}/health",
                timeout=2
            )
            if result.exit_code == 0 and "ok" in result.stdout:
                print(" ✅ 服务已就绪！")
                return True
        except Exception:
            pass

        print(".", end="", flush=True)
        await asyncio.sleep(1)

    print(" ❌ 超时")
    return False


async def main():
    print("🌉 MCP Bridge E2B 快速部署示例\n")

    # 检查 API Key
    if not os.getenv("E2B_API_KEY"):
        print("❌ 请设置 E2B_API_KEY 环境变量")
        print("   获取 API Key: https://e2b.dev/dashboard")
        return

    print(f"📦 创建 E2B 沙箱（模板: {TEMPLATE_ID}）...")

    try:
        # 创建沙箱
        sandbox = await AsyncSandbox.create(TEMPLATE_ID, timeout=120)
        print(f"✅ 沙箱创建成功！ID: {sandbox.sandbox_id}\n")

        try:
            # 启动 MCP Bridge 服务
            print("🚀 启动 MCP Bridge 服务...")
            process = await sandbox.process.start(
                cmd=f"cd /app && ACCESS_TOKEN={ACCESS_TOKEN} PORT={PORT} npm start",
                env={"NODE_ENV": "production"}
            )

            # 等待服务启动
            if not await wait_for_server(sandbox):
                print("❌ 服务启动失败")
                return

            print("\n" + "="*60)
            print("🎉 MCP Bridge 已在 E2B 沙箱中运行！")
            print("="*60 + "\n")

            # 测试健康检查
            print("📍 测试 1: 健康检查")
            result = await sandbox.commands.run(
                f"curl -s http://localhost:{PORT}/health"
            )
            print(f"   响应: {result.stdout}\n")

            # 测试桥接端点
            print("📍 测试 2: 调用 MCP 工具（mcp-server-fetch）")
            bridge_request = {
                "serverPath": "uvx",
                "args": ["mcp-server-fetch"],
                "method": "tools/list",
                "params": {}
            }

            curl_cmd = f"""curl -s -X POST http://localhost:{PORT}/bridge \
  -H "Authorization: Bearer {ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{json.dumps(bridge_request)}'"""

            result = await sandbox.commands.run(curl_cmd, timeout=30)

            if result.exit_code == 0:
                try:
                    response = json.loads(result.stdout)
                    if "tools" in response:
                        print(f"   ✅ 成功！找到 {len(response['tools'])} 个工具")
                        for tool in response['tools'][:3]:
                            print(f"      - {tool.get('name', 'unknown')}")
                        if len(response['tools']) > 3:
                            print(f"      ... 还有 {len(response['tools']) - 3} 个工具")
                    else:
                        print(f"   响应: {result.stdout[:200]}")
                except json.JSONDecodeError:
                    print(f"   响应: {result.stdout[:200]}")
            else:
                print(f"   ❌ 失败: {result.stderr}")

            print("\n" + "="*60)
            print("📊 沙箱信息")
            print("="*60)
            print(f"沙箱 ID: {sandbox.sandbox_id}")
            print(f"模板: {TEMPLATE_ID}")
            print(f"服务地址: http://localhost:{PORT}")
            print(f"访问令牌: {ACCESS_TOKEN}")

            print("\n" + "="*60)
            print("💡 提示")
            print("="*60)
            print("1. 沙箱将在退出后自动销毁")
            print("2. 查看完整日志: python view_sandbox_logs.py <sandbox-id>")
            print("3. 详细文档: docs/deployment-guide.md")

            # 询问是否保持运行
            print("\n⏸  按 Ctrl+C 结束并销毁沙箱...")
            try:
                await asyncio.sleep(3600)  # 保持 1 小时
            except KeyboardInterrupt:
                print("\n👋 正在清理...")

        finally:
            # 清理沙箱
            print("🗑️  销毁沙箱...")
            await sandbox.kill()
            print("✅ 沙箱已销毁")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 已取消")
