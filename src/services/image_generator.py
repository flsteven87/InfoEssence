import os
from typing import Dict, Any
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import requests

from src.config.settings import OPENAI_API_KEY, DATABASE_URL
from src.utils.file_utils import get_image_file_path, get_content_file_path
from src.utils.database_utils import get_news_by_id, Session
from src.database.models import News, File
from src.database.operations import upsert_news_with_png

class ImagePrompt(BaseModel):
    dalle_prompt: str

class ImageGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)

    def _generate_image_prompt(self, ai_title: str, ai_summary: str, content: str, style: str) -> str:
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'image_prompt.txt')
            if not os.path.exists(prompt_path):
                raise FileNotFoundError(f"提示文件不存在：{prompt_path}")
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()

            system_prompt = system_prompt.format(style=style)

            response = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"ai_title: {ai_title}, ai_summary: {ai_summary}, news_content: {content}"}
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "output_dalle_prompt",
                            "description": "Generate a DALL-E prompt for the news image.",
                            "parameters": ImagePrompt.model_json_schema()
                        }
                    }
                ]
            )
            
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and tool_calls[0].function.name == "output_dalle_prompt":
                result = ImagePrompt.model_validate_json(tool_calls[0].function.arguments)
                return result.dalle_prompt
            else:
                raise ValueError("未收到預期的工具調用回應")

        except FileNotFoundError as e:
            print(f"錯誤：{e}")
            return "無法生成圖像提示"
        except Exception as e:
            print(f"生成圖像提示時發生錯誤：{e}")
            return f"處理過程中發生錯誤: {str(e)}"

    def generate_news_image(self, news_id: int, re_gen: bool = False) -> bool:
        try:
            with Session() as db:
                news = get_news_by_id(db, news_id)
                if not news:
                    raise Exception(f"找不到 ID 為 {news_id} 的新聞")

                # 檢查是否已存在圖片且不需要重新生成
                if news.png_file_id and not re_gen:
                    print(f"新聞 ID {news_id} 已有圖片，不需要重新生成。")
                    return True

                # 將 News 對象轉換為字典
                news_data = {
                    'id': news.id,
                    'title': news.title,
                    'ai_title': news.ai_title,
                    'ai_summary': news.ai_summary,
                    'media_name': news.media.name if news.media else None,
                    'feed_name': news.feed.name if news.feed else None,
                }

                # 從數據庫獲取內容文件
                if not news.md_file:
                    raise Exception("內容文件不存在")

                content = news.md_file.data.decode('utf-8')

                style = "news illustration style"
                image_prompt = self._generate_image_prompt(news_data['ai_title'], news_data['ai_summary'], content, style)
                
                max_attempts = 2
                for attempt in range(max_attempts):
                    try:
                        response = self.client.images.generate(
                            model="dall-e-3",
                            prompt=image_prompt,
                            size="1024x1024",
                            quality="standard",
                            n=1,
                        )

                        image_url = response.data[0].url

                        image_response = requests.get(image_url)
                        if image_response.status_code == 200:
                            # 成功下載圖片，保存到數據庫
                            png_content = image_response.content
                            upsert_news_with_png(db, news_id, png_content)
                            return True
                        elif image_response.status_code == 400 and attempt < max_attempts - 1:
                            print(f"生成圖片失敗（狀態碼 400），正在重新生成提示並重試...")
                            image_prompt = self._generate_image_prompt(news_data['ai_title'], news_data['ai_summary'], content, style)
                        else:
                            raise Exception(f"無法下載生成的圖像，狀態碼：{image_response.status_code}")

                    except Exception as e:
                        if attempt < max_attempts - 1:
                            print(f"嘗試 {attempt + 1} 失敗：{e}，正在重試...")
                        else:
                            raise

                raise Exception("達到最大重試次數，無法生成圖片")

        except Exception as e:
            print(f"生成新聞圖片時發生錯誤：{e}")
            return False

def main(news_id: int, re_gen: bool = False) -> None:
    image_generator = ImageGenerator()
    try:
        success = image_generator.generate_news_image(news_id, re_gen)
        if success:
            print(f"成功生成圖片並保存到數據庫。")
        else:
            print("圖片生成失敗")
    except Exception as e:
        print(f"發生錯誤: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="為指定的新聞生成圖片")
    parser.add_argument("news_id", type=int, help="要生成圖片的新聞 ID")
    parser.add_argument("--re_gen", action="store_true", help="是否重新生成圖片")
    args = parser.parse_args()
    
    main(args.news_id, args.re_gen)
