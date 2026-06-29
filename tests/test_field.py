"""Tests for cowboy_up.field"""

import pytest
from cowboy_up.field import Field, FieldParseError


class TestPlainFields:
    def test_text(self):
        f = Field.parse("title:text")
        assert f.name == "title"
        assert f.sql_type == "text"
        assert f.relationship is None
        assert f.target is None
        assert f.is_column is True

    def test_integer(self):
        f = Field.parse("chapter_count:integer")
        assert f.name == "chapter_count"
        assert f.sql_type == "integer"
        assert f.erl_var == "ChapterCount"

    def test_real(self):
        f = Field.parse("price:real")
        assert f.sql_type == "real"

    def test_blob(self):
        f = Field.parse("data:blob")
        assert f.sql_type == "blob"

    def test_erl_var_simple(self):
        assert Field.parse("title:text").erl_var == "Title"

    def test_erl_var_snake(self):
        assert Field.parse("book_id:integer").erl_var == "BookId"

    def test_erl_var_multi_word(self):
        assert Field.parse("duration_in_seconds:integer").erl_var == "DurationInSeconds"


class TestBelongsTo:
    def test_basic(self):
        f = Field.parse("book_id:belongs_to:Book")
        assert f.name == "book_id"
        assert f.sql_type == "integer"   # FK is always integer
        assert f.relationship == "belongs_to"
        assert f.target == "Book"
        assert f.is_belongs_to is True
        assert f.is_column is True       # FK adds a column

    def test_parent_module(self):
        f = Field.parse("book_id:belongs_to:Book")
        assert f.parent_module == "book"

    def test_parent_module_camel(self):
        f = Field.parse("chapter_id:belongs_to:BookChapter")
        assert f.parent_module == "book_chapter"

    def test_parent_table(self):
        f = Field.parse("book_id:belongs_to:Book")
        assert f.parent_table == "books"

    def test_missing_target(self):
        with pytest.raises(FieldParseError, match="belongs_to requires"):
            Field.parse("book_id:belongs_to")


class TestHasMany:
    def test_basic(self):
        f = Field.parse("teachings:has_many:Teaching")
        assert f.name == "teachings"
        assert f.sql_type is None        # no column on parent table
        assert f.relationship == "has_many"
        assert f.target == "Teaching"
        assert f.is_has_many is True
        assert f.is_column is False

    def test_child_module(self):
        f = Field.parse("teachings:has_many:Teaching")
        assert f.child_module == "teaching"

    def test_child_module_camel(self):
        f = Field.parse("book_chapters:has_many:BookChapter")
        assert f.child_module == "book_chapter"

    def test_missing_target(self):
        with pytest.raises(FieldParseError, match="has_many requires"):
            Field.parse("teachings:has_many")


class TestManyToMany:
    def test_basic(self):
        f = Field.parse("tag:many_to_many")
        assert f.name == "tag"
        assert f.sql_type is None
        assert f.relationship == "many_to_many"
        assert f.target is None
        assert f.is_many_to_many is True
        assert f.is_column is False


class TestValidation:
    def test_unknown_type(self):
        with pytest.raises(FieldParseError, match="unknown type"):
            Field.parse("title:varchar")

    def test_invalid_name_starts_upper(self):
        with pytest.raises(FieldParseError, match="must start with a lowercase letter"):
            Field.parse("Title:text")

    def test_invalid_name_number_start(self):
        with pytest.raises(FieldParseError, match="must start with a lowercase letter"):
            Field.parse("1title:text")

    def test_no_colon(self):
        with pytest.raises(FieldParseError):
            Field.parse("titletext")

    def test_empty_name(self):
        with pytest.raises(FieldParseError):
            Field.parse(":text")
