from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import News, File, InstagramPost
from src.config.settings import DATABASE_URL
import os

def news_image(news_id):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        news = session.query(News).filter(News.id == news_id).first()
        if not news:
            print(f"找不到 ID 為 {news_id} 的新聞")
            return

        file = session.query(File).filter(File.id == news.png_file_id).first()
        if not file:
            print(f"找不到與新聞 ID {news_id} 相關的圖片文件")
            return

        # 確保 ./image 目錄存在
        os.makedirs("./image", exist_ok=True)

        # 將二進制數據寫入文件
        destination = os.path.join("./image", f"{news_id}.png")
        with open(destination, "wb") as f:
            f.write(file.data)

        print(f"圖片已成功保存到 {destination}")

    except Exception as e:
        print(f"獲取圖片時發生錯誤：{e}")
    finally:
        session.close()

def news_content(news_id):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        news = session.query(News).filter(News.id == news_id).first()
        if not news:
            print(f"找不到 ID 為 {news_id} 的新聞")
            return

        file = session.query(File).filter(File.id == news.md_file_id).first()
        if not file:
            print(f"找不到與新聞 ID {news_id} 相關的 Markdown 文件")
            return

        # 確保 ./news 目錄存在
        os.makedirs("./news", exist_ok=True)

        # 將二進制數據寫入文件
        destination = os.path.join("./news", f"{news_id}.md")
        with open(destination, "wb") as f:
            f.write(file.data)

        print(f"Markdown 文件已成功保存到 {destination}")

    except Exception as e:
        print(f"獲取 Markdown 文件時發生錯誤：{e}")
    finally:
        session.close()

def get_instagram_post_image(post_id):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        post = session.query(InstagramPost).filter(InstagramPost.id == post_id).first()
        if not post:
            print(f"找不到 ID 為 {post_id} 的 Instagram 貼文")
            return

        file = session.query(File).filter(File.id == post.integrated_image_id).first()
        if not file:
            print(f"找不到與 Instagram 貼文 ID {post_id} 相關的整合圖片")
            return

        # 確保 ./instagram_images 目錄存在
        os.makedirs("./instagram_images", exist_ok=True)

        # 將二進制數據寫入文件
        destination = os.path.join("./instagram_images", f"{post_id}.png")
        with open(destination, "wb") as f:
            f.write(file.data)

        print(f"Instagram 貼文整合圖片已成功保存到 {destination}")

    except Exception as e:
        print(f"獲取 Instagram 貼文整合圖片時發生錯誤：{e}")
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="新聞文件獲取工具")
    subparsers = parser.add_subparsers(dest="command", help="可用的命令")

    # 獲取新聞圖片的子命令
    image_parser = subparsers.add_parser("image", help="獲取新聞圖片")
    image_parser.add_argument("news_id", type=int, help="新聞的 ID")

    # 獲取新聞內容的子命令
    content_parser = subparsers.add_parser("content", help="獲取新聞 Markdown 內容")
    content_parser.add_argument("news_id", type=int, help="新聞的 ID")

    # 獲取 Instagram 貼文整合圖片的子命令
    ig_image_parser = subparsers.add_parser("ig_image", help="獲取 Instagram 貼文整合圖片")
    ig_image_parser.add_argument("post_id", type=int, help="Instagram 貼文的 ID")

    args = parser.parse_args()

    if args.command == "image":
        news_image(args.news_id)
    elif args.command == "content":
        news_content(args.news_id)
    elif args.command == "ig_image":
        get_instagram_post_image(args.post_id)
    else:
        parser.print_help()