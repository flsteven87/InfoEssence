# GlobalNews for Taiwan

GlobalNews for Taiwan is an advanced news aggregation and summarization system designed to provide Taiwanese readers with concise, relevant international news in Traditional Chinese. This project leverages AI technologies to collect, summarize, and present global news in a format tailored for the Taiwanese audience.

## Features

- **News Aggregation**: Collects news from various international sources using RSS feeds.
- **AI-Powered Summarization**: Utilizes OpenAI's GPT models to generate concise summaries and titles in Traditional Chinese.
- **Important News Selection**: Automatically selects the most relevant and important news items for the Taiwanese audience.
- **Instagram Post Generation**: Creates engaging Instagram-ready posts from selected news items.
- **Image Generation**: Generates relevant images for news articles using AI.
- **Web Interface**: Provides a user-friendly web interface for browsing summarized news.

## Technology Stack

- **Backend**: Python
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **API**: OpenAI GPT-4
- **Web Framework**: Streamlit
- **Image Generation**: DALL-E (via OpenAI API)

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/globalnews-for-taiwan.git
   cd globalnews-for-taiwan
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add the following:
   ```
   DATABASE_USER=your_db_user
   DATABASE_PASSWORD=your_db_password
   DATABASE_HOST=your_db_host
   DATABASE_NAME=your_db_name
   OPENAI_API_KEY=your_openai_api_key
   ```

4. Initialize the database:

5. Run the application:

## Usage

The main script supports various operations that can be executed as modules.

### Updating RSS Feeds

To update the RSS feeds:

```
python -m src.main --update
```

### Fetching Latest News

To fetch and process the latest news articles:

```
python -m src.main --fetch
```

### Selecting Important News

To select a specific number of important news items (e.g., 5):

```
python -m src.main --choose 5
```

This will select the 5 most important news items and save them to a CSV file in the `chosen_news` directory.

### Generating Instagram Posts

Instagram posts are automatically generated for the chosen news items and saved to a CSV file in the `instagram_posts` directory.

### Running the Web Interface

To start the Streamlit web interface:

```
streamlit run src/app.py
```


### Typical Workflow

A typical workflow might look like this:

1. Update RSS feeds
2. Fetch latest news
3. Choose important news items
4. View results in the web interface


## Project Structure

- `src/`: Contains the main source code
  - `config/`: Configuration files (config.yaml, rss_feed.yaml)
  - `database/`: Database models and operations
  - `services/`: Core services for news processing
  - `utils/`: Utility functions
- `requirements.txt`: List of Python dependencies
- `.gitignore`: Specifies intentionally untracked files to ignore

## License

MIT

## Acknowledgements

- OpenAI for providing the GPT models used in summarization
- All the news sources that provide RSS feeds