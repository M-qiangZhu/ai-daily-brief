"""
AI Daily Brief - OpenClaw Notifier
Called by OpenClaw to send QQ notification after daily build
"""

import json
import sys
from pathlib import Path


def format_notification():
    """Format notification message for QQ"""
    
    try:
        summary_path = Path(__file__).parent.parent / "dist" / "summary.json"
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        
        total = summary['total_articles']
        categories = summary['categories']
        sources = summary['sources']
        
        # Category emoji mapping
        cat_emojis = {
            'official': '🏢',
            'researcher': '👨‍🔬',
            'media': '📰',
            'chinese': '🇨🇳',
        }
        
        cat_names = {
            'official': '官方',
            'researcher': '研究员',
            'media': '媒体',
            'chinese': '国内',
        }
        
        lines = [
            f"🤖 AI Daily Brief | {summary['generated_at'][:10]}",
            "",
            f"📊 今日共 {total} 篇文章",
            "",
        ]
        
        # Add category breakdown
        for cat, count in sorted(categories.items()):
            emoji = cat_emojis.get(cat, '📄')
            name = cat_names.get(cat, cat)
            lines.append(f"{emoji} {name}: {count}篇")
        
        lines.append("")
        lines.append(f"📰 来源: {', '.join(sources[:3])}")
        if len(sources) > 3:
            lines.append(f"   等共 {len(sources)} 个信源")
        
        lines.append("")
        lines.append("🔗 点击查看完整日报")
        lines.append("(GitHub Pages 链接将在部署后提供)")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ 日报生成通知失败: {e}"


if __name__ == "__main__":
    print(format_notification())
