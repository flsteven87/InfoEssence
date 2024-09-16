from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import joinedload
from src.database.models import News, ChosenNews  # 假設您有一個 News 模型
from src.config.settings import DATABASE_URL
from src.utils.file_utils import get_content_file_path

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_news_by_id(db: Session, news_id: int) -> News:
    return db.query(News).options(joinedload(News.md_file)).filter(News.id == news_id).first()

def get_latest_chosen_news(db: Session):
    return db.query(ChosenNews).order_by(ChosenNews.timestamp.desc()).first()