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
