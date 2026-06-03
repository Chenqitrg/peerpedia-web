"""Layer 1: Reputation algorithm v1.

This algorithm can be upgraded via PIP. The abstract base class defines
the interface; concrete versions implement the algorithm.

Current v1:
- 4 dimensions: academic, review, collaboration, education
- Time decay: 90 days inactivity → 0.1% decay per day
- Identity weights boost initial reputation
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from peerpedia_core.protocol import IdentityType, ReputationVector


# ── Layer 2: Configurable parameters ─────────────────────────────────────────

class ReputationParams:
    """Parameters that can be tuned without protocol upgrade."""

    # Time decay
    decay_grace_days: int = 90
    decay_rate_per_day: float = 0.001  # 0.1%

    # Identity trust weights
    identity_weights: dict[IdentityType, float] = {
        IdentityType.ORCID: 1.0,
        IdentityType.INST_EMAIL: 0.8,
        IdentityType.ARXIV: 0.6,
        IdentityType.GOOGLE_SCHOLAR: 0.5,
        IdentityType.GITHUB: 0.3,
    }

    # Base reputation from verified identities
    base_reputation_per_identity: float = 5.0  # points per verified identity

    # Contribution weight multipliers (Layer 2 — community adjustable)
    change_type_weights: dict[str, float] = {
        "new_theorem": 5.0,
        "proof_fix": 4.0,
        "content": 2.0,
        "prose": 1.0,
        "format": 0.3,
    }

    # Point values
    points_submit: int = 10
    points_accepted: int = 50
    points_review: int = 20
    points_per_citation: int = 2
    points_high_quality_review: int = 5  # base, multiplied by author score
    points_report_spam: int = 5
    points_pin_per_day: int = 1


# ── Abstract base (Layer 1 interface) ────────────────────────────────────────

class BaseReputation(ABC):
    """Abstract reputation algorithm — versioned via PIP."""

    def __init__(self, params: Optional[ReputationParams] = None):
        self.params = params or ReputationParams()

    @abstractmethod
    def compute(self, user_id: str) -> ReputationVector:
        """Compute the current reputation vector for a user."""
        ...

    @abstractmethod
    def apply_decay(self, vector: ReputationVector, last_active: datetime) -> ReputationVector:
        """Apply time-based decay to a reputation vector."""
        ...

    @abstractmethod
    def merge_identities(self, vector: ReputationVector, verified_count: int) -> ReputationVector:
        """Apply identity verification bonus to initial reputation."""
        ...


# ── v1 Implementation ────────────────────────────────────────────────────────

class ReputationV1(BaseReputation):
    """Reputation algorithm v1.

    Four-dimensional radar:
    - academic_contribution: article output × citation impact
    - review_quality: review helpfulness rated by authors
    - collaboration_spirit: co-authored articles + partner ratings
    - education_outreach: reader engagement (pins, shares)
    """

    def compute(self, user_id: str) -> ReputationVector:
        """Compute from stored contribution and review records."""
        # For MVP: placeholder — reads from SQLite via storage layer
        return ReputationVector(user_id=user_id)

    def apply_decay(self, vector: ReputationVector, last_active: datetime) -> ReputationVector:
        """Decay reputation for inactive users."""
        days_inactive = (datetime.utcnow() - last_active).days
        if days_inactive <= self.params.decay_grace_days:
            return vector

        decay_days = days_inactive - self.params.decay_grace_days
        decay_factor = (1 - self.params.decay_rate_per_day) ** decay_days

        vector.academic_contribution *= decay_factor
        vector.review_quality *= decay_factor
        vector.collaboration_spirit *= decay_factor
        vector.education_outreach *= decay_factor

        return vector

    def merge_identities(self, vector: ReputationVector, verified_count: int) -> ReputationVector:
        """Add base reputation from verified identities."""
        bonus = self.params.base_reputation_per_identity * verified_count
        vector.academic_contribution = min(100, vector.academic_contribution + bonus)
        return vector


# ── Registry ─────────────────────────────────────────────────────────────────

REPUTATION_VERSIONS = {
    "v1": ReputationV1,
}


def get_reputation(version: str = "v1") -> BaseReputation:
    """Get the current reputation algorithm."""
    cls = REPUTATION_VERSIONS.get(version)
    if cls is None:
        raise ValueError(f"Unknown reputation version: {version}")
    return cls()
