from src.database.models import News, Media, Feed

def initialize_database():
    Media.create_table()
    Feed.create_table()
    News.create_table()

def save_media(name, url):
    media = Media(id=None, name=name, url=url)
    return Media.insert_or_update(media)

def save_feed(url, media_id, name):
    feed = Feed(url=url, media_id=media_id, name=name)
    return Feed.insert_or_update(feed)

def save_news(link, title, summary, content, ai_title, ai_summary, media_id, feed_url):
    news = News(
        link=link,
        title=title,
        summary=summary,
        content=content,
        ai_title=ai_title,
        ai_summary=ai_summary,
        media_id=media_id,
        feed_url=feed_url
    )
    return News.insert_or_update(news)

def get_news(link):
    return News.get_by_link(link)

def get_media_by_url(url):
    return Media.get_by_url(url)

def get_feed_by_url(url):
    return Feed.get_by_url(url)