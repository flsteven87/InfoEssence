import requests
import time
from ratelimit import limits, sleep_and_retry
from src.config.settings import JINA_API_URL, USE_PROXY, PROXIES
import random

class ContentFetchException(Exception):
    """自定義內容獲取異常類"""
    pass

@sleep_and_retry
@limits(calls=20, period=60)  # 每分鐘 20 次請求
def fetch_content(url: str) -> str:
    jina_reader_url = f"{JINA_API_URL}/{url}"
    
    try:
        if USE_PROXY:
            for _ in range(len(PROXIES)):
                proxy = random.choice(PROXIES)
                try:
                    response = requests.get(jina_reader_url, proxies={'http': proxy['http']}, timeout=100)
                    response.raise_for_status()
                    return response.text
                except requests.RequestException as e:
                    print(f"使用代理 {proxy['http']} 失敗：{e}")
                    continue
            raise ContentFetchException("所有代理都失敗，無法獲取內容")
        else:
            response = requests.get(jina_reader_url, timeout=100)
            response.raise_for_status()
            return response.text
    except requests.RequestException as e:
        raise ContentFetchException(f"獲取內容失敗：URL：{url} - 錯誤：{e}")