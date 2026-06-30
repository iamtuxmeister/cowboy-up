"""
cowboy-up new — scaffold a new Erlang/Cowboy project.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from cowboy_up import console
from cowboy_up.config import (
    ProjectConfig, ConfigError,
    CSS_CHOICES, TEMPLATING_CHOICES, DB_CHOICES,
)
from cowboy_up.renderer import render_file, render_string


# ---------------------------------------------------------------------------
# Entry point called by cli.py
# ---------------------------------------------------------------------------

def run(
    raw_name:   str,
    css:        str = "basic",
    templating: str = "erlydtl",
    db:         str = "sqlite",
    interactive: bool = True,
) -> None:

    # ------------------------------------------------------------------
    # Resolve config — interactive prompts if flags not supplied
    # ------------------------------------------------------------------
    if interactive and _should_prompt(css, templating, db):
        css, templating, db = _prompt_choices(css, templating, db)

    try:
        cfg = ProjectConfig.from_raw_name(
            raw_name=raw_name,
            target_base=Path.cwd(),
            css=css,
            templating=templating,
            db=db,
        )
    except ConfigError as e:
        console.die(str(e))

    if cfg.target_dir.exists():
        console.die(f"{cfg.target_dir} already exists.")

    # ------------------------------------------------------------------
    # Banner
    # ------------------------------------------------------------------
    console.header("cowboy-up new")
    print(f"  App name  : {console.bold(cfg.app_name)}")
    print(f"  Directory : {console.bold(str(cfg.target_dir))}")
    print(f"  CSS       : {cfg.css}")
    print(f"  Templates : {cfg.templating}")
    print(f"  Database  : {cfg.db}")

    # ------------------------------------------------------------------
    # Create directory structure
    # ------------------------------------------------------------------
    console.section("Creating project structure...")

    dirs = [
        "src/models",
        "src/migrations",
        "config",
        "nginx",
        "scripts",
        "priv/static/css",
        "priv/static/js",
        "priv/static/audio",
        "priv/db",
        "priv/templates",
    ]
    # ErlyDTL uses a layouts/ subdirectory for the base template.
    # bbmustache has no layout system — each page is self-contained.
    if cfg.templating == "erlydtl":
        dirs.append("priv/templates/layouts")
    for d in dirs:
        (cfg.target_dir / d).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Render and write all files
    # ------------------------------------------------------------------
    _write_files(cfg)

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    console.section("Done!")
    console.blank()
    print(f"  {console.bold(cfg.app_name)} is ready at {console.bold(str(cfg.target_dir))}")
    console.blank()
    print("  Next steps:")
    console.blank()
    print(f"    {console.cyan(f'cd {cfg.app_name}')}")
    print(f"    {console.cyan('sudo apt install inotify-tools')}   # if not already installed")
    print(f"    {console.cyan('rebar3 as dev shell')}              # compile + start with hot-reload")
    console.blank()
    print(f"  Then open {console.bold('http://localhost:8080')}")
    console.blank()


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def _write_files(cfg: ProjectConfig) -> None:
    """Render all templates and write to target directory."""

    v = _template_vars(cfg)
    is_erlydtl   = cfg.templating == "erlydtl"
    is_bbmustache = cfg.templating == "bbmustache"

    # Select handler and templates module based on templating engine
    handler_tmpl   = "common/handler.erl.tmpl"   if is_erlydtl else \
                     "templating/bbmustache/handler.erl.tmpl"
    templates_tmpl = "common/templates.erl.tmpl"  if is_erlydtl else \
                     "templating/bbmustache/templates.erl.tmpl"

    # HTML template source dir and output paths
    if is_erlydtl:
        html_src  = lambda page: f"css/{cfg.css}/{page}.html.tmpl"
        html_files = [
            (html_src("base"),  "priv/templates/layouts/base.html"),
            (html_src("home"),  "priv/templates/home.html"),
            (html_src("about"), "priv/templates/about.html"),
            (html_src("error"), "priv/templates/error.html"),
        ]
    else:
        # bbmustache — no layout system, no layouts/ dir, no base template
        html_src  = lambda page: f"css/{cfg.css}/mustache/{page}.html.tmpl"
        html_files = [
            (html_src("home"),  "priv/templates/home.html"),
            (html_src("about"), "priv/templates/about.html"),
            (html_src("error"), "priv/templates/error.html"),
        ]

    # Each entry: (template_path, output_path_relative_to_target)
    files = [
        # rebar + OTP
        ("common/rebar.config.tmpl",           "rebar.config"),
        ("common/app.src.tmpl",                f"src/{cfg.app_name}.app.src"),
        ("common/app.erl.tmpl",                f"src/{cfg.app_name}_app.erl"),
        ("common/sup.erl.tmpl",                f"src/{cfg.app_name}_sup.erl"),
        (handler_tmpl,                          f"src/{cfg.app_name}_handler.erl"),
        (templates_tmpl,                        f"src/{cfg.app_name}_templates.erl"),
        ("common/watcher.erl.tmpl",            f"src/{cfg.app_name}_watcher.erl"),
        ("common/logger.erl.tmpl",             f"src/{cfg.app_name}_logger.erl"),
        ("common/home_handler.erl.tmpl",       "src/home_handler.erl"),
        ("common/page_handler.erl.tmpl",       "src/page_handler.erl"),
        # DB
        (f"db/{cfg.db}/db.erl.tmpl",           f"src/{cfg.app_name}_db.erl"),
    ] + ([
        ("db/postgres/pg_worker.erl.tmpl",     f"src/{cfg.app_name}_pg_worker.erl"),
    ] if cfg.db == "postgres" else []) + [
        # Config
        ("common/sys.config.tmpl",             "config/sys.config"),
        ("common/vm.args.tmpl",                "config/vm.args"),
        # Nginx
        ("common/nginx_dev.tmpl",              "nginx/dev.conf"),
        ("common/nginx_prod.tmpl",             "nginx/prod.conf"),
        # Systemd
        ("common/systemd.service.tmpl",        f"scripts/{cfg.app_name}.service"),
        # Seed migration
        ("models/seed_migration.erl.tmpl",
         f"src/migrations/{v['datestamp']}_001_create_example.erl"),
        # CSS
        (f"css/{cfg.css}/app.css.tmpl",        "priv/static/css/app.css"),
    ] + html_files

    # Inline files that don't need a template
    inline = [
        ("priv/static/js/app.js",  _app_js(cfg)),
        (".gitignore",             _gitignore()),
        ("README.md",              _readme(cfg)),
    ]

    for tmpl_path, out_rel in files:
        content = render_file(tmpl_path, v)
        _write(cfg.target_dir / out_rel, content)

    for out_rel, content in inline:
        _write(cfg.target_dir / out_rel, content)

    # Generate the migrations registry so the db module can find migrations
    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(cfg.target_dir)
        from cowboy_up.commands.model import rebuild_registry
        rebuild_registry(cfg.app_name)
    finally:
        os.chdir(orig_cwd)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    # Show path relative to cwd
    try:
        rel = path.relative_to(Path.cwd())
    except ValueError:
        rel = path
    console.created(str(rel))


# ---------------------------------------------------------------------------
# Template variable builders
# ---------------------------------------------------------------------------

def _template_vars(cfg: ProjectConfig) -> dict:
    """Build the full variable dict for all templates."""
    from datetime import date
    v = cfg.template_vars()
    v["datestamp"] = date.today().strftime("%Y%m%d")

    # DB-specific vars
    v["db_backend_atom"] = cfg.db   # sqlite | postgres

    if cfg.db == "sqlite":
        v["db_app"]        = "        esqlite,"
        v["db_extra_deps"] = ""
    else:
        v["db_app"]        = "        epgsql,\n        poolboy,"
        v["db_extra_deps"] = (
            '    {epgsql,   "4.7.1"},\n'
            '    {poolboy,  "1.5.2"},'
        )

    # Templating-specific vars
    if cfg.templating == "erlydtl":
        v["templating_dep"]   = '    {erlydtl, "0.14.0"},'
        v["erlydtl_plugin"]   = "{plugins, [rebar3_erlydtl_plugin]}."
        v["provider_hooks"]   = (
            "{provider_hooks, [\n"
            "    {pre, [{compile, {erlydtl, compile}}]}\n"
            "]}."
        )
        v["erlydtl_opts"] = (
            "{erlydtl_opts, [\n"
            '    {source_ext, ".html"},\n'
            '    {module_ext, "_dtl"},\n'
            '    {doc_root,   "priv/templates"},\n'
            "    {recursive,  true},\n"
            "    {compiler_options, [debug_info, return]}\n"
            "]}."
        )
    else:  # bbmustache
        v["templating_dep"]   = '    {bbmustache, "1.12.2"},'
        v["erlydtl_plugin"]   = ""
        v["provider_hooks"]   = ""
        v["erlydtl_opts"]     = ""

    return v


# ---------------------------------------------------------------------------
# Inline file content
# ---------------------------------------------------------------------------

def _app_js(cfg: ProjectConfig) -> str:
    return f"""\
// {cfg.display_name} — client JS
document.addEventListener("DOMContentLoaded", () => {{
    document.querySelectorAll(".flash").forEach(el => {{
        setTimeout(() => el.remove(), 5000);
    }});
}});
"""


def _gitignore() -> str:
    return """\
_build/
priv/db/*.db
erl_crash.dump
*.beam
.rebar3/
"""


def _readme(cfg: ProjectConfig) -> str:
    return f"""\
# {cfg.display_name}

Erlang/Cowboy web application.

## Quick start

```bash
sudo apt install inotify-tools
rebar3 as dev shell
```

Open http://localhost:8080

## Stack

- HTTP: Cowboy 2.10
- Templates: {cfg.templating}
- CSS: {cfg.css}
- Database: {cfg.db}

## Adding a route

1. Add to `src/{cfg.app_name}_app.erl`: `{{"/things/:id", thing_handler, []}}`
2. Create `src/thing_handler.erl`
3. Create `priv/templates/thing.html`

## Models

```bash
cowboy-up model Book books title:text testament:text teachings:has_many:Teaching
cowboy-up model Teaching teachings book_id:belongs_to:Book title:text tag:many_to_many
```

## Database migrations

Add entries to `migrations()` in `src/{cfg.app_name}_db.erl`.

## Deploy

```bash
rebar3 release
sudo cp scripts/{cfg.app_name}.service /etc/systemd/system/
sudo systemctl enable --now {cfg.app_name}
```
"""


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _should_prompt(css: str, templating: str, db: str) -> bool:
    """Return True if any choice is still at its default and we're in a TTY."""
    import sys
    return sys.stdin.isatty()


def _prompt_choices(css: str, templating: str, db: str):
    """Use questionary to interactively confirm/override choices."""
    try:
        import questionary
    except ImportError:
        # questionary not available — skip prompts, use defaults
        return css, templating, db

    css = questionary.select(
        "CSS framework:",
        choices=list(CSS_CHOICES),
        default=css,
    ).ask() or css

    templating = questionary.select(
        "Template engine:",
        choices=list(TEMPLATING_CHOICES),
        default=templating,
    ).ask() or templating

    db = questionary.select(
        "Database:",
        choices=list(DB_CHOICES),
        default=db,
    ).ask() or db

    console.blank()
    return css, templating, db
