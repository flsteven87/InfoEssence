from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from src.database.models import InstagramPost, File, ChosenNews, Published, News
from src.config.settings import DATABASE_URL
from imgurpython import ImgurClient
import requests
import time
import os
import argparse
from dotenv import load_dotenv
import tempfile
import openai
from pydantic import BaseModel
from datetime import datetime, timedelta
from src.utils.database_utils import (
    get_latest_chosen_news, 
    get_instagram_posts, 
    get_published_instagram_post_ids, 
    get_published_news_ids, 
    get_recent_published_instagram_posts
)
from src.utils.file_utils import load_prompt_template

class ChosenInstagramPost(BaseModel):
    id: int

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
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.imgur_client = ImgurClient(self.imgur_client_id, self.imgur_client_secret)
        self.prompt_template = load_prompt_template('choose_instagram_post_prompt.txt')
        self.env = os.getenv("ENV", "development")

    def select_instagram_post(self, instagram_posts):
        if not instagram_posts:
            print("沒有可用的 Instagram 貼文")
            return None

        posts_data = []
        for post in instagram_posts:
            posts_data.append({
                "id": post.id,
                "ig_title": post.ig_title,
                "ig_caption": post.ig_caption
            })

        print(f"準備選擇的貼文數據：{posts_data}")

        # 這裡需要更新 prompt 模板，以包含最近發布的貼文信息
        prompt = self.prompt_template.format(
            posts_list=posts_data
        )

        try:
            client = openai.OpenAI()
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-2024-08-06",
                        temperature=0,
                        messages=[
                            {"role": "system", "content": "你是一位專業的社交媒體編輯，擅長選擇最適合在 Instagram 上發布的新聞。"},
                            {"role": "user", "content": prompt}
                        ],
                        tools=[{
                            "type": "function",
                            "function": {
                                "name": "output_chosen_instagram_post",
                                "description": "選擇最適合在 Instagram 上發布的貼文。",
                                "parameters": ChosenInstagramPost.model_json_schema()
                            }
                        }]
                    )

                    print(f"OpenAI 回應：{response}")

                    if not response.choices:
                        print("OpenAI 回應中沒有選擇")
                        continue

                    message = response.choices[0].message
                    if not message.tool_calls:
                        print("回應中沒有工具調用")
                        continue

                    tool_call = message.tool_calls[0]
                    if tool_call.function.name == "output_chosen_instagram_post":
                        chosen_post = ChosenInstagramPost.model_validate_json(tool_call.function.arguments)
                        print(f"AI 選擇了 Instagram 貼文 ID: {chosen_post.id}")
                        return next((post for post in instagram_posts if post.id == chosen_post.id), None)
                    else:
                        print(f"未預期的函數調用：{tool_call.function.name}")
                        continue

                except openai.APIError as e:
                    if attempt < max_retries - 1:
                        print(f"API 錯誤，重試中... (嘗試 {attempt + 1}/{max_retries})")
                        time.sleep(2 ** attempt)  # 指數退避
                    else:
                        raise

            print("達到最大重試次數，無法選擇 Instagram 貼文")
            return None

        except Exception as e:
            print(f"選擇 Instagram 貼文時發生錯誤: {e}")
            return None

    def upload_image_to_imgur(self, image_data: bytes) -> str:
        try:
            print("開始上傳圖片到 Imgur")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name

            uploaded_image = self.imgur_client.upload_from_path(temp_file_path, anon=True)

            os.unlink(temp_file_path)

            print(f"Imgur 上傳成功。返回的數據: {uploaded_image['link']}")
            return uploaded_image['link']
        except Exception as e:
            print(f"上傳圖片到 Imgur 時發生錯誤: {e}")
            raise

    def create_media_object(self, image_url: str, caption: str) -> str:
        url = f'{self.BASE_URL}/{self.user_id}/media'
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }

        if self.env == 'production':
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                return response.json()['id']
            else:
                print(f"創建媒體物件時發生錯誤: {response.json()}")
                raise Exception(f"創建媒體物件失敗: {response.text}")
        else:
            print("非生產環境，跳過實際的媒體物件創建")
            return "mock_media_id"

    def publish_media(self, media_id: str) -> None:
        url = f'{self.BASE_URL}/{self.user_id}/media_publish'
        payload = {
            'creation_id': media_id,
            'access_token': self.access_token
        }

        if self.env == 'production':
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("媒體發布成功！")
            else:
                print(f"發布媒體時發生錯誤: {response.json()}")
                raise Exception(f"發布媒體失敗: {response.text}")
        else:
            print("非生產環境，跳過實際的媒體發布")

    def post_instagram(self, post_id: int) -> str:
        try:
            with self.SessionLocal() as session:
                post = session.query(InstagramPost).filter(InstagramPost.id == post_id).first()
                if not post:
                    raise ValueError(f"找不到 ID 為 {post_id} 的 Instagram 貼文")

                file = session.query(File).filter(File.id == post.integrated_image_id).first()
                if not file:
                    raise ValueError(f"找不到 Instagram 貼文 ID {post_id} 的整合圖片")

                image_data = file.data
                caption = post.ig_caption

            image_url = self.upload_image_to_imgur(image_data)

            media_id = self.create_media_object(image_url, caption)

            if media_id:
                time.sleep(5)  # 等待幾秒鐘以確保處理完成
                self.publish_media(media_id)

                # 記錄已發布的貼文
                self.record_published_post(post_id)
                print(f"已發布的貼文：{post.ig_title}, {post.ig_caption}")

                return media_id
        except Exception as e:
            print(f"發布 Instagram 貼文時發生錯誤: {e}")
            raise

    def record_published_post(self, instagram_post_id: int):
        with self.SessionLocal() as session:
            instagram_post = session.query(InstagramPost).filter(InstagramPost.id == instagram_post_id).first()
            if not instagram_post:
                raise ValueError(f"找不到 ID 為 {instagram_post_id} 的 Instagram 貼文")

            published = Published(
                news_id=instagram_post.news_id,
                instagram_post_id=instagram_post_id
            )
            session.add(published)
            session.commit()
            print(f"已記錄發布的貼文：News ID {instagram_post.news_id}, Instagram Post ID {instagram_post_id}")

    def auto_post(self):
        chosen_news = get_latest_chosen_news()
        if not chosen_news:
            print("沒有找到最新的已選新聞")
            return

        instagram_posts = get_instagram_posts(chosen_news.id)
        if not instagram_posts:
            print("沒有找到相關的 Instagram 貼文")
            return

        selected_post = self.select_instagram_post(instagram_posts)
        if not selected_post:
            print("無法選擇合適的 Instagram 貼文")
            return

        try:
            media_id = self.post_instagram(selected_post.id)
            print(f"成功發布 Instagram 貼文。媒體 ID: {media_id}")
        except Exception as e:
            print(f"發布 Instagram 貼文時發生錯誤: {e}")

def main():
    parser = argparse.ArgumentParser(description="發布 Instagram 貼文")
    parser.add_argument("--post_id", type=int, help="要發布的 Instagram 貼文 ID")
    args = parser.parse_args()

    try:
        poster = InstagramPoster()
        if args.post_id:
            media_id = poster.post_instagram(args.post_id)
            print(f"成功發布 Instagram 貼文。媒體 ID: {media_id}")
        else:
            poster.auto_post()
    except Exception as e:
        print(f"發布 Instagram 貼文時發生錯誤: {e}")

if __name__ == "__main__":
    main()