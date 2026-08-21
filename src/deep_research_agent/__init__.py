"""Agent-led deep research with deterministic trust boundaries.

The legacy Supervisor control plane has been removed; the package currently
exposes the domain model and trust-plane primitives that the artifact-based
runtime (docs/ARCHITECTURE.md) is being rebuilt on.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .artifact_store import ArtifactStore, SqliteArtifactStore
from .artifacts import (
    ArtifactDisposition,
    ArtifactEnvelope,
    Provenance,
    evidence_set_id,
)
from .citations import CitationHandle, build_handles, render_citations
from .content_store import ContentStore, InMemoryContentStore, SqliteContentStore
from .contract import ResearchContract, build_contract
from .operations import OperationRequest, SqliteOperationLedger, run_once
from .sources import (
    ArtifactValidationError,
    BodyRef,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    TextLocator,
    locate_quote,
    validate_anchor,
)

try:
    __version__ = _version("deep-research-agent")
except PackageNotFoundError:  # a source tree that was never installed
    __version__ = "0+unknown"

__all__ = [
    "__version__",
    "ArtifactDisposition",
    "ArtifactEnvelope",
    "ArtifactStore",
    "ArtifactValidationError",
    "BodyRef",
    "CitationHandle",
    "ContentStore",
    "InMemoryContentStore",
    "MaterialBody",
    "OperationRequest",
    "Provenance",
    "ResearchContract",
    "SourceAnchor",
    "SourceSnapshotBody",
    "SqliteArtifactStore",
    "SqliteContentStore",
    "SqliteOperationLedger",
    "TextLocator",
    "build_contract",
    "build_handles",
    "evidence_set_id",
    "locate_quote",
    "render_citations",
    "run_once",
    "validate_anchor",
]
