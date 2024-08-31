import os
import yaml
from dotenv import load_dotenv
from pathlib import Path

# 載入 .env 文件
load_dotenv()

# 獲取當前文件的目錄
current_dir = Path(__file__).resolve().parent

def load_yaml_config(file_name):
    with open(current_dir / file_name, 'r') as file:
        return yaml.safe_load(file)

def process_config(cfg):
    if isinstance(cfg, dict):
        return {k: process_config(v) for k, v in cfg.items()}
    elif isinstance(cfg, list):
        return [process_config(v) for v in cfg]
    elif isinstance(cfg, str) and cfg.startswith('${') and cfg.endswith('}'):
        env_var = cfg[2:-1]
        default_value = None
        if ':' in env_var:
            env_var, default_value = env_var.split(':', 1)
        return os.getenv(env_var, default_value)
    else:
        return cfg

# 載入並處理配置
config = process_config(load_yaml_config('config.yaml'))
rss_config = process_config(load_yaml_config('rss_feed.yaml'))

# 數據庫設置
DB_USER = config['database']['user']
DB_PASSWORD = config['database']['password']
DB_HOST = config['database']['host']
DB_NAME = config['database']['name']
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# 其他設置
OPENAI_API_KEY = config['openai']['api_key']
RSS_CONFIG = rss_config

# 可選：如果需要 JINA_API_URL，取消下面的註釋
JINA_API_URL = config['jina']['api_url']

# 可選：如果需要代理設置，取消下面的註釋
USE_PROXY = config.get('proxy', {}).get('use_proxy', False)
PROXIES = config.get('proxy', {}).get('proxies', [])