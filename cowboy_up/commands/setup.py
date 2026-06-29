"""
cowboy-up setup — install Erlang 26, rebar3, sqlite3, inotify-tools on Debian 12.
"""

from __future__ import annotations
import subprocess
import sys
import shutil
from pathlib import Path

from cowboy_up import console


ERLANG_PACKAGES = [
    "erlang-base=1:26.*",
    "erlang-dev=1:26.*",
    "erlang-crypto=1:26.*",
    "erlang-ssl=1:26.*",
    "erlang-public-key=1:26.*",
    "erlang-asn1=1:26.*",
    "erlang-syntax-tools=1:26.*",
    "erlang-parsetools=1:26.*",
    "erlang-runtime-tools=1:26.*",
    "erlang-inets=1:26.*",
    "erlang-eunit=1:26.*",
    "erlang-ftp=1:26.*",
    "erlang-tftp=1:26.*",
    "erlang-tools=1:26.*",
    "erlang-mnesia=1:26.*",
]

RABBITMQ_KEY_URL = (
    "https://keys.openpgp.org/vks/v1/by-fingerprint/"
    "0A9AF2115F4687BD29803A206B73A36E6026DFCA"
)

REBAR3_URL = "https://s3.amazonaws.com/rebar3/rebar3"

ERLANG_REPO = """\
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] \
https://deb1.rabbitmq.com/rabbitmq-erlang/debian/bookworm bookworm main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] \
https://deb2.rabbitmq.com/rabbitmq-erlang/debian/bookworm bookworm main
"""


def run() -> None:
    console.header(
        "cowboy-up setup",
        "Install prerequisites for Debian 12 / bookworm"
    )
    console.warn("This will run apt commands and requires sudo.")
    console.blank()

    try:
        answer = input("  Continue? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    if answer not in ("y", "yes"):
        print("  Aborted.")
        sys.exit(0)

    console.blank()

    # 1. Base packages
    console.section("Installing base packages")
    _apt_update()
    _apt_install([
        "curl", "gnupg", "apt-transport-https", "ca-certificates",
        "lsb-release", "build-essential", "sqlite3", "inotify-tools",
    ])
    console.ok("Base packages installed")

    # 2. RabbitMQ Erlang repo
    console.section("Adding RabbitMQ Erlang 26 repository")
    _install_signing_key()
    _write_erlang_sources()
    _apt_update()
    console.ok("Repository configured")

    # 3. Erlang 26
    console.section("Installing Erlang 26")
    _apt_install(ERLANG_PACKAGES)
    erl_ver = _erl_version()
    console.ok(f"Erlang installed: {erl_ver}")

    # 4. rebar3
    console.section("Installing rebar3")
    if shutil.which("rebar3"):
        ver = _run_capture(["rebar3", "--version"])
        console.ok(f"rebar3 already installed: {ver.strip()}")
    else:
        _install_rebar3()
        ver = _run_capture(["rebar3", "--version"])
        console.ok(f"rebar3 installed: {ver.strip()}")

    # Done
    console.section("Setup complete!")
    console.blank()
    print("  Everything is installed. Create your first project:\n")
    print(f"    {console.cyan('cowboy-up new \"my app\"')}")
    console.blank()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(cmd: list, check: bool = True) -> int:
    console.step(" ".join(str(c) for c in cmd[:4]) + ("..." if len(cmd) > 4 else ""))
    result = subprocess.run(cmd)
    if check and result.returncode != 0:
        console.die(f"Command failed: {' '.join(str(c) for c in cmd)}")
    return result.returncode


def _run_capture(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def _apt_update() -> None:
    console.step("apt-get update")
    subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)


def _apt_install(packages: list) -> None:
    _run(["sudo", "apt-get", "install", "-y"] + packages)


def _install_signing_key() -> None:
    console.step("Fetching RabbitMQ signing key...")
    key_path = Path("/usr/share/keyrings/com.rabbitmq.team.gpg")
    result = subprocess.run(
        ["curl", "-1sLf", RABBITMQ_KEY_URL],
        capture_output=True, check=True
    )
    gpg = subprocess.run(
        ["gpg", "--dearmor"],
        input=result.stdout, capture_output=True, check=True
    )
    subprocess.run(
        ["sudo", "tee", str(key_path)],
        input=gpg.stdout, capture_output=True, check=True
    )
    console.ok("Signing key installed")


def _write_erlang_sources() -> None:
    console.step("Writing /etc/apt/sources.list.d/erlang.list...")
    proc = subprocess.run(
        ["sudo", "tee", "/etc/apt/sources.list.d/erlang.list"],
        input=ERLANG_REPO.encode(),
        capture_output=True,
    )
    if proc.returncode != 0:
        console.die("Failed to write erlang.list")


def _install_rebar3() -> None:
    console.step("Downloading rebar3...")
    tmp = Path("/tmp/rebar3")
    result = subprocess.run(
        ["curl", "-fsSL", REBAR3_URL, "-o", str(tmp)],
        check=True
    )
    tmp.chmod(0o755)
    subprocess.run(["sudo", "mv", str(tmp), "/usr/local/bin/rebar3"], check=True)


def _erl_version() -> str:
    result = subprocess.run(
        ["erl", "-eval",
         'erlang:display(erlang:system_info(otp_release)), halt().',
         "-noshell"],
        capture_output=True, text=True
    )
    return result.stdout.strip().strip('"') or "unknown"
