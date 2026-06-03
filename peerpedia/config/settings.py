"""PeerPedia configuration."""

from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings — loaded from env and config files."""

    # Paths
    peerpedia_home: Path = Path.home() / ".peerpedia"
    articles_dir: Path = Path.home() / ".peerpedia" / "articles"
    profiles_dir: Path = Path.home() / ".peerpedia" / "profiles"
    db_path: Path = Path.home() / ".peerpedia" / "db" / "peerpedia.db"

    # Server
    host: str = "127.0.0.1"
    port: int = 8080
    lan_mode: bool = False

    # Content
    default_license: str = "CC BY-SA 4.0"
    default_language: str = "en"

    # Reputation (Layer 2 — overridable)
    reputation_version: str = "v1"

    # Database
    database_url: str = ""

    def __post_init__(self):
        if not self.database_url:
            self.database_url = f"sqlite:///{self.db_path}"

    def ensure_dirs(self):
        """Create all required directories."""
        for d in [self.peerpedia_home, self.articles_dir, self.profiles_dir, self.db_path.parent]:
            d.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
