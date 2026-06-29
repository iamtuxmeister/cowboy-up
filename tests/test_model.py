"""Tests for cowboy_up.commands.model — model generation."""

import pytest
from cowboy_up.commands.model import (
    _build_vars, _belongs_to_functions, _has_many_functions,
    _m2m_functions, _to_snake,
)
from cowboy_up.field import Field


def parse_fields(specs):
    return [Field.parse(s) for s in specs]


class TestToSnake:
    def test_simple(self):         assert _to_snake("Book")        == "book"
    def test_camel(self):          assert _to_snake("BookChapter") == "book_chapter"
    def test_already_snake(self):  assert _to_snake("book")        == "book"
    def test_three_words(self):    assert _to_snake("BookChapterVerse") == "book_chapter_verse"


class TestBuildVars:
    def _vars(self, specs):
        fields   = parse_fields(specs)
        columns  = [f for f in fields if f.is_column]
        belongs  = [f for f in fields if f.is_belongs_to]
        hasmany  = [f for f in fields if f.is_has_many]
        m2m      = [f for f in fields if f.is_many_to_many]
        return _build_vars("myapp", "Teaching", "teaching", "teachings",
                           columns, belongs, hasmany, m2m)

    def test_sql_fields_basic(self):
        v = self._vars(["title:text", "speaker:text"])
        assert v["sql_fields"] == "id, title, speaker, created_at"

    def test_sql_fields_with_belongs_to(self):
        v = self._vars(["book_id:belongs_to:Book", "title:text"])
        assert "book_id" in v["sql_fields"]

    def test_var_list(self):
        v = self._vars(["title:text"])
        assert v["var_list"] == "Id, Title, CreatedAt"

    def test_var_list_multi(self):
        v = self._vars(["title:text", "duration_s:integer"])
        assert v["var_list"] == "Id, Title, DurationS, CreatedAt"

    def test_insert_cols(self):
        v = self._vars(["title:text", "speaker:text"])
        assert v["insert_cols"] == "title, speaker"

    def test_insert_placeholders(self):
        v = self._vars(["title:text", "speaker:text"])
        assert v["insert_placeholders"] == "?1, ?2"

    def test_update_set(self):
        v = self._vars(["title:text", "speaker:text"])
        assert v["update_set"] == "title = ?1, speaker = ?2"

    def test_id_pos(self):
        v = self._vars(["title:text", "speaker:text"])
        assert v["id_pos"] == "3"  # 2 fields + 1

    def test_exports_base_only(self):
        v = self._vars(["title:text"])
        assert "all/0" in v["exports"]
        assert "tag/2" not in v["exports"]

    def test_exports_with_m2m(self):
        v = self._vars(["title:text", "tag:many_to_many"])
        assert "tag/2" in v["exports"]
        assert "has/1" in v["exports"]

    def test_exports_with_belongs_to(self):
        v = self._vars(["book_id:belongs_to:Book", "title:text"])
        assert "book/1" in v["exports"]

    def test_exports_with_has_many(self):
        v = self._vars(["title:text", "teachings:has_many:Teaching"])
        assert "teachings/1" in v["exports"]

    def test_map_body_contains_all_fields(self):
        v = self._vars(["title:text", "speaker:text"])
        assert "title => Title" in v["map_body"]
        assert "speaker => Speaker" in v["map_body"]
        assert "id => Id" in v["map_body"]
        assert "created_at => CreatedAt" in v["map_body"]


class TestBelongsToFunctions:
    def test_generates_function(self):
        fields = parse_fields(["book_id:belongs_to:Book"])
        code = _belongs_to_functions("myapp", "teaching", fields)
        assert "book(Id)" in code
        assert "myapp_db:q" in code
        assert "books" in code   # parent_table

    def test_empty_when_no_belongs(self):
        code = _belongs_to_functions("myapp", "teaching", [])
        assert code == ""


class TestHasManyFunctions:
    def test_generates_function(self):
        fields = parse_fields(["teachings:has_many:Teaching"])
        code = _has_many_functions("myapp", "book", fields)
        assert "teachings(Id)" in code
        assert "book_id" in code   # FK column on child
        assert "teaching:to_map" in code

    def test_empty_when_no_has_many(self):
        code = _has_many_functions("myapp", "book", [])
        assert code == ""


class TestM2mFunctions:
    def test_generates_tag_function(self):
        fields = parse_fields(["tag:many_to_many"])
        code = _m2m_functions("myapp", "teaching", "teachings", fields)
        assert "tag(Id, TagName)" in code
        assert "tags(Id)" in code
        assert "has(TagNames)" in code
        assert "teachings_tags" in code
        assert "HAVING COUNT(DISTINCT tg.id)" in code

    def test_empty_when_no_m2m(self):
        code = _m2m_functions("myapp", "teaching", "teachings", [])
        assert code == ""


class TestWriteMigrations:
    def test_writes_main_migration(self, tmp_path, monkeypatch):
        from cowboy_up.commands.model import _write_migrations, _build_create_sql
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src/migrations").mkdir(parents=True)
        fields = parse_fields(["title:text", "speaker:text"])
        columns = [f for f in fields if f.is_column]
        _write_migrations("myapp", "teaching", "teachings", columns, [], [])
        files = list((tmp_path / "src/migrations").glob("*.erl"))
        assert len(files) == 1
        assert "create_teachings" in files[0].name
        content = files[0].read_text()
        assert "-migration({myapp})" in content
        assert "CREATE TABLE teachings" in content
        assert "title  TEXT NOT NULL" in content

    def test_writes_m2m_migrations(self, tmp_path, monkeypatch):
        from cowboy_up.commands.model import _write_migrations
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src/migrations").mkdir(parents=True)
        fields = parse_fields(["title:text", "tag:many_to_many"])
        columns  = [f for f in fields if f.is_column]
        m2m      = [f for f in fields if f.is_many_to_many]
        _write_migrations("myapp", "teaching", "teachings", columns, [], m2m)
        files = sorted((tmp_path / "src/migrations").glob("*.erl"))
        assert len(files) == 3
        names = [f.name for f in files]
        assert any("create_teachings" in n for n in names)
        assert any("create_tags" in n for n in names)
        assert any("create_teachings_tags" in n for n in names)

    def test_build_create_sql(self):
        from cowboy_up.commands.model import _build_create_sql
        fields = parse_fields(["title:text", "count:integer"])
        sql = _build_create_sql("books", fields)
        assert "CREATE TABLE books" in sql
        assert "title  TEXT NOT NULL" in sql
        assert "count  INTEGER NOT NULL" in sql
        assert "created_at TEXT" in sql
