"""
cowboy-up model — generate a model module.
"""

from __future__ import annotations
from pathlib import Path
from datetime import date
from typing import List
import textwrap

from cowboy_up import console
from cowboy_up.field import Field, FieldParseError
from cowboy_up.renderer import render_file
from cowboy_up.utils import detect_app_name, to_snake


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(model_name: str, table: str, field_specs: List[str]) -> None:
    # Detect app name from app.src
    app_name = _detect_app_name()

    # Parse fields
    try:
        fields = [Field.parse(s) for s in field_specs]
    except FieldParseError as e:
        console.die(str(e))

    module = _to_snake(model_name)
    out_dir = Path("src/models")
    out_file = out_dir / f"{module}.erl"
    out_dir.mkdir(parents=True, exist_ok=True)

    if out_file.exists():
        console.die(f"{out_file} already exists.")

    # Separate field categories
    columns    = [f for f in fields if f.is_column]
    belongs_to = [f for f in fields if f.is_belongs_to]
    has_many   = [f for f in fields if f.is_has_many]
    m2m        = [f for f in fields if f.is_many_to_many]

    # Banner
    console.header("cowboy-up model")
    print(f"  Model   : {console.bold(model_name)}  (module: {module})")
    print(f"  Table   : {console.bold(table)}")
    col_names = ", ".join(f.name for f in columns)
    print(f"  Columns : id, {col_names}, created_at")
    if belongs_to:
        print(f"  belongs_to : {', '.join(f.target for f in belongs_to)}")
    if has_many:
        print(f"  has_many   : {', '.join(f.target for f in has_many)}")
    if m2m:
        print(f"  many_to_many tags  →  tags + {table}_tags")
    print(f"  Output  : {console.bold(str(out_file))}")
    console.blank()

    # Build template variables
    v = _build_vars(app_name, model_name, module, table,
                    columns, belongs_to, has_many, m2m)

    content = render_file("models/model.erl.tmpl", v)

    # Append association functions
    content += _belongs_to_functions(app_name, module, belongs_to)
    content += _has_many_functions(app_name, module, has_many)
    content += _m2m_functions(app_name, module, table, m2m)

    out_file.write_text(content, encoding="utf-8")
    console.created(str(out_file))

    # Write migration files
    _write_migrations(app_name, module, table, columns, belongs_to, m2m)

    # Shell usage
    _print_shell_usage(module, belongs_to, has_many, m2m)


# ---------------------------------------------------------------------------
# Template variable builder
# ---------------------------------------------------------------------------

def _build_vars(
    app_name, model_name, module, table,
    columns, belongs_to, has_many, m2m
) -> dict:

    # SQL field list
    sql_cols = ["id"] + [f.name for f in columns] + ["created_at"]
    sql_fields = ", ".join(sql_cols)

    # Erlang variable list for to_map
    erl_vars = ["Id"] + [f.erl_var for f in columns] + ["CreatedAt"]
    var_list = ", ".join(erl_vars)

    # Map body
    map_pairs = [("id", "Id")] + [(f.name, f.erl_var) for f in columns] + [("created_at", "CreatedAt")]
    map_body = ",\n      ".join(f"{k} => {v}" for k, v in map_pairs)

    # INSERT
    insert_cols  = ", ".join(f.name for f in columns)
    insert_phs   = ", ".join(f"?{i+1}" for i in range(len(columns)))
    insert_args  = ",\n         ".join(f"maps:get({f.name}, Attrs)" for f in columns)

    # UPDATE
    update_set  = ", ".join(f"{f.name} = ?{i+1}" for i, f in enumerate(columns))
    update_args = ",\n         ".join(
        f"maps:get({f.name}, Attrs, undefined)" for f in columns
    )
    id_pos = len(columns) + 1

    # Exports
    base_exports = "all/0, find/1, create/1, update/2, delete/1, to_map/1"
    extra = []
    for f in belongs_to:
        extra.append(f"{f.parent_module}/1")
    for f in has_many:
        extra.append(f"{f.name}/1")
    if m2m:
        extra += ["tag/2", "tags/1", "has/1"]
    if extra:
        exports = f"-export([{base_exports},\n         {', '.join(extra)}])."
    else:
        exports = f"-export([{base_exports}])."

    # Association doc lines
    doc_lines = []
    for f in belongs_to:
        doc_lines.append(f"%%%   {module}:{f.parent_module}(Id)  — fetch parent {f.target}")
    for f in has_many:
        doc_lines.append(f"%%%   {module}:{f.name}(Id)  — fetch child {f.target} records")
    if m2m:
        doc_lines += [
            f'%%%   {module}:tag(Id, <<"sermon">>)',
            f'%%%   {module}:tags(Id)',
            f'%%%   {module}:has([<<"sermon">>, <<"grace">>])',
        ]
    association_doc = "\n".join(doc_lines) + "\n" if doc_lines else ""

    return {
        "app_name":            app_name,
        "module":              module,
        "table":               table,
        "sql_fields":          sql_fields,
        "var_list":            var_list,
        "map_body":            map_body,
        "insert_cols":         insert_cols,
        "insert_placeholders": insert_phs,
        "insert_args":         insert_args,
        "update_set":          update_set,
        "update_args":         update_args,
        "id_pos":              str(id_pos),
        "exports":             exports,
        "association_doc":     association_doc,
        "association_functions": "",  # appended separately after render
    }


# ---------------------------------------------------------------------------
# Association function generators
# ---------------------------------------------------------------------------

def _belongs_to_functions(app_name: str, module: str, fields: list) -> str:
    if not fields:
        return ""
    out = []
    for f in fields:
        pm = f.parent_module
        pt = f.parent_table
        out.append(f"""
%% ---------------------------------------------------------------------------
%% {pm}/1 — fetch the parent {f.target} for this record.
%%   {module}:{pm}(Id)  ->  {{ok, Map}} | {{error, not_found}}
%% ---------------------------------------------------------------------------
{pm}(Id) ->
    case {app_name}_db:q(
        "SELECT * FROM {pt} p"
        " JOIN " ?TABLE " t ON t.{f.name} = p.id"
        " WHERE t.id = ?1 LIMIT 1",
        [Id]
    ) of
        {{ok, [Row]}} -> {pm}:to_map(Row);
        {{ok, []}}    -> {{error, not_found}}
    end.
""")
    return "\n".join(out)


def _has_many_functions(app_name: str, module: str, fields: list) -> str:
    if not fields:
        return ""
    out = []
    for f in fields:
        cm = f.child_module
        fk = f"{module}_id"
        out.append(f"""
%% ---------------------------------------------------------------------------
%% {f.name}/1 — fetch all {f.target} records belonging to this record.
%%   {module}:{f.name}(Id)  ->  {{ok, [Map, ...]}} | {{ok, []}}
%% ---------------------------------------------------------------------------
{f.name}(Id) ->
    case {app_name}_db:q(
        "SELECT * FROM {f.name} WHERE {fk} = ?1 ORDER BY id",
        [Id]
    ) of
        {{ok, Rows}} -> {{ok, [{cm}:to_map(R) || R <- Rows]}};
        Err         -> Err
    end.
""")
    return "\n".join(out)


def _m2m_functions(app_name: str, module: str, table: str, fields: list) -> str:
    if not fields:
        return ""
    join_table  = f"{table}_tags"
    tags_table  = "tags"
    return f"""
%% ---------------------------------------------------------------------------
%% tag/2 — attach a tag by name, creating it if needed.
%%   {module}:tag(Id, <<"sermon">>)  ->  ok | {{error, Reason}}
%% ---------------------------------------------------------------------------
tag(Id, TagName) when is_binary(TagName) ->
    {{ok, TagId}} = case {app_name}_db:q(
        "SELECT id FROM {tags_table} WHERE name = ?1 LIMIT 1", [TagName]
    ) of
        {{ok, [[Tid]]}} -> {{ok, Tid}};
        {{ok, []}} ->
            ok = {app_name}_db:exec(
                "INSERT INTO {tags_table} (name) VALUES (?1)", [TagName]
            ),
            case {app_name}_db:q("SELECT last_insert_rowid()") of
                {{ok, [[Tid]]}} -> {{ok, Tid}};
                _               -> {{error, insert_failed}}
            end
    end,
    {app_name}_db:exec(
        "INSERT OR IGNORE INTO {join_table} ({module}_id, tag_id) VALUES (?1, ?2)",
        [Id, TagId]
    ).

%% ---------------------------------------------------------------------------
%% tags/1 — list all tag names on this record.
%%   {module}:tags(Id)  ->  {{ok, [<<"sermon">>, <<"grace">>]}}
%% ---------------------------------------------------------------------------
tags(Id) ->
    case {app_name}_db:q(
        "SELECT tg.name FROM {tags_table} tg"
        " JOIN {join_table} jt ON jt.tag_id = tg.id"
        " WHERE jt.{module}_id = ?1 ORDER BY tg.name",
        [Id]
    ) of
        {{ok, Rows}} -> {{ok, [Name || [Name] <- Rows]}};
        Err         -> Err
    end.

%% ---------------------------------------------------------------------------
%% has/1 — find records matching ALL supplied tags (AND logic).
%%
%%   {module}:has(<<"sermon">>)
%%   {module}:has([<<"sermon">>, <<"grace">>, <<"faith">>])
%%
%% Uses relational division: GROUP BY + HAVING COUNT(DISTINCT) = N
%% ---------------------------------------------------------------------------
has(TagName) when is_binary(TagName) ->
    has([TagName]);

has(TagNames) when is_list(TagNames), length(TagNames) > 0 ->
    N = length(TagNames),
    Placeholders = string:join(
        [[$?, integer_to_list(I)] || I <- lists:seq(1, N)],
        ", "
    ),
    Sql =
        "SELECT t." ++ ?FIELDS ++
        "  FROM " ?TABLE " t"
        "  JOIN {join_table} jt ON jt.{module}_id = t.id"
        "  JOIN {tags_table} tg ON tg.id = jt.tag_id"
        " WHERE tg.name IN (" ++ Placeholders ++ ")"
        " GROUP BY t.id"
        " HAVING COUNT(DISTINCT tg.id) = " ++ integer_to_list(N) ++
        " ORDER BY t.id",
    case {app_name}_db:q(Sql, TagNames) of
        {{ok, Rows}} -> {{ok, [to_map(R) || R <- Rows]}};
        Err         -> Err
    end.
"""


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _write_migrations(app_name, module, table, columns, belongs_to, m2m):
    """Write migration .erl files to src/migrations/ instead of printing SQL."""
    from cowboy_up.renderer import render_file
    today   = date.today().strftime("%Y%m%d")
    mig_dir = Path("src/migrations")
    mig_dir.mkdir(parents=True, exist_ok=True)

    # Determine the next available sequence number
    seq = _next_seq(mig_dir, today)

    written = []

    # --- Main table migration -----------------------------------------------
    main_version = f"{today}_{seq:03d}_create_{table}"
    main_sql     = _build_create_sql(table, columns)
    _write_migration_file(mig_dir, app_name, main_version, main_sql)
    written.append(main_version)
    seq += 1

    # --- tags + join table migrations (many_to_many) ------------------------
    if m2m:
        tags_version = f"{today}_{seq:03d}_create_tags"
        tags_sql = (
            "CREATE TABLE IF NOT EXISTS tags ("
            "  id         INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name       TEXT NOT NULL UNIQUE,"
            "  created_at TEXT DEFAULT (datetime('now'))"
            ");"
        )
        _write_migration_file(mig_dir, app_name, tags_version, tags_sql)
        written.append(tags_version)
        seq += 1

        join         = f"{table}_tags"
        join_version = f"{today}_{seq:03d}_create_{join}"
        join_sql = [
            f"CREATE TABLE {join} ("
            f"  {module}_id INTEGER NOT NULL REFERENCES {table}(id),"
            "  tag_id     INTEGER NOT NULL REFERENCES tags(id),"
            f"  PRIMARY KEY ({module}_id, tag_id)"
            ");",
            f"CREATE INDEX IF NOT EXISTS idx_{join}_tag_id ON {join}(tag_id);"
        ]
        _write_migration_file(mig_dir, app_name, join_version, join_sql)
        written.append(join_version)

    console.blank()
    print("  Migrations written:")
    for v in written:
        console.created(f"src/migrations/{v}.erl")
    console.blank()
    print(f"  {console.dim('They will run automatically on next startup.')}")


def _build_create_sql(table, columns):
    cols = ["  id         INTEGER PRIMARY KEY AUTOINCREMENT"]
    for f in columns:
        if f.is_belongs_to:
            cols.append(f"  {f.name}  INTEGER NOT NULL REFERENCES {f.parent_table}(id)")
        else:
            cols.append(f"  {f.name}  {f.sql_type.upper()} NOT NULL")
    cols.append("  created_at TEXT DEFAULT (datetime('now'))")
    return f"CREATE TABLE {table} (\n" + ",\n".join(cols) + "\n);"


def _write_migration_file(mig_dir, app_name, version, sql):
    """Render and write a single migration .erl file."""
    from cowboy_up.renderer import render_file

    # Format SQL as an Erlang string literal.
    # A list of strings becomes a list of Erlang strings.
    if isinstance(sql, list):
        parts = [f'    "{s}"' for s in sql]
        sql_erl = "[\n" + ",\n".join(parts) + "\n    ]"
    else:
        sql_erl = f'"{sql}"'

    content = render_file("models/migration.erl.tmpl", {
        "app_name": app_name,
        "version":  version,
        "sql":      sql_erl,
    })
    out = mig_dir / f"{version}.erl"
    out.write_text(content, encoding="utf-8")


def _next_seq(mig_dir, today):
    """Find the next available sequence number for today's migrations."""
    import re
    existing = list(mig_dir.glob(f"{today}_*.erl"))
    if not existing:
        return 2   # 001 is reserved for create_example on new projects
    nums = []
    for p in existing:
        m = re.match(rf"{today}_(\d+)_", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 2




def _print_shell_usage(module, belongs_to, has_many, m2m):
    console.blank()
    print("  Shell usage:")
    for line in [
        f"{module}:all().",
        f"{module}:find(1).",
        f'{module}:find({{title, <<"value">>}}).',
        f"{module}:create(#{{...}}).",
        f"{module}:update(1, #{{...}}).",
        f"{module}:delete(1).",
    ]:
        print(f"      {line}")
    for f in belongs_to:
        print(f"      {module}:{f.parent_module}(Id).    %% fetch parent {f.target}")
    for f in has_many:
        print(f"      {module}:{f.name}(Id).   %% fetch child {f.target} records")
    if m2m:
        print(f'      {module}:tag(1, <<"sermon">>).')
        print(f'      {module}:has([<<"sermon">>, <<"grace">>]).')
    console.blank()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _detect_app_name() -> str:
    return detect_app_name()


def _to_snake(name: str) -> str:
    return to_snake(name)
