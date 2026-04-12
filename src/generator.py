"""
AI Daily Brief - HTML Generator
Generates the newsletter HTML page
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader

from fetcher import Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLGenerator:
    """Generates static HTML newsletter from articles"""
    
    def __init__(self, template_dir: str = "templates", output_dir: str = "dist"):
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        
        # Setup Jinja2
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )
        
        # Add custom filters
        self.env.filters['format_date'] = self._format_date
        self.env.filters['format_time'] = self._format_time
        
    def generate(self, articles: List[Article], categories: Dict[str, str], date: datetime = None) -> str:
        """Generate HTML newsletter"""
        
        if date is None:
            date = datetime.now()
        
        # Group articles by category
        grouped = self._group_by_category(articles)
        
        # Calculate stats
        stats = {
            'total': len(articles),
            'categories': len(grouped),
            'sources': len(set(a.source_name for a in articles)),
            'generated_at': datetime.now(),
        }
        
        # Prepare template data
        template_data = {
            'title': f"AI Daily Brief - {date.strftime('%Y-%m-%d')}",
            'date': date,
            'stats': stats,
            'categories': categories,
            'grouped_articles': grouped,
            'articles_json': json.dumps([a.to_dict() for a in articles], ensure_ascii=False, default=str),
            'history_page': 'history.html',
        }
        
        # Render template
        template = self.env.get_template('newsletter.html.j2')
        html = template.render(**template_data)
        
        return html
    
    def save(self, html: str, filename: str = "index.html"):
        """Save HTML to output directory"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = self.output_dir / filename
        output_path.write_text(html, encoding='utf-8')
        
        logger.info(f"Saved HTML to {output_path}")
        return output_path
    
    def generate_history_index(self):
        """Generate history index page listing all archived newsletters"""
        
        # Find all dated HTML files
        history_files = []
        for html_file in self.output_dir.glob("*.html"):
            filename = html_file.name
            if filename == "index.html" or filename == "history.html":
                continue
            # Try to parse date from filename (YYYY-MM-DD.html)
            try:
                date_str = filename.replace('.html', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                history_files.append({
                    'date': file_date,
                    'filename': filename,
                    'display_date': file_date.strftime('%Y年%m月%d日'),
                    'weekday': ['周一','周二','周三','周四','周五','周六','周日'][file_date.weekday()]
                })
            except ValueError:
                continue
        
        # Sort by date descending
        history_files.sort(key=lambda x: x['date'], reverse=True)
        
        # Generate history page HTML
        template = self.env.get_template('history.html.j2')
        html = template.render(
            title="AI Daily Brief - 历史归档",
            history_files=history_files,
            total_count=len(history_files)
        )
        
        history_path = self.output_dir / "history.html"
        history_path.write_text(html, encoding='utf-8')
        logger.info(f"Saved history index to {history_path}")
        return history_path
    
    def _group_by_category(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """Group articles by category"""
        grouped = {}
        for article in articles:
            cat = article.category
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(article)
        
        # Sort by published date within each category
        for cat in grouped:
            grouped[cat].sort(key=lambda x: x.published, reverse=True)
        
        return grouped
    
    @staticmethod
    def _format_date(value: datetime) -> str:
        """Format date for display"""
        return value.strftime("%Y-%m-%d")
    
    @staticmethod
    def _format_time(value: datetime) -> str:
        """Format time for display"""
        return value.strftime("%H:%M")


def main():
    """Test generator"""
    from fetcher import ContentFetcher
    import asyncio
    
    async def test():
        async with ContentFetcher() as fetcher:
            articles = await fetcher.fetch_all(days_back=1)
            
            generator = HTMLGenerator()
            html = generator.generate(articles, fetcher.categories)
            generator.save(html)
            
            print(f"Generated newsletter with {len(articles)} articles")
    
    asyncio.run(test())


if __name__ == "__main__":
    main()
