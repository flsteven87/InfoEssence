from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, LargeBinary, ARRAY, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Media(Base):
    __tablename__ = 'media'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String, nullable=False, unique=True)

    feeds = relationship("Feed", back_populates="media")
    news = relationship("News", back_populates="media")

class Feed(Base):
    __tablename__ = 'feeds'

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    media_id = Column(Integer, ForeignKey('media.id'))
    last_fetched = Column(DateTime(timezone=True))

    media = relationship("Media", back_populates="feeds")
    news = relationship("News", back_populates="feed")

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    data = Column(LargeBinary)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class News(Base):
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True)
    link = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    summary = Column(String)
    ai_title = Column(String)
    ai_summary = Column(String)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    media_id = Column(Integer, ForeignKey('media.id'))
    feed_id = Column(Integer, ForeignKey('feeds.id'))
    md_file_id = Column(Integer, ForeignKey('files.id'))
    png_file_id = Column(Integer, ForeignKey('files.id'))

    feed = relationship("Feed", back_populates="news")
    media = relationship("Media", back_populates="news")
    md_file = relationship("File", foreign_keys=[md_file_id])
    png_file = relationship("File", foreign_keys=[png_file_id])

    instagram_post = relationship("InstagramPost", back_populates="news", uselist=False)

    published = relationship("Published", back_populates="news")

class ChosenNews(Base):
    __tablename__ = 'chosen_news'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    news_ids = Column(ARRAY(Integer))

    instagram_posts = relationship("InstagramPost", back_populates="chosen_news")

class InstagramPost(Base):
    __tablename__ = 'instagram_posts'

    id = Column(Integer, primary_key=True)
    chosen_news_id = Column(Integer, ForeignKey('chosen_news.id'))
    news_id = Column(Integer, ForeignKey('news.id'))
    ig_title = Column(String(255), nullable=False)
    ig_caption = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    integrated_image_id = Column(Integer, ForeignKey('files.id'))

    chosen_news = relationship("ChosenNews", back_populates="instagram_posts")
    news = relationship("News", back_populates="instagram_post")
    integrated_image = relationship("File", foreign_keys=[integrated_image_id])

    published = relationship("Published", back_populates="instagram_post")

class Published(Base):
    __tablename__ = 'published'

    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, ForeignKey('news.id'), nullable=False)
    instagram_post_id = Column(Integer, ForeignKey('instagram_posts.id'), nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now())

    news = relationship("News", back_populates="published")
    instagram_post = relationship("InstagramPost", back_populates="published")

    story = relationship("Story", back_populates="published", uselist=False)

class Story(Base):
    __tablename__ = 'stories'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    png_file_id = Column(Integer, ForeignKey('files.id'))
    published_id = Column(Integer, ForeignKey('published.id'))

    png_file = relationship("File", foreign_keys=[png_file_id])
    published = relationship("Published", back_populates="story")

Feed.news = relationship("News", back_populates="feed")
