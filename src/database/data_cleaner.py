from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from .models import News, Media, Feed
from src.config.settings import DATABASE_URL
from src.utils.file_utils import get_content_file_path, sanitize_filename
import logging
import os
import shutil
import argparse

class DataCleaner:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def clear_old_news(self, days=2):
        """清除指定天數之前的舊新聞及其對應的 .md 文件"""
        with self.SessionLocal() as db:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 獲取要刪除的新聞記錄
            old_news = db.execute(
                select(News.id, News.title, Media.name.label('media_name'), Feed.name.label('feed_name'))
                .join(Media, News.media_id == Media.id)
                .join(Feed, News.feed_id == Feed.id)
                .where(News.published_at < cutoff_date)
            ).fetchall()

            # 刪除對應的 .md 文件
            deleted_files = 0
            for news in old_news:
                file_path = get_content_file_path(
                    media_name=news.media_name,
                    feed_name=news.feed_name,
                    news_id=news.id,
                    title=news.title
                )
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files += 1

            # 從數據庫中刪除舊新聞
            stmt = delete(News).where(News.published_at < cutoff_date)
            result = db.execute(stmt)
            db.commit()

            return result.rowcount, deleted_files

    def clear_all_news(self):
        """清除所有新聞及其對應的 .md 文件"""
        with self.SessionLocal() as db:
            # 獲取所有新聞記錄
            all_news = db.execute(
                select(News.id, News.title, Media.name.label('media_name'), Feed.name.label('feed_name'))
                .join(Media, News.media_id == Media.id)
                .join(Feed, News.feed_id == Feed.id)
            ).fetchall()

            # 刪除所有對應的 .md 文件
            deleted_files = 0
            for news in all_news:
                file_path = get_content_file_path(
                    media_name=news.media_name,
                    feed_name=news.feed_name,
                    news_id=news.id,
                    title=news.title
                )
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files += 1

            # 從數據庫中刪除所有新聞
            stmt = delete(News)
            result = db.execute(stmt)
            db.commit()

            return result.rowcount, deleted_files

    def reset_database(self):
        """重置整個數據庫（謹慎使用）"""
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        return "數據庫已重置"

    def clear_folders(self):
        """清除指定文件夾中的所有文件"""
        folders_to_clean = ['./chosen_news', './image', './instagram_posts', ]
        total_removed = 0

        for folder in folders_to_clean:
            if not os.path.exists(folder):
                print(f"文件夾不存在: {folder}")
                continue

            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)
                    total_removed += 1
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    if not os.listdir(dir_path):  # 如果目錄為空
                        os.rmdir(dir_path)

        return total_removed

    def clear_all_data(self):
        """清除所有數據，包括數據庫和文件夾"""
        deleted_news, deleted_md_files = self.clear_all_news()
        removed_files = self.clear_folders()
        return f"已清除 {deleted_news} 條新聞記錄，{deleted_md_files} 個 .md 文件，並清空所有相關文件夾（額外刪除了 {removed_files} 個文件）"

def main():
    parser = argparse.ArgumentParser(description="數據清理工具")
    parser.add_argument('--clear-old', type=int, help='清除指定天數之前的舊新聞')
    parser.add_argument('--clear-folders', action='store_true', help='清除所有指定文件夾中的文件')
    parser.add_argument('--clear-all', action='store_true', help='清除所有數據（數據庫和文件夾）')
    parser.add_argument('--reset-db', action='store_true', help='重置整個數據庫')

    args = parser.parse_args()
    cleaner = DataCleaner()

    if args.clear_old:
        deleted_old, deleted_files = cleaner.clear_old_news(args.clear_old)
        print(f"已清除 {deleted_old} 條舊新聞和 {deleted_files} 個對應的 .md 文件")

    if args.clear_folders:
        removed_files = cleaner.clear_folders()
        print(f"已清除 {removed_files} 個文件")

    if args.clear_all:
        result = cleaner.clear_all_data()
        print(result)

    if args.reset_db:
        result = cleaner.reset_database()
        print(result)

    if not any(vars(args).values()):
        print("請指定要執行的操作。使用 -h 或 --help 查看可用選項。")

if __name__ == "__main__":
    main()


# 清除 5 天前的舊新聞
# python -m src.database.data_cleaner --clear-old 5

# 清除所有指定文件夾中的文件
# python -m src.database.data_cleaner --clear-folders

# 清除所有數據（數據庫和文件夾）
# python -m src.database.data_cleaner --clear-all

# 重置整個數據庫
# python -m src.database.data_cleaner --reset-db