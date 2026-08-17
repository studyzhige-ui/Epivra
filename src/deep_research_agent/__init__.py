"""Agent-led deep research with deterministic trust boundaries.

The legacy Supervisor control plane has been removed; the package currently
exposes the trust-plane primitives that the new artifact-based runtime
(docs/ARCHITECTURE.md) is being rebuilt on.
"""

from .citations import CitationRenderer, render_citations
from .content_store import ContentStore, InMemoryContentStore, SqliteContentStore
from .state import (
    ArtifactValidationError,
    BodyRef,
    CuratedMaterial,
    HydratedSource,
    ResearchContract,
    SourceAnchor,
    SourceDocument,
    TextLocator,
    locate_quote,
    validate_anchor,
)

__version__ = "0.1.0"

__all__ = [
    "ArtifactValidationError",
    "BodyRef",
    "CitationRenderer",
    "ContentStore",
    "CuratedMaterial",
    "HydratedSource",
    "InMemoryContentStore",
    "ResearchContract",
    "SourceAnchor",
    "SourceDocument",
    "SqliteContentStore",
    "TextLocator",
    "locate_quote",
    "render_citations",
    "validate_anchor",
]
