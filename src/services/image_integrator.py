import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from src.utils.file_utils import get_image_file_path
from src.utils.database_utils import get_news_by_id
import unicodedata

class ImageIntegrator:
    def __init__(self):
        self.instagram_posts_dir = "./instagram_posts/"
        self.image_dir = "./image/"
        self.title_font_path = "./src/assets/jf-openhuninn-2.0.ttf"
        self.brand_mark_font_path = "./src/assets/Montserrat-SemiBold.ttf"

        # 先定義字體大小
        self.brand_mark_font_size = int(16)
        self.title_font_size = int(56)

        # 然後創建字體對象
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
        self.published_time_bottom_margin = 40

    def get_latest_instagram_csv(self) -> str:
        csv_files = [f for f in os.listdir(self.instagram_posts_dir) if f.endswith('.csv')]
        if not csv_files:
            raise FileNotFoundError("未找到 Instagram CSV 檔案")
        return max(csv_files, key=lambda x: os.path.getctime(os.path.join(self.instagram_posts_dir, x)))

    def load_instagram_posts(self, csv_file: str) -> pd.DataFrame:
        return pd.read_csv(os.path.join(self.instagram_posts_dir, csv_file))

    def find_image_for_post(self, news_id: int) -> str:
        news_data = get_news_by_id(news_id)
        image_path = get_image_file_path(
            media_name=news_data['media_name'],
            feed_name=news_data['feed_name'],
            news_id=news_data['id'],
            title=news_data['title']
        )
        if os.path.exists(image_path):
            return image_path
        return ""

    def integrate_image(self, image_path: str) -> str:
        integrated_image_path = image_path.rsplit('.', 1)[0] + '_integrated.png'
        
        # 開啟圖片
        self.img = Image.open(image_path)

        self.process_title()
        self.draw_background()
        self.draw_title()
        self.draw_brand_mark()
        self.draw_published_time()
        self.draw_white_line()
        self.draw_gradient_square()

        self.img.save(integrated_image_path)
        return integrated_image_path

    def draw_published_time(self):
        draw = ImageDraw.Draw(self.img)
        # 計算發布時間的位置

        # 從background的右下角開始
        x = self.img.width - self.published_time_right_margin - 200
        y = self.img.height - self.published_time_bottom_margin
        # 繪製發布時間
        draw.text((x, y), str(self.published_time), font=self.brand_mark_font, fill=(255, 255, 255))

    def draw_white_line(self):  
        #放一條橫跨整個圖片寬度的白色細線，線高為2px, 距離底部64px
        draw = ImageDraw.Draw(self.img)
        line_y = self.img.height - 60
        draw.line([(0, line_y), (self.img.width, line_y)], fill=(255, 255, 255), width=1)

    def draw_gradient_square(self):
        
        pass

    @staticmethod
    def get_text_width(font, text):
        width = 0
        for char in text:
            # 使用 getbbox 方法獲取每個字元的寬度
            bbox = font.getbbox(char)
            char_width = bbox[2] - bbox[0]  # bbox 返回 (x_min, y_min, x_max, y_max)
            width += char_width
        return width

    def process_title(self):
        
        def get_first_line_threshold(font, ig_title):
            # 計算出臨界點，如果超過這個臨界點，就會換行，回傳臨界點的index
            for i, char in enumerate(ig_title):
                if self.get_text_width(font, ig_title[:i]) > self.title_width_for_draw:
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
            
            if self.get_text_width(self.title_font, first_part) <= self.title_width_for_draw and self.get_text_width(self.title_font, second_part) <= self.title_width_for_draw:
                self.first_line = first_part
                self.second_line = second_part
            # 用第二個標點符號切分，檢查前後兩段是否都小於 17 個字，若都小於則將其切分並放置到第一跟第二行，若只有一段小於則17個字第一行，剩餘第二行
            elif second_split_index != -1:
                first_part = self.ig_title[:second_split_index + 1]
                second_part = self.ig_title[second_split_index + 1:]
                if self.get_text_width(self.title_font, first_part) <= self.title_width_for_draw and self.get_text_width(self.title_font, second_part) <= self.title_width_for_draw:
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

        # 根據 title 的高度，加上本來就固定的 Brand Mark 高度，計算出 background 的高度
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

    def process_ig_title_fullwidth(self, text):
        """將 ig_title 的標點符號轉換成全形，保持數字、%和.為半形"""
        return ''.join([
            char if char.isdigit() or char in ['%', '.'] else
            unicodedata.normalize('NFKC', char).translate({
                ord(c): ord(c) + 0xFEE0 for c in '!"#$&\'()*+,-/:;<=>?@[\\]^_`{|}~'
            })
            for char in text
        ])

    def integrate_ig_images(self):
        latest_csv = self.get_latest_instagram_csv()
        posts_df = self.load_instagram_posts(latest_csv)
        
        for _, row in posts_df.iterrows():
            news_id = row['id']
            self.ig_title = self.process_ig_title_fullwidth(row['ig_title'])
            print(self.ig_title)

            news_data = get_news_by_id(news_id)
            self.published_time = news_data['published_at']
            # 將時間轉換成 2024.05.01 19:24 GMT+8 的格式
            self.published_time = self.published_time.strftime('%Y.%m.d %H:%M GMT+8')

            image_path = self.find_image_for_post(news_id)
            if image_path:
                integrated_image_path = self.integrate_image(image_path)
                print(f"已整合圖片: {integrated_image_path}")

def main():
    integrator = ImageIntegrator()
    try:
        integrator.integrate_ig_images()
        print("圖片整合完成")
    except Exception as e:
        print(f"處理過程中發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()