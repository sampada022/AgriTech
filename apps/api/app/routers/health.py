from fastapi import APIRouter
import httpx
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

async def check_basemap() -> bool:
    if settings.DEMO_MODE:
        # In demo mode, avoid blocking on external network calls
        return True
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.head("https://tile.openstreetmap.org/0/0/0.png")
            return resp.status_code == 200
    except Exception:
        return False

@router.get("")
def get_health():
    llm_configured = bool(settings.LLM_API_KEY)
    llm_mode = "cached_fallback" if (settings.DEMO_FORCE_CACHED_AI or not llm_configured) else "live"

    return {
        "status": "ok",
        "service": "AeroScout Core API",
        "demo_mode": settings.DEMO_MODE,
        "llm": {
            "mode": llm_mode,
            "configured": llm_configured,
            "provider": settings.LLM_PROVIDER
        },
        "basemap": {
            "reachability": "online",
            "fallback": "dark_canvas"
        }
    }
