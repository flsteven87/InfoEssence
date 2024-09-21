import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import DATABASE_URL
import logging
from datetime import timedelta
import os
import base64
import html
from io import BytesIO
from PIL import Image

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 連接到數據庫
@st.cache_resource
def init_connection():
    return psycopg2.connect(DATABASE_URL)

conn = init_connection()

# 一般查詢函數
@st.cache_data(ttl=600)
def run_query(query, params=None):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

# 二進制數據查詢函數
def run_binary_query(query, params=None):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        result = cur.fetchone()
        if result:
            return {k: v for k, v in result.items()}
    return None

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

    # 修改查詢以包含所需的所有信息
    query = """
    SELECT n.id, n.title, n.ai_title, n.ai_summary, n.link, 
           m.name as media_name, f.name as feed_name, n.published_at,
           ip.ig_title, ip.ig_caption, ip.integrated_image_id,
           n.md_file_id, n.png_file_id,
           CASE WHEN p.id IS NOT NULL THEN true ELSE false END as is_published
    FROM news n
    JOIN media m ON n.media_id = m.id
    JOIN feeds f ON n.feed_id = f.id
    LEFT JOIN instagram_posts ip ON n.id = ip.news_id
    LEFT JOIN published p ON n.id = p.news_id
    WHERE n.published_at >= %s AND n.published_at < %s
    """
    # 將結束日期加天，以包含整個結束日期
    params = [start_date, end_date + timedelta(days=1)]

    if selected_media:
        query += " AND m.name IN %s"
        params.append(tuple(selected_media))

    query += " ORDER BY n.published_at DESC"

    # 執行查詢
    news_items = run_query(query, params)

    # 顯示新聞
    for item in news_items:
        # 格式化發布時間
        published_time = item['published_at'].strftime('%Y-%m-%d %H:%M')
        
        # 決定顯示的標題和摘要
        display_title = item['ig_title'] if item['ig_title'] else item['ai_title']
        display_summary = item['ig_caption'] if item['ig_caption'] else item['ai_summary']
        
        # 添加特殊符號
        title_display = f"{item['id']} - {display_title} - {published_time}"
        if item['is_published']:
            title_display += " 🚀"  # 已發布的符號
        if item['ig_title']:
            title_display += " 📸"  # Instagram 帖子的符號

        with st.expander(title_display):
            # 顯示圖片
            image_id = item['integrated_image_id'] if item['integrated_image_id'] else item['png_file_id']
            if image_id:
                image_query = "SELECT data, content_type FROM files WHERE id = %s"
                image_data = run_binary_query(image_query, (image_id,))
                if image_data and image_data['data']:
                    try:
                        image = Image.open(BytesIO(bytes(image_data['data'])))
                        st.image(image, caption="新聞相關圖片")
                    except Exception as e:
                        st.error(f"無法載入圖片: {e}")

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

            # 顯示 Markdown 內容（預設不展開）
            if item['md_file_id']:
                md_query = "SELECT data FROM files WHERE id = %s"
                md_data = run_binary_query(md_query, (item['md_file_id'],))
                if md_data and md_data['data']:
                    try:
                        md_content = bytes(md_data['data']).decode('utf-8')
                        with st.expander("顯示完整內容"):
                            st.markdown(md_content)
                    except Exception as e:
                        st.error(f"無法載入 Markdown 內容: {e}")

if __name__ == "__main__":
    main()
