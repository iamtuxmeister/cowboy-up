"""
Shared utilities used across cowboy_up commands.
"""

from __future__ import annotations
from pathlib import Path
import re

from cowboy_up import console


def detect_app_name() -> str:
    """
    Detect the app name from src/*.app.src in the current directory.

    Path.stem only strips the last extension, so "bible_site.app.src"
    gives stem="bible_site.app". We want just the first segment.
    """
    src = Path("src")
    if not src.exists():
        console.die("No src/ directory found. Run from your project root.")

    matches = list(src.glob("*.app.src"))
    if not matches:
        console.die("No src/*.app.src found. Run from your project root.")

    # "bible_site.app.src" -> ["bible_site", "app", "src"] -> "bible_site"
    return matches[0].name.split(".")[0]


def to_snake(name: str) -> str:
    """
    Convert CamelCase model name to snake_case module name.
    BookChapter -> book_chapter,  Book -> book
    """
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return s.lower()
