"""
renderer.py — template rendering using stdlib string.Template.

Templates use $var or ${var} substitution. No logic in templates —
all conditionals are handled in Python before rendering.

Template files live in cowboy_up/templates/ and are included in the
package via pyproject.toml package-data.
"""

from __future__ import annotations
from pathlib import Path
from string import Template
from typing import Dict, Any
import importlib.resources as pkg_resources


# ---------------------------------------------------------------------------
# Locate the templates directory bundled with the package
# ---------------------------------------------------------------------------

def _templates_root() -> Path:
    """Return the path to cowboy_up/templates/ whether installed or local."""
    try:
        # Python 3.9+ preferred API
        ref = pkg_resources.files("cowboy_up") / "templates"
        return Path(str(ref))
    except AttributeError:
        # Python 3.8 fallback
        import cowboy_up
        return Path(cowboy_up.__file__).parent / "templates"


TEMPLATES_ROOT = _templates_root()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_file(template_path: str, variables: Dict[str, Any]) -> str:
    """
    Read a template file relative to the templates root and render it.

    Args:
        template_path:  e.g. "common/app.erl.tmpl"
                             "css/pico/base.html.tmpl"
        variables:      dict of substitution values

    Returns:
        Rendered string.

    Raises:
        TemplateNotFoundError if the template file does not exist.
        TemplateRenderError   if a required variable is missing.
    """
    full_path = TEMPLATES_ROOT / template_path
    if not full_path.exists():
        raise TemplateNotFoundError(f"Template not found: {template_path}")

    raw = full_path.read_text(encoding="utf-8")
    return _render(raw, variables, source=template_path)


def render_string(template_str: str, variables: Dict[str, Any], source: str = "<string>") -> str:
    """Render a template from a string rather than a file."""
    return _render(template_str, variables, source=source)


def template_exists(template_path: str) -> bool:
    """Return True if the given template path exists."""
    return (TEMPLATES_ROOT / template_path).exists()


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _render(raw: str, variables: Dict[str, Any], source: str) -> str:
    # Stringify all values so Template doesn't choke on Path objects etc.
    safe_vars = {k: str(v) for k, v in variables.items()}
    try:
        return Template(raw).substitute(safe_vars)
    except KeyError as e:
        raise TemplateRenderError(
            f"Template {source!r} references undefined variable {e}.\n"
            f"Available variables: {', '.join(sorted(safe_vars))}"
        ) from e
    except ValueError as e:
        raise TemplateRenderError(
            f"Template {source!r} has a syntax error: {e}"
        ) from e


class TemplateNotFoundError(FileNotFoundError):
    pass


class TemplateRenderError(ValueError):
    pass
