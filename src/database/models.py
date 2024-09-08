from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
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

    feed = relationship("Feed", back_populates="news")
    media = relationship("Media", back_populates="news")

Feed.news = relationship("News", back_populates="feed")
