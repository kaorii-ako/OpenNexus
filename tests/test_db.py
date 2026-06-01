import pytest
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session, select
from backend.core.db import Conversation, Turn, DigestLog, ConnectorStatus


@pytest.fixture
def session(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_turn_roundtrip(session):
    turn = Turn(session_id="s1", role="user", content="hello")
    session.add(turn)
    session.commit()
    session.refresh(turn)
    assert turn.id is not None
    result = session.exec(select(Turn).where(Turn.session_id == "s1")).first()
    assert result.content == "hello"


def test_connector_status_roundtrip(session):
    status = ConnectorStatus(name="notion", healthy=True)
    session.add(status)
    session.commit()
    result = session.exec(select(ConnectorStatus).where(ConnectorStatus.name == "notion")).first()
    assert result.healthy is True


def test_digest_log_roundtrip(session):
    log = DigestLog(date="2026-06-01", content="Morning briefing content")
    session.add(log)
    session.commit()
    result = session.exec(select(DigestLog).where(DigestLog.date == "2026-06-01")).first()
    assert result.content == "Morning briefing content"
