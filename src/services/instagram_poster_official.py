import os
import requests
import time
import argparse
from typing import Dict, Any
from dotenv import load_dotenv
from src.services.image_generator import get_news_by_id, generate_news_image
from src.utils.file_utils import sanitize_filename
from imgurpython import ImgurClient

class InstagramPoster:
    BASE_URL = "https://graph.facebook.com/v20.0"

    def __init__(self):
        load_dotenv()
        self.user_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")
        self.imgur_client_secret = os.getenv("IMGUR_CLIENT_SECRET")
        if not self.user_id or not self.access_token or not self.imgur_client_id or not self.imgur_client_secret:
            raise ValueError("請確保在 .env 檔案中設置了所有必要的環境變量")
        self.imgur_client = ImgurClient(self.imgur_client_id, self.imgur_client_secret)

    def create_media_object(self, image_url: str, caption: str) -> str:
        """創建媒體物件"""
        url = f'{self.BASE_URL}/{self.user_id}/media'
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }
        
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json()['id']
        else:
            print(f"創建媒體物件時發生錯誤: {response.json()}")
            raise Exception(f"創建媒體物件失敗: {response.text}")

    def publish_media(self, media_id: str) -> None:
        """發布媒體"""
        url = f'{self.BASE_URL}/{self.user_id}/media_publish'
        payload = {
            'creation_id': media_id,
            'access_token': self.access_token
        }
        
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("媒體發布成功！")
        else:
            print(f"發布媒體時發生錯誤: {response.json()}")
            raise Exception(f"發布媒體失敗: {response.text}")

    def post_image(self, image_url: str, caption: str) -> str:
        """發布圖片到 Instagram"""
        try:
            # 步驟 1：創建媒體物件
            media_id = self.create_media_object(image_url, caption)
            
            if media_id:
                # 步驟 2：等待媒體物件處理完成
                time.sleep(5)  # 等待幾秒鐘以確保處理完成
                
                # 步驟 3：發布媒體
                self.publish_media(media_id)
                
                return media_id
        except Exception as e:
            print(f"發布圖片時發生錯誤: {e}")
            raise

    def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """獲取媒體資訊"""
        url = f'{self.BASE_URL}/{media_id}'
        params = {
            "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username",
            "access_token": self.access_token
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"獲取媒體資訊時發生錯誤: {response.json()}")
            raise Exception(f"獲取媒體資訊失敗: {response.text}")

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

    def post_news_image(self, news_id: int) -> str:
        """根據新聞 ID 發布圖片到 Instagram"""
        try:
            # 獲取新聞數據
            news_data = get_news_by_id(news_id)
            print(f"成功獲取新聞數據，ID: {news_id}")
            
            # 生成圖片（如果還沒有生成）
            image_path = generate_news_image(news_id)
            if not image_path:
                raise ValueError(f"無法為新聞 ID {news_id} 生成圖片")
            print(f"成功生成新聞圖片，路徑: {image_path}")
            
            # 構建完整的圖片路徑
            save_dir = os.path.join("./image", sanitize_filename(news_data['media_name']), sanitize_filename(news_data['feed_name']))
            file_name = f"{news_data['id']}_{sanitize_filename(news_data['title'][:50])}_news illustration style.png"
            full_image_path = os.path.join(save_dir, file_name)
            print(f"完整圖片路徑: {full_image_path}")
            
            # 上傳圖片到 Imgur
            image_url = self.upload_image_to_imgur(full_image_path)
            print(f"成功上傳圖片到 Imgur，URL: {image_url}")
            
            # 構建 caption
            caption = f"{news_data['ai_title']}\n\n{news_data['ai_summary']}\n\n#GlobalNews #Taiwan"
            print(f"貼文內容：{caption}")
            
            # 發布圖片
            media_id = self.post_image(image_url, caption)
            print(f"成功發布新聞圖片。媒體 ID: {media_id}")
            return media_id
        except Exception as e:
            print(f"發布新聞圖片時發生錯誤: {e}")
            print(f"錯誤詳情: {str(e)}")
            raise

def main():
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
