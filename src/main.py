import argparse
from src.config.settings import RSS_CONFIG, DATABASE_URL, update_proxies
from src.database.operations import upsert_media, upsert_feed, upsert_news
from src.database.models import News
from src.services.feed_parser import parse_feed
from src.services.content_fetcher import fetch_content, ContentFetchException, update_proxy_list
from src.services.news_summarizer import summarize_content
from src.services.news_chooser import NewsChooser
from src.services.instagram_post_generator import InstagramPostGenerator
from src.services.image_generator import generate_news_image
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import os
import logging
from dateutil.parser import parse as parse_date
from src.utils.file_utils import get_content_file_path, sanitize_filename, get_image_file_path
from src.utils.database_utils import get_news_by_id
# 設置日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 禁用 httpx 的日誌記錄
logging.getLogger("httpx").setLevel(logging.WARNING)

def ensure_directory(path):
    os.makedirs(path, exist_ok=True)

def generate_id(url):
    return hashlib.md5(url.encode()).hexdigest()

def save_content(media_name, feed_name, news_id, title, content):
    file_path = get_content_file_path(media_name, feed_name, news_id, title)
    directory = os.path.dirname(file_path)
    ensure_directory(directory)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path

def fetch_and_store_news(db, re_crawl=False, re_summarize=False):
    for media_info in RSS_CONFIG.values():
        if media_info.get('status', '').lower() != 'active':
            continue
        
        media_id = upsert_media(db, name=media_info['name'], url=media_info['url'])
        for feed in media_info['feeds']:
            feed_id = upsert_feed(db, url=feed['url'], media_id=media_id, name=feed['name'])
            entries = parse_feed(feed['url'])
            for entry in entries:
                try:
                    existing_news = db.query(News).filter(News.link == entry['link']).first()
                    
                    if existing_news and not re_crawl:
                        continue
                    
                    if re_crawl or not existing_news:
                        content = fetch_content(entry['link'])
                    else:
                        content = None
                    
                    ai_title, ai_summary = None, None
                    if re_summarize:
                        ai_title, ai_summary, _ = summarize_content(entry['title'], content)
                    
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
                        save_content(media_info['name'], feed['name'], news_id, entry['title'], content)
                    
                except Exception as e:
                    logging.error(f"處理新聞時發生錯誤：{e},{entry['link']}")

def update_media_and_feeds(db):
    logging.info("開始更新媒體和 Feed 資訊")
    for media_info in RSS_CONFIG.values():
        media_id = upsert_media(db, name=media_info['name'], url=media_info['url'])
        for feed in media_info['feeds']:
            upsert_feed(db, url=feed['url'], media_id=media_id, name=feed['name'])
    logging.info("媒體和 Feed 資訊已更新完成")

def choose_and_generate_images(db, num_chosen):
    chooser = NewsChooser(num_chosen)
    news_list = chooser.load_news()
    chosen_news = chooser.choose_important_news(news_list)
    chooser.save_chosen_news_to_csv(chosen_news)
    
    if chosen_news:
        logging.info(f"從 {len(news_list)} 條新聞中選出了 {len(chosen_news)} 條重要新聞")
        
        # 初始化 InstagramPostGenerator
        ig_generator = InstagramPostGenerator()
        
        # 生成圖片和 Instagram 內容
        ig_posts = []
        for item in chosen_news:
            try:
                news_data = get_news_by_id(item.id)
                existing_image_path = get_image_file_path(news_data['media_name'], news_data['feed_name'], news_data['id'], news_data['title'])
                if os.path.exists(existing_image_path):
                    logging.info(f"新聞 ID {item.id} 的圖片已存在：{existing_image_path}")
                else:
                    image_path = generate_news_image(item.id)
                    if image_path:
                        logging.info(f"成功為新聞 ID {item.id} 生成圖片：{image_path}")
                    else:
                        logging.warning(f"無法為新聞 ID {item.id} 生成圖片")
                
                # 生成 Instagram 內容
                ig_post = ig_generator.generate_instagram_post(item.id)
                ig_posts.append(ig_post)
                logging.info(f"成功為新聞 ID {item.id} 生成 Instagram 內容")
            except Exception as e:
                logging.error(f"處理新聞 ID {item.id} 時發生錯誤：{str(e)}")
        
        # 一次性保存所有 Instagram 內容
        if ig_posts:
            save_path = ig_generator.save_instagram_posts(ig_posts)
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
    parser.add_argument('--no-summarize', action='store_true', help='不進行新聞總結')
    parser.add_argument('--choose', type=int, help='選擇指定數量的重要新聞並生成圖片')
    args = parser.parse_args()

    # 更新代理列表
    new_proxies = update_proxy_list()
    update_proxies(new_proxies)
    logging.info("代理列表已更新")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        if args.update:
            update_media_and_feeds(session)
        elif args.fetch:
            fetch_and_store_news(session, re_crawl=args.re_crawl, re_summarize=not args.no_summarize)
        elif args.choose:
            choose_and_generate_images(session, args.choose)
        else:
            logging.warning("未指定操。請使用 -u 或 --update 參數來更新媒體和 Feed 資訊，或使用 -f 或 --fetch 參數來取並存儲新聞，或使用 --choose 參數來選擇重要新聞並生成圖片")

    logging.info("處理完成")

if __name__ == "__main__":
    main()