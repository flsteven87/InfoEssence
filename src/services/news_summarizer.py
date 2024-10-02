from openai import OpenAI
from src.config.settings import OPENAI_API_KEY
from src.utils.file_utils import load_prompt_template
import os
from pydantic import BaseModel
import openai

class News(BaseModel):
    ai_title: str
    ai_summary: str

class NewsSummarizer:
    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = load_prompt_template('summarize_prompt.txt')

    def summarize_content(self, title: str, content: str, model: str = 'gpt-4o-mini') -> tuple[str, str, str]:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
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
                    if attempt < max_attempts - 1:
                        print(f"未收到預期的工具調用回應，正在進行第 {attempt + 2} 次嘗試...")
                        continue
                    else:
                        raise ValueError("連續三次未收到預期的工具調用回應")

            except FileNotFoundError as e:
                print(f"錯誤：{e}")
                return "摘要生成失敗", "無法找到提示文件", model
            except Exception as e:
                print(f"摘要內容時發生錯誤：{e}")
                return "摘要生成失敗", f"處理過程中發生錯誤: {str(e)}", model

        # 如果所有嘗試都失敗
        return "摘要生成失敗", "連續三次未收到預期的工具調用回應", model