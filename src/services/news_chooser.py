from typing import List
import openai
from pydantic import BaseModel
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from src.config.settings import DATABASE_URL, OPENAI_API_KEY
from src.database.models import News, Media, Feed
import os
import logging
from datetime import date, timedelta
import csv
from datetime import datetime

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定義 Pydantic 模型來結構化輸出
class ChosenNewsItem(BaseModel):
    id: int
    title: str

class ChosenNewsParameters(BaseModel):
    chosen_news: List[ChosenNewsItem]

class NewsChooser:
    def __init__(self, n: int):
        self.n = n
        
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        openai.api_key = OPENAI_API_KEY
        self.prompt_template = self.load_prompt_template()

    def load_prompt_template(self):
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'choose_news_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def load_news(self):
        now = datetime.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        with self.SessionLocal() as session:
            query = session.query(News).filter(
                News.published_at.between(twenty_four_hours_ago, now)
            ).order_by(News.published_at.desc())
            return query.all()

    def choose_important_news(self, news_list):
        total_news = len(news_list)
        news_data = [{
            "id": news.id,
            "title": news.title,
            "summary": news.summary,
            "ai_title": news.ai_title,
            "ai_summary": news.ai_summary
        } for news in news_list]

        prompt = self.prompt_template.format(n=self.n, news_list=news_data, total_news=total_news)

        client = openai.OpenAI()

        try:
            response = client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                temperature=0,
                messages=[
                    {"role": "system", "content": "You are a professional news editor skilled at selecting important and valuable news."},
                    {"role": "user", "content": prompt}
                ],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "output_chosen_news",
                        "description": "Select the most important news with original IDs from the original list.",
                        "parameters": ChosenNewsParameters.model_json_schema()
                    }
                }]
            )

            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "output_chosen_news":
                chosen_news = ChosenNewsParameters.model_validate_json(tool_call.function.arguments).chosen_news
                logger.info(f"AI selected {len(chosen_news)} news items")
                return chosen_news
            else:
                logger.error("Unexpected function call")
                return []
        except Exception as e:
            logger.error(f"Error in AI selection: {str(e)}")
            return []

    def save_chosen_news_to_csv(self, chosen_news):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"./chosen_news/{timestamp}.csv"
        os.makedirs("./chosen_news", exist_ok=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'title']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for item in chosen_news:
                writer.writerow({
                    'id': item.id, 
                    'title': item.title
                })
        
        logger.info(f"已將選擇的新聞保存到 {filename}")

    def run(self):
        news_list = self.load_news()
        total_news = len(news_list)
        logger.info(f"載入了 {total_news} 條過去 24 小時內發布的新聞")

        chosen_news = self.choose_important_news(news_list)

        if chosen_news:
            logger.info(f"從 {total_news} 條新聞中選出了 {len(chosen_news)} 條重要新聞：")
            for item in chosen_news:
                print(f"ID: {item.id}, 標題: {item.title}")
            print(f"\n總共從 {total_news} 條新聞中選出了 {len(chosen_news)} 條重要新聞")
            
            self.save_chosen_news_to_csv(chosen_news)
        else:
            logger.warning("沒有選出任何新聞")
            print(f"從 {total_news} 條新聞中沒有選出任何重要新聞")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="選擇今天發布的重要新聞")
    parser.add_argument('-n', '--num_chosen', type=int, required=True, help='選擇的重要新聞數量')
    args = parser.parse_args()

    chooser = NewsChooser(args.num_chosen)
    chooser.run()

if __name__ == "__main__":
    main()