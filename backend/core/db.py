from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlmodel import SQLModel, Field, Session, create_engine, select


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Turn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str  # "user" | "assistant"
    content: str
    model: Optional[str] = None
    sources_used: Optional[str] = None  # JSON list of page_ids
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DigestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True)  # YYYY-MM-DD
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectorStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    healthy: bool = False
    last_checked: Optional[datetime] = None
    last_synced: Optional[datetime] = None
    error_message: Optional[str] = None


_engine = None


def get_engine(data_dir: Path):
    global _engine
    if _engine is None:
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "nexus.db"
        _engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(_engine)
    return _engine


def get_session(data_dir: Path) -> Session:
    return Session(get_engine(data_dir))
