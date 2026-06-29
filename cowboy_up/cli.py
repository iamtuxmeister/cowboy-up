"""
cowboy-up CLI entry point.

Commands:
    cowboy-up new "app name" [--css basic|pico|tailwind|daisyui]
                              [--templates erlydtl|bbmustache]
                              [--db sqlite|postgres]
                              [--no-prompt]

    cowboy-up model <ModelName> <table> [field:type ...]
                                        [field:belongs_to:Parent]
                                        [field:has_many:Child]
                                        [field:many_to_many]

    cowboy-up model add-field <ModelName> <field:type>

    cowboy-up setup
"""

from __future__ import annotations
import argparse
import sys

from cowboy_up import __version__
from cowboy_up import console
from cowboy_up.config import CSS_CHOICES, TEMPLATING_CHOICES, DB_CHOICES


def main() -> None:
    parser = _build_parser()

    # Print help if no args given
    if len(sys.argv) == 1:
        _print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cowboy-up",
        description="Erlang/Cowboy/ErlyDTL project generator",
        add_help=True,
    )
    parser.add_argument(
        "--version", action="version", version=f"cowboy-up {__version__}"
    )

    sub = parser.add_subparsers(title="commands", metavar="<command>")

    # ------------------------------------------------------------------
    # cowboy-up new
    # ------------------------------------------------------------------
    new_p = sub.add_parser(
        "new",
        help="Scaffold a new Cowboy/ErlyDTL/SQLite project",
        description=(
            "Create a new Erlang/Cowboy project in the current directory.\n"
            "App name is normalised: \"My App\" becomes my_app/"
        ),
    )
    new_p.add_argument("name", nargs="+", help="Application name (words, spaces OK)")
    new_p.add_argument(
        "--css",
        choices=CSS_CHOICES,
        default=None,
        help="CSS framework (default: prompted interactively, fallback basic)",
    )
    new_p.add_argument(
        "--templates",
        choices=TEMPLATING_CHOICES,
        default=None,
        dest="templating",
        help="Template engine (default: prompted interactively, fallback erlydtl)",
    )
    new_p.add_argument(
        "--db",
        choices=DB_CHOICES,
        default=None,
        help="Database backend (default: prompted interactively, fallback sqlite)",
    )
    new_p.add_argument(
        "--no-prompt",
        action="store_true",
        help="Skip interactive prompts, use defaults or supplied flags",
    )
    new_p.set_defaults(func=_cmd_new)

    # ------------------------------------------------------------------
    # cowboy-up model
    # ------------------------------------------------------------------
    model_p = sub.add_parser(
        "model",
        help="Generate a model module or add a field to an existing one",
        description=(
            "Generate a model in src/models/<name>.erl.\n"
            "Must be run from your project root.\n\n"
            "Field types:\n"
            "  name:text                  plain SQLite column\n"
            "  name:integer               plain SQLite column\n"
            "  name:real                  plain SQLite column\n"
            "  name:blob                  plain SQLite column\n"
            "  book_id:belongs_to:Book    FK column + parent lookup function\n"
            "  teachings:has_many:Teaching  reverse lookup, no column added\n"
            "  tag:many_to_many           tags + join table + tag/2 tags/1 has/1\n\n"
            "Subcommand:\n"
            "  add-field <ModelName> <field:type>  show edits needed to add a field"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    model_p.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="ModelName table field:type ... | add-field ModelName field:type",
    )
    model_p.set_defaults(func=_cmd_model)

    # ------------------------------------------------------------------
    # cowboy-up setup
    # ------------------------------------------------------------------
    setup_p = sub.add_parser(
        "setup",
        help="Install Erlang 26, rebar3, sqlite3, inotify-tools on Debian 12",
    )
    setup_p.set_defaults(func=_cmd_setup)

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_new(args: argparse.Namespace) -> None:
    from cowboy_up.commands.new import run
    raw_name   = " ".join(args.name)
    css        = args.css or "basic"
    templating = args.templating or "erlydtl"
    db         = args.db or "sqlite"
    interactive = not args.no_prompt

    run(
        raw_name=raw_name,
        css=css,
        templating=templating,
        db=db,
        interactive=interactive,
    )


def _cmd_model(args: argparse.Namespace) -> None:
    remainder = args.args

    if not remainder:
        console.die(
            "Usage:\n"
            "  cowboy-up model <ModelName> <table> [field:type ...]\n"
            "  cowboy-up model add-field <ModelName> <field:type>"
        )

    # Subcommand: add-field
    if remainder[0] == "add-field":
        rest = remainder[1:]
        if len(rest) < 2:
            console.die("Usage: cowboy-up model add-field <ModelName> <field:type>")
        from cowboy_up.commands.add_field import run
        run(model_name=rest[0], field_spec=rest[1])
        return

    # Regular model generation
    if len(remainder) < 2:
        console.die("Usage: cowboy-up model <ModelName> <table> [field:type ...]")

    from cowboy_up.commands.model import run
    run(
        model_name=remainder[0],
        table=remainder[1],
        field_specs=remainder[2:],
    )


def _cmd_setup(args: argparse.Namespace) -> None:
    from cowboy_up.commands.setup import run
    run()


# ---------------------------------------------------------------------------
# Custom help output
# ---------------------------------------------------------------------------

def _print_help() -> None:
    console.blank()
    print(console.bold("cowboy-up") + f"  v{__version__} — Erlang/Cowboy/ErlyDTL project generator")
    console.blank()
    print("  " + console.bold("Commands:"))
    console.blank()

    cmds = [
        (
            f"cowboy-up new {console.cyan('\"app name\"')} [--css basic|pico|tailwind|daisyui]\n"
            f"                         [--templates erlydtl|bbmustache]\n"
            f"                         [--db sqlite|postgres]",
            "Scaffold a new project. Prompts for choices if flags omitted.",
        ),
        (
            f"cowboy-up model {console.cyan('<ModelName> <table> [fields...]')}",
            "Generate src/models/<name>.erl\n"
            f"      Field types: name:{console.cyan('text|integer|real|blob')}\n"
            f"                   fk:{console.cyan('belongs_to:Parent')}\n"
            f"                   rel:{console.cyan('has_many:Child')}\n"
            f"                   rel:{console.cyan('many_to_many')}",
        ),
        (
            f"cowboy-up model add-field {console.cyan('<ModelName> <field:type>')}",
            "Show the edits needed to add a field to an existing model.",
        ),
        (
            "cowboy-up setup",
            "Install Erlang 26, rebar3, sqlite3, inotify-tools\n"
            "      on Debian 12 / bookworm. Requires sudo.",
        ),
    ]

    for cmd, desc in cmds:
        print(f"    {console.cyan(cmd)}")
        for line in desc.split("\n"):
            print(f"        {line}")
        console.blank()

    print("  " + console.bold("Examples:"))
    console.blank()
    examples = [
        'cowboy-up new "bible site" --css pico --db sqlite',
        "cowboy-up model Book books title:text testament:text teachings:has_many:Teaching",
        "cowboy-up model Teaching teachings book_id:belongs_to:Book title:text tag:many_to_many",
        "cowboy-up model add-field Teaching notes:text",
        "cowboy-up setup",
    ]
    for ex in examples:
        print(f"    {console.cyan(ex)}")
    console.blank()
