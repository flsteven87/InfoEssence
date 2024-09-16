import argparse
import logging
import os
from datetime import datetime
from dateutil.parser import parse as parse_date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import RSS_CONFIG, DATABASE_URL
from src.database.operations import upsert_media, upsert_feed, upsert_news
from src.database.models import News
from src.services.feed_parser import FeedParser
from src.services.content_fetcher import ContentFetcher, ContentFetchException
from src.services.news_summarizer import NewsSummarizer
from src.services.news_chooser import NewsChooser
from src.services.instagram_post_generator import InstagramPostGenerator
from src.services.image_generator import ImageGenerator
from src.services.image_integrator import ImageIntegrator
from src.utils.file_utils import get_content_file_path, get_image_file_path
from src.utils.database_utils import get_news_by_id
from src.services.instagram_poster import InstagramPoster

# 設置日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 禁用 httpx 的日誌記錄
logging.getLogger("httpx").setLevel(logging.WARNING)

class InfoEssence:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.content_fetcher = ContentFetcher()
        self.feed_parser = FeedParser()
        self.news_summarizer = NewsSummarizer()
        self.image_generator = ImageGenerator()
        self.instagram_post_generator = InstagramPostGenerator()
        self.image_integrator = ImageIntegrator()
        self.instagram_poster = InstagramPoster()

    @staticmethod
    def ensure_directory(path):
        os.makedirs(path, exist_ok=True)

    def save_content(self, media_name, feed_name, news_id, title, content):
        file_path = get_content_file_path(media_name, feed_name, news_id, title)
        directory = os.path.dirname(file_path)
        self.ensure_directory(directory)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path

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
                            
                            if re_crawl or not existing_news:
                                content = self.content_fetcher.fetch_content(entry['link'])
                            else:
                                content = None
                            
                            ai_title, ai_summary = None, None
                            if re_summarize:
                                ai_title, ai_summary, _ = self.news_summarizer.summarize_content(entry['title'], content)
                            
                            published_at = parse_date(entry['published'])
                            
                            news_id = upsert_news(
                                db,
                                link=entry['link'],
                                title=entry['title'],
                                summary=entry['summary'],
                                ai_title=ai_title,
                                ai_summary=ai_summary,
                                published_at=published_at,
                                media_id=media_id,
                                feed_id=feed_id,
                                update_ai_fields=re_summarize
                            )
                            
                            if content:
                                self.save_content(media_info['name'], feed['name'], news_id, entry['title'], content)
                            
                        except ContentFetchException as e:
                            logging.error(f"獲取內容時發生錯誤：{e},{entry['link']}")
                        except Exception as e:
                            logging.error(f"處理新聞時發生錯誤：{e},{entry['link']}")

    def update_media_and_feeds(self):
        logging.info("開始更新媒體和 Feed 資訊")
        with self.SessionLocal() as db:
            for media_info in RSS_CONFIG.values():
                media_id = upsert_media(db, name=media_info['name'], url=media_info['url'])
                for feed in media_info['feeds']:
                    upsert_feed(db, url=feed['url'], media_id=media_id, name=feed['name'])
        logging.info("媒體和 Feed 資訊已更新完成")

    def choose_generate_and_post(self, num_chosen):
        chooser = NewsChooser(num_chosen)
        news_list = chooser.load_news()
        chosen_news = chooser.choose_important_news(news_list)
        chooser.save_chosen_news_to_csv(chosen_news)
        
        if chosen_news:
            logging.info(f"從 {len(news_list)} 條新聞中選出了 {len(chosen_news)} 條重要新聞")
            
            ig_posts = []
            for item in chosen_news:
                try:
                    news_data = get_news_by_id(item.id)
                    existing_image_path = get_image_file_path(news_data['media_name'], news_data['feed_name'], news_data['id'], news_data['title'])
                    if os.path.exists(existing_image_path):
                        logging.info(f"新聞 ID {item.id} 的圖片已存在：{existing_image_path}")
                    else:
                        image_path = self.image_generator.generate_news_image(item.id)
                        if image_path:
                            logging.info(f"成功為新聞 ID {item.id} 生成圖片：{image_path}")
                        else:
                            logging.warning(f"無法為新聞 ID {item.id} 生成圖片")
                    
                    ig_post = self.instagram_post_generator.generate_instagram_post(item.id)
                    ig_posts.append(ig_post)
                    logging.info(f"成功為新聞 ID {item.id} 生成 Instagram 內容")
                except Exception as e:
                    logging.error(f"處理新聞 ID {item.id} 時發生錯誤：{str(e)}")
            
            # 確保所有圖片都已生成後，再進行整合
            self.image_integrator.integrate_ig_images()
            logging.info("已完成圖片整合")

            if ig_posts:
                save_path = self.instagram_post_generator.save_instagram_posts(ig_posts)
                logging.info(f"成功保存 {len(ig_posts)} 條 Instagram 內容：{save_path}")
            else:
                logging.warning("沒有生成任何 Instagram 內容")

        else:
            logging.warning("沒有選出任何新聞")

def main():
    parser = argparse.ArgumentParser(description="InfoEssence: RSS Feed 處理器")
    parser.add_argument('-u', '--update', action='store_true', help='更新媒體和 Feed 資訊')
    parser.add_argument('-f', '--fetch', action='store_true', help='獲取並存儲新聞')
    parser.add_argument('--re-crawl', action='store_true', help='重新爬取所有新聞內容')
    parser.add_argument('--re-summarize', action='store_true', help='重新進行新聞總結')
    parser.add_argument('--choose', type=int, help='選擇指定數量的重要新聞並生成圖片')
    parser.add_argument('--post', action='store_true', help='自動選擇並發布新聞到 Instagram')
    args = parser.parse_args()

    info_essence = InfoEssence()

    new_proxies = info_essence.content_fetcher.update_proxy_list()
    logging.info("代理列表已更新")

    # 檢查是否有任何參數被設置
    if not any(vars(args).values()):
        # 如果沒有參數，執行完整流程
        info_essence.update_media_and_feeds()
        info_essence.fetch_and_store_news()
        info_essence.choose_generate_and_post(5)
    else:
        if args.update:
            info_essence.update_media_and_feeds()
        if args.fetch:
            info_essence.fetch_and_store_news(re_crawl=args.re_crawl, re_summarize=args.re_summarize)
        if args.choose:
            info_essence.choose_generate_and_post(args.choose)
        if args.post:
            info_essence.instagram_poster.post_auto_selected_news()

    logging.info("處理完成")

if __name__ == "__main__":
    main()