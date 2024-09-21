from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from src.database.models import Story, File, Published, News
from src.config.settings import DATABASE_URL
from imgurpython import ImgurClient
import requests
import time
import os
import argparse
from dotenv import load_dotenv
import tempfile
from datetime import timedelta
import json

class InstagramStoryPoster:
    BASE_URL = "https://graph.facebook.com/v20.0"

    def __init__(self):
        load_dotenv()
        self.user_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")
        self.imgur_client_secret = os.getenv("IMGUR_CLIENT_SECRET")
        if not self.user_id or not self.access_token or not self.imgur_client_id or not self.imgur_client_secret:
            raise ValueError("請確保在 .env 檔案中設置了所有必要的環境變量")
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.imgur_client = ImgurClient(self.imgur_client_id, self.imgur_client_secret)
        self.env = os.getenv("ENV", "development")
        # self.env = "production"

    def upload_image_to_imgur(self, image_data: bytes) -> str:
        try:
            print("開始上傳圖片到 Imgur")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name

            uploaded_image = self.imgur_client.upload_from_path(temp_file_path, anon=True)
            
            os.unlink(temp_file_path)

            print(f"Imgur 上傳成功。返回的連結: {uploaded_image['link']}")
            return uploaded_image['link']
        except Exception as e:
            print(f"上傳圖片到 Imgur 時發生錯誤: {e}")
            raise

    def create_story_media_object(self, image_url: str) -> str:
        url = f'{self.BASE_URL}/{self.user_id}/media'
        payload = {
            'image_url': image_url,
            'access_token': self.access_token,
            'is_stories': True
        }

        if self.env == 'production':
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                return response.json()['id']
            else:
                print(f"創建限時動態媒體物件��發生錯誤: {response.json()}")
                raise Exception(f"創建限時動態媒體物件失敗: {response.text}")
        else:
            print("非生產環境，跳過實際的限時動態媒體物件創建")
            return "mock_story_media_id"

    def create_story_container(self, image_url: str, link: str) -> str:
        url = f'{self.BASE_URL}/{self.user_id}/media'
        payload = {
            'image_url': image_url,
            'media_type': 'STORIES',
            'access_token': self.access_token,
            'story_media_link_data': json.dumps({
                'link_type': 'WEB',
                'url': link
            })
        }

        if self.env == 'production':
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                return response.json()['id']
            else:
                print(f"創建限時動態容器時發生錯誤: {response.json()}")
                raise Exception(f"創建限時動態容器失敗: {response.text}")
        else:
            print("非生產環境，跳過實際的限時動態容器創建")
            return "mock_story_container_id"

    def publish_story(self, container_id: str) -> None:
        url = f'{self.BASE_URL}/{self.user_id}/media_publish'
        payload = {
            'creation_id': container_id,
            'access_token': self.access_token
        }
        
        if self.env == 'production':
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("限時動態發布成功！")
            else:
                print(f"發布限時動態時發生錯誤: {response.json()}")
                raise Exception(f"發布限時動態失敗: {response.text}")
        else:
            print("非生產環境，跳過實際的限時動態發布")

    def post_story(self, story_id: int) -> str:
        try:
            with self.SessionLocal() as session:
                story = session.query(Story).filter(Story.id == story_id).first()
                if not story:
                    raise ValueError(f"找不到 ID 為 {story_id} 的限時動態")
                
                published = story.published
                if not published:
                    raise ValueError(f"限時動態 ID {story_id} 沒有關聯的已發布記錄")
                
                instagram_post = published.instagram_post
                if not instagram_post:
                    raise ValueError(f"已發布記錄 ID {published.id} 沒有關聯的 Instagram 貼文")
                
                integrated_image = instagram_post.integrated_image
                if not integrated_image:
                    raise ValueError(f"Instagram 貼文 ID {instagram_post.id} 沒有關聯的整合圖片")
                
                image_data = integrated_image.data
                post_link = f"https://www.instagram.com/p/{instagram_post.id}/"  # 假設的 Instagram 貼文連結格式

            image_url = self.upload_image_to_imgur(image_data)
            
            container_id = self.create_story_container(image_url, post_link)
            
            if container_id:
                time.sleep(5)  # 等待幾秒鐘以確保處理完成
                self.publish_story(container_id)
                                
                return container_id
        except Exception as e:
            print(f"發布限時動態時發生錯誤: {e}")
            raise


    def auto_post_story(self):
        with self.SessionLocal() as session:
            # 獲取最近一天內發布的新聞
            recent_news = session.query(Published).join(News).filter(
                Published.published_at >= func.now() - timedelta(days=1)
            ).order_by(desc(Published.published_at)).first()

            if not recent_news:
                print("沒有找到最近發布的新聞")
                return

            # 檢查是否已經為這條新聞創建了限時動態
            existing_story = session.query(Story).filter(
                Story.published_id == recent_news.id
            ).first()

            if existing_story:
                print("已經為最近的新聞創建了限時動態")
                return

            # 創建新的限時動態
            new_story = Story(
                title=f"{recent_news.news.title}",
                content=recent_news.news.ai_summary[:200] if recent_news.news.ai_summary else "",  # 限制內容長度
                png_file_id=recent_news.news.png_file_id,
                published_id=recent_news.id,
            )
            session.add(new_story)
            session.commit()

            try:
                media_id = self.post_story(new_story.id)  # 移除了 recent_news.news.link 參數
                print(f"成功發布限時動態。媒體 ID: {media_id}")
            except Exception as e:
                print(f"發布限時動態時發生錯誤: {e}")

def main():
    parser = argparse.ArgumentParser(description="發布 Instagram 限時動態")
    parser.add_argument("--story_id", type=int, help="要發布的限時動態 ID")
    args = parser.parse_args()

    try:
        poster = InstagramStoryPoster()
        if args.story_id:
            media_id = poster.post_story(args.story_id)
            print(f"成功發布指定的限時動態。媒體 ID: {media_id}")
        else:
            poster.auto_post_story()
    except Exception as e:
        print(f"發布 Instagram 限時動態時發生錯誤: {e}")

if __name__ == "__main__":
    main()