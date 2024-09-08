import requests
import time
from ratelimit import limits, sleep_and_retry
from src.config.settings import JINA_API_URL, USE_PROXY, PROXIES, update_proxies
import random
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ContentFetchException(Exception):
    """自定義內容獲取異常類"""
    pass

@sleep_and_retry
@limits(calls=20, period=60)  # 每分鐘 20 次請求
def fetch_content(url: str) -> str:
    jina_reader_url = f"{JINA_API_URL}/{url}"
    
    for attempt in range(2):  # 最多嘗試 2 次
        try:
            # 首先嘗試不使用代理
            response = requests.get(jina_reader_url, timeout=100)
            if response.status_code == 200:
                logger.info(f"成功獲取內容：{url}")
                time.sleep(3)  # 每次成功請求後休眠 3 秒
                return response.text
            
            # 如果狀態碼不是 200，嘗試使用代理
            if USE_PROXY:
                for _ in range(len(PROXIES)):
                    proxy = random.choice(PROXIES)
                    try:
                        response = requests.get(jina_reader_url, proxies={'http': proxy['http']}, timeout=100)
                        if response.status_code == 200:
                            logger.info(f"使用代理成功獲取內容：{url}")
                            time.sleep(3)  # 每次成功請求後休眠 3 秒
                            return response.text
                    except requests.RequestException as e:
                        logger.warning(f"使用代理 {proxy['http']} 失敗：{e}")
                        continue
                logger.error("所有代理都失敗，無法獲取內容")
            
            # 處理非 200 狀態碼
            response.raise_for_status()
        except requests.RequestException as e:
            if "429" in str(e):
                logger.warning(f"達到速率限制，增加休眠時間。嘗試次數：{attempt + 1}")
                time.sleep(60 * (attempt + 1))  # 隨著嘗試次數增加休眠時間
            elif "451" in str(e):
                logger.error(f"獲取內容失敗：URL：{url} - 錯誤：{e}")
                attempt -= 1
                time.sleep(3)  # 其他錯誤也增加一些休眠時間
            else:
                logger.error(f"獲取內容失敗：URL：{url} - 錯誤：{e}")
                time.sleep(10)  # 其他錯誤也增加一些休眠時間

    raise ContentFetchException(f"多次嘗試後仍無法獲取內容：URL：{url}")

def update_proxy_list():
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
    return proxies[:5]
