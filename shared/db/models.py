from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Text, Integer
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent:agentpass@localhost:5432/social_agent")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class SignalRecord(Base):
    __tablename__ = "signals"
    id              = Column(String, primary_key=True)
    platform        = Column(String(32))
    external_id     = Column(String(128))
    author_id       = Column(String(128))
    author_username = Column(String(128))
    content         = Column(Text)
    intent          = Column(String(64), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    is_crisis       = Column(Boolean, default=False)
    embedding       = Column(Vector(384), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

class ActionRecord(Base):
    __tablename__ = "actions"
    id              = Column(String, primary_key=True)
    signal_id       = Column(String)
    agent_id        = Column(String(64))
    action_type     = Column(String(32))
    draft_content   = Column(Text)
    final_content   = Column(Text, nullable=True)
    review_status   = Column(String(32), default="pending")
    human_edits     = Column(Text, nullable=True)
    toxicity_score  = Column(Float, default=0.0)
    published_at    = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_base"
    id          = Column(String, primary_key=True)
    title       = Column(String(256))
    content     = Column(Text)
    category    = Column(String(64))
    embedding   = Column(Vector(384), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(__import__('sqlalchemy').text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
