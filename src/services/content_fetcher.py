import requests
import time
import random
import logging
from ratelimit import limits, sleep_and_retry
from bs4 import BeautifulSoup
from src.config.settings import JINA_API_URL, USE_PROXY, PROXIES, update_proxies
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
        self.use_proxy = USE_PROXY
        self.proxies = PROXIES

    @sleep_and_retry
    @limits(calls=20, period=60)  # 每分鐘 20 次請求
    def fetch_and_save_content(self, url: str, news_data: dict) -> str:
        jina_reader_url = f"{self.jina_api_url}/{url}"
        
        for attempt in range(2):  # 最多嘗試 2 次
            try:
                # 首先嘗試不使用代理
                response = self._make_request(jina_reader_url)
                if response.status_code == 200:
                    content = response.text
                    news_id = upsert_news_with_content(self.db, news_data, content)
                    return content
                
                # 如果狀態碼不是 200，嘗試使用代理
                if self.use_proxy:
                    response = self._try_proxies(jina_reader_url)
                    if response:
                        content = response.text
                        news_id = upsert_news_with_content(self.db, news_data, content)
                        return content
                
                # 處理非 200 狀態碼
                response.raise_for_status()
            except requests.RequestException as e:
                self._handle_request_exception(e, attempt, url)

        raise ContentFetchException(f"多次嘗試後仍無法獲取內容：URL：{url}")

    def _make_request(self, url, proxy=None):
        if proxy:
            return requests.get(url, proxies={'http': proxy}, timeout=100)
        return requests.get(url, timeout=100)

    def _try_proxies(self, url):
        for _ in range(len(self.proxies)):
            proxy = random.choice(self.proxies)
            try:
                response = self._make_request(url, proxy['http'])
                if response.status_code == 200:
                    logger.info(f"使用代理成功獲取內容：{url}")
                    return response
            except requests.RequestException as e:
                logger.warning(f"使用代理 {proxy['http']} 失敗：{e}")
        logger.error("所有代理都失敗，無法獲取內容")
        return None

    def _handle_successful_response(self, response, url):
        logger.info(f"成功獲取內容：{url}")
        time.sleep(3)  # 每次成功請求後休眠 3 秒
        return response.text

    def _handle_request_exception(self, e, attempt, url):
        if "429" in str(e):
            logger.warning(f"達到速率限制，增加休眠時間。嘗試次數：{attempt + 1}")
            time.sleep(60 * (attempt + 1))  # 隨著嘗試次數增加休眠時間
        elif "451" in str(e):
            logger.error(f"獲取內容失敗：URL：{url} - 錯誤：{e}")
            time.sleep(3)
        else:
            logger.error(f"獲取內容失敗：URL：{url} - 錯誤：{e}")
            time.sleep(10)

    def update_proxy_list(self):
        url = "https://free-proxy-list.net/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        proxies = []
        table = soup.find("table", attrs={"class": "table table-striped table-bordered"})
        if table:
            for row in table.find_all("tr")[1:]:  # 跳過表頭
                tds = row.find_all("td")
                if len(tds) >= 8:
                    google_support = tds[5].text.strip()  # 第 6 欄：Google 支援狀態
                    https_support = tds[6].text.strip()   # 第 7 欄：HTTPS 支援狀態
                    if google_support == "yes" and https_support == "yes":
                        ip = tds[0].text.strip()  # 抓取 IP
                        port = tds[1].text.strip()  # 抓取 Port
                        proxies.append(f"http://{ip}:{port}")  # 直接添加格式化的代理字符串

        logging.info(f"更新後的代理列表：{proxies}")
        update_proxies(proxies[:5])
        self.proxies = proxies[:5]
        return self.proxies
