import os
import re

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def get_content_file_path(media_name, feed_name, news_id, title):
    base_path = "./news"
    sanitized_media_name = sanitize_filename(media_name)
    sanitized_feed_name = sanitize_filename(feed_name)
    sanitized_title = sanitize_filename(title)
    
    directory = os.path.join(base_path, sanitized_media_name, sanitized_feed_name)
    filename = f"{news_id}_{sanitized_title[:50]}.md"
    return os.path.join(directory, filename)

def get_image_file_path(media_name, feed_name, news_id, title):
    base_path = "./image"
    sanitized_media_name = sanitize_filename(media_name)
    sanitized_feed_name = sanitize_filename(feed_name)
    sanitized_title = sanitize_filename(title)
    
    directory = os.path.join(base_path, sanitized_media_name, sanitized_feed_name)
    filename = f"{news_id}_{sanitized_title[:50]}.png"
    return os.path.join(directory, filename)

def get_text_width(font, text):
    width = 0
    for char in text:
    # 使用 getbbox 方法獲取每個字元的寬度
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]  # bbox 返回 (x_min, y_min, x_max, y_max)
        width += char_width
    return width
