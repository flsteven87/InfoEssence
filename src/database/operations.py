from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .models import Media, Feed, News, File, InstagramPost
import hashlib
import logging
from sqlalchemy.exc import SQLAlchemyError

def upsert_media(db: Session, name: str, url: str) -> int:
    stmt = insert(Media).values(name=name, url=url)
    stmt = stmt.on_conflict_do_update(
        index_elements=['url'],
        set_=dict(name=stmt.excluded.name)
    )
    result = db.execute(stmt)
    db.commit()
    return result.inserted_primary_key[0]

def upsert_feed(db: Session, url: str, media_id: int, name: str) -> int:
    stmt = insert(Feed).values(url=url, media_id=media_id, name=name)
    stmt = stmt.on_conflict_do_update(
        index_elements=['url'],
        set_=dict(media_id=stmt.excluded.media_id, name=stmt.excluded.name)
    )
    result = db.execute(stmt)
    db.commit()
    return result.inserted_primary_key[0]

def upsert_news_with_content(db: Session, news_data: dict, md_content: str) -> int:
    try:
        url_hash = hashlib.md5(news_data['link'].encode()).hexdigest()
        
        md_file = File(
            filename=f"{url_hash}.md",
            content_type="text/markdown",
            data=md_content.encode('utf-8')
        )
        db.add(md_file)
        db.flush()

        news_values = {
            'link': news_data['link'],
            'title': news_data['title'],
            'summary': news_data['summary'],
            'ai_title': news_data.get('ai_title'),
            'ai_summary': news_data.get('ai_summary'),
            'published_at': news_data['published_at'],
            'media_id': news_data['media_id'],
            'feed_id': news_data['feed_id'],
            'md_file_id': md_file.id
        }

        stmt = insert(News).values(**news_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=['link'],
            set_={
                'title': stmt.excluded.title,
                'summary': stmt.excluded.summary,
                'ai_title': stmt.excluded.ai_title,
                'ai_summary': stmt.excluded.ai_summary,
                'published_at': stmt.excluded.published_at,
                'media_id': stmt.excluded.media_id,
                'feed_id': stmt.excluded.feed_id,
                'md_file_id': stmt.excluded.md_file_id
            }
        )
        
        result = db.execute(stmt)
        db.commit()
        return result.inserted_primary_key[0]
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"數據庫操作錯誤：{str(e)}")
        raise

def upsert_news_with_png(db: Session, news_id: int, png_content: bytes) -> int:
    try:
        news = db.query(News).filter(News.id == news_id).first()
        if not news:
            raise ValueError(f"找不到 ID 為 {news_id} 的新聞記錄")

        url_hash = hashlib.md5(news.link.encode()).hexdigest()
        
        png_file = File(
            filename=f"{url_hash}.png",
            content_type="image/png",
            data=png_content
        )
        db.add(png_file)
        db.flush()

        news.png_file_id = png_file.id
        db.commit()

        return news.id
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"數據庫操作錯誤：{str(e)}")
        raise

def upsert_file(db: Session, filename: str, content_type: str, data: bytes) -> int:
    file = db.query(File).filter(File.filename == filename).first()
    if file:
        file.content_type = content_type
        file.data = data
    else:
        file = File(
            filename=filename,
            content_type=content_type,
            data=data
        )
        db.add(file)
    db.commit()
    db.refresh(file)
    return file.id

def upsert_ig_post_with_png(db: Session, post_id: int, png_content: bytes) -> int:
    try:
        ig_post = db.query(InstagramPost).filter(InstagramPost.id == post_id).first()
        if not ig_post:
            raise ValueError(f"找不到 ID 為 {post_id} 的 Instagram 貼文記錄")

        # 使用貼文 ID 和新聞 ID 來生成唯一的文件名
        filename = f"integrated_{ig_post.news_id}_{post_id}.png"
        
        png_file = File(
            filename=filename,
            content_type="image/png",
            data=png_content
        )
        db.add(png_file)
        db.flush()

        ig_post.integrated_image_id = png_file.id
        db.commit()

        return ig_post.id
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"數據庫操作錯誤：{str(e)}")
        raise
