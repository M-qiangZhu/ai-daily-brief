"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import aiohttp
import feedparser
import yaml
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a single article/news item"""
    title: str
    url: str
    summary: str
    published: datetime
    source_name: str
    source_url: str
    category: str
    author: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'url': self.url,
            'summary': self.summary,
            'published': self.published.isoformat(),
            'source_name': self.source_name,
            'source_url': self.source_url,
            'category': self.category,
            'author': self.author,
        }


class ContentFetcher:
    """Fetches content from multiple sources"""
    
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config = self._load_config(config_path)
        self.sources = self.config.get('sources', {})
        self.categories = self.config.get('categories', {})
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _load_config(self, path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {'sources': {}, 'categories': {}}
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_all(self, days_back: int = 1) -> List[Article]:
        """Fetch articles from all enabled sources"""
        tasks = []
        
        for source_id, source_config in self.sources.items():
            if not source_config.get('enabled', True):
                continue
                
            task = self._fetch_source(source_id, source_config, days_back)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Source failed: {result}")
            else:
                articles.extend(result)
        
        # Sort by published date (newest first)
        articles.sort(key=lambda x: x.published, reverse=True)
        
        return articles
    
    async def _fetch_source(self, source_id: str, config: Dict, days_back: int) -> List[Article]:
        """Fetch articles from a single source"""
        source_type = config.get('type', 'rss')
        
        try:
            if source_type == 'rss':
                return await self._fetch_rss(source_id, config, days_back)
            else:
                return await self._fetch_web(source_id, config, days_back)
        except Exception as e:
            logger.error(f"Error fetching {source_id}: {e}")
            return []
    
    async def _fetch_rss(self, source_id: str, config: Dict, days_back: int) -> List[Article]:
        """Fetch from RSS feed"""
        rss_url = config.get('rss_url')
        if not rss_url:
            logger.warning(f"No RSS URL for {source_id}")
            return []
        
        # Use feedparser for RSS (it's synchronous but reliable)
        feed = await asyncio.to_thread(feedparser.parse, rss_url)
        
        if feed.bozo:
            logger.warning(f"RSS parse warning for {source_id}: {feed.bozo_exception}")
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        articles = []
        
        for entry in feed.entries[:15]:  # Limit to 15 most recent
            try:
                # Parse publication date
                published = self._parse_date(entry)
                if published and published < cutoff_date:
                    continue
                
                url = entry.get('link', '')
                summary = self._extract_summary(entry)
                
                # If no summary from RSS, try to fetch from URL
                if not summary or len(summary) < 50:
                    summary = await self._fetch_article_summary(url)
                
                article = Article(
                    title=self._clean_text(entry.get('title', 'Untitled')),
                    url=url,
                    summary=summary,
                    published=published or datetime.now(),
                    source_name=config.get('name', source_id),
                    source_url=config.get('url', ''),
                    category=config.get('category', 'unknown'),
                    author=entry.get('author'),
                )
                articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing entry from {source_id}: {e}")
                continue
        
        logger.info(f"Fetched {len(articles)} articles from {source_id}")
        return articles
    
    async def _fetch_web(self, source_id: str, config: Dict, days_back: int) -> List[Article]:
        """Fetch by scraping webpage using jina.ai for content extraction"""
        url = config.get('url')
        if not url or not self.session:
            return []
        
        articles = []
        
        # Try jina.ai first for better content extraction
        try:
            jina_url = f"https://r.jina.ai/{url}"
            async with self.session.get(jina_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    text = await response.text()
                    # Parse jina.ai output (title and content)
                    lines = text.split('\n')
                    title = ''
                    content_lines = []
                    
                    for line in lines:
                        if line.startswith('Title: '):
                            title = line[7:].strip()
                        elif line and not line.startswith('URL:') and not line.startswith('---'):
                            content_lines.append(line)
                    
                    if title and content_lines:
                        summary = '\n'.join(content_lines)[:400]
                        articles.append(Article(
                            title=self._clean_text(title),
                            url=url,
                            summary=summary,
                            published=datetime.now(),
                            source_name=config.get('name', source_id),
                            source_url=url,
                            category=config.get('category', 'unknown'),
                        ))
                        logger.info(f"Fetched {len(articles)} articles from {source_id} via jina.ai")
                        return articles
        except Exception as e:
            logger.debug(f"jina.ai fetch failed for {source_id}: {e}")
        
        # Fallback to direct scraping
        try:
            async with self.session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {source_id}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                # Look for common article patterns
                article_selectors = [
                    'article', '.post', '.entry', '.blog-post',
                    '[class*="article"]', '[class*="post"]', '.card'
                ]
                
                for selector in article_selectors:
                    elements = soup.select(selector)
                    if elements:
                        for elem in elements[:5]:
                            article = self._parse_article_element(elem, config)
                            if article:
                                articles.append(article)
                        break
                
                # If no articles found, try to get page title as single article
                if not articles:
                    title_elem = soup.find('title')
                    if title_elem:
                        articles.append(Article(
                            title=self._clean_text(title_elem.get_text()),
                            url=url,
                            summary="点击查看官网最新内容",
                            published=datetime.now(),
                            source_name=config.get('name', source_id),
                            source_url=url,
                            category=config.get('category', 'unknown'),
                        ))
                
                return articles[:5]
                
        except Exception as e:
            logger.error(f"Error scraping {source_id}: {e}")
            return []
    
    def _parse_article_element(self, elem: BeautifulSoup, config: Dict) -> Optional[Article]:
        """Parse a single article element from HTML"""
        try:
            # Find title
            title_elem = elem.find(['h1', 'h2', 'h3', '.title'])
            title = title_elem.get_text(strip=True) if title_elem else 'Untitled'
            
            # Find link
            link_elem = elem.find('a', href=True)
            url = link_elem['href'] if link_elem else ''
            if url and not url.startswith('http'):
                url = urljoin(config.get('url', ''), url)
            
            # Find summary
            summary_elem = elem.find(['p', '.summary', '.excerpt', '.description'])
            summary = summary_elem.get_text(strip=True)[:300] if summary_elem else ''
            
            return Article(
                title=self._clean_text(title),
                url=url,
                summary=summary,
                published=datetime.now(),
                source_name=config.get('name', 'Unknown'),
                source_url=config.get('url', ''),
                category=config.get('category', 'unknown'),
            )
        except Exception:
            return None
    
    def _parse_date(self, entry: Dict) -> Optional[datetime]:
        """Extract and parse date from RSS entry"""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if field in entry:
                try:
                    parsed = entry[field]
                    if parsed:
                        return datetime(*parsed[:6])
                except Exception:
                    continue
        
        # Try string dates
        date_strings = ['published', 'updated', 'created', 'pubDate']
        for field in date_strings:
            if field in entry:
                try:
                    from dateutil import parser
                    return parser.parse(entry[field])
                except Exception:
                    continue
        
        return None
    
    async def _fetch_article_summary(self, url: str, max_length: int = 300) -> str:
        """Fetch article page and extract summary text"""
        if not self.session or not url:
            return ''
        
        try:
            async with self.session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return ''
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                # Remove script and style elements
                for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    script.decompose()
                
                # Try to find main content
                content_selectors = [
                    'article', '[class*="article"]', '[class*="post-content"]',
                    '[class*="entry-content"]', '[class*="content"]', 'main',
                    '.post', '.entry', '.blog-post'
                ]
                
                content_text = ''
                for selector in content_selectors:
                    element = soup.select_one(selector)
                    if element:
                        content_text = element.get_text(separator=' ', strip=True)
                        if len(content_text) > 100:
                            break
                
                # Fallback to body if no content found
                if not content_text:
                    body = soup.find('body')
                    if body:
                        content_text = body.get_text(separator=' ', strip=True)
                
                # Clean and truncate
                content_text = ' '.join(content_text.split())
                
                # Skip if too short (probably not article content)
                if len(content_text) < 100:
                    return ''
                
                # Return first meaningful paragraph (not just title/author)
                sentences = content_text.split('。')
                summary_parts = []
                current_length = 0
                
                for sentence in sentences[:5]:  # Check first 5 sentences
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Meaningful sentence
                        summary_parts.append(sentence)
                        current_length += len(sentence)
                        if current_length >= max_length:
                            break
                
                summary = '。'.join(summary_parts) + '。' if summary_parts else content_text[:max_length] + '...'
                
                return summary[:max_length] + ('...' if len(content_text) > max_length else '')
                
        except Exception as e:
            logger.debug(f"Error fetching article summary from {url}: {e}")
            return ''
    
    def _extract_summary(self, entry: Dict) -> str:
        """Extract summary from RSS entry"""
        # Try different fields
        for field in ['summary', 'description', 'content', 'subtitle']:
            if field in entry:
                text = entry[field]
                if isinstance(text, list) and text:
                    text = text[0].get('value', str(text[0]))
                
                # Strip HTML
                soup = BeautifulSoup(str(text), 'lxml')
                text = soup.get_text(strip=True)
                
                # Limit length
                return text[:500] if len(text) > 500 else text
        
        return ''
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ''
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove common problematic characters
        text = text.replace('\x00', '')
        return text.strip()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }


async def main():
    """Test the fetcher"""
    async with ContentFetcher() as fetcher:
        articles = await fetcher.fetch_all(days_back=1)
        
        print(f"\nFetched {len(articles)} articles\n")
        
        # Group by category
        by_category = {}
        for article in articles:
            cat = article.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(article)
        
        for category, items in by_category.items():
            print(f"\n{category.upper()}: {len(items)} articles")
            for item in items[:3]:
                print(f"  - {item.title[:60]}... ({item.source_name})")


if __name__ == "__main__":
    asyncio.run(main())
