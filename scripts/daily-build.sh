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

# ===== GitHub Pages 自动推送 =====
echo ""
echo "🚀 开始推送到 GitHub Pages..."

# 保存当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 添加 venv 到 gitignore（如果还没添加）
if ! grep -q "^venv/" .gitignore 2>/dev/null; then
    echo "venv/" >> .gitignore
fi

# 储藏所有未提交的变更（包括 dist 目录）
git add -A
git stash push -m "deploy-stash-$(date +%s)"

# 保存 dist 内容到临时目录
TEMP_DIR=$(mktemp -d)
cp -r dist/* "$TEMP_DIR/"

# 检查是否存在 gh-pages 分支
if git show-ref --quiet refs/heads/gh-pages; then
    # 分支存在，切换到它
    git checkout gh-pages
else
    # 创建新的 orphan 分支
    git checkout --orphan gh-pages
    # 清空所有文件
    git rm -rf . 2>/dev/null || true
fi

# 复制 dist 内容到根目录（保留已有文件，覆盖新文件）
cp -r "$TEMP_DIR/"* ./

# 添加 .nojekyll 文件（禁用 Jekyll 处理）
touch .nojekyll

# 提交并推送（如果有变更的话）
git add -A
if git diff --staged --quiet; then
    echo "📋 没有需要提交的变更"
else
    git commit -m "Update: $(date '+%Y-%m-%d %H:%M:%S') - $TOTAL articles"
    git push origin gh-pages
    echo "✅ 已推送到 GitHub Pages"
fi

# 清理临时目录
rm -rf "$TEMP_DIR"

# 切回原分支并恢复储藏
git checkout "$CURRENT_BRANCH"
git stash pop || true

echo ""
echo "✅ GitHub Pages 部署完成！"
echo "🌐 访问地址: https://m-qiangzhu.github.io/ai-daily-brief/"
