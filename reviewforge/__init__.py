"""ReviewForge — an LLM-powered code review tool for diffs and pull requests."""

from .models import (
    FileDiff,
    Hunk,
    DiffLine,
    LineType,
    Finding,
    Severity,
    Category,
    ReviewResult,
)
from .diff_parser import parse_diff

__version__ = "0.1.0"

__all__ = [
    "FileDiff",
    "Hunk",
    "DiffLine",
    "LineType",
    "Finding",
    "Severity",
    "Category",
    "ReviewResult",
    "parse_diff",
]
