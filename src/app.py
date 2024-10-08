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
import psycopg2.pool

# 獲取當前腳本的目錄
current_dir = os.path.dirname(os.path.abspath(__file__))
# 構建 logo 文件的路徑
logo_path = os.path.join(current_dir, 'assets', 'globalnews_logo.jpg')

# 設置頁面配置
st.set_page_config(
    page_title="GlobalNews for Taiwan",
    page_icon=logo_path
)

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用連接池
@st.cache_resource
def init_connection_pool():
    return psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)

pool = init_connection_pool()

# 一般查詢函數
def run_query(query, params=None):
    with pool.getconn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            result = [dict(row) for row in cur.fetchall()]
        pool.putconn(conn)
    return result

# ���改二進制數據查詢函數
def run_binary_query(query, params=None):
    with pool.getconn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            result = cur.fetchone()
        pool.putconn(conn)
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

    # 新增：篩選有圖片的帖子（Instagram 帖子），預設為打勾
    only_instagram = st.sidebar.checkbox("僅顯示有圖片的新聞", value=True)

    # 獲取所有可用的 chosen_news.id
    chosen_news_query = "SELECT id, timestamp FROM chosen_news ORDER BY timestamp DESC"
    chosen_news_options = run_query(chosen_news_query)
    
    # 創建選項列表，包含時間戳
    chosen_news_list = [f"{row['id']} - {row['timestamp']}" for row in chosen_news_options]
    chosen_news_list.insert(0, "")  # 添加一個空選項

    # 新增：下拉式選單選擇 chosen_news.id
    selected_chosen_news = st.sidebar.selectbox("選擇 Chosen News（可選）", chosen_news_list)
    
    # 從選擇中提取 ID
    selected_chosen_news_id = selected_chosen_news.split(" - ")[0] if selected_chosen_news else None

    # 修改查詢以包含所需的所有信息
    query = """
    SELECT DISTINCT n.id, n.title, n.ai_title, n.ai_summary, n.link, 
           m.name as media_name, f.name as feed_name, n.published_at,
           ip.ig_title, ip.ig_caption, ip.integrated_image_id,
           n.md_file_id, n.png_file_id,
           CASE WHEN p.id IS NOT NULL THEN true ELSE false END as is_published
    FROM news n
    JOIN media m ON n.media_id = m.id
    JOIN feeds f ON n.feed_id = f.id
    LEFT JOIN instagram_posts ip ON n.id = ip.news_id
    LEFT JOIN published p ON n.id = p.news_id
    LEFT JOIN chosen_news cn ON n.id = ANY(cn.news_ids)
    WHERE n.published_at AT TIME ZONE 'UTC' >= %s 
      AND n.published_at AT TIME ZONE 'UTC' < %s
    """
    # 結束日期加天，以包含整個結束日期
    params = [start_date, end_date + timedelta(days=1)]

    if selected_media:
        query += " AND m.name IN %s"
        params.append(tuple(selected_media))

    # 新增：如果選擇只顯示 Instagram 帖子，添加相應的條件
    if only_instagram:
        query += " AND ip.id IS NOT NULL"

    # 新增：如果選擇了特定的 chosen_news.id，添加相應的條件
    if selected_chosen_news_id:
        query += " AND cn.id = %s"
        params.append(selected_chosen_news_id)

    query += " ORDER BY n.published_at DESC"

    # 執行查詢
    news_items = run_query(query, params)

    # 在顯示新聞之前去重
    seen_ids = set()
    unique_news_items = []
    for item in news_items:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_news_items.append(item)

    # 顯示新聞
    for item in unique_news_items:
        # 格式化發布時間
        published_time = item['published_at'].strftime('%Y-%m-%d %H:%M')
        
        # 決定顯示的標題和摘要
        display_title = item['ig_title'] if item['ig_title'] else item['ai_title']
        display_summary = item['ig_caption'] if item['ig_caption'] else item['ai_summary']
        
        # 修改這裡，移除 item['id']
        title_display = f"{display_title} - {published_time}"
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

            # 提供 Markdown 文件下載
            if item['md_file_id']:
                md_query = "SELECT data FROM files WHERE id = %s"
                md_data = run_binary_query(md_query, (item['md_file_id'],))
                if md_data and md_data['data']:
                    try:
                        md_content = bytes(md_data['data']).decode('utf-8')
                        md_filename = f"news_{item['id']}.md"
                        st.download_button(
                            label="下載完整內容 (Markdown)",
                            data=md_content,
                            file_name=md_filename,
                            mime="text/markdown"
                        )
                    except Exception as e:
                        st.error(f"無法準備 Markdown 文件下載: {e}")

    # 移除了這裡的分隔線
    # st.markdown("---")

if __name__ == "__main__":
    main()
