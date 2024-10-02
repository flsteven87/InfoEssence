import requests
import time
import logging
from ratelimit import limits, sleep_and_retry
from src.config.settings import JINA_API_URL
from src.database.operations import upsert_news_with_content
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ContentFetchException(Exception):
    """自定義內容獲取異常類"""
    pass

class ContentFetcher:
    def __init__(self, db: Session):
        self.db = db
        self.jina_api_url = JINA_API_URL

    @sleep_and_retry
    @limits(calls=20, period=60)  # 每分鐘 20 次請求
    def fetch_and_save_content(self, url: str, news_data: dict) -> str:
        jina_reader_url = f"{self.jina_api_url}/{url}"
        
        for attempt in range(2):  # 最多嘗試 2 次
            try:
                response = self._make_request(jina_reader_url)
                if response.status_code == 200:
                    content = response.text
                    news_id = upsert_news_with_content(self.db, news_data, content)
                    self._log_fetched_news(news_data['title'])
                    return content
                
                # 處理非 200 狀態碼
                response.raise_for_status()
            except requests.RequestException as e:
                self._handle_request_exception(e, attempt, url)

        raise ContentFetchException(f"多次嘗試後仍無法獲取內容：URL：{url}")

    def _make_request(self, url):
        return requests.get(url, timeout=100)

    def _handle_successful_response(self, response, url):
        logger.info(f"成功獲取內容：{url}")
        time.sleep(3)  # 每次成功請求後休眠 3 秒
        return response.text

    def _handle_request_exception(self, e, attempt, url):
        if "429" in str(e):
            logger.warning(f"達到速率限制，增加休眠時間。嘗試次數：{attempt + 1}")
            time.sleep(60 * (attempt + 1))  # 隨著嘗試次數增加休眠時間
        elif "451" in str(e):
            logger.error(f"爬取內容失敗：URL：{url} - 錯誤：{e}")
            time.sleep(3)
        else:
            logger.error(f"爬取內容失敗：URL：{url} - 錯誤：{e}")
            time.sleep(10)

    def _log_fetched_news(self, title):
        logger.info(f"成功爬取新聞：{title}")
