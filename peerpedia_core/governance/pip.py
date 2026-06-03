"""Layer 1: PIP (PeerPedia Improvement Proposal) governance.

Protocol evolution mechanism. Analogous to Python PEPs or Bitcoin BIPs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PIPStatus(str, Enum):
    DRAFT = "draft"
    DISCUSSION = "discussion"
    VOTING = "voting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class PIPLayer(int):
    """Which protocol layer the PIP targets."""
    CORE = 0       # Layer 0: almost never changed
    MODULE = 1     # Layer 1: versioned modules
    PARAMETER = 2  # Layer 2: configurable parameters


@dataclass
class PIP:
    """A PeerPedia Improvement Proposal."""
    id: str
    title: str
    author_id: str
    layer: int
    summary: str
    specification: str
    status: PIPStatus = PIPStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    discussion_url: Optional[str] = None
    votes_for: int = 0
    votes_against: int = 0
    vote_threshold: float = 0.67  # 67% for Layer 1, 51% for Layer 2

    def is_accepted(self) -> bool:
        if self.votes_for + self.votes_against == 0:
            return False
        ratio = self.votes_for / (self.votes_for + self.votes_against)
        return ratio >= self.vote_threshold

    def advance(self, new_status: PIPStatus) -> None:
        """Advance the PIP through the lifecycle."""
        valid_transitions = {
            PIPStatus.DRAFT: [PIPStatus.DISCUSSION],
            PIPStatus.DISCUSSION: [PIPStatus.VOTING, PIPStatus.REJECTED],
            PIPStatus.VOTING: [PIPStatus.ACCEPTED, PIPStatus.REJECTED],
            PIPStatus.ACCEPTED: [PIPStatus.SUPERSEDED],
            PIPStatus.REJECTED: [PIPStatus.DRAFT],  # can revise and resubmit
        }
        if new_status in valid_transitions.get(self.status, []):
            self.status = new_status
        else:
            raise ValueError(
                f"Invalid PIP transition: {self.status} → {new_status}"
            )
