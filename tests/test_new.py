"""Tests for cowboy_up.commands.new — project scaffolding."""

import pytest
from pathlib import Path
from cowboy_up.commands.new import _template_vars, _app_js, _gitignore, _readme
from cowboy_up.config import ProjectConfig


def make_cfg(name="bible site", css="basic", templating="erlydtl", db="sqlite"):
    return ProjectConfig.from_raw_name(name, Path("/tmp"), css=css,
                                       templating=templating, db=db)


class TestTemplateVars:
    def test_app_name_present(self):
        v = _template_vars(make_cfg())
        assert v["app_name"] == "bible_site"

    def test_sqlite_db_app(self):
        v = _template_vars(make_cfg(db="sqlite"))
        assert "esqlite" in v["db_app"]

    def test_postgres_db_app(self):
        v = _template_vars(make_cfg(db="postgres"))
        assert "epgsql" in v["db_app"]

    def test_erlydtl_dep(self):
        v = _template_vars(make_cfg(templating="erlydtl"))
        assert "erlydtl" in v["templating_dep"]
        assert "provider_hooks" in v
        assert "erlydtl_opts" in v

    def test_bbmustache_dep(self):
        v = _template_vars(make_cfg(templating="bbmustache"))
        assert "bbmustache" in v["templating_dep"]
        assert v["provider_hooks"] == ""
        assert v["erlydtl_opts"] == ""

    def test_db_backend_atom_sqlite(self):
        v = _template_vars(make_cfg(db="sqlite"))
        assert v["db_backend_atom"] == "sqlite"

    def test_db_backend_atom_postgres(self):
        v = _template_vars(make_cfg(db="postgres"))
        assert v["db_backend_atom"] == "postgres"


class TestInlineContent:
    def test_app_js_contains_app_name(self):
        cfg = make_cfg("my app")
        js = _app_js(cfg)
        assert "My App" in js

    def test_gitignore_has_build(self):
        gi = _gitignore()
        assert "_build/" in gi
        assert "*.beam" in gi

    def test_readme_has_app_name(self):
        cfg = make_cfg("bible site")
        md = _readme(cfg)
        assert "Bible Site" in md
        assert "bible_site" in md
        assert "rebar3" in md


class TestProjectGeneration:
    def test_creates_directory(self, tmp_path, monkeypatch):
        from cowboy_up.commands.new import run
        monkeypatch.chdir(tmp_path)
        run(raw_name="test app", css="basic", templating="erlydtl",
            db="sqlite", interactive=False)
        assert (tmp_path / "test_app").is_dir()
        assert (tmp_path / "test_app" / "rebar.config").exists()
        assert (tmp_path / "test_app" / "src" / "test_app_app.erl").exists()
        assert (tmp_path / "test_app" / "priv" / "templates" / "layouts" / "base.html").exists()

    def test_bbmustache_creates_mustache_files(self, tmp_path, monkeypatch):
        from cowboy_up.commands.new import run
        monkeypatch.chdir(tmp_path)
        run(raw_name="mustache app", css="basic", templating="bbmustache",
            db="sqlite", interactive=False)
        proj = tmp_path / "mustache_app"
        # bbmustache outputs .html files directly in priv/templates/ — no layouts/
        assert (proj / "priv" / "templates" / "home.html").exists()
        assert (proj / "priv" / "templates" / "about.html").exists()
        assert (proj / "priv" / "templates" / "error.html").exists()
        # No layouts directory — bbmustache has no layout system
        assert not (proj / "priv" / "templates" / "layouts").exists()
        # Handler should be the bbmustache one
        handler = (proj / "src" / "mustache_app_handler.erl").read_text()
        assert "bbmustache" in handler
        assert "erlydtl" not in handler
        # rebar.config should have bbmustache dep, not erlydtl
        rebar = (proj / "rebar.config").read_text()
        assert "bbmustache" in rebar
        assert "erlydtl" not in rebar

    def test_all_css_themes_have_templates(self):
        """Every CSS theme must have base, home, about, error, app.css for erlydtl."""
        from cowboy_up.renderer import TEMPLATES_ROOT
        for theme in ("basic", "pico", "tailwind", "daisyui"):
            theme_dir = TEMPLATES_ROOT / "css" / theme
            assert theme_dir.exists(), f"Missing theme dir: {theme}"
            for f in ("base.html.tmpl", "home.html.tmpl",
                      "about.html.tmpl", "error.html.tmpl", "app.css.tmpl"):
                p = theme_dir / f
                assert p.exists(), f"Missing {theme}/{f}"

    def test_all_css_themes_have_mustache_templates(self):
        """Every CSS theme must have all four mustache variants."""
        from cowboy_up.renderer import TEMPLATES_ROOT
        for theme in ("basic", "pico", "tailwind", "daisyui"):
            mustache_dir = TEMPLATES_ROOT / "css" / theme / "mustache"
            assert mustache_dir.exists(), f"Missing mustache dir: {theme}/mustache"
            for f in ("base.html.tmpl", "home.html.tmpl",
                      "about.html.tmpl", "error.html.tmpl"):
                p = mustache_dir / f
                assert p.exists(), f"Missing {theme}/mustache/{f}"
