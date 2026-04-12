"""
AI Daily Brief - OpenClaw Notifier
Send QQ notification via OpenClaw
"""

import json
import sys
from pathlib import Path


def send_qq_notification(summary_path: str = "dist/summary.json"):
    """Send notification to QQ via OpenClaw message tool"""
    
    try:
        summary = json.loads(Path(summary_path).read_text(encoding='utf-8'))
        
        total = summary['total_articles']
        categories = summary['categories']
        
        # Build message
        lines = [
            f"🤖 AI Daily Brief | 今日资讯 ({summary['generated_at'][:10]})",
            "",
            f"📊 共 {total} 篇文章",
        ]
        
        # Add category breakdown
        cat_names = {
            'official': '🏢 官方',
            'researcher': '👨‍🔬 研究员',
            'media': '📰 媒体',
            'chinese': '🇨🇳 国内',
        }
        
        for cat, count in categories.items():
            name = cat_names.get(cat, cat)
            lines.append(f"   {name}: {count}篇")
        
        lines.append("")
        lines.append("🔗 点击查看完整日报")
        
        # This output will be captured by OpenClaw
        print("\n".join(lines))
        
        return True
        
    except Exception as e:
        print(f"❌ Notification failed: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    send_qq_notification()
