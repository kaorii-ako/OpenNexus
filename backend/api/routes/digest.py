from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/digest")
async def get_digest(request: Request):
    content = getattr(request.app.state, "last_digest", None)
    return {"content": content or ""}

@router.post("/digest/run")
async def run_digest(request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    from backend.agents.digest import DigestAgent
    content = await DigestAgent(cfg, engine).run()
    request.app.state.last_digest = content
    return {"content": content}
