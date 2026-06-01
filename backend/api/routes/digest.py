from fastapi import APIRouter, Request, BackgroundTasks
router = APIRouter()

@router.get("/digest")
async def get_digest(request: Request):
    return {"content": "No digest yet"}

@router.post("/digest/run")
async def run_digest(request: Request, background_tasks: BackgroundTasks):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    async def _run():
        from backend.agents.digest import DigestAgent
        await DigestAgent(cfg, engine).run()
    background_tasks.add_task(_run)
    return {"status": "running"}
