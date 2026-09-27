"""Shared immutable data objects for Insight Monitor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceDocument:
    """A fetched (or failed) public source."""

    url: str
    title: str = ""
    text: str = ""
    date_hint: str = ""
    status: str = "success"
    error: str = ""
    source_kind: str = "web"


@dataclass(frozen=True)
class SourceSummary:
    url: str
    title: str
    summary: str
    date_hint: str = ""
    status: str = "success"
    error: str = ""
    source_kind: str = "web"
    evidence: str = ""


@dataclass(frozen=True)
class Report:
    topic: str
    angle: str
    mode: str
    generated_at: str
    executive_summary: list[str] = field(default_factory=list)
    common_points: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    sources: list[SourceSummary] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
