import os
from openai import OpenAI
from src.config.settings import OPENAI_API_KEY, DATABASE_URL
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import News  # 假設您有一個 News 模型
from src.utils.file_utils import get_content_file_path, sanitize_filename, get_image_file_path
from src.utils.database_utils import get_news_by_id
import requests

client = OpenAI(api_key=OPENAI_API_KEY)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class ImagePrompt(BaseModel):
    dalle_prompt: str

def generate_image_prompt(ai_title: str, ai_summary: str, style: str) -> str:
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'image_prompt.txt')
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"提示文件不存在：{prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()

        # 在這裡插入參數
        system_prompt = system_prompt.format(style=style)

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ai_title: {ai_title}, ai_summary: {ai_summary}"}
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

def generate_news_image(news_id: int) -> str:
    try:
        # 獲取新聞數據
        news_data = get_news_by_id(news_id)
        
        # 生成圖像提示
        style = "news illustration style"
        image_prompt = generate_image_prompt(news_data['ai_title'], news_data['ai_summary'], style)
        
        # 使用 DALL-E 生成圖像
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        # 獲取生成的圖像 URL
        image_url = response.data[0].url

        # 下載圖像
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            raise Exception("無法下載生成的圖像")

        # 使用 get_image_file_path 函數獲取保存路徑
        save_path = get_image_file_path(
            media_name=news_data['media_name'],
            feed_name=news_data['feed_name'],
            news_id=news_data['id'],
            title=news_data['title']
        )

        # 確保目錄存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 保存圖像
        with open(save_path, 'wb') as f:
            f.write(image_response.content)

        # 返回相對路徑
        return os.path.relpath(save_path, "./image")

    except Exception as e:
        print(f"生成新聞圖片時發生錯誤：{e}")
        return ""

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="為指定的新聞生成圖片")
    parser.add_argument("news_id", type=int, help="要生成圖片的新聞 ID")
    args = parser.parse_args()
    
    try:
        image_url = generate_news_image(args.news_id)
        if image_url:
            print(f"成功生成圖片。URL: {image_url}")
        else:
            print("圖片生成失敗")
    except Exception as e:
        print(f"發生錯誤: {str(e)}")
