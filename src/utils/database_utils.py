from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import create_engine, desc
from src.database.models import ChosenNews, InstagramPost, News, File, Published
from src.config.settings import DATABASE_URL
from datetime import datetime, timedelta

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_news_by_id(news_id: int) -> News:
    with SessionLocal() as session:
        return session.query(News).options(joinedload(News.md_file)).filter(News.id == news_id).first()

def get_latest_chosen_news():
    with SessionLocal() as session:
        return session.query(ChosenNews).order_by(desc(ChosenNews.timestamp)).first()

def get_instagram_posts(chosen_news_id):
    with SessionLocal() as session:
        return session.query(InstagramPost).filter(InstagramPost.chosen_news_id == chosen_news_id).all()

def get_news_image(news_id):
    with SessionLocal() as session:
        news = session.query(News).filter(News.id == news_id).first()
        if news and news.png_file_id:
            file = session.query(File).filter(File.id == news.png_file_id).first()
            if file:
                return file.data
    return None

def get_published_instagram_post_ids():
    with SessionLocal() as session:
        published_posts = session.query(Published.instagram_post_id).all()
        return [post.instagram_post_id for post in published_posts]

def get_published_news_ids():
    with SessionLocal() as session:
        published_news = session.query(Published.news_id).distinct().all()
        return [news.news_id for news in published_news]

def get_recent_published_instagram_posts(hours=8):
    with SessionLocal() as session:
        n_hours_ago = datetime.utcnow() - timedelta(hours=hours)
        recent_published = session.query(Published).filter(Published.published_at >= n_hours_ago).all()

        post_ids = [pub.instagram_post_id for pub in recent_published]
        posts = session.query(InstagramPost).filter(InstagramPost.id.in_(post_ids)).all()

        return [{"id": post.id, "ig_title": post.ig_title, "ig_caption": post.ig_caption} for post in posts]