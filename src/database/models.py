import psycopg2
from psycopg2.extras import RealDictCursor
from src.config.settings import DATABASE_URL

class Media:
    def __init__(self, id, name, url, created_at=None):
        self.id = id
        self.name = name
        self.url = url
        self.created_at = created_at

    @classmethod
    def create_table(cls):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS media (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()

    @classmethod
    def insert_or_update(cls, media):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO media (name, url)
                    VALUES (%s, %s)
                    ON CONFLICT (url) DO UPDATE SET
                        name = EXCLUDED.name
                    RETURNING id, created_at
                """, (media.name, media.url))
                result = cur.fetchone()
                media.id = result['id']
                media.created_at = result['created_at']
            conn.commit()
        return media

    @classmethod
    def get_by_url(cls, url):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM media WHERE url = %s", (url,))
                result = cur.fetchone()
                if result:
                    return cls(**result)
        return None

class Feed:
    def __init__(self, url, media_id, name=None, created_at=None):
        self.url = url
        self.media_id = media_id
        self.name = name
        self.created_at = created_at

    @classmethod
    def create_table(cls):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS feeds (
                        url TEXT PRIMARY KEY,
                        media_id INTEGER REFERENCES media(id),
                        name TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()

    @classmethod
    def insert_or_update(cls, feed):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO feeds (url, media_id, name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (url) DO UPDATE SET
                        media_id = EXCLUDED.media_id,
                        name = COALESCE(EXCLUDED.name, feeds.name)
                    RETURNING created_at, name
                """, (feed.url, feed.media_id, feed.name))
                result = cur.fetchone()
                feed.created_at = result['created_at']
                feed.name = result['name']  # 更新 name，以防為 None
            conn.commit()
        return feed

    @classmethod
    def get_by_url(cls, url):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM feeds WHERE url = %s", (url,))
                result = cur.fetchone()
                if result:
                    return cls(**result)
        return None

class News:
    def __init__(self, link, title=None, summary=None, content=None, ai_title=None, ai_summary=None, media_id=None, feed_url=None, created_at=None):
        self.link = link
        self.title = title
        self.summary = summary
        self.content = content
        self.ai_title = ai_title
        self.ai_summary = ai_summary
        self.media_id = media_id
        self.feed_url = feed_url
        self.created_at = created_at

    @classmethod
    def create_table(cls):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS news (
                        link TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        summary TEXT,
                        content TEXT,
                        ai_title TEXT,
                        ai_summary TEXT,
                        media_id INTEGER REFERENCES media(id),
                        feed_url TEXT REFERENCES feeds(url),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()

    @classmethod
    def insert_or_update(cls, news):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO news (link, title, summary, content, ai_title, ai_summary, media_id, feed_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (link) DO UPDATE SET
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        content = EXCLUDED.content,
                        ai_title = EXCLUDED.ai_title,
                        ai_summary = EXCLUDED.ai_summary,
                        media_id = EXCLUDED.media_id,
                        feed_url = EXCLUDED.feed_url
                    RETURNING created_at
                """, (news.link, news.title, news.summary, news.content, news.ai_title, news.ai_summary, news.media_id, news.feed_url))
                result = cur.fetchone()
                news.created_at = result['created_at']
            conn.commit()
        return news

    @classmethod
    def get_by_link(cls, link):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM news WHERE link = %s", (link,))
                result = cur.fetchone()
                if result:
                    return cls(**result)
        return None