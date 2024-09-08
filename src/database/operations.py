from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker
from .models import Media, Feed, News, Base
from datetime import datetime
from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL

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

def upsert_news(db: Session, link: str, title: str, summary: str, ai_title: str, ai_summary: str, published_at: datetime, media_id: int, feed_id: int, update_ai_fields: bool = True) -> int:
    stmt = insert(News).values(
        link=link,
        title=title,
        summary=summary,
        ai_title=ai_title,
        ai_summary=ai_summary,
        published_at=published_at,
        media_id=media_id,
        feed_id=feed_id
    )
    
    set_dict = {
        'title': stmt.excluded.title,
        'summary': stmt.excluded.summary,
        'published_at': stmt.excluded.published_at,
        'media_id': stmt.excluded.media_id,
        'feed_id': stmt.excluded.feed_id
    }
    
    if update_ai_fields:
        set_dict.update({
            'ai_title': stmt.excluded.ai_title,
            'ai_summary': stmt.excluded.ai_summary
        })
    
    stmt = stmt.on_conflict_do_update(
        index_elements=['link'],
        set_=set_dict
    )
    
    result = db.execute(stmt)
    db.commit()
    return result.inserted_primary_key[0]

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("數據庫已初始化")

def truncate_tables(db: Session):
    tables = ['news', 'feeds', 'media']
    for table in tables:
        db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    db.commit()
    print("所有表格已清空")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="數據庫操作工具")
    parser.add_argument('action', choices=['init', 'truncate'], help="選擇操作：init（初始化數據庫）或 truncate（清空表格）")
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_db()
    elif args.action == 'truncate':
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as db:
            truncate_tables(db)
    
    print(f"{args.action} 操作完成")
