"""
cowboy-up model add-field — add a field to an existing model.

Safe edits made automatically:
  1. Write a migration .erl file to src/migrations/
  2. Update -define(FIELDS, ...) in the model
  3. Update to_map([...]) pattern in the model
  4. Insert the new key into the map body in to_map/1

Shown but not touched (placeholder renumbering is risky):
  5. create/1 and update/2
"""

from __future__ import annotations
from pathlib import Path
from datetime import date
import re

from cowboy_up import console
from cowboy_up.field import Field, FieldParseError
from cowboy_up.utils import detect_app_name, to_snake


def run(model_name: str, field_spec: str) -> None:
    try:
        f = Field.parse(field_spec)
    except FieldParseError as e:
        console.die(str(e))

    if f.relationship in ("has_many", "many_to_many"):
        console.die(
            f"add-field does not support relationship types. "
            f"Use 'cowboy-up model' to add has_many or many_to_many."
        )

    app_name   = detect_app_name()
    module     = to_snake(model_name)
    model_file = Path(f"src/models/{module}.erl")

    if not model_file.exists():
        console.die(f"{model_file} not found.")

    source = model_file.read_text(encoding="utf-8")

    current_fields = _extract_fields_macro(source)
    current_tomap  = _extract_tomap_line(source)

    if current_fields is None:
        console.die(f"Could not find -define(FIELDS, ...) in {model_file}")
    if current_tomap is None:
        console.die(f"Could not find to_map([...]) in {model_file}")

    # Derived values
    new_fields  = _insert_before(current_fields, f.name, r",\s*created_at", f", {f.name}, created_at")
    new_tomap   = _insert_before(current_tomap,  f.erl_var, r",\s*CreatedAt\]", f", {f.erl_var}, CreatedAt]")
    table       = _extract_table(source)

    # ------------------------------------------------------------------
    console.header("cowboy-up model add-field")
    print(f"  Model : {console.bold(model_name)}  →  {model_file}")
    print(f"  Field : {console.bold(f.name)}  ({f.sql_type})")
    console.blank()

    # ------------------------------------------------------------------
    # Step 1 — Write migration file
    # ------------------------------------------------------------------
    console.section("Step 1 of 4 — Migration file")
    mig_file = _write_migration(app_name, module, table, f)
    console.blank()
    print(f"  {console.dim('Runs automatically on next startup.')}")
    console.blank()
    print("  Apply immediately in the running shell (no restart needed):\n")
    sql_type = f.sql_type.upper()
    print(f"      {console.cyan(f'{app_name}_db:exec(\"ALTER TABLE {table} ADD COLUMN {f.name} {sql_type};\").')}")
    print(f"      {console.cyan(f'l({app_name}_db).')}")
    console.blank()

    # ------------------------------------------------------------------
    # Step 2 — Edit FIELDS macro
    # ------------------------------------------------------------------
    console.section(f"Step 2 of 4 — FIELDS macro  (auto-editing {model_file})")
    source = source.replace(
        f'-define(FIELDS, "{current_fields}").',
        f'-define(FIELDS, "{new_fields}").',
    )
    console.blank()
    print(f"  {console.dim(f'Was:')}  -define(FIELDS, \"{current_fields}\").")
    print(f"  {console.green('Now:')}  -define(FIELDS, \"{new_fields}\").")
    console.blank()

    # ------------------------------------------------------------------
    # Step 3 — Edit to_map/1 pattern
    # ------------------------------------------------------------------
    console.section(f"Step 3 of 4 — to_map/1 pattern  (auto-editing {model_file})")
    source = source.replace(current_tomap, new_tomap)
    console.blank()
    print(f"  {console.dim('Was:')}  {current_tomap}")
    print(f"  {console.green('Now:')}  {new_tomap}")
    console.blank()

    # ------------------------------------------------------------------
    # Step 4 — Edit map body
    # ------------------------------------------------------------------
    console.section(f"Step 4 of 4 — map body  (auto-editing {model_file})")
    source, inserted = _insert_map_key(source, f.name, f.erl_var)
    if inserted:
        console.blank()
        print(f"  {console.green('Added:')}  {f.name} => {f.erl_var},")
        print(f"           (before created_at => CreatedAt)")
    else:
        console.blank()
        console.warn("Could not auto-insert map key — add manually before created_at:")
        print(f"      {f.name} => {f.erl_var},")
    console.blank()

    # Write the edited model file
    model_file.write_text(source, encoding="utf-8")
    console.ok(f"Saved {model_file}")
    console.blank()

    # ------------------------------------------------------------------
    # Step 5 — Manual: create/1 and update/2
    # ------------------------------------------------------------------
    console.section("Step 5 of 4 — Manual: create/1 and update/2")
    console.blank()
    print(f"  Placeholder renumbering cannot be done safely automatically.")
    print(f"  If you want {console.bold(f.name)} to be writable, edit {model_file}:\n")
    print("  In create/1 — add to the INSERT column list and VALUES:")
    print(f"      \"INSERT INTO ... (existing_cols, {f.name}) VALUES (existing_vals, ?N)\"")
    print(f"      maps:get({f.name}, Attrs, null)   %% new arg")
    console.blank()
    print("  In update/2 — add to the SET clause:")
    print(f"      {f.name} = ?N,")
    print(f"      maps:get({f.name}, Attrs, undefined)   %% new arg")
    console.blank()
    print("  Renumber all ?N placeholders after inserting.")
    console.blank()

    # ------------------------------------------------------------------
    # Hot reload
    # ------------------------------------------------------------------
    console.section("Hot-reload")
    console.blank()
    print(f"  {console.cyan(f'l({module}).')}")
    console.blank()
    print("  Or just save the file — the watcher recompiles automatically.")
    console.blank()


# ---------------------------------------------------------------------------
# Migration file writer
# ---------------------------------------------------------------------------

def _write_migration(app_name: str, module: str, table: str, f: Field) -> Path:
    from cowboy_up.renderer import render_file
    today   = date.today().strftime("%Y%m%d")
    mig_dir = Path("src/migrations")
    mig_dir.mkdir(parents=True, exist_ok=True)

    seq     = _next_seq(mig_dir, today)
    version = f"{today}_{seq:03d}_add_{f.name}_to_{table}"
    sql     = f"ALTER TABLE {table} ADD COLUMN {f.name} {f.sql_type.upper()};"

    content = render_file("models/migration.erl.tmpl", {
        "app_name": app_name,
        "version":  version,
        "sql":      f'"{sql}"',
    })
    out = mig_dir / f"{version}.erl"
    out.write_text(content, encoding="utf-8")
    console.created(str(out))
    return out


def _next_seq(mig_dir: Path, today: str) -> int:
    existing = list(mig_dir.glob(f"{today}_*.erl"))
    if not existing:
        return 2
    nums = []
    for p in existing:
        m = re.match(rf"{today}_(\d+)_", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 2


# ---------------------------------------------------------------------------
# Source file parsing and editing
# ---------------------------------------------------------------------------

def _extract_fields_macro(source: str) -> str | None:
    m = re.search(r'-define\(FIELDS,\s*"([^"]+)"\)', source)
    return m.group(1) if m else None


def _extract_tomap_line(source: str) -> str | None:
    m = re.search(r'(to_map\(\[[^\]]+\]\))', source)
    return m.group(1) if m else None


def _extract_table(source: str) -> str:
    m = re.search(r'-define\(TABLE,\s*"([^"]+)"\)', source)
    return m.group(1) if m else "unknown_table"


def _insert_before(text: str, new_item: str, pattern: str, replacement: str) -> str:
    return re.sub(pattern, replacement, text, count=1)


def _insert_map_key(source: str, name: str, erl_var: str) -> tuple[str, bool]:
    """Insert 'name => ErlVar,' before 'created_at => CreatedAt' in the map body."""
    pattern = r'(\s+)(created_at\s*=>\s*CreatedAt)'
    replacement = rf'\1{name} => {erl_var},\n\1\2'
    new_source, count = re.subn(pattern, replacement, source, count=1)
    return new_source, count > 0


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _detect_app_name() -> str:
    return detect_app_name()


def _to_snake(name: str) -> str:
    return to_snake(name)
