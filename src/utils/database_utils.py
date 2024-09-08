from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import News  # 假設您有一個 News 模型
from src.config.settings import DATABASE_URL
from src.utils.file_utils import get_content_file_path

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_news_by_id(news_id: int) -> News:
    with Session() as session:
        news = session.query(News).filter(News.id == news_id).first()
        if not news:
            raise ValueError(f"找不到 ID 為 {news_id} 的新聞")
        
        # 構建 .md 檔案路徑
        file_path = get_content_file_path(
            media_name=news.media.name,
            feed_name=news.feed.name,
            news_id=news.id,
            title=news.title
        )
        
        # 讀取 .md 檔案內容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = "無法找到對應的內容文件"
        
        # 創建一個包含所需資訊的字典
        news_data = {
            "id": news.id,
            "title": news.title,
            "summary": news.summary,
            "content": content,
            "ai_title": news.ai_title,
            "ai_summary": news.ai_summary,
            "published_at": news.published_at,
            "media_name": news.media.name,
            "feed_name": news.feed.name
        }
        
        return news_data