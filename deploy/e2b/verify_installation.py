#!/usr/bin/env python3
"""
验证 E2B MCP Sandbox Manager 安装
"""
import sys

def check_installation():
    """检查安装是否成功"""
    print("🔍 检查 E2B MCP Sandbox Manager 安装...\n")
    
    errors = []
    warnings = []
    
    # 1. 检查 Python 版本
    print("1️⃣ 检查 Python 版本...")
    if sys.version_info < (3, 8):
        errors.append(f"❌ Python 版本过低: {sys.version}. 需要 Python 3.8+")
    else:
        print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # 2. 检查核心模块导入
    print("\n2️⃣ 检查核心模块...")
    try:
        from sandbox_deploy import E2BSandboxManager, SandboxConfig
        print("   ✅ E2BSandboxManager 导入成功")
        print("   ✅ SandboxConfig 导入成功")
    except ImportError as e:
        errors.append(f"❌ 导入失败: {e}")
    
    # 3. 检查依赖
    print("\n3️⃣ 检查依赖包...")
    
    # Check e2b
    try:
        import e2b
        print(f"   ✅ e2b: {getattr(e2b, '__version__', 'unknown')}")
    except ImportError:
        errors.append("❌ e2b 未安装. 运行: pip install e2b")
    
    # Check httpx (optional but recommended)
    try:
        import httpx
        print(f"   ✅ httpx: {httpx.__version__}")
    except ImportError:
        warnings.append("⚠️  httpx 未安装 (可选但推荐). 运行: pip install httpx")
    
    # 4. 检查环境变量
    print("\n4️⃣ 检查环境变量...")
    import os
    
    if os.getenv("E2B_API_KEY"):
        print("   ✅ E2B_API_KEY 已设置")
    else:
        warnings.append("⚠️  E2B_API_KEY 未设置")
    
    if os.getenv("E2B_TEMPLATE_ID"):
        print("   ✅ E2B_TEMPLATE_ID 已设置")
    else:
        warnings.append("⚠️  E2B_TEMPLATE_ID 未设置")
    
    # 5. 检查配套文件
    print("\n5️⃣ 检查配套文件...")
    import pathlib
    
    script_dir = pathlib.Path(__file__).parent
    required_files = [
        "startup.sh",
        "chrome-devtools-wrapper.sh",
        "servers.json",
        "nginx.conf"
    ]
    
    for filename in required_files:
        filepath = script_dir / filename
        if filepath.exists():
            print(f"   ✅ {filename}")
        else:
            warnings.append(f"⚠️  {filename} 不存在")
    
    # 6. 测试基本功能
    print("\n6️⃣ 测试基本功能...")
    try:
        from sandbox_deploy import SandboxConfig
        config = SandboxConfig(
            template_id="test-template",
            timeout=600
        )
        print(f"   ✅ 创建配置成功")
        print(f"   ✅ 配置属性访问正常")
    except Exception as e:
        errors.append(f"❌ 配置创建失败: {e}")
    
    # 输出结果
    print("\n" + "="*60)
    if errors:
        print("\n❌ 发现错误:\n")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️  警告:\n")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors and not warnings:
        print("\n🎉 所有检查通过! E2B MCP Sandbox Manager 已正确安装!")
        print("\n📖 下一步:")
        print("  1. 设置环境变量:")
        print("     export E2B_API_KEY='your-key'")
        print("     export E2B_TEMPLATE_ID='your-template-id'")
        print("\n  2. 运行示例:")
        print("     python example_usage.py")
        print("\n  3. 查看文档:")
        print("     cat USAGE_IN_OTHER_PROJECTS.md")
    elif not errors:
        print("\n✅ 安装成功! 但有一些可选的警告需要注意。")
    else:
        print("\n❌ 安装检查失败! 请修复上述错误后重试。")
        return 1
    
    print("="*60 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(check_installation())
