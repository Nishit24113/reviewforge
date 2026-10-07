# ReviewForge

LLM-powered code review for diffs and pull requests. ReviewForge parses a
`git diff`, sends the changed code to an LLM with a structured review prompt,
and turns the response into **anchored findings** — each tied to a specific file
and line so it can be posted as an inline PR comment.

> Status: in active development. This commit lays the foundation — the diff
> parser and core data models that everything else builds on.

## Why

Automated review tools either drown you in style nits or require heavy CI setup.
ReviewForge aims for a focused middle ground: a small, well-tested core that

- parses real-world unified diffs (new/deleted/renamed files, multi-hunk),
- anchors each finding to the correct **new-file line number**,
- returns structured, severity-ranked findings instead of a wall of prose,
- posts them as inline PR comments (or prints a report locally).

## Architecture

```
diff text ──▶ diff_parser ──▶ FileDiff/Hunk/DiffLine
                                     │
                                     ▼
                             reviewer (LLM)  ──▶ ReviewResult(Finding[])
                                     │
                                     ▼
                       github poster / CLI report
```

### Implemented

- **`models.py`** — `FileDiff`, `Hunk`, `DiffLine`, `Finding`, `Severity`,
  `Category`, `ReviewResult`. Shared vocabulary across the whole pipeline.
- **`diff_parser.py`** — unified-diff → structured objects, tracking added-line
  positions in the new file (where review comments must land).

### Planned

- `reviewer.py` — orchestrates diff → prompt → LLM → findings (LLM client injected).
- `llm.py` — Claude client abstraction.
- `github.py` — post findings as inline PR comments via the GitHub API.
- `cli.py` — `reviewforge review <diff>` entrypoint.

## Usage (foundation)

```python
from reviewforge import parse_diff

files = parse_diff(open("change.diff").read())
for f in files:
    print(f.path, "added lines:", f.added_line_numbers())
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

**Built by Nishit Patel** | MS Computer Science, Arizona State University
