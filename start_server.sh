#!/bin/bash
# 乡礼 Spark 后端服务启动脚本

set -e

cd "$(dirname "$0")"

# 默认端口
PORT=${PORT:-8000}

echo "🚀 启动乡礼 Spark 后端服务..."
echo "📦 端口: $PORT"
echo "📖 API文档: http://localhost:$PORT/docs"
echo ""

exec python -m uvicorn wuyan_ai.server.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload
