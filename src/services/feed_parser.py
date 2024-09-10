import feedparser
from typing import List, Dict

class FeedParser:
    @staticmethod
    def parse_feed(url: str) -> List[Dict]:
        feed = feedparser.parse(url)
        return [
            {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', 'No link'),
                'summary': entry.get('summary', entry.get('description', 'No summary available')),
                'published': entry.get('published', entry.get('updated', 'No publish date'))
            }
            for entry in feed.entries
        ]