#!/bin/bash
# MCP 服务器启动脚本

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查 Python 版本
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "📦 Python 版本: $PYTHON_VERSION"

# 根据版本选择模式
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
    echo "✅ 支持 MCP 模式"
    MODE="mcp"
else
    echo "⚠️  Python 版本低于 3.10，使用 HTTP 模式"
    MODE="http"
fi

# 检查依赖
if ! python3 -c "import requests" 2>/dev/null; then
    echo "⚠️  正在安装依赖..."
    python3 -m pip install -r requirements.txt -q
fi

# 解析命令行参数
TRANSPORT=$1
HOST=${2:-0.0.0.0}
PORT=${3:-8000}

# 如果没有指定传输协议，使用自动检测的模式
if [ -z "$TRANSPORT" ]; then
    TRANSPORT=$MODE
fi

echo "🚀 启动模式: $TRANSPORT"
if [ "$TRANSPORT" = "http" ]; then
    echo "📍 监听地址: http://$HOST:$PORT"
    echo "📖 API 文档: http://$HOST:$PORT/docs"
fi
echo ""

# 启动服务器
if [ "$TRANSPORT" = "mcp" ]; then
    python3 scripts/mcp_server.py --transport mcp
else
    python3 scripts/mcp_server.py --transport http --host "$HOST" --port "$PORT"
fi