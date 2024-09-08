import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from instabot import Bot
from src.services.image_generator import generate_news_image
from src.utils.file_utils import sanitize_filename
from src.utils.database_utils import get_news_by_id

class InstagramPoster:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv("INSTAGRAM_USERNAME")
        self.password = os.getenv("INSTAGRAM_PASSWORD")
        if not self.username or not self.password:
            raise ValueError("請確保在 .env 檔案中設置了 INSTAGRAM_USERNAME 和 INSTAGRAM_PASSWORD")
        self.bot = Bot()
        self.bot.login(username=self.username, password=self.password)

    def post_image(self, image_path: str, caption: str) -> str:
        """發布圖片到 Instagram"""
        try:
            upload_result = self.bot.upload_photo(image_path, caption=caption)
            if upload_result:
                media_id = self.bot.last_response.json()["media"]["id"]
                print(f"媒體發布成功！媒體 ID: {media_id}")
                return media_id
            else:
                raise Exception("發布媒體失敗")
        except Exception as e:
            print(f"發布圖片時發生錯誤: {e}")
            raise

    def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """獲取媒體資訊"""
        try:
            media_info = self.bot.get_media_info(media_id)[0]
            return {
                "id": media_info["id"],
                "caption": media_info.get("caption", {}).get("text", ""),
                "media_type": media_info["media_type"],
                "permalink": f"https://www.instagram.com/p/{media_info['code']}/",
                "timestamp": media_info["taken_at"],
                "username": media_info["user"]["username"]
            }
        except Exception as e:
            print(f"獲取媒體資訊時發生錯誤: {e}")
            raise

    def post_news_image(self, news_id: int) -> str:
        """根據新聞 ID 發布圖片到 Instagram"""
        try:
            # 獲取新聞數據
            news_data = get_news_by_id(news_id)
            
            # 生成圖片（如果還沒有生成）
            image_path = generate_news_image(news_id)
            if not image_path:
                raise ValueError(f"無法為新聞 ID {news_id} 生成圖片")
            
            # 構建完整的圖片路徑
            save_dir = os.path.join("./image", sanitize_filename(news_data['media_name']), sanitize_filename(news_data['feed_name']))
            file_name = f"{news_data['id']}_{sanitize_filename(news_data['title'][:50])}_news illustration style.png"
            full_image_path = os.path.join(save_dir, file_name)
            
            # 構建 caption
            caption = f"{news_data['ai_title']}\n\n{news_data['ai_summary']}\n\n#GlobalNews #Taiwan"
            print(f"貼文內容：{caption}")
            
            # 發布圖片
            media_id = self.post_image(full_image_path, caption)
            print(f"成功發布新聞圖片。媒體 ID: {media_id}")
            return media_id
        except Exception as e:
            print(f"發布新聞圖片時發生錯誤: {e}")
            raise

def main():
    import argparse
    parser = argparse.ArgumentParser(description="發布新聞圖片到 Instagram")
    parser.add_argument("news_id", type=int, help="要發布的新聞 ID")
    args = parser.parse_args()

    try:
        poster = InstagramPoster()
        media_id = poster.post_news_image(args.news_id)
        print(f"成功發布新聞圖片。媒體 ID: {media_id}")
    except Exception as e:
        print(f"發布新聞圖片時發生錯誤: {e}")

if __name__ == "__main__":
    main()