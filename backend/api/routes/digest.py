from __future__ import annotations
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request
from sqlmodel import Session, select
from backend.core.db import get_engine, DigestLog

router = APIRouter()


def _save_digest(data_dir: Path, content: str) -> None:
    engine = get_engine(data_dir)
    with Session(engine) as session:
        entry = DigestLog(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            content=content,
        )
        session.add(entry)
        session.commit()


def _load_latest_digest(data_dir: Path) -> dict | None:
    engine = get_engine(data_dir)
    with Session(engine) as session:
        stmt = select(DigestLog).order_by(DigestLog.id.desc()).limit(1)
        entry = session.exec(stmt).first()
        if entry is None:
            return None
        return {
            "content": entry.content,
            "generated_at": entry.created_at.isoformat(),
        }


@router.get("/digest")
async def get_digest(request: Request):
    cfg = request.app.state.cfg
    result = _load_latest_digest(cfg.data_dir)
    if result is None:
        return {"content": "", "generated_at": None}
    return result


@router.post("/digest/run")
async def run_digest(request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    from backend.agents.digest import DigestAgent
    content = await DigestAgent(cfg, engine).run()
    _save_digest(cfg.data_dir, content)
    return {
        "content": content,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/config")
async def get_config(request: Request):
    cfg = request.app.state.cfg
    return {
        "user": {
            "name": cfg.user.name,
            "timezone": cfg.user.timezone,
            "role": cfg.user.role,
        },
        "llm": {
            "provider": cfg.llm.provider,
            "model": cfg.llm.model,
        },
        "connectors": {
            "notion": cfg.connectors.notion_enabled,
            "gmail": cfg.connectors.gmail_enabled,
            "calendar": cfg.connectors.calendar_enabled,
            "classroom": cfg.connectors.classroom_enabled,
            "github": cfg.connectors.github_enabled,
            "discord": cfg.connectors.discord_enabled,
        },
    }
