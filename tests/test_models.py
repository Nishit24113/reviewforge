"""
Tests for the core data models — severity ordering, finding serialization,
and review-result aggregation/sorting.
"""

from reviewforge.models import (
    Finding, Severity, Category, ReviewResult,
)


def test_severity_rank_ordering():
    assert Severity.INFO.rank < Severity.MINOR.rank
    assert Severity.MINOR.rank < Severity.MAJOR.rank
    assert Severity.MAJOR.rank < Severity.CRITICAL.rank


def _finding(file="a.py", line=1, severity=Severity.MINOR, category=Category.BUG, title="t"):
    return Finding(
        file=file, line=line, severity=severity, category=category,
        title=title, body="details",
    )


def test_finding_to_dict():
    f = _finding(severity=Severity.CRITICAL, category=Category.SECURITY)
    d = f.to_dict()
    assert d["severity"] == "critical"
    assert d["category"] == "security"
    assert d["title"] == "t"
    assert d["suggestion"] is None


def test_review_result_by_severity():
    result = ReviewResult(findings=[
        _finding(severity=Severity.CRITICAL),
        _finding(severity=Severity.MINOR),
        _finding(severity=Severity.CRITICAL),
    ])
    assert len(result.by_severity(Severity.CRITICAL)) == 2
    assert len(result.by_severity(Severity.MINOR)) == 1


def test_sorted_findings_most_severe_first():
    result = ReviewResult(findings=[
        _finding(severity=Severity.INFO, file="b.py", line=5),
        _finding(severity=Severity.CRITICAL, file="a.py", line=10),
        _finding(severity=Severity.MAJOR, file="a.py", line=2),
    ])
    ordered = result.sorted_findings()
    assert [f.severity for f in ordered] == [
        Severity.CRITICAL, Severity.MAJOR, Severity.INFO
    ]


def test_sorted_findings_tiebreak_by_file_then_line():
    result = ReviewResult(findings=[
        _finding(severity=Severity.MAJOR, file="b.py", line=1),
        _finding(severity=Severity.MAJOR, file="a.py", line=9),
        _finding(severity=Severity.MAJOR, file="a.py", line=3),
    ])
    ordered = result.sorted_findings()
    assert [(f.file, f.line) for f in ordered] == [
        ("a.py", 3), ("a.py", 9), ("b.py", 1)
    ]


def test_review_result_to_dict():
    result = ReviewResult(
        findings=[_finding(severity=Severity.CRITICAL)],
        files_reviewed=3,
        summary="Looks mostly good",
    )
    d = result.to_dict()
    assert d["finding_count"] == 1
    assert d["files_reviewed"] == 3
    assert d["summary"] == "Looks mostly good"
    assert len(d["findings"]) == 1
