"""
ProjectConfig — all user choices for a cowboy-up project in one object.

Created once during `cowboy-up new` (from CLI flags or interactive prompts)
and passed through the entire generation pipeline.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import re


CssChoice        = Literal["basic", "pico", "tailwind", "daisyui"]
TemplatingChoice = Literal["erlydtl", "bbmustache"]
DbChoice         = Literal["sqlite", "postgres"]

CSS_CHOICES        = ("basic", "pico", "tailwind", "daisyui")
TEMPLATING_CHOICES = ("erlydtl", "bbmustache")
DB_CHOICES         = ("sqlite", "postgres")


@dataclass
class ProjectConfig:
    """All resolved configuration for a new project."""

    # Core identity
    raw_name:     str           # exactly what the user typed
    app_name:     str           # snake_case Erlang atom  e.g. way_life_truth
    display_name: str           # title-cased             e.g. "Way Life Truth"
    target_dir:   Path          # absolute path to project root

    # Feature choices
    css:        CssChoice        = "basic"
    templating: TemplatingChoice = "erlydtl"
    db:         DbChoice         = "sqlite"

    # -----------------------------------------------------------------------
    # Factory
    # -----------------------------------------------------------------------

    @classmethod
    def from_raw_name(
        cls,
        raw_name:     str,
        target_base:  Path,
        css:          CssChoice        = "basic",
        templating:   TemplatingChoice = "erlydtl",
        db:           DbChoice         = "sqlite",
    ) -> "ProjectConfig":
        app_name = _normalise_name(raw_name)
        if not app_name:
            raise ConfigError(
                f"Could not derive a valid Erlang atom from {raw_name!r}.\n"
                "Use letters, numbers, spaces, hyphens, or underscores."
            )
        if not app_name[0].isalpha():
            raise ConfigError(
                f"App name must start with a letter (got: {app_name!r})."
            )

        target_dir = target_base / app_name

        return cls(
            raw_name=raw_name,
            app_name=app_name,
            display_name=_display_name(raw_name),
            target_dir=target_dir,
            css=css,
            templating=templating,
            db=db,
        )

    # -----------------------------------------------------------------------
    # Convenience properties used by templates
    # -----------------------------------------------------------------------

    @property
    def app_name_upper(self) -> str:
        return self.app_name.upper()

    @property
    def erlang_node(self) -> str:
        return f"{self.app_name}@127.0.0.1"

    @property
    def erlang_cookie(self) -> str:
        return f"{self.app_name}_cookie"

    def template_vars(self) -> dict:
        """
        Return a flat dict suitable for string.Template substitution.
        All keys use the $app_name convention.
        """
        return {
            "app_name":       self.app_name,
            "app_name_upper": self.app_name_upper,
            "display_name":   self.display_name,
            "erlang_node":    self.erlang_node,
            "erlang_cookie":  self.erlang_cookie,
            "css":            self.css,
            "templating":     self.templating,
            "db":             {"sqlite": "SQLite", "postgres": "PostgreSQL"}.get(self.db, self.db),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_name(raw: str) -> str:
    """
    "My New App" -> "my_new_app"
    "Bible-Site" -> "bible_site"
    "  spaced  " -> "spaced"
    """
    lowered   = raw.strip().lower()
    replaced  = re.sub(r'[ \-]+', '_', lowered)
    cleaned   = re.sub(r'[^a-z0-9_]', '', replaced)
    collapsed = re.sub(r'_+', '_', cleaned).strip('_')
    return collapsed


def _display_name(raw: str) -> str:
    """
    "my new app"  -> "My New App"
    "bible_site"  -> "Bible Site"
    """
    return re.sub(r'[_\-]', ' ', raw).title()


class ConfigError(ValueError):
    """Raised when project configuration is invalid."""
    pass
