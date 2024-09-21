from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.config.settings import DATABASE_URL
import argparse
import logging

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    logging.info("數據庫已初始化")

def create_tables():
    Base.metadata.create_all(engine)
    logging.info("數據庫已創建")

def truncate_tables():
    with SessionLocal() as db:
        tables = ['news', 'feeds', 'media', 'files']
        for table in tables:
            db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        db.commit()
    logging.info("所有表格已清空")

def main():
    parser = argparse.ArgumentParser(description="數據庫管理工具")
    parser.add_argument('action', choices=['init', 'truncate'], help="選擇操作：init（初始化數據庫）或 truncate（清空表格）")
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_db()
    elif args.action == 'truncate':
        truncate_tables()
    
    logging.info(f"{args.action} 操作完成")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()