from typing import List
import openai
from pydantic import BaseModel
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from src.config.settings import DATABASE_URL, OPENAI_API_KEY
from src.database.models import News, Media, Feed, File, ChosenNews
import os
import logging
from datetime import date, timedelta
import csv
from datetime import datetime
from src.utils.database_utils import get_recent_published_instagram_posts, get_published_news_ids, get_news_by_id
from src.utils.file_utils import load_prompt_template

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
    def __init__(self, num_chosen):
        self.num_chosen = num_chosen
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.prompt_template = load_prompt_template('choose_news_prompt.txt')
        self.filter_prompt_template = load_prompt_template('filter_published_news_prompt.txt')

    def load_news(self):
        now = datetime.now()
        six_hours_ago = now - timedelta(hours=6)
        with self.SessionLocal() as session:
            query = session.query(News).filter(
                News.published_at.between(six_hours_ago, now)
            ).order_by(News.published_at.desc())
            return query.all()

    def choose_important_news(self, news_list):
        total_news = len(news_list)
        news_data = []

        for news_item in news_list:
            news = get_news_by_id(news_item.id)
            if news:
                news_data.append({
                    "id": news.id,
                    "title": news.title,
                    "summary": news.summary,
                    "ai_title": news.ai_title,
                    "ai_summary": news.ai_summary
                })

        prompt = self.prompt_template.format(
            n=self.num_chosen, 
            news_list=news_data, 
            total_news=total_news
        )

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
                print(chosen_news)
                return chosen_news
            else:
                logger.error("Unexpected function call")
                return []
        except Exception as e:
            logger.error(f"Error in AI selection: {str(e)}")
            return []

    def filter_unpublished_news(self, news_list):
        published_news_ids = get_published_news_ids()
        recent_published_ig_posts = get_recent_published_instagram_posts()

        with self.SessionLocal() as session:
            unpublished_news = [news for news in news_list if news.id not in published_news_ids]

            if not unpublished_news:
                logger.warning("所有新聞都已發布")
                return []

            total_news = len(unpublished_news)
            news_data = []

            for news in unpublished_news:
                news_data.append({
                    "id": news.id,
                    "title": news.title,
                    "summary": news.summary,
                    "ai_title": news.ai_title,
                    "ai_summary": news.ai_summary
                })

        # AI 過濾邏輯保持不變
        prompt = self.filter_prompt_template.format(
            news_list=news_data,
            total_news=total_news,
            recent_published_ig_posts=recent_published_ig_posts
        )

        client = openai.OpenAI()

        try:
            response = client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                temperature=0,
                messages=[
                    {"role": "system", "content": "You are a professional news editor skilled at filtering out published news."},
                    {"role": "user", "content": prompt}
                ],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "output_unpublished_news",
                        "description": "Filter out published news from the original list, keeping the original IDs.",
                        "parameters": ChosenNewsParameters.model_json_schema()
                    }
                }]
            )

            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "output_unpublished_news":
                unpublished_news = ChosenNewsParameters.model_validate_json(tool_call.function.arguments).chosen_news
                logger.info(f"AI 從 {len(news_data)} 條新聞中識別出 {len(unpublished_news)} 條未發布的新聞")
                return unpublished_news
            else:
                logger.error("意外的函數調用")
                return []
        except Exception as e:
            logger.error(f"AI 過濾過程中出錯：{str(e)}")
            return []

    def save_chosen_news_to_database(self, chosen_news):
        with self.SessionLocal() as session:
            news_ids = [item.id for item in chosen_news]
            chosen_news_entry = ChosenNews(news_ids=news_ids)
            session.add(chosen_news_entry)
            session.commit()
            logger.info(f"已將選擇的新聞保存到數據庫，ID: {chosen_news_entry.id}")

    def run(self):
        news_list = self.load_news()
        total_news = len(news_list)
        logger.info(f"載入了 {total_news} 條過去 6 小時內發布的新聞")

        unpublished_news = self.filter_unpublished_news(news_list)
        
        if not unpublished_news:
            logger.warning("沒有未發布的新聞")
            print(f"從 {total_news} 條新聞中沒有找到未發布的新聞")
            return

        chosen_news = self.choose_important_news(unpublished_news)

        if chosen_news:
            logger.info(f"從 {len(unpublished_news)} 條未發布的新聞中選出了 {len(chosen_news)} 條重要新聞：")
            for item in chosen_news:
                print(f"ID: {item.id}, 標題: {item.title}")
            print(f"\n總共從 {len(unpublished_news)} 條未發布的新聞中選出了 {len(chosen_news)} 條重要新聞")

            self.save_chosen_news_to_database(chosen_news)
        else:
            logger.warning("沒有選出任何新聞")
            print(f"從 {len(unpublished_news)} 條未發布的新聞中沒有選出任何重要新聞")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="選擇今天發布的重要新聞")
    parser.add_argument('-n', '--num_chosen', type=int, required=True, help='選擇的重要新聞數量')
    args = parser.parse_args()

    chooser = NewsChooser(args.num_chosen)
    chooser.run()

if __name__ == "__main__":
    main()