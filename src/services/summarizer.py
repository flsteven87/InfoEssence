from openai import OpenAI
from src.config.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def summarize_content(title: str, content: str) -> tuple[str, str]:
    try:
        with open('./services/prompts/summarize_prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"title: {title}, content: {content}"}
            ]
        )
        # 假設回應中第一行是標題，其餘是摘要
        result = response.choices[0].message.content.split('\n', 1)
        ai_title = result[0].strip()
        ai_summary = result[1].strip() if len(result) > 1 else ""
        return ai_title, ai_summary
    except Exception as e:
        print(f"Error in summarizing content: {e}")
        return "處理失敗", f"處理過程中發生錯誤: {str(e)}"