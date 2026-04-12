"""
AI Daily Brief - Main Entry Point

Usage:
    python main.py                    # Fetch and generate today's newsletter
    python main.py --notify           # Also send QQ notification
    python main.py --days 3           # Fetch last 3 days
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetcher import ContentFetcher
from generator import HTMLGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_newsletter(days_back: int = 1, notify: bool = False) -> dict:
    """Generate the daily newsletter"""
    
    logger.info(f"🚀 Starting AI Daily Brief generation (days_back={days_back})")
    
    # Fetch content
    async with ContentFetcher("config/sources.yaml") as fetcher:
        articles = await fetcher.fetch_all(days_back=days_back)
        categories = fetcher.categories
    
    if not articles:
        logger.warning("⚠️ No articles fetched!")
        return {"success": False, "error": "No articles fetched"}
    
    logger.info(f"✅ Fetched {len(articles)} articles from {len(set(a.source_name for a in articles))} sources")
    
    # Generate HTML
    generator = HTMLGenerator("templates", "dist")
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    
    # Generate dated version for archive
    html = generator.generate(articles, categories, date=today)
    dated_path = generator.save(html, f"{date_str}.html")
    
    # Also save as index.html (latest)
    output_path = generator.save(html, "index.html")
    
    # Generate history index page
    generator.generate_history_index()
    
    # Also save JSON for potential API use
    json_path = Path("dist") / "articles.json"
    json_path.write_text(
        json.dumps([a.to_dict() for a in articles], ensure_ascii=False, indent=2, default=str),
        encoding='utf-8'
    )
    
    logger.info(f"✅ Generated newsletter: {output_path}")
    
    # Build summary
    by_category = {}
    for a in articles:
        cat = a.category
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += 1
    
    result = {
        "success": True,
        "total_articles": len(articles),
        "categories": by_category,
        "sources": list(set(a.source_name for a in articles)),
        "output_path": str(output_path),
        "generated_at": datetime.now().isoformat(),
    }
    
    # Save summary
    summary_path = Path("dist") / "summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # Send notification if requested
    if notify:
        await send_notification(result)
    
    return result


async def send_notification(result: dict):
    """Send QQ notification"""
    try:
        # This will be called from OpenClaw
        # The actual message sending is handled by OpenClaw's message tool
        print(f"NOTIFY:AI日报已生成 | 共{result['total_articles']}篇文章 | 来源: {', '.join(result['sources'][:5])}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def main():
    parser = argparse.ArgumentParser(description="AI Daily Brief Generator")
    parser.add_argument("--days", type=int, default=1, help="Number of days to fetch")
    parser.add_argument("--notify", action="store_true", help="Send notification after generation")
    parser.add_argument("--output", type=str, default="dist", help="Output directory")
    
    args = parser.parse_args()
    
    result = asyncio.run(generate_newsletter(days_back=args.days, notify=args.notify))
    
    if result["success"]:
        print(f"\n🎉 Success! Generated {result['total_articles']} articles")
        print(f"📁 Output: {result['output_path']}")
        print(f"📊 Categories:")
        for cat, count in result['categories'].items():
            print(f"   - {cat}: {count}")
    else:
        print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
