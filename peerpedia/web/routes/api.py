"""Web — API endpoint facade.

Combines sub-routers from api_articles, api_users, and api_collab
into a single router with the /api/v1 prefix.
"""

from fastapi import APIRouter, Form, HTTPException

from peerpedia.web.routes.api_articles import router as articles_router
from peerpedia.web.routes.api_users import router as users_router
from peerpedia.web.routes.api_collab import router as collab_router

router = APIRouter(prefix="/api/v1")

router.include_router(articles_router)
router.include_router(users_router)
router.include_router(collab_router)


# ── Citation Click Tracking ──────────────────────────────────────────────────

from peerpedia.web.db_session import get_db_session


@router.post("/citations/click")
async def api_record_click(
    from_article_id: str = Form(...),
    to_article_id: str = Form(...),
    user_id: str = Form(""),
    node_id: str = Form("unknown"),
):
    """Record a citation click event for transition probability tracking."""
    from peerpedia_core.workflow.citations import record_click

    session = get_db_session()
    try:
        result = record_click(
            session,
            from_article_id=from_article_id,
            to_article_id=to_article_id,
            node_id=node_id or "unknown",
            user_id=user_id or None,
        )
        session.commit()
        return {
            "status": "recorded",
            "from_article_id": result["from_article_id"],
            "to_article_id": result["to_article_id"],
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/citations/transitions")
async def api_get_transitions(
    article_id: str,
    source: str = "local",
):
    """Get click-based transition probabilities from an article.

    Query params:
        article_id: Source article ID.
        source: "local" (SQLite only) or "merged" (local + catalog data).
    """
    from peerpedia_core.workflow.citations import compute_transition_probabilities

    session = get_db_session()
    try:
        other_clicks = None
        # Note: "merged" source loads other node clicks from catalog (future)

        result = compute_transition_probabilities(
            session,
            from_article_id=article_id,
            other_nodes_clicks=other_clicks,
        )
        result["source"] = source
        return result
    finally:
        session.close()
