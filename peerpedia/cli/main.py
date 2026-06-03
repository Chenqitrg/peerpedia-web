"""PeerPedia CLI — Reference client command-line interface."""

from __future__ import annotations

from pathlib import Path

import click

from peerpedia_core import __version__

# Import subcommand modules
from peerpedia.cli.article_commands import submit, review, decide
from peerpedia.cli.social_commands import mirror, collaborate, propose_edit, merge_proposal
from peerpedia.cli.user_commands import user


@click.group()
@click.version_option(__version__)
def cli():
    """知著网 (PeerPedia) — 去中心化学术出版系统。

    用 Typst 写作，同行审核，P2P 发布。
    """
    pass


@cli.command()
def init():
    """Initialize PeerPedia in the current directory.

    Creates ~/.peerpedia/ with default configuration, empty database,
    and required directory structure.
    """
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

    engine = get_engine(settings.database_url)
    init_db(engine)

    click.echo(f"PeerPedia 初始化完成: {base}")
    click.echo(f"  文章仓库目录: {DEFAULT_ARTICLES_DIR}")
    click.echo(f"  数据库: {settings.db_path}")
    click.echo(f"  下一步: peerpedia serve")


@cli.command()
@click.option("--lan", is_flag=True, help="Enable LAN mode for multi-user collaboration")
@click.option("--port", default=8080, help="Port to listen on")
def serve(lan: bool, port: int):
    """Start the PeerPedia web interface.

    In default mode, runs as single-user local server.
    With --lan, discovers other PeerPedia nodes on the local network.
    """
    import uvicorn

    mode = "局域网" if lan else "本地"
    click.echo(f"PeerPedia 启动中 ({mode}模式，端口 {port})...")
    click.echo(f"浏览器打开 http://localhost:{port}")

    uvicorn.run(
        "peerpedia.web.app:app",
        host="0.0.0.0" if lan else "127.0.0.1",
        port=port,
        reload=True,
    )


# Register subcommands
cli.add_command(submit)
cli.add_command(review)
cli.add_command(decide)
cli.add_command(mirror)
cli.add_command(collaborate)
cli.add_command(propose_edit)
cli.add_command(merge_proposal)
cli.add_command(user)


if __name__ == "__main__":
    cli()
