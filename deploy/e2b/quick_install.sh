#!/bin/bash
# Quick Install Script for E2B MCP Sandbox Manager
# This script provides a fast installation method using shallow clone

set -e

REPO_URL="https://github.com/EvalsOne/MCP-bridge.git"
BRANCH="${1:-dev_streamable_http}"
INSTALL_DIR="${2:-./e2b-mcp-sandbox}"

echo "🚀 E2B MCP Sandbox Manager - Quick Install"
echo "============================================"
echo ""
echo "Repository: $REPO_URL"
echo "Branch: $BRANCH"
echo "Install directory: $INSTALL_DIR"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Error: git is not installed"
    echo "Please install git first: https://git-scm.com/downloads"
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip is not installed"
    echo "Please install Python and pip first"
    exit 1
fi

PIP_CMD=$(command -v pip3 2>/dev/null || command -v pip)

echo "📦 Step 1: Cloning repository (shallow clone for speed)..."
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory $INSTALL_DIR already exists"
    read -p "Do you want to remove it and continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "❌ Installation cancelled"
        exit 1
    fi
fi

# Use shallow clone with depth=1 for faster cloning
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"

echo ""
echo "📦 Step 2: Installing package..."
cd "$INSTALL_DIR/deploy/e2b"

# Install the package
$PIP_CMD install -e .

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "📖 Quick Start:"
echo ""
echo "  1. Set your E2B API key:"
echo "     export E2B_API_KEY='your-api-key-here'"
echo "     export E2B_TEMPLATE_ID='your-template-id'"
echo ""
echo "  2. Test the installation:"
echo "     cd $INSTALL_DIR/deploy/e2b"
echo "     python example_usage.py"
echo ""
echo "  3. Use in your code:"
echo "     from sandbox_deploy import E2BSandboxManager, SandboxConfig"
echo ""
echo "📚 Documentation:"
echo "  - Installation Guide: $INSTALL_DIR/deploy/e2b/INSTALL.md"
echo "  - Usage Guide: $INSTALL_DIR/deploy/e2b/USAGE_IN_OTHER_PROJECTS.md"
echo "  - Examples: $INSTALL_DIR/deploy/e2b/example_usage.py"
echo ""
echo "🎉 Happy coding!"
