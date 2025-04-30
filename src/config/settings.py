import os
import yaml
from dotenv import load_dotenv
from pathlib import Path

# 確定當前環境
load_dotenv()
ENV = os.getenv('ENV', 'development')

# 根據環境載入對應的 .env 文件
if ENV == 'production':
    load_dotenv('.env_heroku')
else:
    load_dotenv('.env')

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
DATABASE_URL = os.getenv('DATABASE_URL')  # 優先使用環境變量中的 DATABASE_URL
if not DATABASE_URL:
    DB_USER = os.getenv('DB_USER', config['database']['user'])
    DB_PASSWORD = os.getenv('DB_PASSWORD', config['database']['password'])
    DB_HOST = os.getenv('DB_HOST', config['database']['host'])
    DB_NAME = os.getenv('DB_NAME', config['database']['name'])
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# 確保 URL 使用 postgresql:// 而不是 postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 其他設置
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', config['openai']['api_key'])
JINA_API_URL = os.getenv('JINA_API_URL', config['jina']['api_url'])

# RSS 配置
RSS_CONFIG = rss_config

# 顯示當前使用的環境
print(f"Current environment: {ENV}")
print(f"Using DATABASE_URL: {DATABASE_URL}")
print(f"Using JINA_API_URL: {JINA_API_URL}")