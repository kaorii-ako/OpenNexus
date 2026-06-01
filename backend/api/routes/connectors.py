from fastapi import APIRouter, Request
import asyncio
router = APIRouter()

@router.get("/status")
async def status(request: Request):
    cfg = request.app.state.cfg
    from backend.connectors.notion import NotionConnector
    from backend.connectors.weather import WeatherConnector
    from backend.connectors.github import GitHubConnector
    from backend.connectors.discord import DiscordConnector
    from backend.connectors.gmail import GmailConnector

    connectors_list = [
        NotionConnector(cfg), GmailConnector(cfg),
        WeatherConnector(cfg), GitHubConnector(cfg), DiscordConnector(cfg),
    ]
    results = await asyncio.gather(*[c.health() for c in connectors_list], return_exceptions=True)
    return {
        "connectors": [
            {"name": r.name, "healthy": r.healthy, "error": r.error}
            for r in results if hasattr(r, "name")
        ],
        "model": request.app.state.engine.model,
    }
