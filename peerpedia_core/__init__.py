"""PeerPedia Core — Protocol library.

This package defines the PeerPedia protocol. It is independent of any
specific client implementation. Anyone can build a PeerPedia client
by implementing the interfaces defined here.

Layers:
    Layer 0 (immutable): protocol/ — message schemas, signing, CID addressing
    Layer 1 (versioned): reputation/, governance/ — PIP-upgradable algorithms
    Layer 2 (configurable): algorithm parameters, community-adjustable weights
"""

__version__ = "0.1.0"
