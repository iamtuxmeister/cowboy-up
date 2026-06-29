"""Tests for cowboy_up.utils"""

from cowboy_up.utils import to_snake


class TestToSnake:
    def test_single_word(self):    assert to_snake("Book")            == "book"
    def test_two_words(self):      assert to_snake("BookChapter")     == "book_chapter"
    def test_three_words(self):    assert to_snake("BookChapterVerse") == "book_chapter_verse"
    def test_already_lower(self):  assert to_snake("book")            == "book"
    def test_consecutive_caps(self):
        assert to_snake("HTMLParser") == "html_parser"
