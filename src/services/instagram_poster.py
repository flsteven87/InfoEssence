import os
import time
import argparse
import shutil
from typing import Dict, Any, List
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.types import Media
from src.services.image_generator import ImageGenerator
from src.utils.file_utils import get_image_file_path
from src.utils.database_utils import get_news_by_id
from imgurpython import ImgurClient
import pandas as pd
import openai
from pydantic import BaseModel

class ChosenNewsItem(BaseModel):
    id: int
    title: str

class ChosenNewsParameters(BaseModel):
    chosen_news: ChosenNewsItem

class ChosenNewsId(BaseModel):
    id: int

class InstagramPoster:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv("INSTAGRAM_USERNAME")
        self.password = os.getenv("INSTAGRAM_PASSWORD")
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")
        self.imgur_client_secret = os.getenv("IMGUR_CLIENT_SECRET")
        self.env = os.getenv("ENV", "development")
        if not self.username or not self.password or not self.imgur_client_id or not self.imgur_client_secret:
            raise ValueError("請確保在 .env 檔案中設置了所有必要的環境變量")
        self.client = Client()
        self.client.login(self.username, self.password)
        self.imgur_client = ImgurClient(self.imgur_client_id, self.imgur_client_secret)
        self.image_generator = ImageGenerator()

    def post_image(self, image_path: str, caption: str) -> Media:
        """發布圖片到 Instagram"""
        try:
            if self.env == "production":
                media = self.client.photo_upload(image_path, caption)
                print("媒體發布成功！")
                return media
            else:
                print("非生產環境，模擬發布圖片")
        except Exception as e:
            print(f"發布圖片時發生錯誤: {e}")
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

    def publish(self, news_id: int):
        """根據新聞 ID 發布圖片到 Instagram 並保存相關內容"""
        try:
            # 獲取新聞數據
            news_data = get_news_by_id(news_id)
            print(f"成功獲取新聞數據，ID: {news_id}")
            
            # 獲取 integrated_image_path  
            image_path = get_image_file_path(news_data['media_name'], news_data['feed_name'], news_id, news_data['title'])
            integrated_image_path = image_path.replace(".png", "_integrated.png")
            if not integrated_image_path:
                raise ValueError(f"無法找到新聞 ID {news_id} 的 integrated 圖片")
            print(f"成功找到新聞 ID {news_id} 的 integrated 圖片，路徑: {integrated_image_path}")
                        
            # 構建 caption
            df = self.get_latest_csv_data()
            caption = df.loc[df['id'] == news_id, 'ig_caption'].values[0]
            print(f"成功找到新聞 ID {news_id} 的 caption，內容: {caption}")

            # 保存相關內容到 published 資料夾
            self.save_to_published_folder(news_id, integrated_image_path, caption)

            # 發布圖片
            media = self.post_image(integrated_image_path, caption)
            if media is not None:
                media_id = media.id
                print(f"成功發布新聞圖片。媒體 ID: {media_id}")

        except Exception as e:
            print(f"處理新聞圖片時發生錯誤: {e}")
            print(f"錯誤詳情: {str(e)}")
            raise

    def save_to_published_folder(self, news_id: int, image_path: str, caption: str):
        """將圖片和 caption 保存到 published 資料夾"""
        published_folder = "published"
        news_folder = os.path.join(published_folder, str(news_id))
        
        # 創建資料夾（如果不存在）
        os.makedirs(news_folder, exist_ok=True)
        
        # 複製圖片
        image_filename = os.path.basename(image_path)
        shutil.copy2(image_path, os.path.join(news_folder, image_filename))
        
        # 保存 caption
        caption_filename = "caption.txt"
        with open(os.path.join(news_folder, caption_filename), 'w', encoding='utf-8') as f:
            f.write(caption)
        
        print(f"已將圖片和 caption 保存到 {news_folder}")

    def _get_latest_csv_file_path(self) -> str:
        """獲取最新的 CSV 文件路徑"""
        instagram_posts_path = "./instagram_posts"
        csv_files = [f for f in os.listdir(instagram_posts_path) if f.endswith('.csv')]
        if not csv_files:
            raise ValueError("無法找到 .csv 文件")
        latest_csv_file = max(csv_files, key=lambda x: os.path.getmtime(os.path.join(instagram_posts_path, x)))
        return os.path.join(instagram_posts_path, latest_csv_file)

    def get_latest_csv_data(self) -> pd.DataFrame:
        """獲取最新 CSV 文件的數據"""
        csv_file_path = self._get_latest_csv_file_path()
        return pd.read_csv(csv_file_path)

    def get_latest_csv_news(self) -> List[int]:
        """從最新的 CSV 文件中獲取所有新聞 ID"""
        df = self.get_latest_csv_data()
        return df['id'].tolist()

    def filter_unpublished_news(self, news_ids: List[int]) -> List[int]:
        """過濾掉已經發布的新聞"""
        published_folder = "published"
        unpublished_ids = []
        for news_id in news_ids:
            if not os.path.exists(os.path.join(published_folder, str(news_id))):
                unpublished_ids.append(news_id)
        return unpublished_ids

    def load_prompt_template(self):
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'choose_instagram_news_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def get_latest_instagram_posts(self) -> pd.DataFrame:
        csv_files = [f for f in os.listdir('./instagram_posts') if f.endswith('.csv')]
        latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join('./instagram_posts', x)))
        df = pd.read_csv(f'./instagram_posts/{latest_file}')
        return df

    def select_news_with_gpt(self, unpublished_ids) -> int:
        """使用 gpt-4o-2024-08-06 選擇要發布的新聞"""
        try:
            df = self.get_latest_instagram_posts()
            df = df[df['id'].isin(unpublished_ids)]
            news_data = df[['id', 'ig_title', 'ig_caption']].to_dict('records')

            # print(news_data)
            
            prompt_template = self.load_prompt_template()
            prompt = prompt_template.format(news_list=news_data)

            # print(prompt)

            client = openai.OpenAI()
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
                        "name": "output_chosen_news_id",
                        "description": "選擇最適合在 Instagram 上發布的新聞ID。",
                        "parameters": ChosenNewsId.model_json_schema()
                    }
                }]
            )

            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "output_chosen_news_id":
                chosen_news_id = ChosenNewsId.model_validate_json(tool_call.function.arguments).id
                print(f"AI 選擇了新聞 ID: {chosen_news_id}")
                return chosen_news_id
            else:
                print("未預期的函數調用")
                return None
        except Exception as e:
            print(f"在 AI 選擇過程中發生錯誤: {str(e)}")
            return None

    def post_auto_selected_news(self):
        """自動選擇並發布新聞"""
        try:
            # 獲取最新 CSV 中的所有新聞 ID
            all_news_ids = self.get_latest_csv_news()
            print(f"從最新的 CSV 文件中獲取了 {len(all_news_ids)} 條新聞")

            # 過濾掉已發布的新聞
            unpublished_ids = self.filter_unpublished_news(all_news_ids)
            print(f"過濾後剩餘 {len(unpublished_ids)} 條未發布的新聞")

            if not unpublished_ids:
                print("沒有未發布的新聞可選擇")
                return

            # 使用 GPT-4 選擇要發布的新聞
            selected_news_id = self.select_news_with_gpt(unpublished_ids)
            if selected_news_id is None:
                print("GPT-4 沒有選出合適的新聞")
                return

            print(f"GPT-4 選擇了新聞 ID: {selected_news_id}")

            # 發布選中的新聞
            self.publish(selected_news_id)

        except Exception as e:
            print(f"自動選擇並發布新聞時發生錯誤: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="發布新聞圖片到 Instagram")
    parser.add_argument("--news_id", type=int, help="要處理的新聞 ID", default=None)
    args = parser.parse_args()

    try:
        poster = InstagramPoster()
        if args.news_id:
            poster.publish(args.news_id)
        else:
            poster.post_auto_selected_news()
    except Exception as e:
        print(f"處理新聞圖片時發生誤: {e}")

if __name__ == "__main__":
    main()