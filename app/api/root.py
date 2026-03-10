from fastapi import APIRouter

from app.api.deps import get_settings


router = APIRouter()


@router.get("/")
def read_root() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "status": "ok",
        "version": "v1",
    }
