"""PeerPedia CLI — Reference client command-line interface."""

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

    Creates ~/.peerpedia/ with default configuration and empty database.
    """
    from pathlib import Path
    from peerpedia_core.storage import DEFAULT_ARTICLES_DIR

    base = Path.home() / ".peerpedia"
    dirs = [
        base,
        DEFAULT_ARTICLES_DIR,
        base / "profiles",
        base / "db",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    click.echo(f"PeerPedia initialized at {base}")
    click.echo(f"  Articles repo dir: {DEFAULT_ARTICLES_DIR}")
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
def submit(article_path: str):
    """Submit a Typst or Markdown article for peer review.

    ARTICLE_PATH: Path to the main .typ or .md file.
    """
    from pathlib import Path
    path = Path(article_path)
    click.echo(f"Submitting article: {path.name}")
    click.echo("(Not yet implemented — coming in Phase 3)")


@cli.command()
@click.argument("article_id")
def review(article_id: str):
    """Review an article pending peer review.

    ARTICLE_ID: The article UUID to review.
    """
    click.echo(f"Opening review for article: {article_id}")
    click.echo("(Not yet implemented — coming in Phase 3)")


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
