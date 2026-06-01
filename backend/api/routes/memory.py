from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
router = APIRouter()

class IndexRequest(BaseModel):
    path: str

@router.post("/memory/index")
async def index_path(req: IndexRequest, request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(lambda: None)
    return {"status": "queued", "path": req.path}

@router.post("/sync")
async def force_sync(request: Request, background_tasks: BackgroundTasks):
    cfg = request.app.state.cfg
    async def _sync():
        from backend.connectors.notion_sync import NotionSync
        await NotionSync(cfg).sync_all()
    background_tasks.add_task(_sync)
    return {"status": "syncing"}
