"""
Core data models for ReviewForge.

These types describe both the *input* to a review (a parsed diff) and its
*output* (structured findings). Keeping them in one place lets the diff parser,
the LLM reviewer, and the GitHub poster share a single vocabulary.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class LineType(Enum):
    """The role of a line within a diff hunk."""
    CONTEXT = "context"    # unchanged, shown for context
    ADDED = "added"        # new line (prefixed with +)
    REMOVED = "removed"    # deleted line (prefixed with -)


class Severity(Enum):
    """How serious a finding is. Ordered from least to most severe."""
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        order = [Severity.INFO, Severity.MINOR, Severity.MAJOR, Severity.CRITICAL]
        return order.index(self)


class Category(Enum):
    """What kind of issue a finding describes."""
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    TEST = "test"
    OTHER = "other"


@dataclass
class DiffLine:
    """A single line within a hunk, with its line numbers in each file version."""
    type: LineType
    content: str
    old_lineno: Optional[int] = None   # line number in the original file
    new_lineno: Optional[int] = None   # line number in the new file


@dataclass
class Hunk:
    """A contiguous block of changes within a file."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLine] = field(default_factory=list)
    section: str = ""   # the optional "@@ ... @@ section heading" text

    def added_lines(self) -> List[DiffLine]:
        """Only the newly added lines — the ones a reviewer can comment on."""
        return [ln for ln in self.lines if ln.type == LineType.ADDED]


@dataclass
class FileDiff:
    """All changes to a single file."""
    old_path: str
    new_path: str
    hunks: List[Hunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    is_rename: bool = False

    @property
    def path(self) -> str:
        """The current path (new path unless the file was deleted)."""
        return self.new_path if not self.is_deleted else self.old_path

    def added_line_numbers(self) -> List[int]:
        """New-file line numbers of all added lines across every hunk."""
        return [
            ln.new_lineno
            for hunk in self.hunks
            for ln in hunk.added_lines()
            if ln.new_lineno is not None
        ]


@dataclass
class Finding:
    """A single issue the reviewer identified."""
    file: str
    line: int
    severity: Severity
    category: Category
    title: str
    body: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "body": self.body,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewResult:
    """The outcome of reviewing a diff."""
    findings: List[Finding] = field(default_factory=list)
    files_reviewed: int = 0
    summary: str = ""

    def by_severity(self, severity: Severity) -> List[Finding]:
        return [f for f in self.findings if f.severity == severity]

    def sorted_findings(self) -> List[Finding]:
        """Findings ordered most-severe first, then by file and line."""
        return sorted(
            self.findings,
            key=lambda f: (-f.severity.rank, f.file, f.line),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "files_reviewed": self.files_reviewed,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.sorted_findings()],
        }
