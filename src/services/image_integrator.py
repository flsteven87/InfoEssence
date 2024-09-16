import os
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, desc
from src.config.settings import DATABASE_URL
from src.database.models import ChosenNews, InstagramPost, News, File
from src.database.operations import upsert_file, upsert_ig_post_with_png
from src.utils.file_utils import get_text_width
import io
import hashlib

class ImageIntegrator:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.title_font_path = "./src/assets/jf-openhuninn-2.0.ttf"
        self.brand_mark_font_path = "./src/assets/Montserrat-SemiBold.ttf"

        # 定義字體大小
        self.brand_mark_font_size = int(16)
        self.title_font_size = int(56)

        # 創建字體對象
        self.brand_mark_font = ImageFont.truetype(self.brand_mark_font_path, self.brand_mark_font_size)
        self.title_font = ImageFont.truetype(self.title_font_path, self.title_font_size)

        self.brand_mark = 'GLOBAL NEWS for TAIWAN'
        self.brand_mark_up_margin = 20
        self.brand_mark_left_margin = 40

        self.title_up_margin = 20
        self.title_left_margin = 40
        self.title_right_margin = 40
        self.title_bottom_margin = 80
        self.title_line_space = self.title_font_size * 0.2

        # 計算 title 的寬度 
        self.title_width = 1024 - self.title_left_margin - self.title_right_margin
        self.title_width_for_draw = self.title_width - 30
        # 計算 title 的高度
        self.title_height = int(self.title_font_size * 2 + self.title_line_space)

        self.published_time_font_size = int(30)
        self.published_time_font = ImageFont.truetype(self.brand_mark_font_path, self.published_time_font_size)
        self.published_time_right_margin = 28
        self.published_time_bottom_margin = 30

    def get_latest_chosen_news(self, session: Session):
        return session.query(ChosenNews).order_by(desc(ChosenNews.timestamp)).first()

    def get_instagram_posts(self, session: Session, chosen_news_id: int):
        return session.query(InstagramPost).filter(InstagramPost.chosen_news_id == chosen_news_id).all()

    def get_news_image(self, session: Session, news_id: int):
        news = session.query(News).filter(News.id == news_id).first()
        if news and news.png_file_id:
            file = session.query(File).filter(File.id == news.png_file_id).first()
            if file:
                return Image.open(io.BytesIO(file.data))
        return None

    def integrate_image(self, news_id: int, ig_title: str, published_time: str):
        with Session(self.engine) as session:
            img = self.get_news_image(session, news_id)
            if img is None:
                raise ValueError(f"無法找到新聞 ID {news_id} 的圖片")

            self.img = img
            self.ig_title = ig_title
            self.published_time = published_time

            self.process_title()
            self.draw_background()
            self.draw_title()
            self.draw_brand_mark()
            self.draw_published_time()
            self.draw_white_line()
            self.draw_gradient_square()

            # 將圖片保存到內存中
            img_byte_arr = io.BytesIO()
            self.img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            return img_byte_arr

    def integrate_ig_images(self):
        with Session(self.engine) as session:
            latest_chosen_news = self.get_latest_chosen_news(session)
            if not latest_chosen_news:
                print("沒有找到最新的已選新聞")
                return

            instagram_posts = self.get_instagram_posts(session, latest_chosen_news.id)
            for post in instagram_posts:
                news = session.query(News).filter(News.id == post.news_id).first()
                if news:
                    integrated_image = self.integrate_image(post.news_id, post.ig_title, news.published_at.strftime('%Y.%m.%d %H:%M GMT+8'))
                    
                    # 使用新的 upsert_ig_post_with_png 函數
                    post_id = upsert_ig_post_with_png(session, post.id, integrated_image)
                    
                    print(f"已整合並上傳圖片: Instagram 貼文 ID {post_id}, 新聞 ID {post.news_id}")

    def process_title(self):

        def get_first_line_threshold(font, ig_title):
            # 計算出臨界點，如果超過這個臨界點，就會換行，回傳臨界點的index
            for i, char in enumerate(ig_title):
                if get_text_width(font, ig_title[:i]) > self.title_width_for_draw:
                    return i
            return len(ig_title)

        first_line_threshold = get_first_line_threshold(self.title_font, self.ig_title)

        # 定義中文標點符號列表
        punctuation = '，：；。？！-｜'
        
        # 尋找第一個出現的標點符號
        split_index = next((i for i, char in enumerate(self.ig_title) if char in punctuation), -1)

        # 尋找第二個出現的標點符號
        second_split_index = -1
        if split_index != -1:
            second_split_index = next((i for i, char in enumerate(self.ig_title[split_index+1:]) if char in punctuation), -1)
            if second_split_index != -1:
                second_split_index += split_index + 1
        
        # 用第一個標點符號切分，檢查前後兩段是否都小於 17 個字，若都小於則將其切分並放置到第一跟第二行，若只有一段小於則17個字第一行，剩餘第二行
        if split_index != -1:
            first_part = self.ig_title[:split_index + 1]
            second_part = self.ig_title[split_index + 1:]
            
            if get_text_width(self.title_font, first_part) <= self.title_width_for_draw and get_text_width(self.title_font, second_part) <= self.title_width_for_draw:
                self.first_line = first_part
                self.second_line = second_part
            # 用第二個標點符號切分，檢查前後兩段是否都小於 17 個字，若都小於則將其切分並放置到第一跟第二行，若只有一段小於則17個字第一行，剩餘第二行
            elif second_split_index != -1:
                first_part = self.ig_title[:second_split_index + 1]
                second_part = self.ig_title[second_split_index + 1:]
                if get_text_width(self.title_font, first_part) <= self.title_width_for_draw and get_text_width(self.title_font, second_part) <= self.title_width_for_draw:
                    self.first_line = first_part
                    self.second_line = second_part
                else:
                    self.first_line = self.ig_title[:first_line_threshold]
                    self.second_line = self.ig_title[first_line_threshold:]
            else:
                self.first_line = self.ig_title[:first_line_threshold]
                self.second_line = self.ig_title[first_line_threshold:]
        else:
            # 如果沒有找到標點符號，直接分割
            self.first_line = self.ig_title[:first_line_threshold]
            self.second_line = self.ig_title[first_line_threshold:]

        # 將分行後的標題存入 title_list
        self.title_list = [self.first_line, self.second_line]

    def draw_background(self):

        # 根據 title 的高度，加上本就固定的 Brand Mark 高度，計算出 background 的高度
        self.background_height = int(self.title_height + self.brand_mark_up_margin + self.brand_mark_font_size + self.title_up_margin + self.title_bottom_margin)
        # 寬度跟圖片一樣
        self.background_width = self.img.width
        
        # 創建一個新的透明圖層
        self.background = Image.new('RGBA', (self.background_width, self.background_height), (0, 0, 0, 0))
        
        # 在新圖層上繪製半透明黑色矩形
        draw = ImageDraw.Draw(self.background)
        draw.rectangle([(0, 0), (self.background_width, self.background_height)], fill=(0, 0, 0, 150))
        
        # 將背景圖層貼到原圖的底部
        self.img = self.img.convert('RGBA')
        self.img.paste(self.background, (0, self.img.height - self.background_height), self.background)

    def draw_title(self):
        draw = ImageDraw.Draw(self.img)
        
        # 計算標題的起始位置（從底部往上）
        start_y = int(self.img.height - self.title_bottom_margin - self.title_height)

        # 將title_list 的文字繪製到圖片上
        for i, line in enumerate(self.title_list):
            # 修改這行，確保使用整數
            y_position = int(start_y + i * self.title_font_size + i * self.title_line_space)
            draw.text((self.title_left_margin, y_position), line, font=self.title_font, fill=(255, 255, 255))

    def draw_brand_mark(self):
        draw = ImageDraw.Draw(self.img)
        
        # 計算品牌標記的位置
        x = self.brand_mark_left_margin
        y = self.img.height - self.background_height + self.brand_mark_up_margin
        
        # 繪製品牌標記
        draw.text((x, y), self.brand_mark, font=self.brand_mark_font, fill=(255, 255, 255))

    def draw_published_time(self):
        draw = ImageDraw.Draw(self.img)
        
        # 計算發布時間的置
        x = self.img.width - self.published_time_right_margin - get_text_width(self.published_time_font, self.published_time)
        y = self.img.height - self.published_time_bottom_margin - self.published_time_font_size
        
        # 繪製發布時間
        draw.text((x, y), self.published_time, font=self.published_time_font, fill=(255, 255, 255))

    def draw_white_line(self):  
        #放一條橫跨整個圖片寬度的白色細線，線高為2px, 距離底部64px
        draw = ImageDraw.Draw(self.img)
        line_y = self.img.height - 60
        draw.line([(0, line_y), (self.img.width, line_y)], fill=(255, 255, 255), width=1)

    def draw_gradient_square(self):
        # 保持原有的實現
        pass

def main():
    integrator = ImageIntegrator()
    try:
        integrator.integrate_ig_images()
        print("圖片整合完成")
    except Exception as e:
        print(f"處理過程中發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()