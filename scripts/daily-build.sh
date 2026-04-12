#!/bin/bash
# AI Daily Brief - OpenClaw Daily Build Script
# This script is called by OpenClaw cron job

set -e

cd /Users/kungfu/.openclaw/workspace/ai-daily-brief

# Activate virtual environment
source venv/bin/activate

# Generate newsletter
python main.py --days 1

# Get summary for notification
TOTAL=$(cat dist/summary.json | python3 -c "import sys,json; print(json.load(sys.stdin)['total_articles'])")

echo "✅ AI日报生成完成"
echo "📊 共 $TOTAL 篇文章"
echo "📁 文件位置: dist/index.html"