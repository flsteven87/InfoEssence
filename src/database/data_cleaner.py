from sqlalchemy import create_engine, delete, select, and_, not_, update, func, or_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from .models import News, File, InstagramPost, Published
from src.config.settings import DATABASE_URL
import argparse

class DataCleaner:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def clear_old_news(self, hours=24):
        """清除指定小時數之前的所有舊新聞及其關聯數據，包括已發布的新聞"""
        with self.SessionLocal() as db:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 獲取要刪除的所有舊新聞記錄
            old_news_ids = db.execute(
                select(News.id).where(News.published_at < cutoff_time)
            ).scalars().all()

            deleted_news = 0
            deleted_files = 0
            deleted_instagram_posts = 0
            deleted_published = 0

            # 首先解除所有相關表的外鍵約束
            db.execute(update(InstagramPost).where(InstagramPost.news_id.in_(old_news_ids)).values(news_id=None))
            db.execute(update(News).where(News.id.in_(old_news_ids)).values(md_file_id=None, png_file_id=None))

            # 刪除相關的 InstagramPost 記錄
            instagram_posts = db.execute(select(InstagramPost).where(InstagramPost.news_id.in_(old_news_ids))).scalars().all()
            for post in instagram_posts:
                if post.integrated_image_id:
                    db.execute(delete(File).where(File.id == post.integrated_image_id))
                    deleted_files += 1
                db.delete(post)
                deleted_instagram_posts += 1

            # 刪除相關的 Published 記錄
            deleted_published = db.execute(delete(Published).where(Published.news_id.in_(old_news_ids))).rowcount

            # 刪除相關的 File 記錄
            files_to_delete = db.execute(
                select(File.id).where(
                    or_(
                        File.id.in_(select(News.md_file_id).where(News.id.in_(old_news_ids))),
                        File.id.in_(select(News.png_file_id).where(News.id.in_(old_news_ids)))
                    )
                )
            ).scalars().all()
            deleted_files += db.execute(delete(File).where(File.id.in_(files_to_delete))).rowcount

            # 最後刪除 News 記錄
            deleted_news = db.execute(delete(News).where(News.id.in_(old_news_ids))).rowcount

            db.commit()

            return deleted_news, deleted_files, deleted_instagram_posts, deleted_published

def main():
    parser = argparse.ArgumentParser(description="數據清理工具")
    parser.add_argument('--clear-old', type=int, help='清除指定小時數之前的所有舊新聞（包括已發布的）')

    args = parser.parse_args()
    cleaner = DataCleaner()

    if args.clear_old:
        deleted_news, deleted_files, deleted_instagram_posts, deleted_published = cleaner.clear_old_news(args.clear_old)
        print(f"已清除 {deleted_news} 條舊新聞、{deleted_files} 個關聯文件、{deleted_instagram_posts} 個 Instagram 貼文和 {deleted_published} 條已發布記錄")
    else:
        print("請指定要執行的操作。使用 -h 或 --help 查看可用選項。")

if __name__ == "__main__":
    main()

# 清除 48 小時前的舊新聞（保留已發布的）
# python -m src.database.data_cleaner --clear-old 48