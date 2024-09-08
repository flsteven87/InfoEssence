from openai import OpenAI
from src.config.settings import OPENAI_API_KEY
import os
from pydantic import BaseModel
import openai

client = OpenAI(api_key=OPENAI_API_KEY)

class News(BaseModel):
    ai_title: str
    ai_summary: str

def summarize_content(title: str, content: str, model: str = 'gpt-4o-mini') -> tuple[str, str, str]:
    try:
        # 使用絕對路徑或相對於專案根目錄的路徑
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'summarize_prompt.txt')
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"提示文件不存在：{prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"title: {title}, content: {content}"}
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "output_title_and_summary",
                        "description": "Generate a title and summary for the news.",
                        "parameters": News.model_json_schema()
                    }
                }
            ]
        )
        
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls and tool_calls[0].function.name == "output_title_and_summary":
            result = News.model_validate_json(tool_calls[0].function.arguments)
            return result.ai_title, result.ai_summary, model
        else:
            raise ValueError("未收到預期的工具調用回應")

    except FileNotFoundError as e:
        print(f"錯誤：{e}")
        return "摘要生成失敗", "無法找到提示文件"
    except Exception as e:
        print(f"摘要內容時發生錯誤：{e}")
        return "摘要生成失敗", f"處理過程中發生錯誤: {str(e)}"