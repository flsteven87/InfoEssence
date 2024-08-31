import argparse
from src.config.settings import RSS_CONFIG
from src.services.feed_parser import parse_feed
from src.services.content_fetcher import fetch_content, ContentFetchException
from src.services.summarizer import summarize_content
from src.database.operations import initialize_database, save_news, get_news, save_media, save_feed, get_media_by_url, get_feed_by_url

def process_feed(feed_url: str, media_name: str, media_url: str, feed_name: str):
    media = get_media_by_url(media_url)
    if not media:
        media = save_media(name=media_name, url=media_url)
    
    feed = get_feed_by_url(feed_url)
    if not feed:
        feed = save_feed(url=feed_url, media_id=media.id, name=feed_name)

    entries = parse_feed(feed_url)
    for entry in entries:
        try:
            # print(f"處理文章: {entry['title']}")
            
            existing_news = get_news(entry['link'])
            if existing_news:
                print(f"文章已存在，跳過: {entry['title']}")
                continue

            content = fetch_content(entry['link'])
            if not content:
                print(f"警: 無法獲取內容，跳過文章 {entry['title']}")
                continue

            ai_title, ai_summary = summarize_content(entry['title'], content)
            
            saved_news = save_news(
                link=entry['link'],
                title=entry['title'],
                summary=entry.get('summary', ''),
                content=content,
                ai_title=ai_title,
                ai_summary=ai_summary,
                media_id=media.id,
                feed_url=feed.url
            )
            print(f"處理成功: {saved_news.title} (連結: {saved_news.link})")
        
        except ContentFetchException as e:
            print(f"內容獲取失敗: {e}")
        except Exception as e:
            print(f"處理過程中發生錯誤: {e}")

def main():
    parser = argparse.ArgumentParser(description="InfoEssence: RSS Feed 處理器")
    parser.add_argument('-m', '--media', type=str, help='指定要處理的媒體名稱')
    args = parser.parse_args()

    print("初始化數據庫...")
    initialize_database()
    
    if args.media:
        media_to_process = [m for m in RSS_CONFIG.values() if m['name'].lower() == args.media.lower()]
        if not media_to_process:
            print(f"錯誤: 找不到指定的媒體 '{args.media}'")
            return
    else:
        media_to_process = list(RSS_CONFIG.values())  # 將 dict_values 轉換為列表

    # 顯示可用的媒體和 feed 選項
    print("可用的媒體和 feed：")
    for i, media_info in enumerate(media_to_process, 1):
        print(f"{i}. {media_info['name']}")
        for j, feed in enumerate(media_info['feeds'], 1):
            print(f"  {i}.{j} {feed['name']}")

    # 讓使用者選擇
    choice = input("請輸入要處理的媒體或 feed 編號（例如：1 或 1.2）：")

    if '.' in choice:
        media_index, feed_index = map(int, choice.split('.'))
        media_index -= 1
        feed_index -= 1
        if 0 <= media_index < len(media_to_process) and 0 <= feed_index < len(media_to_process[media_index]['feeds']):
            media_info = media_to_process[media_index]
            feed = media_info['feeds'][feed_index]
            print(f"處理 feed: {feed['name']}")
            process_feed(feed['url'], media_info['name'], media_info['url'], feed['name'])
        else:
            print("無效的選擇")
    else:
        try:
            media_index = int(choice) - 1
            if 0 <= media_index < len(media_to_process):
                media_info = media_to_process[media_index]
                print(f"處理媒體: {media_info['name']}")
                for feed in media_info['feeds']:
                    print(f"  處理 feed: {feed['name']}")
                    process_feed(feed['url'], media_info['name'], media_info['url'], feed['name'])
            else:
                print("無效的選擇")
        except ValueError:
            print("無效的輸入，請輸入數字")

    print("處理完成")

if __name__ == "__main__":
    main()