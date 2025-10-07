"""
Example: Using E2BSandboxManager in Your Project

This example shows how to import and use E2BSandboxManager 
from the MCP-bridge repository in your own project.
"""
import asyncio
import os
from sandbox_deploy import E2BSandboxManager, SandboxConfig

async def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===\n")
    
    # Configure sandbox
    config = SandboxConfig(
        template_id=os.getenv("E2B_TEMPLATE_ID", "your-template-id"),
        auth_token="my-secure-token",
        port=3000,
        timeout=1800  # 30 minutes
    )
    
    # Create manager
    manager = E2BSandboxManager(config)
    
    # Create sandbox
    result = await manager.create_sandbox(
        sandbox_id="example-sandbox",
        enable_internet=True,
        wait_for_ready=True
    )
    
    if result["success"]:
        print(f"✅ Sandbox created successfully!")
        print(f"   Sandbox ID: {result['sandbox_id']}")
        print(f"   Public URL: {result['public_url']}")
        print(f"   MCP URL: {result['services']['mcp_connect']['url']}")
        print(f"   noVNC URL: {result['novnc_url']}")
        
        # Do something with the sandbox...
        await asyncio.sleep(10)
        
        # Clean up
        await manager.stop_sandbox("example-sandbox")
        print("✅ Sandbox stopped")
    else:
        print(f"❌ Failed: {result.get('error')}")


async def example_advanced_usage():
    """Advanced usage with custom configuration"""
    print("\n=== Advanced Usage Example ===\n")
    
    # Custom configuration
    config = SandboxConfig(
        template_id=os.getenv("E2B_TEMPLATE_ID"),
        auth_token="advanced-token",
        port=3001,
        host="0.0.0.0",
        secure=True,
        timeout=7200,  # 2 hours
        keepalive_interval=30,  # Ping every 30 seconds
        platform_keepalive_interval=60,
        display=":99",
        xvfb_resolution="1920x1080x24",
        vnc_port=5900,
        novnc_port=6080,
        vnc_password="custom-vnc-password"
    )
    
    manager = E2BSandboxManager(config)
    
    # Create multiple sandboxes
    sandbox_ids = []
    for i in range(2):
        result = await manager.create_sandbox(
            sandbox_id=f"advanced-sandbox-{i}",
            enable_internet=True,
            wait_for_ready=True
        )
        if result["success"]:
            sandbox_ids.append(result["sandbox_id"])
            print(f"✅ Created: {result['sandbox_id']}")
    
    # List all active sandboxes
    sandboxes = await manager.list_sandboxes()
    print(f"\n📦 Active sandboxes: {sandboxes['count']}")
    for sb in sandboxes["sandboxes"]:
        print(f"   - {sb['sandbox_id']}: {sb['public_url']}")
    
    # Keep sandboxes running
    print("\n⏳ Sandboxes running for 30 seconds...")
    await asyncio.sleep(30)
    
    # Stop all sandboxes
    await manager.stop_all_sandboxes()
    print("✅ All sandboxes stopped")


async def example_error_handling():
    """Example with error handling"""
    print("\n=== Error Handling Example ===\n")
    
    config = SandboxConfig(
        template_id=os.getenv("E2B_TEMPLATE_ID"),
        timeout=600
    )
    
    manager = E2BSandboxManager(config)
    
    try:
        result = await manager.create_sandbox(
            sandbox_id="error-example",
            enable_internet=True,
            wait_for_ready=True
        )
        
        if not result["success"]:
            print(f"❌ Sandbox creation failed: {result.get('error')}")
            return
        
        print(f"✅ Sandbox ready: {result['public_url']}")
        
        # Simulate some work
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Always clean up
        try:
            await manager.stop_sandbox("error-example")
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


async def example_integration_with_app():
    """Example: Integrating with your application"""
    print("\n=== Integration Example ===\n")
    
    class MyApp:
        def __init__(self):
            self.sandbox_manager = None
            self.active_sandbox = None
        
        async def initialize(self):
            """Initialize sandbox for the app"""
            config = SandboxConfig(
                template_id=os.getenv("E2B_TEMPLATE_ID"),
                auth_token="app-token",
                timeout=3600
            )
            self.sandbox_manager = E2BSandboxManager(config)
            
            result = await self.sandbox_manager.create_sandbox(
                sandbox_id="app-sandbox",
                enable_internet=True,
                wait_for_ready=True
            )
            
            if result["success"]:
                self.active_sandbox = result
                print(f"✅ App sandbox ready: {result['public_url']}")
                return True
            return False
        
        async def get_mcp_endpoint(self):
            """Get MCP endpoint URL"""
            if self.active_sandbox:
                return self.active_sandbox["services"]["mcp_connect"]["url"]
            return None
        
        async def cleanup(self):
            """Clean up resources"""
            if self.sandbox_manager and self.active_sandbox:
                await self.sandbox_manager.stop_sandbox(
                    self.active_sandbox["sandbox_id"]
                )
                print("✅ App cleanup completed")
    
    # Use the app
    app = MyApp()
    if await app.initialize():
        mcp_url = await app.get_mcp_endpoint()
        print(f"🔗 MCP Endpoint: {mcp_url}")
        
        # Your app logic here...
        await asyncio.sleep(5)
        
        await app.cleanup()


async def main():
    """Run all examples"""
    # Check for API key
    if not os.getenv("E2B_API_KEY"):
        print("❌ Error: E2B_API_KEY environment variable not set")
        print("Please set your E2B API key:")
        print("  export E2B_API_KEY='your-api-key-here'")
        return
    
    if not os.getenv("E2B_TEMPLATE_ID"):
        print("❌ Error: E2B_TEMPLATE_ID environment variable not set")
        print("Please set your E2B template ID:")
        print("  export E2B_TEMPLATE_ID='your-template-id'")
        return
    
    # Run examples
    try:
        await example_basic_usage()
        await example_advanced_usage()
        await example_error_handling()
        await example_integration_with_app()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
