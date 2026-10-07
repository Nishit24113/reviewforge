"""
Unified-diff parser for ReviewForge.

Converts the `git diff` text a PR produces into structured FileDiff/Hunk/DiffLine
objects. The reviewer needs two things the raw text doesn't give it directly:
which lines were *added* (those are what we comment on) and the *new-file line
number* of each, so a finding can be anchored to the right place in the PR.
"""

import re
from typing import List, Optional

from .models import FileDiff, Hunk, DiffLine, LineType

# @@ -oldStart,oldCount +newStart,newCount @@ optional section heading
_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<section>.*)$"
)


def parse_diff(diff_text: str) -> List[FileDiff]:
    """
    Parse a unified diff into a list of FileDiff objects.

    Handles multi-file diffs, new/deleted/renamed files, and hunks with or
    without explicit line counts. Unrecognized lines are ignored so that
    extended git headers (index, mode, similarity) don't break parsing.
    """
    files: List[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[Hunk] = None
    old_lineno = 0
    new_lineno = 0

    for line in diff_text.splitlines():
        # Start of a new file's diff
        if line.startswith("diff --git"):
            current_file = _start_file(line)
            files.append(current_file)
            current_hunk = None
            continue

        if current_file is None:
            # Content before the first "diff --git" header — skip it
            continue

        # File-state markers
        if line.startswith("new file mode"):
            current_file.is_new = True
            continue
        if line.startswith("deleted file mode"):
            current_file.is_deleted = True
            continue
        if line.startswith("rename from") or line.startswith("rename to"):
            current_file.is_rename = True
            if line.startswith("rename from"):
                current_file.old_path = line[len("rename from "):].strip()
            else:
                current_file.new_path = line[len("rename to "):].strip()
            continue

        # Canonical path headers override the ones parsed from "diff --git"
        if line.startswith("--- "):
            current_file.old_path = _strip_path(line[4:])
            continue
        if line.startswith("+++ "):
            current_file.new_path = _strip_path(line[4:])
            continue

        # Hunk header
        match = _HUNK_RE.match(line)
        if match:
            current_hunk = Hunk(
                old_start=int(match.group("old_start")),
                old_count=int(match.group("old_count") or 1),
                new_start=int(match.group("new_start")),
                new_count=int(match.group("new_count") or 1),
                section=match.group("section").strip(),
            )
            current_file.hunks.append(current_hunk)
            old_lineno = current_hunk.old_start
            new_lineno = current_hunk.new_start
            continue

        # Hunk body lines
        if current_hunk is not None:
            if line.startswith("+"):
                current_hunk.lines.append(
                    DiffLine(LineType.ADDED, line[1:], old_lineno=None, new_lineno=new_lineno)
                )
                new_lineno += 1
            elif line.startswith("-"):
                current_hunk.lines.append(
                    DiffLine(LineType.REMOVED, line[1:], old_lineno=old_lineno, new_lineno=None)
                )
                old_lineno += 1
            elif line.startswith(" "):
                current_hunk.lines.append(
                    DiffLine(LineType.CONTEXT, line[1:], old_lineno=old_lineno, new_lineno=new_lineno)
                )
                old_lineno += 1
                new_lineno += 1
            elif line.startswith("\\"):
                # "\ No newline at end of file" — not a real line
                continue

    return files


def _start_file(header: str) -> FileDiff:
    """Build a FileDiff from a `diff --git a/x b/y` header."""
    old_path, new_path = _parse_git_header(header)
    return FileDiff(old_path=old_path, new_path=new_path)


def _parse_git_header(header: str) -> tuple:
    """
    Extract the two paths from `diff --git a/<old> b/<new>`.

    Paths with spaces are uncommon in this header form; we split on ' b/' which
    reliably separates the two sides for the typical case.
    """
    body = header[len("diff --git "):]
    if " b/" in body:
        a_part, b_part = body.split(" b/", 1)
        old_path = _strip_path(a_part)
        new_path = _strip_path("b/" + b_part)
        return old_path, new_path
    # Fallback: duplicate whatever we have
    stripped = _strip_path(body)
    return stripped, stripped


def _strip_path(path: str) -> str:
    """Remove the leading a/ or b/ prefix git adds, and surrounding whitespace."""
    path = path.strip()
    if path.startswith(("a/", "b/")):
        return path[2:]
    if path == "/dev/null":
        return path
    return path
