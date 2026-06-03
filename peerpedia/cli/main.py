"""PeerPedia CLI — Reference client command-line interface."""

from __future__ import annotations

import click

from peerpedia_core import __version__


@click.group()
@click.version_option(__version__)
def cli():
    """PeerPedia — Decentralized academic publishing.

    Write, review, and publish academic articles with peer review
    and git-native version control.
    """
    pass


@cli.command()
def init():
    """Initialize PeerPedia in the current directory.

    Creates ~/.peerpedia/ with default configuration, empty database,
    and required directory structure.
    """
    from pathlib import Path
    from peerpedia_core.storage import DEFAULT_ARTICLES_DIR
    from peerpedia_core.storage.db import get_engine, init_db
    from peerpedia.config.settings import settings

    base = Path.home() / ".peerpedia"
    dirs = [
        base,
        DEFAULT_ARTICLES_DIR,
        base / "profiles",
        base / "db",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Initialize database tables
    engine = get_engine(settings.database_url)
    init_db(engine)

    click.echo(f"PeerPedia initialized at {base}")
    click.echo(f"  Articles repo dir: {DEFAULT_ARTICLES_DIR}")
    click.echo(f"  Database: {settings.db_path}")
    click.echo(f"  Next: peerpedia serve")


@cli.command()
@click.option("--lan", is_flag=True, help="Enable LAN mode for multi-user collaboration")
@click.option("--port", default=8080, help="Port to listen on")
def serve(lan: bool, port: int):
    """Start the PeerPedia web interface.

    In default mode, runs as single-user local server.
    With --lan, discovers other PeerPedia nodes on the local network.
    """
    import uvicorn

    mode = "LAN" if lan else "local"
    click.echo(f"Starting PeerPedia in {mode} mode on port {port}...")
    click.echo(f"Open http://localhost:{port} in your browser")

    uvicorn.run(
        "peerpedia.web.app:app",
        host="0.0.0.0" if lan else "127.0.0.1",
        port=port,
        reload=True,
    )


@cli.command()
@click.argument("article_path", type=click.Path(exists=True))
@click.option("--author", default=None, help="Your name for git commits")
@click.option("--email", default=None, help="Your email for git commits")
def submit(article_path: str, author: str | None, email: str | None):
    """Submit a Typst or Markdown article for peer review.

    ARTICLE_PATH: Path to the main .typ or .md file.
    """
    from pathlib import Path
    from peerpedia.config.settings import settings
    from peerpedia.submit import submit_article

    path = Path(article_path).resolve()

    author_name = author or "peerpedia"
    author_email = email or "peerpedia@localhost"

    click.echo(f"Submitting article: {path.name}")
    click.echo(f"  Format: {'Typst' if path.suffix in ('.typ', '.typst') else 'Markdown'}")

    # Ensure database is initialized
    from peerpedia_core.storage.db import get_engine, init_db
    engine = get_engine(settings.database_url)
    init_db(engine)

    settings.ensure_dirs()

    result = submit_article(
        source_path=path,
        database_url=settings.database_url,
        articles_dir=settings.articles_dir,
        author_name=author_name,
        author_email=author_email,
    )

    if result.success:
        click.echo()
        click.echo(f"✓ Article submitted successfully!")
        click.echo(f"  ID:     {result.article_id}")
        click.echo(f"  Title:  {result.title}")
        click.echo(f"  Commit: {result.git_commit_hash[:8]}")
        if result.cid:
            click.echo(f"  CID:    {result.cid[:16]}...")
        if result.compile_output:
            click.echo(f"  Output: {result.compile_output}")
        click.echo()
        click.echo(f"  View: peerpedia serve → http://localhost:{settings.port}")
    else:
        click.echo(f"✗ Submission failed: {result.error}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("article_id")
@click.option("--decision", "-d", type=click.Choice(["accept", "revise", "reject"]), prompt="Decision (accept/revise/reject)")
@click.option("--comments", "-c", prompt="Review comments (Markdown)")
@click.option("--scientific", type=click.IntRange(1, 5), default=3, help="Scientific correctness (1-5)")
@click.option("--clarity", type=click.IntRange(1, 5), default=3, help="Clarity score (1-5)")
@click.option("--reviewer", default=None, help="Your reviewer ID/name")
def review(article_id: str, decision: str, comments: str, scientific: int, clarity: int, reviewer: str | None):
    """Review an article pending peer review.

    ARTICLE_ID: The article UUID to review.
    """
    from peerpedia.config.settings import settings
    from peerpedia_core.workflow.review import assign_reviewer, submit_review
    from peerpedia_core.storage.db import get_engine, init_db

    reviewer_id = reviewer or "anonymous"

    engine = get_engine(settings.database_url)
    init_db(engine)

    click.echo(f"Reviewing article: {article_id}")
    click.echo(f"  Reviewer: {reviewer_id}")

    # Step 1: Assign reviewer (if not already in_review)
    assign_result = assign_reviewer(
        article_id=article_id,
        reviewer_id=reviewer_id,
        database_url=settings.database_url,
    )
    if not assign_result.success:
        if "must be" not in assign_result.error:
            click.echo(f"✗ Assignment failed: {assign_result.error}", err=True)
            raise SystemExit(1)
        click.echo(f"  (Article already in review)")

    # Step 2: Submit review
    result = submit_review(
        article_id=article_id,
        reviewer_id=reviewer_id,
        decision=decision,
        comments=comments,
        scientific_correctness=scientific,
        clarity=clarity,
        database_url=settings.database_url,
    )

    if result.success:
        click.echo()
        click.echo(f"✓ Review submitted successfully!")
        click.echo(f"  Review ID: {result.review_id}")
        click.echo(f"  Decision:  {decision}")
        click.echo(f"  Points:    +{result.points_earned}")
    else:
        click.echo(f"✗ Review failed: {result.error}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("article_id")
def decide(article_id: str):
    """Make a decision on an article based on accumulated reviews.

    ARTICLE_ID: The article UUID to decide on.
    """
    from peerpedia.config.settings import settings
    from peerpedia_core.workflow.review import make_decision
    from peerpedia_core.storage.db import get_engine, init_db

    engine = get_engine(settings.database_url)
    init_db(engine)

    result = make_decision(
        article_id=article_id,
        database_url=settings.database_url,
    )

    if result.success:
        click.echo(f"✓ Decision made: {result.new_status}")
        if result.author_points:
            click.echo(f"  Author points: +{result.author_points}")
        if result.new_status == "accepted":
            click.echo(f"  Next: peerpedia publish {article_id}")
    else:
        click.echo(f"✗ Decision failed: {result.error}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("article_id")
def collaborate(article_id: str):
    """Request to collaborate on an article as a reviewer.

    ARTICLE_ID: The article UUID to collaborate on.
    """
    click.echo(f"Requesting collaboration on: {article_id}")
    click.echo("(Not yet implemented — coming in Phase 3)")


@cli.command()
@click.argument("article_id")
def propose_edit(article_id: str):
    """Propose an edit to a published article (post-publication editing).

    ARTICLE_ID: The article UUID to edit.
    """
    click.echo(f"Creating edit proposal for: {article_id}")
    click.echo("(Not yet implemented — coming in Phase 3)")


if __name__ == "__main__":
    cli()
