"""
cowboy-up model add-field — show the manual edits needed to add a field.
"""

from __future__ import annotations
from pathlib import Path
from datetime import date
import re

from cowboy_up import console
from cowboy_up.field import Field, FieldParseError
from cowboy_up.utils import detect_app_name, to_snake


def run(model_name: str, field_spec: str) -> None:
    # Parse the field
    try:
        f = Field.parse(field_spec)
    except FieldParseError as e:
        console.die(str(e))

    # Detect app and locate model file
    app_name   = _detect_app_name()
    module     = _to_snake(model_name)
    model_file = Path(f"src/models/{module}.erl")
    db_file    = Path(f"src/{app_name}_db.erl")

    if not model_file.exists():
        console.die(f"{model_file} not found.")
    if not db_file.exists():
        console.die(f"{db_file} not found.")

    # Read current state from the model file
    source = model_file.read_text(encoding="utf-8")
    current_fields = _extract_fields_macro(source)
    current_tomap  = _extract_tomap_line(source)

    if current_fields is None:
        console.die(f"Could not find -define(FIELDS, ...) in {model_file}")
    if current_tomap is None:
        console.die(f"Could not find to_map([...]) in {model_file}")

    # Derive new values
    new_fields = _insert_before_created_at(current_fields, f.name)
    new_tomap  = _insert_var_before_created_at(current_tomap, f.erl_var)
    today      = date.today().strftime("%Y%m%d")
    sql_type   = (f.sql_type or "text").upper()

    # -----------------------------------------------------------------------
    console.header("cowboy-up model add-field")
    print(f"  Model : {console.bold(model_name)}  →  {model_file}")
    print(f"  Field : {console.bold(f.name)}  ({f.sql_type or 'text'})")
    console.blank()

    # Step 1 — Migration
    console.section(f"Step 1 of 3 — Migration  ({db_file})")
    console.blank()
    print(f"  Add this entry at the bottom of migrations() in {db_file}:\n")
    print(f'      {{"{today}_NNN_add_{f.name}_to_{module}",')
    print(f'       "ALTER TABLE {module}s ADD COLUMN {f.name} {sql_type};"}},')
    console.blank()
    print("  SQLite ALTER TABLE rules:")
    print("    • You can ADD a column but not DROP, RENAME, or REORDER.")
    print("    • The new column must allow NULL or have a DEFAULT value.")
    print(f"    • For NOT NULL use:  {f.name} {sql_type} NOT NULL DEFAULT ''")
    console.blank()
    print("  Apply immediately in the running shell (no restart needed):\n")
    print(f"      {console.cyan(f'{app_name}_db:exec(\"ALTER TABLE {module}s ADD COLUMN {f.name} {sql_type};\").')}")
    print(f"      {console.cyan(f'l({app_name}_db).')}")
    console.blank()

    # Step 2 — FIELDS macro
    console.section(f"Step 2 of 3 — FIELDS macro  ({model_file})")
    console.blank()
    print("  Find:\n")
    print(f'      -define(FIELDS, "{current_fields}").')
    console.blank()
    print("  Change to:\n")
    print(f'      -define(FIELDS, "{new_fields}").')
    console.blank()

    # Step 3 — to_map/1
    console.section(f"Step 3 of 3 — to_map/1  ({model_file})")
    console.blank()
    print("  Find:\n")
    print(f"      {current_tomap}")
    console.blank()
    print("  Change to:\n")
    print(f"      {new_tomap}")
    console.blank()
    print("  And add the new key to the map body — insert before created_at:\n")
    print(f"      {f.name} => {f.erl_var},")
    print( "      created_at => CreatedAt")
    console.blank()

    # Optional — create/1 and update/2
    console.section(f"Optional — create/1 and update/2  ({model_file})")
    console.blank()
    print(f"  If you want {console.bold(f.name)} to be writable:\n")
    print("  In create/1 — add to the INSERT column list and VALUES:")
    print(f"      \"INSERT INTO ... (existing_cols, {f.name}) VALUES (existing_vals, ?N)\"")
    print(f"      maps:get({f.name}, Attrs, null)")
    console.blank()
    print("  In update/2 — add to the SET clause:")
    print(f"      {f.name} = ?N")
    print(f"      maps:get({f.name}, Attrs, undefined)  %% add to args list")
    console.blank()
    print("  Remember to renumber all ?N placeholders after inserting.")
    console.blank()

    # Hot reload
    console.section("Hot-reload")
    console.blank()
    print("  After saving, reload from the running shell:\n")
    print(f"      {console.cyan(f'l({module}).')}")
    console.blank()
    print("  Or just save the file — the watcher recompiles it automatically.")
    console.blank()


# ---------------------------------------------------------------------------
# Source file parsing
# ---------------------------------------------------------------------------

def _extract_fields_macro(source: str) -> str | None:
    m = re.search(r'-define\(FIELDS,\s*"([^"]+)"\)', source)
    return m.group(1) if m else None


def _extract_tomap_line(source: str) -> str | None:
    m = re.search(r'(to_map\(\[[^\]]+\]\))', source)
    return m.group(1) if m else None


def _insert_before_created_at(fields: str, new_field: str) -> str:
    """Insert new_field before 'created_at' in the comma-separated field list."""
    return re.sub(r',\s*created_at', f', {new_field}, created_at', fields)


def _insert_var_before_created_at(tomap_line: str, new_var: str) -> str:
    """Insert new_var before 'CreatedAt' in the to_map pattern."""
    return re.sub(r',\s*CreatedAt\]', f', {new_var}, CreatedAt]', tomap_line)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _detect_app_name() -> str:
    return detect_app_name()


def _to_snake(name: str) -> str:
    return to_snake(name)
