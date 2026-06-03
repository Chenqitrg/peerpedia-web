"""Layer 0: Content addressing (CID).

Each article version gets a content identifier. For Phase 1 (pre-IPFS),
we use SHA-256 hashes. For Phase 2, these map 1:1 to IPFS CIDs.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional


def compute_article_cid(
    typst_source: str,
    metadata: dict,
    git_commit_hash: str,
) -> str:
    """Compute a content identifier for an article version.

    CID = SHA-256(typst_source + canonical_metadata + git_commit)

    In Phase 2, this becomes IPFS CID (multihash format).
    """
    canonical_meta = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    payload = f"{typst_source}\n{canonical_meta}\n{git_commit_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_file_cid(file_path: Path) -> str:
    """Compute CID for a single file."""
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def resolve_cid(cid: str, local_store: Path) -> Optional[Path]:
    """Resolve a CID to a local file path.

    For MVP: looks up in local SQLite index.
    Phase 2: IPFS blockstore lookup.
    """
    # Placeholder — will be implemented with SQLite in storage layer
    return None
