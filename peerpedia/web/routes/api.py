"""Web — API endpoints (REST)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/articles")
async def list_articles():
    """List all articles."""
    return {"articles": [], "total": 0}


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    """Get article metadata."""
    return {"article_id": article_id, "message": "Not yet implemented"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
