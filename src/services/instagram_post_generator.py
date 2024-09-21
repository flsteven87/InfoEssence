import os
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import joinedload
from PIL import ImageFont
import logging
from src.database.models import News, Media, Feed, ChosenNews, InstagramPost
from src.services.image_integrator import ImageIntegrator
from src.utils.file_utils import get_text_width
from src.utils.database_utils import get_latest_chosen_news
from src.config.settings import DATABASE_URL, OPENAI_API_KEY
from pydantic import BaseModel
import unicodedata
from datetime import datetime
from typing import List, Dict
import time
from pydantic import ValidationError

class InstagramPostContent(BaseModel):
    ig_title: str
    ig_caption: str

class InstagramPostGenerator:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.system_prompt = self.load_prompt_template()
        self.title_font_path = "./src/assets/jf-openhuninn-2.0.ttf"
        self.max_regeneration_attempts = 30
        self.title_font_size = int(56)
        self.title_font = ImageFont.truetype(self.title_font_path, self.title_font_size)
        self.title_width_for_draw = 1024 - 40 - 40 - 30

    def load_prompt_template(self):
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'instagram_post_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def process_ig_title_fullwidth(self, text):
        return ''.join([
            char if char.isdigit() or char in ['%', '.'] else
            unicodedata.normalize('NFKC', char).translate({
                ord(c): ord(c) + 0xFEE0 for c in '!"#$&\'()*+,-/:;<=>?@[\\]^_`{|}~'
            })
            for char in text
        ])

    def generate_instagram_post(self, news: News):
        for attempt in range(self.max_regeneration_attempts):
            result = self._generate_post_content(news)
            
            if self._is_title_valid(result.ig_title):
                return {
                    "ig_title": self.process_ig_title_fullwidth(result.ig_title),
                    "ig_caption": result.ig_caption,
                    "news": news
                }
            else:
                logging.warning(f"第 {attempt + 1} 次嘗試：ig_title: '{result.ig_title}' 寬度超過2行，重新生成")
        
        logging.error(f"無法生成符合寬度要求的 ig_title，使用最後一次生成的結果 '{result.ig_title}'")
        return {
            "ig_title": self.process_ig_title_fullwidth(result.ig_title),
            "ig_caption": result.ig_caption,
            "news": news
        }

    def _generate_post_content(self, news: News):
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                content = ""
                if news.md_file:
                    content = news.md_file.data.decode('utf-8')
                user_prompt = f"""
                title: {news.title}
                summary: {news.summary}
                content: {content}
                ai_title: {news.ai_title}
                ai_summary: {news.ai_summary}
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
                            "parameters": InstagramPostContent.model_json_schema()
                        }
                    }]
                )
                tool_call = response.choices[0].message.tool_calls[0]
                if tool_call.function.name == "output_instagram_post":
                    return InstagramPostContent.model_validate_json(tool_call.function.arguments)
                else:
                    raise ValueError("未收到預期的工具調用回應")
            except (ValidationError, ValueError) as e:
                if attempt < max_retries - 1:
                    logging.warning(f"生成 Instagram 貼文內容失敗（嘗試 {attempt + 1}/{max_retries}）：{str(e)}。正在重試...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"生成 Instagram 貼文內容失敗，已達到最大重試次數：{str(e)}")
                    raise

        raise RuntimeError("無法生成有效的 Instagram 貼文內容")

    def _is_title_valid(self, title):
        return get_text_width(self.title_font, title) <= self.title_width_for_draw * 2

    def generate_instagram_posts(self):
        with self.SessionLocal() as db:
            chosen_news = get_latest_chosen_news(db)
            if not chosen_news:
                logging.warning("沒有找到最新的已選新聞")
                return []
            ig_posts = []
            for news_id in chosen_news.news_ids:
                news = db.query(News).options(joinedload(News.md_file)).filter(News.id == news_id).first()
                if news:
                    post_content = self.generate_instagram_post(news)
                    ig_posts.append(post_content)
                else:
                    logging.warning(f"找不到 ID 為 {news_id} 的新聞")
        self.save_instagram_posts(ig_posts, chosen_news.id)
        return ig_posts

    def save_instagram_posts(self, ig_posts: List[Dict], chosen_news_id: int):
        with self.SessionLocal() as db:
            for post in ig_posts:
                instagram_post = InstagramPost(
                    news_id=post['news'].id,
                    chosen_news_id=chosen_news_id,
                    ig_title=post['ig_title'],
                    ig_caption=post['ig_caption']
                )
                db.add(instagram_post)
            
            db.commit()
        logging.info(f"已保存 {len(ig_posts)} 條 Instagram 貼文")

def main():
    try:
        generator = InstagramPostGenerator()
        ig_posts = generator.generate_instagram_posts()
        
        if not ig_posts:
            print("沒有找到可生成的 Instagram 貼文")
            return
        for post in ig_posts:
            print(f"\n新聞 ID {post['news'].id}:")
            print(f"Instagram 標題: {post['ig_title']}")
            print(f"Instagram 說明: {post['ig_caption']}")
        print(f"\n所有貼文內容已保存到數據庫")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
        logging.exception("發生未預期的錯誤")

if __name__ == "__main__":
    main()