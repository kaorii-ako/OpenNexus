from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/notion/tree")
async def notion_tree(request: Request):
    from backend.connectors.notion import NotionConnector
    nc = NotionConnector(request.app.state.cfg)
    pages = await nc.get_all_pages()
    return {"pages": [{"id": p["id"], "title": _extract_title(p)} for p in pages[:50]]}

@router.get("/notion/page")
async def notion_page(page_id: str, request: Request):
    from backend.connectors.notion import NotionConnector
    nc = NotionConnector(request.app.state.cfg)
    content = await nc.get_page_content(page_id)
    return {"page_id": page_id, "content_md": content}

@router.get("/notion/search")
async def notion_search(q: str, request: Request):
    from backend.connectors.notion import NotionConnector
    nc = NotionConnector(request.app.state.cfg)
    results = await nc.search_pages(q)
    return {"results": [{"id": r["id"], "title": _extract_title(r)} for r in results[:10]]}

def _extract_title(page: dict) -> str:
    props = page.get("properties", {})
    for key in ("title", "Title", "Name"):
        if key in props:
            rt = props[key].get("title", []) or props[key].get("rich_text", [])
            if rt:
                return rt[0].get("plain_text", "Untitled")
    return "Untitled"
