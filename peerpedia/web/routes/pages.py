"""Web — Route handlers for HTML pages."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page — article listing."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "PeerPedia",
            "articles": [],  # TODO: load from storage
        },
    )


@router.get("/article/{article_id}", response_class=HTMLResponse)
async def view_article(request: Request, article_id: str):
    """View a single article."""
    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "title": "Article",
            "article": None,  # TODO: load from storage
        },
    )


@router.get("/submit", response_class=HTMLResponse)
async def submit_page(request: Request):
    """Article submission page."""
    return templates.TemplateResponse(
        "submit.html",
        {"request": request, "title": "Submit Article"},
    )


@router.get("/review", response_class=HTMLResponse)
async def review_queue(request: Request):
    """Review queue — list articles pending review."""
    return templates.TemplateResponse(
        "review.html",
        {"request": request, "title": "Review Queue"},
    )
