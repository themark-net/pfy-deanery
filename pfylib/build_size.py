"""File and line caps for a pfy build task.

small is the historical default (40 files, 4000 lines). product is the
larger cap a multi-file round needs. An explicit --max-files or
--max-lines flag wins over the preset for that dimension.
"""

from __future__ import annotations

import re

SMALL_MAX_FILES = 40
SMALL_MAX_LINES = 4000
PRODUCT_MAX_FILES = 120
PRODUCT_MAX_LINES = 12000

PRESETS = {
    "small": {"files": SMALL_MAX_FILES, "lines": SMALL_MAX_LINES},
    "product": {"files": PRODUCT_MAX_FILES, "lines": PRODUCT_MAX_LINES},
}

_SIZE_LINE = re.compile(r"(?m)^size:\s*(small|product)\s*$")


def task_size(task: str) -> str | None:
    """The first `size: small|product` line in a task, if any."""
    match = _SIZE_LINE.search(task or "")
    if not match:
        return None
    return match.group(1)


def resolve_caps(
    *,
    size_flag: str | None,
    max_files_flag: int | None,
    max_lines_flag: int | None,
    task: str,
) -> dict:
    """Effective caps. The flag wins over the task line, which wins over small."""
    name = size_flag or task_size(task) or "small"
    if name not in PRESETS:
        name = "small"
    preset = PRESETS[name]
    files_explicit = max_files_flag is not None
    lines_explicit = max_lines_flag is not None
    return {
        "size": name,
        "max_files": int(max_files_flag) if files_explicit else int(preset["files"]),
        "max_lines": int(max_lines_flag) if lines_explicit else int(preset["lines"]),
        "files_explicit": files_explicit,
        "lines_explicit": lines_explicit,
    }


def file_cap_reason(size: dict) -> str | None:
    """None when the file count is inside the cap. The text names the flag."""
    files = int(size.get("files") or 0)
    max_files = int(size.get("max_files") or 0)
    if files <= max_files:
        return None
    extra = ""
    if not size.get("files_explicit") and files <= PRODUCT_MAX_FILES:
        extra = " or --size product"
    return (
        "changed files %d (max %d). "
        "The flag that raises the file cap is --max-files. "
        "Rerun with --max-files%s."
        % (files, max_files, extra)
    )


def line_cap_message(size: dict) -> str:
    """Stderr text for a line-cap refusal. Names --max-lines, and --size when it would fit."""
    lines = int(size.get("lines") or 0)
    max_lines = int(size.get("max_lines") or 0)
    files = int(size.get("files") or 0)
    hint = "Rerun with --max-lines."
    if (
        not size.get("lines_explicit")
        and lines <= PRODUCT_MAX_LINES
        and files <= PRODUCT_MAX_FILES
    ):
        hint = "Rerun with --max-lines or --size product."
    return (
        "pfy build --local: diff has %d changed lines, over the %d-line cap. "
        "The flag that raises the line cap is --max-lines. "
        "Not reviewed, not committed, not retried. %s"
        % (lines, max_lines, hint)
    )
