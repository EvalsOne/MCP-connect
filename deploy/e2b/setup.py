#!/usr/bin/env python3
"""
Setup script for e2b-mcp-sandbox package
"""
from setuptools import setup, find_packages
import os

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="e2b-mcp-sandbox",
    version="0.1.0",
    author="EvalsOne",
    description="E2B Sandbox Manager for MCP-enabled Web Sandbox",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/EvalsOne/MCP-bridge",
    packages=find_packages(where="."),
    py_modules=["sandbox_deploy"],
    python_requires=">=3.8",
    install_requires=[
        "e2b>=0.17.0",
        "httpx>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={
        "console_scripts": [
            "e2b-mcp-sandbox=sandbox_deploy:main",
        ],
    },
    package_data={
        "": [
            "startup.sh",
            "chrome-devtools-wrapper.sh",
            "servers.json",
            "nginx.conf",
        ],
    },
    include_package_data=True,
)
