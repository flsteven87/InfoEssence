import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import DATABASE_URL
import logging
from datetime import timedelta
import os
import pandas as pd
from utils.file_utils import sanitize_filename
import html

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 連接到數據庫
@st.cache_resource
def init_connection():
    return psycopg2.connect(DATABASE_URL)

conn = init_connection()

# 查詢數據
@st.cache_data(ttl=600)
def run_query(query, params=None):
    global conn
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()
    except psycopg2.Error as e:
        logger.error(f"資料庫錯誤: {e}")
        st.error("發生資料庫錯誤，正在嘗試重新連接...")
        conn.rollback()  # 回滾交易
        conn = init_connection()  # 重新建立連接
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"試後仍然發生錯誤: {e}")
            st.error("無法連接到資料庫，請稍後再試。")
            return []

# 新增函數：獲取最新的 CSV 檔案
def get_latest_csv():
    csv_dir = "chosen_news/"
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    if not csv_files:
        return None
    latest_csv = max(csv_files, key=lambda x: os.path.getctime(os.path.join(csv_dir, x)))
    return os.path.join(csv_dir, latest_csv)

# 修改函數：讀取 CSV 檔案並返回重要新聞的字典
@st.cache_data(ttl=600)
def get_important_news():
    csv_path = get_latest_csv()
    if not csv_path:
        logger.warning("未找到 CSV 檔案")
        return {}, None
    try:
        df = pd.read_csv(csv_path)
        if 'id' not in df.columns:
            logger.error(f"CSV 檔案 {csv_path} 中缺少必要欄位")
            st.warning("無法載入重要新聞列表，請檢查 CSV 檔案格式")
            return {}, os.path.basename(csv_path)
        # 將 id 轉換為字符串
        df['id'] = df['id'].astype(str)
        important_news = df.set_index('id').to_dict(orient='index')
        logger.info(f"已載入 {len(important_news)} 條重要新聞")
        return important_news, os.path.basename(csv_path)
    except Exception as e:
        logger.error(f"讀取 CSV 檔案時發生錯誤: {e}")
        st.error("讀取重要新聞列表時發生錯誤")
        return {}, os.path.basename(csv_path)

# 新增函數：獲取最新的 Instagram CSV 檔案
def get_latest_instagram_csv():
    csv_dir = "./instagram_posts/"
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    if not csv_files:
        return None
    latest_csv = max(csv_files, key=lambda x: os.path.getctime(os.path.join(csv_dir, x)))
    return os.path.join(csv_dir, latest_csv)

# 新增函數：讀取 Instagram CSV 檔案並返回映射
@st.cache_data(ttl=600)
def get_instagram_posts():
    csv_path = get_latest_instagram_csv()
    if not csv_path:
        logger.warning("未找到 Instagram CSV 檔案")
        return {}, None
    try:
        df = pd.read_csv(csv_path)
        if 'id' not in df.columns or 'ig_title' not in df.columns or 'ig_caption' not in df.columns:
            logger.error(f"Instagram CSV 檔案 {csv_path} 中缺少必要欄位")
            st.warning("無法載入 Instagram 貼文列表，請檢查 CSV 檔案格式")
            return {}, os.path.basename(csv_path)
        df['id'] = df['id'].astype(str)
        instagram_posts = df.set_index('id').to_dict(orient='index')
        logger.info(f"已載入 {len(instagram_posts)} 條 Instagram 貼文")
        return instagram_posts, os.path.basename(csv_path)
    except Exception as e:
        logger.error(f"讀取 Instagram CSV 檔案時發生錯誤: {e}")
        st.error("讀取 Instagram 貼文列表時發生錯誤")
        return {}, os.path.basename(csv_path)

# 主應用
def main():
    st.title("GlobalNews for Taiwan")

    # 側邊欄
    st.sidebar.title("篩選選項")
    
    media_query = "SELECT DISTINCT media.name FROM news JOIN media ON news.media_id = media.id"
    media_list = [row['name'] for row in run_query(media_query) if row]
    
    if not media_list:
        st.sidebar.error("無法載入媒體列表")
        return

    selected_media = st.sidebar.multiselect("選擇媒體", media_list)

    # 日期範圍選擇
    start_date = st.sidebar.date_input("開始日期")
    end_date = st.sidebar.date_input("結束日期")

    # 構建查詢
    query = """
    SELECT news.id, news.title, news.ai_title, news.ai_summary, news.link, 
           media.name as media_name, feeds.name as feed_name, news.published_at
    FROM news
    JOIN media ON news.media_id = media.id
    JOIN feeds ON news.feed_id = feeds.id
    WHERE news.published_at >= %s AND news.published_at < %s
    """
    # 將結束日期加��天，以包含整個結束日期
    params = [start_date, end_date + timedelta(days=1)]

    if selected_media:
        query += " AND media.name IN %s"
        params.append(tuple(selected_media))

    query += " ORDER BY news.published_at DESC"

    # 執行查詢
    news_items = run_query(query, params)

    # 獲取重要新聞的字典和 CSV 檔案名稱
    important_news, csv_filename = get_important_news()
    
    # 獲取 Instagram 貼文的字典和 CSV 檔案名稱
    instagram_posts, instagram_csv_filename = get_instagram_posts()

    # 顯示正在使用的 CSV 檔案名稱
    if csv_filename:
        st.sidebar.info(f"正在使用的重要新聞 CSV 檔案: {csv_filename}")
    else:
        st.sidebar.warning("未找到重要新聞 CSV 檔案")

    if instagram_csv_filename:
        st.sidebar.info(f"正在使用的 Instagram CSV 檔案: {instagram_csv_filename}")
    else:
        st.sidebar.warning("未找到 Instagram CSV 檔案")

    if not important_news:
        st.warning("未找到重要新聞，請確保 CSV 檔案存在且格式正確")

    # 顯示新聞
    for item in news_items:
        item_id = str(item['id'])
        is_important = item_id in important_news
        has_instagram_post = item_id in instagram_posts
        
        # 格式化發布時間
        published_time = item['published_at'].strftime('%Y-%m-%d %H:%M')
        
        title_display = f"{item['id']} - {item['ai_title']} - {published_time}"
        if is_important:
            title_display += " 🔥"
        if has_instagram_post:
            title_display += " 📸"

        with st.expander(title_display):
            # 如果是重要新聞，顯示圖片
            if is_important:
                image_dir = "./image/"
                media_dir = sanitize_filename(item['media_name'])
                feed_dir = sanitize_filename(item.get('feed_name', ''))
                image_path = os.path.join(image_dir, media_dir, feed_dir)
                image_files = [f for f in os.listdir(image_path) if f.startswith(f"{item['id']}_") and f.endswith("_integrated.png")]
                if image_files:
                    image_file = image_files[0]
                    full_image_path = os.path.join(image_path, image_file)
                    st.image(full_image_path, caption="新聞相關圖片")

            # 顯示標題和摘要
            if has_instagram_post:
                display_title = instagram_posts[item_id]['ig_title']
                display_summary = instagram_posts[item_id]['ig_caption']
            else:
                display_title = item['ai_title']
                display_summary = item['ai_summary']

            # 確保 display_title 和 display_summary 不是 None
            display_title = str(display_title) if display_title is not None else ""
            display_summary = str(display_summary) if display_summary is not None else ""

            # 處理摘要中的 hashtag
            hashtag_index = display_summary.find('#')
            if hashtag_index != -1:
                display_summary = display_summary[:hashtag_index] + '<br><br>' + display_summary[hashtag_index:]
            else:
                display_summary += '<br><br>'
            display_summary += '#GlobalNewsTaiwan'

            # 在顯示之前進行 HTML 轉義
            display_title = html.escape(display_title)
            display_summary = html.escape(display_summary).replace('&lt;br&gt;', '<br>')
            media_name = html.escape(item['media_name'])
            link = html.escape(item['link'])

            st.write(f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px;">
                <h3>{display_title}</h3>
                <p>{display_summary}</p>
                <p><strong>來源:</strong> {media_name}</p>
                <p><strong>發布時間:</strong> {published_time}</p>
                <p><a href="{link}" target="_blank">閱讀原文</a></p>
            </div>
            """, unsafe_allow_html=True)

    # 在頁面底部顯示載入的重要新聞和 Instagram 貼文數量
    st.info(f"已載入 {len(important_news)} 條重要新聞和 {len(instagram_posts)} 條 Instagram 貼文")

if __name__ == "__main__":
    main()
