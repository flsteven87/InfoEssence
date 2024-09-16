import os
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import ImageFont
import logging
from src.database.models import News, Media, Feed
from src.services.image_integrator import ImageIntegrator
from src.utils.file_utils import get_content_file_path, sanitize_filename, get_text_width
from src.utils.database_utils import get_news_by_id
from src.config.settings import DATABASE_URL, OPENAI_API_KEY
from pydantic import BaseModel
import csv
import unicodedata
from datetime import datetime
from typing import List, Dict

class InstagramPost(BaseModel):
    ig_title: str
    ig_caption: str

class InstagramPostGenerator:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.system_prompt = self.load_prompt_template()
        self.title_font_path = "./src/assets/jf-openhuninn-2.0.ttf"
        self.max_regeneration_attempts = 10

        # 搶先確認
        self.title_font_size = int(56)
        self.title_font = ImageFont.truetype(self.title_font_path, self.title_font_size)
        self.title_width_for_draw = 1024 - 40 - 40 - 30

    def load_prompt_template(self):
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'instagram_post_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def process_ig_title_fullwidth(self, text):
        """將 ig_title 的標點符號轉換成全形，保持數字、%和.為半形"""
        return ''.join([
            char if char.isdigit() or char in ['%', '.'] else
            unicodedata.normalize('NFKC', char).translate({
                ord(c): ord(c) + 0xFEE0 for c in '!"#$&\'()*+,-/:;<=>?@[\\]^_`{|}~'
            })
            for char in text
        ])

    def generate_instagram_post(self, news_id: int):
        news_data = get_news_by_id(news_id)
        
        for attempt in range(self.max_regeneration_attempts):
            result = self._generate_post_content(news_data)
            
            if self._is_title_valid(result.ig_title):
                return {
                    "ig_title": self.process_ig_title_fullwidth(result.ig_title),
                    "ig_caption": result.ig_caption,
                    "news_data": news_data
                }
            else:
                logging.warning(f"第 {attempt + 1} 次嘗試：ig_title: '{result.ig_title}' 寬度超過2行，重新生成")
        
        logging.error(f"無法生成符合寬度要求的 ig_title，使用最後一次生成的結果 '{result.ig_title}'")
        return {
            "ig_title": self.process_ig_title_fullwidth(result.ig_title),
            "ig_caption": result.ig_caption,
            "news_data": news_data
        }

    def _generate_post_content(self, news_data):
        user_prompt = f"""
        title: {news_data['title']}
        summary: {news_data['summary']}
        content: {news_data['content']}
        ai_title: {news_data['ai_title']}
        ai_summary: {news_data['ai_summary']}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "output_instagram_post",
                    "description": "Generate an Instagram title and caption for the news.",
                    "parameters": InstagramPost.model_json_schema()
                }
            }]
        )

        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "output_instagram_post":
            return InstagramPost.model_validate_json(tool_call.function.arguments)
        else:
            raise ValueError("未收到預期的工具調用回應")

    def _is_title_valid(self, title):
        return get_text_width(self.title_font, title) <= self.title_width_for_draw * 2

    def save_instagram_posts(self, ig_posts: List[Dict], output_dir="./instagram_posts"):
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{timestamp}.csv"
        file_path = os.path.join(output_dir, file_name)

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'ig_title', 'ig_caption'])
            for post in ig_posts:
                writer.writerow([
                    post['news_data']['id'],
                    post['ig_title'],
                    post['ig_caption']
                ])

        return file_path

# 主函數用於測試
def main():
    try:
        generator = InstagramPostGenerator()
        
        news_ids = input("請輸入要生成 Instagram 貼文的新聞 ID（多個 ID 請用逗號分隔）: ").split(',')
        news_ids = [int(id.strip()) for id in news_ids]

        ig_posts = []
        for news_id in news_ids:
            post_content = generator.generate_instagram_post(news_id)
            ig_posts.append(post_content)
            print(f"\n新聞 ID {news_id}:")
            print(f"Instagram 標題: {post_content['ig_title']}")
            print(f"Instagram 說明: {post_content['ig_caption']}")

        saved_path = generator.save_instagram_posts(ig_posts)
        print(f"\n所有貼文內容已保存到: {saved_path}")

    except ValueError as ve:
        print(f"錯誤: {ve}")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")

if __name__ == "__main__":
    main()
