from sqlalchemy import create_engine, delete, select, and_, not_, update
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
        """清除指定小時數之前的舊新聞及其關聯數據，但保留已發布的新聞"""
        with self.SessionLocal() as db:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 獲取要刪除的新聞記錄（排除已發布的新聞）
            old_news = db.execute(
                select(News).where(
                    and_(
                        News.published_at < cutoff_time,
                        not_(News.id.in_(select(Published.news_id)))
                    )
                )
            ).scalars().all()

            deleted_news = 0
            deleted_files = 0
            deleted_instagram_posts = 0

            for news in old_news:
                # 刪除關聯的 InstagramPost 和其整合圖片
                if news.instagram_post:
                    if news.instagram_post.integrated_image_id:
                        db.execute(update(InstagramPost).where(InstagramPost.id == news.instagram_post.id).values(integrated_image_id=None))
                        db.execute(delete(File).where(File.id == news.instagram_post.integrated_image_id))
                        deleted_files += 1
                    db.delete(news.instagram_post)
                    deleted_instagram_posts += 1

                # 解除 News 對 File 的引用
                if news.md_file_id:
                    db.execute(update(News).where(News.id == news.id).values(md_file_id=None))
                if news.png_file_id:
                    db.execute(update(News).where(News.id == news.id).values(png_file_id=None))

                # 刪除關聯的 md 和 png 文件
                if news.md_file_id:
                    db.execute(delete(File).where(File.id == news.md_file_id))
                    deleted_files += 1
                if news.png_file_id:
                    db.execute(delete(File).where(File.id == news.png_file_id))
                    deleted_files += 1

                # 刪除新聞本身
                db.delete(news)
                deleted_news += 1

            db.commit()

            return deleted_news, deleted_files, deleted_instagram_posts

def main():
    parser = argparse.ArgumentParser(description="數據清理工具")
    parser.add_argument('--clear-old', type=int, help='清除指定小時數之前的舊新聞（保留已發布的）')

    args = parser.parse_args()
    cleaner = DataCleaner()

    if args.clear_old:
        deleted_news, deleted_files, deleted_instagram_posts = cleaner.clear_old_news(args.clear_old)
        print(f"已清除 {deleted_news} 條舊新聞、{deleted_files} 個關聯文件和 {deleted_instagram_posts} 個 Instagram 貼文")
    else:
        print("請指定要執行的操作。使用 -h 或 --help 查看可用選項。")

if __name__ == "__main__":
    main()

# 清除 48 小時前的舊新聞（保留已發布的）
# python -m src.database.data_cleaner --clear-old 48