"""Web — API endpoints (REST)."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import tempfile

from peerpedia.config.settings import settings
from peerpedia_core.storage.db import (
    get_engine, get_session, init_db, list_articles, get_article,
)
from peerpedia.submit import submit_article

router = APIRouter(prefix="/api/v1")


def _get_db_session():
    """Get a database session, ensuring tables exist."""
    engine = get_engine(settings.database_url)
    init_db(engine)
    return get_session(engine)


@router.get("/articles")
async def api_list_articles():
    """List all articles (most recent first)."""
    session = _get_db_session()
    try:
        articles = list_articles(session)
        return {
            "articles": [a.to_dict() for a in articles],
            "total": len(articles),
        }
    finally:
        session.close()


@router.get("/articles/{article_id}")
async def api_get_article(article_id: str):
    """Get article metadata by ID."""
    session = _get_db_session()
    try:
        article = get_article(session, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return article.to_dict()
    finally:
        session.close()


@router.post("/articles")
async def api_create_article(
    title: str = Form(...),
    abstract: str = Form(""),
    format: str = Form("typst"),
    categories: str = Form(""),
    keywords: str = Form(""),
    language: str = Form("en"),
    article_file: UploadFile = File(...),
):
    """Submit a new article via file upload (multipart form)."""
    # Validate format
    if format not in ("typst", "markdown"):
        raise HTTPException(status_code=400, detail="Format must be 'typst' or 'markdown'")

    # Save uploaded file to temp location
    suffix = ".typ" if format == "typst" else ".md"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as tmp:
        content = await article_file.read()
        # If the file doesn't have frontmatter, prepend from form fields
        text = content.decode("utf-8")
        if not text.startswith("---"):
            cats = [c.strip() for c in categories.split(",") if c.strip()]
            kws = [k.strip() for k in keywords.split(",") if k.strip()]
            cats_yaml = "\n".join(f"  - {c}" for c in cats) if cats else ""
            kws_yaml = "\n".join(f"  - {k}" for k in kws) if kws else ""
            fm = f"---\ntitle: {title}\nabstract: {abstract}\nlanguage: {language}\n"
            if cats_yaml:
                fm += f"categories:\n{cats_yaml}\n"
            if kws_yaml:
                fm += f"keywords:\n{kws_yaml}\n"
            fm += "---\n\n"
            text = fm + text
        tmp.write(text)
        tmp_path = Path(tmp.name)

    try:
        settings.ensure_dirs()
        result = submit_article(
            source_path=tmp_path,
            database_url=settings.database_url,
            articles_dir=settings.articles_dir,
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        return {
            "article_id": result.article_id,
            "title": result.title,
            "commit": result.git_commit_hash,
            "status": "submitted",
        }
    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


@router.get("/articles/{article_id}/reviews")
async def api_get_reviews(article_id: str):
    """Get all reviews for an article."""
    from peerpedia_core.storage.db import get_reviews_for_article
    session = _get_db_session()
    try:
        article = get_article(session, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        reviews = get_reviews_for_article(session, article_id)
        return {
            "article_id": article_id,
            "reviews": [r.to_dict() for r in reviews],
            "total": len(reviews),
        }
    finally:
        session.close()


@router.post("/articles/{article_id}/reviews")
async def api_submit_review(
    article_id: str,
    reviewer_id: str = Form(...),
    decision: str = Form(...),
    comments: str = Form(""),
    scientific_correctness: int = Form(0),
    clarity: int = Form(0),
):
    """Submit a review for an article."""
    from peerpedia_core.workflow.review import assign_reviewer, submit_review

    # Assign (no-op if already in_review)
    assign_result = assign_reviewer(
        article_id=article_id,
        reviewer_id=reviewer_id,
        database_url=settings.database_url,
    )
    if not assign_result.success and "must be" not in assign_result.error:
        raise HTTPException(status_code=400, detail=assign_result.error)

    # Submit review
    result = submit_review(
        article_id=article_id,
        reviewer_id=reviewer_id,
        decision=decision,
        comments=comments,
        scientific_correctness=scientific_correctness,
        clarity=clarity,
        database_url=settings.database_url,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "review_id": result.review_id,
        "points_earned": result.points_earned,
        "status": "submitted",
    }


@router.post("/articles/{article_id}/decide")
async def api_decide_article(article_id: str):
    """Make a decision on an article."""
    from peerpedia_core.workflow.review import make_decision

    result = make_decision(
        article_id=article_id,
        database_url=settings.database_url,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "article_id": article_id,
        "new_status": result.new_status,
        "author_points": result.author_points,
    }


@router.get("/articles/{article_id}/compile")
async def api_compile_article(article_id: str, fmt: str = "html"):
    """Compile an article on demand.

    Args:
        fmt: 'html' (default) or 'pdf'
    """
    from pathlib import Path
    from peerpedia_core.storage.compiler import TypstBackend, MarkdownBackend

    session = _get_db_session()
    try:
        article = get_article(session, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")

        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            raise HTTPException(status_code=404, detail="Article source not found")

        # Find source file
        source_files = []
        if article.format == "typst":
            source_files = list(repo.glob("*.typ"))
            backend = TypstBackend()
        else:
            source_files = list(repo.glob("*.md"))
            backend = MarkdownBackend()

        if not source_files:
            raise HTTPException(status_code=404, detail="Source file not found")

        source_file = source_files[0]

        # Compile
        result = backend.compile(source_file, repo)

        if not result.success:
            raise HTTPException(status_code=500, detail=f"Compilation failed: {result.error}")

        if fmt == "pdf" and result.output_path:
            from fastapi.responses import FileResponse
            return FileResponse(
                result.output_path,
                media_type="application/pdf",
                filename=f"{article.title}.pdf",
            )
        elif result.html_content:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=result.html_content)
        elif result.output_path:
            # Read output as text
            output = Path(result.output_path)
            return {"content": output.read_text(), "format": article.format}
        else:
            raise HTTPException(status_code=500, detail="No output produced")
    finally:
        session.close()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
