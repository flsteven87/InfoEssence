import os
import requests
from dotenv import load_dotenv, set_key
import logging
from datetime import datetime

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加載環境變量
load_dotenv()

def refresh_instagram_token():
    # 從 .env 文件讀取必要的信息
    app_id = os.getenv('FB_APP_ID')
    app_secret = os.getenv('FB_APP_SECRET')
    current_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')

    if not all([app_id, app_secret, current_token]):
        logging.error("Missing required environment variables.")
        return

    # 構建 API 請求 URL
    url = f"https://graph.facebook.com/v12.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": current_token
    }

    try:
        # 發送請求以刷新 token
        response = requests.get(url, params=params)
        response.raise_for_status()  # 如果請求失敗，這將引發異常
        new_token = response.json()["access_token"]

        # 更新 .env 文件中的 token
        env_path = '.env'
        set_key(env_path, 'INSTAGRAM_ACCESS_TOKEN', new_token)

        logging.info(f"Instagram access token successfully refreshed at {datetime.now()}")
    except requests.RequestException as e:
        logging.error(f"Error refreshing token: {e}")
    except KeyError:
        logging.error("Unexpected response format from Facebook API")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    refresh_instagram_token()