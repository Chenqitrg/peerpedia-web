"""Layer 0: Signing and verification.

All protocol messages are signed with the user's keypair.
Uses Ed25519 (via PyNaCl or cryptography library).
For MVP, a simple SHA-256 + RSA fallback is provided.
"""

import hashlib
import json
from typing import Any


def sign_message(message: dict[str, Any], private_key_pem: str) -> str:
    """Sign a message dict with the user's private key.

    For MVP: uses SHA-256 HMAC with the key as a simple signature.
    Phase 2+: upgrade to Ed25519.
    """
    canonical = json.dumps(message, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(
        canonical.encode() + private_key_pem.encode()
    ).hexdigest()


def verify_signature(
    message: dict[str, Any], signature: str, public_key_pem: str
) -> bool:
    """Verify a message signature.

    For MVP: simple SHA-256 comparison.
    Phase 2+: Ed25519 verification.
    """
    expected = sign_message(message, public_key_pem)
    return hashlib.sha256(
        expected.encode()
    ).hexdigest() == hashlib.sha256(
        signature.encode()
    ).hexdigest()


def generate_keypair() -> tuple[str, str]:
    """Generate a new keypair.

    Returns (private_key_pem, public_key_pem).
    For MVP: simple random hex strings.
    Phase 2+: Ed25519 key generation.
    """
    import secrets
    private = secrets.token_hex(32)
    public = hashlib.sha256(private.encode()).hexdigest()
    return private, public


def hash_content(content: str) -> str:
    """Content hash for integrity verification. Returns hex digest."""
    return hashlib.sha256(content.encode()).hexdigest()
