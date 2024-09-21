import argparse
import logging
import os
from datetime import datetime
from dateutil.parser import parse as parse_date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import RSS_CONFIG, DATABASE_URL
from src.database.operations import upsert_media, upsert_feed, upsert_news_with_content
from src.database.models import News, ChosenNews, InstagramPost
from src.services.feed_parser import FeedParser
from src.services.content_fetcher import ContentFetcher, ContentFetchException
from src.services.news_summarizer import NewsSummarizer
from src.services.news_chooser import NewsChooser
from src.services.instagram_post_generator import InstagramPostGenerator
from src.services.image_generator import ImageGenerator
from src.services.image_integrator import ImageIntegrator
from src.services.instagram_poster_official import InstagramPoster

# 設置日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 禁用 httpx 的日誌記錄
logging.getLogger("httpx").setLevel(logging.WARNING)

class InfoEssence:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.content_fetcher = ContentFetcher(self.SessionLocal())
        self.feed_parser = FeedParser()
        self.news_summarizer = NewsSummarizer()
        self.image_generator = ImageGenerator()
        self.instagram_post_generator = InstagramPostGenerator()
        self.image_integrator = ImageIntegrator()
        self.instagram_poster = InstagramPoster()

    def update_media_and_feeds(self):
        logging.info("開始更新 Media 和 Feed 資訊")
        with self.SessionLocal() as db:
            for media_info in RSS_CONFIG.values():
                media_id = upsert_media(db, name=media_info['name'], url=media_info['url'])
                for feed in media_info['feeds']:
                    upsert_feed(db, url=feed['url'], media_id=media_id, name=feed['name'])
        logging.info("Media 和 Feed 資訊已更新完成")

    def fetch_and_store_news(self, re_crawl=False, re_summarize=False):
        with self.SessionLocal() as db:
            for media_info in RSS_CONFIG.values():
                if media_info.get('status', '').lower() != 'active':
                    continue
                
                media_id = upsert_media(db, name=media_info['name'], url=media_info['url'])
                for feed in media_info['feeds']:
                    feed_id = upsert_feed(db, url=feed['url'], media_id=media_id, name=feed['name'])
                    entries = self.feed_parser.parse_feed(feed['url'])
                    for entry in entries:
                        try:
                            existing_news = db.query(News).filter(News.link == entry['link']).first()
                            
                            if existing_news and not re_crawl:
                                continue
                            
                            news_data = {
                                'link': entry['link'],
                                'title': entry['title'],
                                'summary': entry['summary'],
                                'published_at': parse_date(entry['published']),
                                'media_id': media_id,
                                'feed_id': feed_id,
                            }
                            
                            content = self.content_fetcher.fetch_and_save_content(entry['link'], news_data)
                            
                            if re_summarize or not existing_news:
                                ai_title, ai_summary, _ = self.news_summarizer.summarize_content(entry['title'], content)
                                db.query(News).filter(News.link == entry['link']).update({
                                    'ai_title': ai_title,
                                    'ai_summary': ai_summary
                                })
                                db.commit()
                            
                        except Exception as e:
                            logging.error(f"處理新聞時發生錯誤：{str(e)},{entry['link']}")
                            db.rollback()

    def choose_and_generate_post(self, num_chosen):
        chooser = NewsChooser(num_chosen)
        chooser.run()
                    
        # 生成 Instagram 貼文並存入資料庫
        self.instagram_post_generator.generate_instagram_posts()
        
        # 從資料庫獲取最新的 Instagram 貼文
        with self.SessionLocal() as db:
            latest_chosen_news = db.query(ChosenNews).order_by(ChosenNews.timestamp.desc()).first()
            print(latest_chosen_news)
            if latest_chosen_news:
                ig_posts = db.query(InstagramPost).filter(InstagramPost.chosen_news_id == latest_chosen_news.id).all()
                
                if ig_posts:
                    logging.info(f"成功獲取 {len(ig_posts)} 條 Instagram 貼文")
                    
                    # 生成圖片並存入資料庫
                    for post in ig_posts:
                        try:
                            self.image_generator.generate_news_image(post.news_id)
                            logging.info(f"成功為新聞 ID {post.news_id} 生成圖片")
                        except Exception as e:
                            logging.error(f"處理新聞 ID {post.news_id} 的圖片時發生錯誤：{str(e)}")
                    
                    # 整合圖片
                    self.image_integrator.integrate_ig_images()
                    logging.info("已完成圖片整合")
                else:
                    logging.warning("沒有找到任何 Instagram 貼文")
            else:
                logging.warning("沒有找到最新的已選擇新聞")

def run_complete_process():
    info_essence = InfoEssence()
    info_essence.update_media_and_feeds()
    info_essence.fetch_and_store_news()
    info_essence.choose_and_generate_post(15)
    info_essence.instagram_poster.auto_post()

def main():
    parser = argparse.ArgumentParser(description="InfoEssence: RSS Feed 處理器")
    parser.add_argument('-u', '--update', action='store_true', help='更新媒體和 Feed 資訊')
    parser.add_argument('-f', '--fetch', action='store_true', help='獲取並存儲新聞')
    parser.add_argument('--re-crawl', action='store_true', help='重新爬取所有新聞內容')
    parser.add_argument('--re-summarize', action='store_true', help='重新進行新聞總結')
    parser.add_argument('--choose', type=int, help='選擇指定數量的重要新聞並生成圖片')
    parser.add_argument('--post', action='store_true', help='自動選擇並發布新聞到 Instagram')
    parser.add_argument('--list-posts', action='store_true', help='列出最新的 Instagram 貼文')
    args = parser.parse_args()

    info_essence = InfoEssence()

    if not any(vars(args).values()):
        run_complete_process()
    else:
        if args.update:
            info_essence.update_media_and_feeds()
        if args.fetch:
            info_essence.fetch_and_store_news(re_crawl=args.re_crawl, re_summarize=args.re_summarize)
        if args.choose:
            info_essence.choose_and_generate_post(args.choose)
        if args.post:
            info_essence.instagram_poster.auto_post()
        if args.list_posts:
            list_latest_instagram_posts(info_essence.SessionLocal())

    logging.info("處理完成")

def list_latest_instagram_posts(db_session):
    with db_session() as session:
        latest_chosen_news = session.query(ChosenNews).order_by(ChosenNews.timestamp.desc()).first()
        if latest_chosen_news:
            posts = session.query(InstagramPost).filter(InstagramPost.chosen_news_id == latest_chosen_news.id).all()
            if posts:
                print(f"最新的 Instagram 貼文 (生成於 {latest_chosen_news.timestamp}):")
                for post in posts:
                    news = session.query(News).filter(News.id == post.news_id).first()
                    print(f"\n新聞 ID: {post.news_id}")
                    print(f"原始標題: {news.title}")
                    print(f"Instagram 標題: {post.ig_title}")
                    print(f"Instagram 說明: {post.ig_caption[:100]}...")  # 只顯示前100個字符
            else:
                print("沒有找到最新的 Instagram 貼文")
        else:
            print("沒有找到已選擇的新聞")

if __name__ == "__main__":
    main()