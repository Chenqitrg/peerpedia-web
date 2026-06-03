"""Version string utilities for article version bumps.

Version strings follow the format v<major>.<minor> (e.g., v0.1 -> v0.2).
"""


def bump_minor_version(version_str: str) -> str:
    """Bump the minor version component: v0.1 -> v0.2, v1.5 -> v1.6.

    Falls back to 'v0.2' if the version string cannot be parsed.
    """
    try:
        parts = version_str.lstrip("v").split(".")
        minor = int(parts[1]) + 1 if len(parts) > 1 else 1
        return f"v{parts[0]}.{minor}"
    except (ValueError, IndexError):
        return "v0.2"
