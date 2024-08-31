import psycopg2
from src.config.settings import DATABASE_URL

def query_tables():
    try:
        # 連接到資料庫
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 執行查詢以獲取所有表格
        cursor.execute("""
            SELECT content
            FROM news
            LIMIT 1
        """)

        # 獲取結果
        tables = cursor.fetchall()

        # 打印表格名稱
        print("資料庫中的表格:")
        for table in tables:
            print(table[0])

    except (Exception, psycopg2.Error) as error:
        print(f"連接到資料庫時發生錯誤: {error}")

    finally:
        # 關閉資料庫連接
        if conn:
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")

if __name__ == "__main__":
    query_tables()