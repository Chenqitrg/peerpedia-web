# 知诸网 (PeerPedia)

**去中心化学术出版系统 — 取代 arXiv 和学术期刊。**

> 谐音「蜘蛛网」🕸️：P2P 节点互联。取"孜孜以求，诸子百家"之意。

```
Author writes in Typst → Peer review → Publish → Cite & collaborate
                           ↑
              Reviewer can join as co-author
              Post-publication open editing
              Git-native contribution timeline
              Citation DAG with click-to-jump
              Multi-dimensional reputation radar
```

## Architecture

```
peerpedia_core/     ← Protocol (messages, signing, reputation, storage, citations)
peerpedia/          ← Reference client (CLI + Web)
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Register a user
peerpedia user register zhangsan --name "张三" --email "zhang@example.com"

# Submit an article (auto-scans peerpedia references)
peerpedia submit article.typ --author zhangsan

# Start the web interface
peerpedia serve

# Start LAN mode (multi-user on same network)
peerpedia serve --lan
```

## Features

| Category | Feature | Status |
|---|---|---|
| **Online Editor** | CodeMirror + Markdown/KaTeX + Typst SVG live preview, $$ auto-close, 5D stars, upload | ✅ |
| **Submit** | Typst + Markdown/KaTeX with 5-dimension self-assessment, unified with editor | ✅ |
| **Version History** | Git commit list with semantic version labels, 🟢 current badge, +X/−Y line counts | ✅ |
| **Sedimentation Pool** | Anonymous ratings + discussion, auto-publish by sink score | ✅ |
| **5D Scoring** | Originality/Rigor/Completeness/Pedagogy/Impact (self + community) | ✅ |
| **Fork & Merge** | Fork articles, propose merge back, author review, version bump | ✅ |
| **Reputation** | 4D radar chart (academic/review/collaboration/education) + identity boost | ✅ |
| **Citations** | Reference scanning, NetworkX citation graph, click-to-jump sidebar | ✅ |
| **Collaboration** | Reviewer → co-author, post-publication edit proposals | ✅ |
| **Search** | Real-time search by title/abstract/keywords (HTMX) | ✅ |
| **Git Diff** | Version history tab with diff2html side-by-side view | ✅ |
| **Review Versioning** | One review per person per version, old reviews frozen, published → real names | ✅ |
| **Mirror** | ArXiv article import with dangling founder accounts | ✅ |
| **LAN** | UDP broadcast node discovery + catalog.md article pool sync | ✅ |
| **Follow** | Follow authors, activity feed (HTMX-driven) | ✅ |

## Available Commands

```bash
peerpedia init                                    # Initialize ~/.peerpedia/
peerpedia seed --force                            # Rebuild demo data (4 users + 5 articles)
peerpedia serve [--lan] [--port 8080]             # Start web interface
peerpedia submit article.typ --author zhangsan    # Submit article
peerpedia review <id> -d accept -c "great work"   # Submit peer review
peerpedia decide <id>                             # Decide on article
peerpedia mirror 2301.00001 -u zhangsan           # Mirror from arXiv
peerpedia collaborate <id> -r reviewer_name       # Accept collaboration
peerpedia propose-edit <id> -t minor -d "fix typo" # Propose post-publication edit
peerpedia merge-proposal <pid> <aid>              # Merge approved proposal
peerpedia user register <id> --name 张三 --email .. # Register user
peerpedia lan status                              # LAN node status
peerpedia lan sync [-n <node>]                    # Sync article catalog
```

## API Endpoints (30+ routes, 10 route modules)

| Module | Endpoints |
|---|---|
| `api_articles.py` | GET/POST `/articles`, GET `/articles/{id}`, POST `/articles/{id}/reviews`, POST `/articles/{id}/fork`, POST `/articles/{id}/merge-proposal`, GET `/articles/{id}/forks` |
| `api_compile.py` | GET `/articles/{id}/compile`, GET `/articles/{id}/source`, POST `/compile-preview` |
| `api_contributions.py` | GET `/articles/{id}/contributions`, GET `/articles/{id}/commits`, GET `/articles/{id}/diff/*`, GET `/articles/{id}/blame` |
| `api_comments.py` | GET/POST `/articles/{id}/comments`, POST `/articles/{id}/comments/{id}/resolve` |
| `api_citations.py` | GET `/articles/{id}/citations`, POST `/citations/click`, GET `/citations/transitions` |
| `api_users.py` | GET/POST `/users`, GET `/users/{id}`, POST `/users/{id}/identities`, GET `/users/{id}/reputation` |
| `api_collab.py` | POST `/articles/{id}/collaborate`, POST `/articles/{id}/proposals`, POST `/proposals/{id}/review`, POST `/proposals/{id}/merge` |
| `api_lan.py` | GET `/lan/catalog`, GET `/lan/nodes`, GET `/lan/status` |
| `api_search.py` | GET `/search` |
| `api.py` | Facade router (`/api/v1` prefix), health check |

## Development

```bash
# Run tests
pytest                    # 371 tests passed, 31 test files

# Run with coverage
pytest --cov=peerpedia_core --cov=peerpedia
```

## Design

See [design/brainstorm.md](design/brainstorm.md) for the full vision, decisions, and roadmap.
See [STATUS.md](STATUS.md) for current state and restart guide.

## License

MIT — Protocol is free, reference implementation is MIT.
Content published via PeerPedia is CC BY-SA 4.0 by default.
