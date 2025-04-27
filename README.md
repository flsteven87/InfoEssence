# GlobalNews for Taiwan

GlobalNews for Taiwan 是一個進階的新聞聚合和摘要系統，專為台灣讀者設計，提供簡潔、相關的國際新聞繁體中文摘要。本專案利用 AI 技術收集、摘要並以適合台灣讀者的格式呈現全球新聞，並自動發佈到 Instagram 平台。

## 功能特點

- **News Aggregation**：透過 RSS feed 從各種國際來源收集新聞
- **AI-Powered Summarization**：利用 OpenAI 的 GPT 模型生成繁體中文的簡潔摘要和標題
- **Important News Selection**：自動為台灣讀者選擇最相關和重要的新聞
- **Instagram Post Generation**：從選定的新聞項目創建並自動發佈吸引人的 Instagram 貼文
- **Image Generation**：使用 AI 為新聞文章生成相關圖片
- **Web Interface**：提供使用者友好的網頁介面瀏覽摘要新聞

## Technology Stack

- **Backend**: Python
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **API**: OpenAI GPT-4
- **Web Framework**: Streamlit
- **Image Generation**: DALL-E (via OpenAI API)
- **Deployment**: Heroku

## 線上服務

本專案已經上線並自動運行，透過以下方式提供服務：

- **Instagram 帳號**：[@GlobalNewsTaiwan](https://www.instagram.com/GlobalNewsTaiwan/)
- **Web 介面**：[GlobalNews for Taiwan Web](https://globalnews-for-taiwan.herokuapp.com/)

## Installation and Setup

1. Clone 專案:
   ```bash
   git clone https://github.com/your-username/globalnews-for-taiwan.git
   cd globalnews-for-taiwan
   ```

2. 建立並啟用 conda 環境:
   ```bash
   conda create -n infoessence python=3.12
   conda activate infoessence
   ```

3. 安裝相依套件:
   ```bash
   pip install -r requirements.txt
   ```

4. 設定環境變數:
   複製 `.env.example` 檔案為 `.env`，並填入您的實際資訊:
   ```bash
   cp .env.example .env
   ```
   
   在 `.env` 檔案中填入以下資訊:
   ```
   # 資料庫連線資訊
   DATABASE_URL=postgresql://username:password@host:port/database_name
   
   # OpenAI API 金鑰
   OPENAI_API_KEY=your_openai_api_key
   
   # Instagram 帳號資訊
   FB_APP_ID=your_fb_app_id
   FB_APP_SECRET=your_fb_app_secret
   INSTAGRAM_ACCOUNT_ID=your_instagram_account_id
   INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
   ```

5. 初始化資料庫:
   ```bash
   python -m src.database.db_management init
   ```

6. 啟動應用程式:
   ```bash
   streamlit run src/app.py
   ```

## Usage

主要腳本支援各種可作為模組執行的操作：

### Update RSS Feeds

更新 RSS feeds:

```bash
python -m src.main --update
```

### Fetch Latest News

獲取並處理最新新聞文章:

```bash
python -m src.main --fetch
```

### Select Important News

選擇特定數量的重要新聞項目（例如，5）並自動生成 Instagram 貼文:

```bash
python -m src.main --choose 5
```

### Manual Instagram Posting

手動觸發向 Instagram 發佈已選擇的新聞:

```bash
python -m src.main --post
```

### Run Web Interface

啟動 Streamlit web 介面:

```bash
streamlit run src/app.py
```

### Typical Workflow

典型的工作流程如下:

1. 更新 RSS feeds
2. 獲取最新新聞
3. 選擇重要新聞項目並生成 Instagram 貼文
4. 自動發佈到 Instagram
5. 透過 web 介面查看結果

當部署到 production 環境時，這些步驟會透過排程任務自動執行。

## Project Structure

- `src/`: 包含主要程式碼
  - `config/`: 設定檔 (config.yaml, rss_feed.yaml, settings.py)
  - `database/`: 資料庫模型和操作
  - `services/`: 新聞處理的核心服務
  - `utils/`: 工具函數
  - `assets/`: 靜態資源檔案
  - `main.py`: 主程式進入點
  - `app.py`: Streamlit web 應用程式
- `requirements.txt`: Python 相依套件清單
- `.gitignore`: 指定要忽略的未追蹤檔案
- `.env.example`: 環境變數範例檔案
- `Procfile`: Heroku 部署設定
- `Dockerfile`: Docker 容器設定

## Development

### Local Development

對於本地開發，您需要設定一個本地 PostgreSQL 資料庫，並設定適當的環境變數。確保您使用 conda 環境來管理相依套件。

### Contribution

歡迎貢獻！請隨時提出 issue 或提交 pull request。

## Deployment

### Heroku Deployment

本專案設計為在 Heroku 上運行。確保 `Procfile` 正確設定，並設置所有必要的環境變數。

#### 設定 Heroku 環境變數

為了管理生產環境的環境變數，我們使用一個單獨的 `.env.production` 檔案，該檔案不會進入 git 版本控制。

1. **建立生產環境變數檔案**：
   ```bash
   # 從範例檔案複製一份作為起點
   cp .env.example .env.production
   
   # 確保此檔案不被 git 追蹤
   echo ".env.production" >> .gitignore
   ```

2. **設定生產環境變數**：
   在 `.env.production` 中設定所有 Heroku 生產環境需要的變數，例如：
   ```
   ENV=production
   # 其他生產環境專用變數...
   ```

3. **將環境變數推送到 Heroku**：
   ```bash
   # 一次性設定所有環境變數
   cat .env.production | grep -v '^#' | xargs -L 1 heroku config:set --app globalnews-for-taiwan
   
   # 查看當前設定
   heroku config --app globalnews-for-taiwan
   ```

4. **管理 Instagram 憑證**：
   對於長期的 Instagram 存取權杖，建議：
   - 使用 Facebook 開發者平台取得長期存取權杖
   - 將權杖存儲在 `.env.production` 中
   - 定期更新權杖並重新推送至 Heroku

5. **設定 Heroku 定時任務**：
   ```bash
   # 安裝 Scheduler 插件
   heroku addons:create scheduler:standard --app globalnews-for-taiwan
   
   # 開啟排程器設定
   heroku addons:open scheduler --app globalnews-for-taiwan
   ```
   在 Heroku Scheduler 中設定排程任務：
   ```
   python -m src.main
   ```

#### 更新或重設環境變數

```bash
# 更新單個環境變數
heroku config:set KEY=new_value --app globalnews-for-taiwan

# 移除環境變數
heroku config:unset KEY --app globalnews-for-taiwan

# 完全重設並從 .env.production 重新設定
heroku config:unset $(heroku config --app globalnews-for-taiwan | grep -v '=' | xargs) --app globalnews-for-taiwan
cat .env.production | grep -v '^#' | xargs -L 1 heroku config:set --app globalnews-for-taiwan
```

## License

MIT

## 鳴謝

- OpenAI 提供用於摘要的 GPT 模型
- 提供 RSS feeds 的所有新聞來源