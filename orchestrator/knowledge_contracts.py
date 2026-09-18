"""Контракты локального code-only Project Knowledge Service."""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass


class KnowledgeError(Exception):
    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details

    def as_dict(self):
        return {"code": self.code, "message": self.message, "details": copy.deepcopy(self.details)}


@dataclass(frozen=True)
class ProviderIdentity:
    upstream: str = "Graphify-Labs/graphify"
    package: str = "graphifyy"
    version: str = "0.9.63"
    extraction: str = "code-only/no-cluster"
    schema: str = "graphify-raw-json/0.9.63"

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ProviderCapabilities:
    query: bool = True
    full_rebuild: bool = True
    incremental_refresh: bool = True
    textual_provenance: bool = True
    semantic_documents: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class CorpusPolicy:
    include_roots: tuple[str, ...] = (".",)
    version: str = "code-corpus/v1"
    extensions: tuple[str, ...] = (".py", ".js", ".ts", ".tsx", ".jsx", ".vue")
    max_files: int = 5000
    max_file_bytes: int = 2 * 1024 * 1024
    max_total_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        # Замкнутый профиль: расширять языки только после provider tests.
        if (self.version != "code-corpus/v1" or not isinstance(self.include_roots, tuple)
                or not self.include_roots or any(not isinstance(root, str) or not root for root in self.include_roots)
                or not isinstance(self.extensions, tuple) or not self.extensions
                or any(ext not in {".py", ".js", ".ts", ".tsx", ".jsx", ".vue"} for ext in self.extensions)):
            raise KnowledgeError("validation_failed", "Неверный code-only corpus profile")
        for value in (self.max_files, self.max_file_bytes, self.max_total_bytes):
            if type(value) is not int or value < 1:
                raise KnowledgeError("validation_failed", "Corpus limits должны быть положительными целыми")

    def to_dict(self):
        value = asdict(self)
        value["include_roots"] = list(self.include_roots)
        value["extensions"] = list(self.extensions)
        return value


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class SourceSnapshot:
    digest: str
    policy_digest: str
    files: tuple[SourceFile, ...]
    total_bytes: int

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GraphStatus:
    state: str
    current_snapshot: dict | None
    indexed_snapshot: dict | None
    graph: dict | None
    provider: dict
    error: dict | None = None

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeQueryResult:
    status: str
    content: str
    freshness: str
    citations: tuple[dict, ...]
    provenance: tuple[str, ...]
    indexed_snapshot: dict | None
    provider: dict
    limitations: tuple[str, ...]
    error: dict | None = None

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeRefreshResult:
    status: str
    snapshot: dict | None
    graph: dict | None
    node_count: int = 0
    edge_count: int = 0
    error: dict | None = None
    mode: str = "full-rebuild"
    details: dict | None = None

    def to_dict(self):
        return asdict(self)
