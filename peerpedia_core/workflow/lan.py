"""Layer 1: LAN node discovery and catalog sync.

Handles UDP broadcast heartbeat for peer discovery and catalog.md
YAML frontmatter serialization/parsing for article pool exchange.

No new dependencies -- hand-written YAML for the fixed catalog schema.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

CATALOG_YAML_DELIMITER = "---"


# ============================================================================
# Catalog YAML Serialization
# ============================================================================

def catalog_to_yaml_string(data: dict[str, Any]) -> str:
    """Serialize catalog data to YAML frontmatter + Markdown table.

    The output is a valid .md file: YAML frontmatter between --- delimiters,
    followed by a human-readable Markdown table.
    """
    lines = [CATALOG_YAML_DELIMITER]
    _dict_to_yaml_lines(data, lines, indent=0)
    lines.append(CATALOG_YAML_DELIMITER)
    lines.append("")
    lines.append(f"# 知著网 文章目录 -- {data.get('node_id', 'unknown')}")
    lines.append("")

    articles = data.get("articles", [])
    if articles:
        lines.append("| ID | 标题 | 作者 | 版本 | CID |")
        lines.append("|----|------|------|------|-----|")
        for a in articles:
            aid = a.get("id", "")[:8]
            title = a.get("title", "")
            authors = ", ".join(a.get("authors", []))
            version = a.get("version", "")
            cid = (a.get("cid") or "")[:12]
            lines.append(f"| {aid} | {title} | {authors} | {version} | {cid} |")

    return "\n".join(lines) + "\n"


def _dict_to_yaml_lines(data: dict[str, Any], lines: list[str], indent: int):
    """Recursively write dict to YAML lines (hand-written, no PyYAML)."""
    prefix = "  " * indent
    for key, value in data.items():
        if value is None:
            lines.append(f"{prefix}{key}:")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, float):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, str):
            if "\n" in value or '"' in value or (":" in value and not value.startswith("http")):
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{prefix}{key}: "{escaped}"')
            else:
                lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            elif all(isinstance(v, dict) for v in value):
                lines.append(f"{prefix}{key}:")
                for v in value:
                    lines.append(f"{prefix}  -")
                    _dict_to_yaml_lines(v, lines, indent + 2)
            else:
                # Simple list: inline
                items = ", ".join(
                    f'"{v}"' if isinstance(v, str) else str(v) for v in value
                )
                lines.append(f"{prefix}{key}: [{items}]")
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            _dict_to_yaml_lines(value, lines, indent + 1)
        else:
            lines.append(f'{prefix}{key}: "{value}"')


# ============================================================================
# Catalog YAML Parsing
# ============================================================================

def parse_catalog_yaml(content: str) -> dict[str, Any]:
    """Parse catalog.md content, extracting the YAML frontmatter.

    Only the YAML frontmatter (between --- delimiters) is parsed.
    The Markdown table below is ignored (it's for human readers).
    """
    lines = content.split("\n")

    # Find the YAML block between first two --- delimiters
    yaml_start = -1
    yaml_end = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == CATALOG_YAML_DELIMITER:
            if yaml_start == -1:
                yaml_start = i
            elif yaml_end == -1:
                yaml_end = i
                break

    if yaml_start == -1 or yaml_end == -1 or yaml_end <= yaml_start + 1:
        return {"node_id": "unknown", "updated": "", "articles": []}

    yaml_lines = lines[yaml_start + 1 : yaml_end]
    return _parse_yaml_lines(yaml_lines)


def _parse_yaml_lines(lines: list[str]) -> dict[str, Any]:
    """Parse a list of YAML lines into a dict using a simple recursive descent parser."""
    result: dict[str, Any] = {}
    i = 0

    def current_indent() -> int:
        if i >= len(lines):
            return 0
        line = lines[i]
        if not line.strip():
            return 0
        return len(line) - len(line.lstrip())

    def parse_value(stripped: str, key_indent: int) -> tuple[Any, int]:
        """Parse a value starting from current position. Returns (value, lines_consumed_after_key)."""
        nonlocal i
        if not stripped:
            # Empty value after colon -- could be nested structure
            j = i + 1
            while j < len(lines):
                nl = lines[j]
                if not nl.strip():
                    j += 1
                    continue
                nindent = len(nl) - len(nl.lstrip())
                if nindent <= key_indent:
                    return None, 0  # Empty/null value
                nstripped = nl.strip()
                if nstripped.startswith("-"):
                    # List of items (possibly dicts)
                    result_list = []
                    while j < len(lines):
                        nl2 = lines[j]
                        if not nl2.strip():
                            j += 1
                            continue
                        nindent2 = len(nl2) - len(nl2.lstrip())
                        if nindent2 < nindent:
                            break
                        nstripped2 = nl2.strip()
                        if nstripped2.startswith("-"):
                            # Extract value after "-" (case: "- " or bare "-")
                            val_str = nstripped2[2:].strip() if len(nstripped2) > 1 else ""
                            if val_str:
                                result_list.append(_parse_scalar(val_str))
                                j += 1
                            else:
                                # Dict item (bare "-" with indented keys on following lines)
                                sub_lines = _collect_indented(lines, j + 1, nindent2 + 2)
                                result_list.append(_parse_yaml_lines(sub_lines))
                                j += 1 + len(sub_lines)
                        else:
                            break
                    i = j - 1
                    return result_list, i - (key_line_idx)
                else:
                    # Nested dict
                    sub_lines = _collect_indented(lines, j, nindent)
                    i = j + len(sub_lines) - 1
                    return _parse_yaml_lines(sub_lines), i - (key_line_idx)
            return None, 0

        # Non-empty value
        return _parse_scalar(stripped), 0

    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if ":" in stripped:
            key, _, value_str = stripped.partition(":")
            key = key.strip()
            value_str = value_str.strip()
            key_line_idx = i

            val, consumed = parse_value(value_str, indent)
            # Advance past any lines consumed by the value parser
            # (parse_value updates i internally for nested structures)
            if consumed == 0 and not value_str:
                # Check if this is a nested structure
                next_i = i + 1
                if next_i < len(lines):
                    nl = lines[next_i]
                    if nl.strip():
                        nindent = len(nl) - len(nl.lstrip())
                        if nindent > indent:
                            # parse_value already handled this
                            pass
                if val is None and i == key_line_idx:
                    # Truly empty -- no nested content
                    result[key] = None
            else:
                result[key] = val

        i += 1

    return result


def _parse_scalar(value_str: str) -> Any:
    """Parse a single scalar YAML value."""
    value_str = value_str.strip()
    if value_str == "true":
        return True
    if value_str == "false":
        return False
    if value_str in ("null", "~", ""):
        return None
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        inner = value_str[1:-1]
        if value_str.startswith('"'):
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1]
        if not inner.strip():
            return []
        items = []
        for item in inner.split(","):
            item = item.strip().strip('"').strip("'")
            items.append(item)
        return items
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    return value_str


def _collect_indented(lines: list[str], start: int, min_indent: int) -> list[str]:
    """Collect consecutive lines indented at least min_indent from a base context.

    Stops at blank lines followed by lines below min_indent, or end of input.
    """
    result = []
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            # Include blank lines that are sandwiched between indented content
            result.append(line)
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent < min_indent:
            break
        result.append(line)
        i += 1
    return result


# ============================================================================
# UDP Heartbeat
# ============================================================================

HEARTBEAT_TYPE = "peerpedia_hello"
BROADCAST_ADDR = "255.255.255.255"


def build_heartbeat_message(
    node_id: str,
    host: str,
    port: int,
    version: str = "0.2.0",
    articles_count: int = 0,
) -> str:
    """Build a JSON heartbeat message."""
    return json.dumps({
        "type": HEARTBEAT_TYPE,
        "node_id": node_id,
        "host": host,
        "port": port,
        "version": version,
        "articles_count": articles_count,
    })


def parse_heartbeat_message(data: str) -> dict[str, Any] | None:
    """Parse a received heartbeat message.

    Returns the message dict if valid, None otherwise.
    """
    try:
        msg = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None

    if msg.get("type") != HEARTBEAT_TYPE:
        return None

    required = ["node_id", "host", "port"]
    for key in required:
        if key not in msg:
            return None

    return msg


def start_udp_broadcaster(
    node_id: str,
    host: str,
    port: int,
    *,
    broadcast_port: int = 3690,
    interval: float = 3.0,
    stop_event: threading.Event | None = None,
) -> threading.Thread:
    """Start a background thread that sends UDP heartbeat broadcasts.

    Args:
        node_id: This node's unique ID.
        host: This node's IP address (for the heartbeat, not binding).
        port: This node's HTTP port.
        broadcast_port: UDP port for broadcasting.
        interval: Seconds between heartbeats.
        stop_event: Set to stop the broadcaster.

    Returns:
        The running Thread object.
    """
    if stop_event is None:
        stop_event = threading.Event()

    def _broadcast_loop():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        while not stop_event.is_set():
            try:
                msg = build_heartbeat_message(
                    node_id=node_id,
                    host=host,
                    port=port,
                    articles_count=_count_local_articles(),
                )
                sock.sendto(msg.encode("utf-8"), (BROADCAST_ADDR, broadcast_port))
            except Exception:
                pass  # Network not available -- retry next interval
            stop_event.wait(interval)

        sock.close()

    thread = threading.Thread(target=_broadcast_loop, daemon=True, name="peerpedia-udp-bcast")
    thread.start()
    return thread


def start_udp_listener(
    database_url: str,
    *,
    listen_port: int = 3690,
    stop_event: threading.Event | None = None,
) -> threading.Thread:
    """Start a background thread that listens for UDP heartbeat broadcasts.

    Received heartbeats are upserted into the local lan_nodes table.
    """
    from peerpedia_core.storage.db import get_engine, init_db, get_session, upsert_node

    if stop_event is None:
        stop_event = threading.Event()

    def _listen_loop():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", listen_port))
        except OSError:
            return  # Port already in use

        sock.settimeout(1.0)

        engine = get_engine(database_url)
        init_db(engine)

        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(4096)
                msg = parse_heartbeat_message(data.decode("utf-8", errors="replace"))
                if msg is None:
                    continue

                # Ignore our own broadcasts
                self_id = _get_self_node_id(database_url)
                if self_id and msg["node_id"] == self_id:
                    continue

                session = get_session(engine)
                try:
                    upsert_node(
                        session,
                        node_id=msg["node_id"],
                        host=msg["host"],
                        port=msg["port"],
                        version=msg.get("version", "0.2.0"),
                        articles_count=msg.get("articles_count", 0),
                    )
                    session.commit()
                except Exception:
                    session.rollback()
                finally:
                    session.close()
            except socket.timeout:
                continue
            except Exception:
                continue

        sock.close()

    thread = threading.Thread(target=_listen_loop, daemon=True, name="peerpedia-udp-listen")
    thread.start()
    return thread


def _count_local_articles() -> int:
    """Count local articles for heartbeat."""
    try:
        from peerpedia.config.settings import settings
        from peerpedia_core.storage.db import get_engine, init_db, get_session, list_articles
        engine = get_engine(settings.database_url)
        init_db(engine)
        session = get_session(engine)
        try:
            return len(list_articles(session, limit=10000))
        finally:
            session.close()
    except Exception:
        return 0


def _get_self_node_id(database_url: str) -> str | None:
    """Get this node's own node_id from the database."""
    try:
        from peerpedia_core.storage.db import get_engine, init_db, get_session, get_online_nodes
        engine = get_engine(database_url)
        init_db(engine)
        session = get_session(engine)
        try:
            nodes = get_online_nodes(session, timeout_seconds=86400)
            for n in nodes:
                if bool(n.is_self):
                    return n.node_id
            return None
        finally:
            session.close()
    except Exception:
        return None
