"""API route for article search."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from peerpedia.web.db_session import get_db_session
from peerpedia_core.storage.db import Article, list_articles

router = APIRouter()


@router.get("/search")
async def api_search(q: str = "", format: str = "json"):
    """Search articles by title, abstract, and keywords.

    Set ?format=html for HTMX swap into #article-list.
    """

    session = get_db_session()
    try:
        if not q.strip():
            articles = list_articles(session)
        else:
            pattern = f"%{q.strip()}%"
            articles = (
                session.query(Article)
                .filter(
                    Article.title.ilike(pattern)
                    | Article.abstract.ilike(pattern)
                    | Article.keywords.contains(q.strip())
                )
                .order_by(Article.created_at.desc())
                .limit(50)
                .all()
            )

        if format == "html":
            if not articles:
                return HTMLResponse(
                    '<p class="empty-state" style="padding:24px;">'
                    f'未找到与 "{q}" 相关的文章。</p>'
                )
            html = '<h2>文章</h2>'
            for a in articles:
                ad = a.to_dict()
                authors = ", ".join(ad.get("founding_authors", []))
                abstract = (ad.get("abstract") or "")[:200]
                status = ad.get("status", "")
                html += (
                    f'<article class="article-card">'
                    f'<h3><a href="/article/{ad["id"]}">{ad["title"]}</a></h3>'
                    f'<p class="meta">'
                    f'{authors} · {ad["format"]} · '
                    f'<span class="status {status}">{status}</span>'
                    f' · {str(ad.get("created_at", ""))[:10]}'
                    f'</p>'
                )
                if abstract:
                    html += f'<p class="abstract">{abstract}</p>'
                html += '</article>'
            return HTMLResponse(html)

        return {
            "q": q,
            "articles": [a.to_dict() for a in articles],
            "total": len(articles),
        }
    finally:
        session.close()
