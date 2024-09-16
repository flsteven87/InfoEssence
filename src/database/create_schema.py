# file: create_schema.py

from sqlalchemy import create_engine
from src.database.models import Base  # 假設您的模型定義在這個位置
import os

# 獲取數據庫 URL
DATABASE_URL = os.getenv('DATABASE_URL')

# Heroku 的 PostgreSQL URL 需要做一個小調整
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 創建數據庫引擎
engine = create_engine(DATABASE_URL)

def create_schema():
    # 創建所有定義在 Base 中的表
    Base.metadata.create_all(engine)
    print("數據庫 schema 已成功創建！")

if __name__ == "__main__":
    create_schema()