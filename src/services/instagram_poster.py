import os
import time
import argparse
from typing import Dict, Any
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.types import Media
from src.services.image_generator import ImageGenerator
from src.utils.file_utils import sanitize_filename
from src.utils.database_utils import get_news_by_id
from imgurpython import ImgurClient

class InstagramPoster:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv("INSTAGRAM_USERNAME")
        self.password = os.getenv("INSTAGRAM_PASSWORD")
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")
        self.imgur_client_secret = os.getenv("IMGUR_CLIENT_SECRET")
        if not self.username or not self.password or not self.imgur_client_id or not self.imgur_client_secret:
            raise ValueError("請確保在 .env 檔案中設置了所有必要的環境變量")
        self.client = Client()
        self.client.login(self.username, self.password)
        self.imgur_client = ImgurClient(self.imgur_client_id, self.imgur_client_secret)
        self.image_generator = ImageGenerator()

    def post_image(self, image_path: str, caption: str) -> Media:
        """發布圖片到 Instagram"""
        try:
            media = self.client.photo_upload(image_path, caption)
            print("媒體發布成功！")
            return media
        except Exception as e:
            print(f"發布圖片時發生錯誤: {e}")
            raise

    def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """獲取媒體資訊"""
        try:
            media_info = self.client.media_info(media_id).dict()
            return {
                "id": media_info["id"],
                "caption": media_info["caption_text"],
                "media_type": media_info["media_type"],
                "media_url": media_info["thumbnail_url"],
                "permalink": f"https://www.instagram.com/p/{media_info['code']}/",
                "timestamp": media_info["taken_at"].isoformat(),
                "username": media_info["user"]["username"]
            }
        except Exception as e:
            print(f"獲取媒體資訊時發生錯誤: {e}")
            raise

    def upload_image_to_imgur(self, image_path: str) -> str:
        """上傳圖片到 Imgur 並返回 URL"""
        try:
            print(f"開始上傳圖片到 Imgur: {image_path}")
            uploaded_image = self.imgur_client.upload_from_path(image_path, anon=True)
            print(f"Imgur 上傳成功。返回的數據: {uploaded_image['link']}")
            return uploaded_image['link']
        except Exception as e:
            print(f"上傳圖片到 Imgur 時發生錯誤: {e}")
            print(f"錯誤詳情: {str(e)}")
            raise

    def save_image_as_draft(self, image_path: str, caption: str) -> str:
        """將圖片保存為 Instagram 草稿"""
        try:
            media = self.client.photo_upload_to_story(image_path, caption=caption, configure_timeout=0)
            print("圖片已成功保存為草稿！")
            return media.id
        except Exception as e:
            print(f"將圖片保存為草稿時發生錯誤: {e}")
            raise

    def post_news_image(self, news_id: int, publish: bool = False) -> str:
        """根據新聞 ID 發布圖片到 Instagram 或保存為草稿"""
        try:
            # 獲取新聞數據
            news_data = get_news_by_id(news_id)
            print(f"成功獲取新聞數據，ID: {news_id}")
            
            # 生成圖片
            image_path = self.image_generator.generate_news_image(news_id)
            if not image_path:
                raise ValueError(f"無法為新聞 ID {news_id} 生成圖片")
            print(f"成功生成新聞圖片，路徑: {image_path}")
            
            # 構建完整的圖片路徑
            full_image_path = os.path.join("./image", image_path)
            print(f"完整圖片路徑: {full_image_path}")
            
            # 構建 caption
            caption = f"{news_data['ai_title']}\n\n{news_data['ai_summary']}\n\n#GlobalNews #Taiwan"
            print(f"貼文內容：{caption}")
            
            # 發布圖片或保存為草稿
            if publish:
                media = self.post_image(full_image_path, caption)
                media_id = media.id
                print(f"成功發布新聞圖片。媒體 ID: {media_id}")
            else:
                media_id = self.save_image_as_draft(full_image_path, caption)
                print(f"成功將新聞圖片保存為草稿。媒體 ID: {media_id}")
            
            return media_id
        except Exception as e:
            print(f"處理新聞圖片時發生錯誤: {e}")
            print(f"錯誤詳情: {str(e)}")
            raise

def main():
    parser = argparse.ArgumentParser(description="發布新聞圖片到 Instagram 或保存為草稿")
    parser.add_argument("news_id", type=int, help="要處理的新聞 ID")
    parser.add_argument("--publish", action="store_true", help="直接發布圖片而不是保存為草稿")
    args = parser.parse_args()

    try:
        poster = InstagramPoster()
        media_id = poster.post_news_image(args.news_id, publish=args.publish)
        action = "發布" if args.publish else "保存為草稿"
        print(f"成功將新聞圖片{action}。媒體 ID: {media_id}")
    except Exception as e:
        print(f"處理新聞圖片時發生錯誤: {e}")

if __name__ == "__main__":
    main()