"""
console.py — simple coloured terminal output.

No external dependencies — just ANSI codes. Colour is automatically
disabled when stdout is not a TTY (pipes, CI, etc.)
"""

import sys
import os


def _supports_colour() -> bool:
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return True


USE_COLOUR = _supports_colour()


def _c(code: str, text: str) -> str:
    if USE_COLOUR:
        return f"\033[{code}m{text}\033[0m"
    return text


def bold(text: str)    -> str: return _c("1",      text)
def cyan(text: str)    -> str: return _c("0;36",   text)
def green(text: str)   -> str: return _c("0;32",   text)
def yellow(text: str)  -> str: return _c("0;33",   text)
def red(text: str)     -> str: return _c("0;31",   text)
def dim(text: str)     -> str: return _c("2",      text)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n{bold(cyan('── ' + title))}")


def created(path: str) -> None:
    print(f"  {green('create')}  {path}")


def info(message: str) -> None:
    print(f"  {cyan('info')}    {message}")


def warn(message: str) -> None:
    print(f"  {yellow('warn')}    {message}")


def error(message: str) -> None:
    print(f"\n  {red('error')}   {message}\n", file=sys.stderr)


def step(message: str) -> None:
    print(f"  {cyan('▸')} {message}")


def ok(message: str) -> None:
    print(f"  {green('✓')} {message}")


def blank() -> None:
    print()


def header(title: str, subtitle: str = "") -> None:
    print()
    print(bold(title))
    if subtitle:
        print(dim(f"  {subtitle}"))
    print()


def die(message: str) -> None:
    """Print error and exit with code 1."""
    error(message)
    sys.exit(1)
