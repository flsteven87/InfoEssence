from sqlalchemy import create_engine, delete, select, and_, not_, update, func, or_
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from .models import News, File, InstagramPost, Published, Story
from src.config.settings import DATABASE_URL
import argparse
import logging
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCleaner:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def clear_old_news(self, hours=24):
        """清除指定小時數之前的所有舊新聞及其關聯數據"""
        with self.SessionLocal() as db:
            db.autoflush = False  # 禁用自動刷新
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            deleted_news = 0
            deleted_files = 0
            deleted_instagram_posts = 0
            deleted_published = 0
            deleted_stories = 0

            # 獲取要刪除的所有舊新聞記錄
            old_news = db.execute(
                select(News).where(News.published_at < cutoff_time)
            ).scalars().all()

            old_news_ids = [news.id for news in old_news]

            # 處理 Instagram 貼文
            instagram_posts = db.execute(
                select(InstagramPost).where(or_(
                    InstagramPost.news_id.in_(old_news_ids),
                    InstagramPost.news_id.notin_(select(News.id))
                ))
            ).scalars().all()

            for post in instagram_posts:
                db.delete(post)
                deleted_instagram_posts += 1

            # 處理 Published 記錄
            published_records = db.execute(
                select(Published).where(Published.news_id.in_(old_news_ids))
            ).scalars().all()

            for record in published_records:
                db.delete(record)
                deleted_published += 1

            # 處理 Story 記錄
            # 注意：這裡我們移除了 Story 的處理，因為它似乎沒有 news_id 字段
            # 如果 Story 與 News 有其他關聯方式，請相應地修改這部分代碼

            # 刪除新聞記錄
            for news in old_news:
                db.delete(news)
                deleted_news += 1

            db.commit()

            # 查找並刪除孤立的文件
            orphaned_files = db.execute(
                select(File).where(
                    and_(
                        not_(File.id.in_(select(News.md_file_id).where(News.md_file_id.isnot(None)))),
                        not_(File.id.in_(select(News.png_file_id).where(News.png_file_id.isnot(None)))),
                        not_(File.id.in_(select(InstagramPost.integrated_image_id).where(InstagramPost.integrated_image_id.isnot(None)))),
                        not_(File.id.in_(select(Published.instagram_post_id).where(Published.instagram_post_id.isnot(None))))
                    )
                )
            ).scalars().all()

            for file in orphaned_files:
                db.delete(file)
                deleted_files += 1

            db.commit()

            logger.info(f"已清除 {deleted_news} 條舊新聞、{deleted_files} 個關聯文件、{deleted_instagram_posts} 個 Instagram 貼文、{deleted_published} 條已發布記錄和 {deleted_stories} 條故事")

            return deleted_news, deleted_files, deleted_instagram_posts, deleted_published, deleted_stories

def main():
    parser = argparse.ArgumentParser(description="數據清理工具")
    parser.add_argument('--clear-old', type=int, help='清除指定小時數之前的所有舊新聞（括已發布的）')

    args = parser.parse_args()
    cleaner = DataCleaner()

    if args.clear_old:
        deleted_news, deleted_files, deleted_instagram_posts, deleted_published, deleted_stories = cleaner.clear_old_news(args.clear_old)
        print(f"已清除 {deleted_news} 條舊新聞、{deleted_files} 個關聯文件、{deleted_instagram_posts} 個 Instagram 貼文和 {deleted_published} 條已發布記錄")
    else:
        print("請指定要執行的操作。使用 -h 或 --help 查看可用選項。")

if __name__ == "__main__":
    main()

# 清除 48 小時前的舊新聞（保留已發布的）
# python -m src.database.data_cleaner --clear-old 48