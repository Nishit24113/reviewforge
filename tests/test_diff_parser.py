"""
Tests for the unified-diff parser.

Cover single/multi-file diffs, new/deleted/renamed files, line-number tracking
across hunks, hunks without explicit counts, and robustness against extended
git headers.
"""

from reviewforge.diff_parser import parse_diff
from reviewforge.models import LineType


SIMPLE_DIFF = """diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -1,4 +1,5 @@
 def main():
-    x = 1
+    x = 2
+    y = 3
     return x
"""


def test_parses_single_file():
    files = parse_diff(SIMPLE_DIFF)
    assert len(files) == 1
    assert files[0].path == "app.py"
    assert len(files[0].hunks) == 1


def test_added_lines_detected():
    files = parse_diff(SIMPLE_DIFF)
    added = files[0].hunks[0].added_lines()
    assert [ln.content for ln in added] == ["    x = 2", "    y = 3"]


def test_added_line_numbers_are_new_file_positions():
    files = parse_diff(SIMPLE_DIFF)
    # hunk starts at new line 1: " def main()"=1, "+ x=2"=2, "+ y=3"=3, " return"=4
    assert files[0].added_line_numbers() == [2, 3]


def test_removed_line_tracked_with_old_lineno():
    files = parse_diff(SIMPLE_DIFF)
    removed = [ln for ln in files[0].hunks[0].lines if ln.type == LineType.REMOVED]
    assert len(removed) == 1
    assert removed[0].content == "    x = 1"
    assert removed[0].old_lineno == 2
    assert removed[0].new_lineno is None


MULTI_FILE_DIFF = """diff --git a/one.py b/one.py
--- a/one.py
+++ b/one.py
@@ -1,2 +1,3 @@
 a
+b
 c
diff --git a/two.py b/two.py
--- a/two.py
+++ b/two.py
@@ -5,2 +5,3 @@
 d
+e
 f
"""


def test_parses_multiple_files():
    files = parse_diff(MULTI_FILE_DIFF)
    assert [f.path for f in files] == ["one.py", "two.py"]


def test_second_file_hunk_line_numbers():
    files = parse_diff(MULTI_FILE_DIFF)
    # two.py hunk starts at new line 5: " d"=5, "+e"=6, " f"=7
    assert files[1].added_line_numbers() == [6]


NEW_FILE_DIFF = """diff --git a/new.py b/new.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+print("hello")
+print("world")
"""


def test_new_file_flagged():
    files = parse_diff(NEW_FILE_DIFF)
    assert files[0].is_new is True
    assert files[0].path == "new.py"
    assert files[0].added_line_numbers() == [1, 2]


DELETED_FILE_DIFF = """diff --git a/gone.py b/gone.py
deleted file mode 100644
index 3333333..0000000
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-print("bye")
-print("now")
"""


def test_deleted_file_flagged_and_path_is_old():
    files = parse_diff(DELETED_FILE_DIFF)
    assert files[0].is_deleted is True
    assert files[0].path == "gone.py"
    assert files[0].added_line_numbers() == []


RENAME_DIFF = """diff --git a/old_name.py b/new_name.py
similarity index 95%
rename from old_name.py
rename to new_name.py
--- a/old_name.py
+++ b/new_name.py
@@ -1,1 +1,1 @@
-old
+new
"""


def test_rename_flagged():
    files = parse_diff(RENAME_DIFF)
    assert files[0].is_rename is True
    assert files[0].old_path == "old_name.py"
    assert files[0].new_path == "new_name.py"


HUNK_WITHOUT_COUNTS = """diff --git a/single.py b/single.py
--- a/single.py
+++ b/single.py
@@ -3 +3 @@
-old
+new
"""


def test_hunk_without_explicit_counts_defaults_to_one():
    files = parse_diff(HUNK_WITHOUT_COUNTS)
    hunk = files[0].hunks[0]
    assert hunk.old_count == 1
    assert hunk.new_count == 1
    assert hunk.new_start == 3
    assert files[0].added_line_numbers() == [3]


def test_hunk_section_heading_captured():
    diff = """diff --git a/x.py b/x.py
--- a/x.py
+++ b/x.py
@@ -10,3 +10,4 @@ def my_function():
 a
+b
 c
"""
    files = parse_diff(diff)
    assert files[0].hunks[0].section == "def my_function():"


def test_empty_diff_returns_empty_list():
    assert parse_diff("") == []


def test_content_before_first_header_ignored():
    diff = "garbage line\n" + SIMPLE_DIFF
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].path == "app.py"


def test_no_newline_marker_ignored():
    diff = """diff --git a/x.py b/x.py
--- a/x.py
+++ b/x.py
@@ -1 +1 @@
-old
+new
\\ No newline at end of file
"""
    files = parse_diff(diff)
    added = files[0].hunks[0].added_lines()
    assert len(added) == 1
    assert added[0].content == "new"
