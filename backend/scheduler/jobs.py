from __future__ import annotations
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from backend.core.config import NexusConfig
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore


def create_scheduler(cfg: NexusConfig, engine: OllamaEngine, store: MemoryStore) -> AsyncIOScheduler:
    tz = ZoneInfo(cfg.timezone)
    scheduler = AsyncIOScheduler(timezone=tz)

    async def run_digest():
        from backend.agents.digest import DigestAgent
        await DigestAgent(cfg, engine).run()

    async def run_notion_sync():
        from backend.connectors.notion_sync import NotionSync
        await NotionSync(cfg).sync_all()

    digest_parts = cfg.scheduler.digest_cron.split()
    digest_cron = dict(zip(["minute", "hour", "day", "month", "day_of_week"], digest_parts))

    scheduler.add_job(run_digest, CronTrigger(**digest_cron, timezone=tz), id="digest")
    scheduler.add_job(run_notion_sync, CronTrigger(minute="*/15", timezone=tz), id="notion_sync")

    return scheduler
