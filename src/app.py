import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import DATABASE_URL

# 連接到數據庫
@st.cache_resource
def init_connection():
    return psycopg2.connect(DATABASE_URL)

conn = init_connection()

# 查詢數據
@st.cache_data(ttl=600)
def run_query(query):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        return cur.fetchall()

# 主應用
def main():
    st.title("InfoEssence 新聞摘要")

    # 側邊欄
    st.sidebar.title("篩選選項")
    media_query = "SELECT DISTINCT media.name FROM news JOIN media ON news.media_id = media.id"
    media_list = [row['name'] for row in run_query(media_query)]
    selected_media = st.sidebar.multiselect("選擇媒體", media_list)

    # 構建查詢
    query = """
    SELECT news.title, news.ai_title, news.ai_summary, news.link, media.name as media_name
    FROM news
    JOIN media ON news.media_id = media.id
    """
    if selected_media:
        query += f" WHERE media.name IN {tuple(selected_media)}"
    query += " ORDER BY news.created_at DESC LIMIT 50"

    # 執行查詢
    news_items = run_query(query)

    # 顯示新聞
    for item in news_items:
        with st.expander(item['title']):
            st.markdown(f"""
            {item['ai_title']}

            {item['ai_summary']}

            **來源:** {item['media_name']}

            [閱讀原文]({item['link']})
            """)

if __name__ == "__main__":
    main()