"""Tests for cowboy_up.config"""

import pytest
from pathlib import Path
from cowboy_up.config import ProjectConfig, ConfigError


class TestNameNormalisation:
    def _make(self, name):
        return ProjectConfig.from_raw_name(name, Path("/tmp"))

    def test_spaces(self):
        assert self._make("my new app").app_name == "my_new_app"

    def test_hyphens(self):
        assert self._make("bible-site").app_name == "bible_site"

    def test_mixed_case(self):
        assert self._make("Bible Site").app_name == "bible_site"

    def test_extra_spaces(self):
        assert self._make("  spaced  ").app_name == "spaced"

    def test_multiple_underscores(self):
        assert self._make("a__b").app_name == "a_b"

    def test_three_words(self):
        assert self._make("way life truth").app_name == "way_life_truth"

    def test_display_name(self):
        assert self._make("bible site").display_name == "Bible Site"

    def test_display_name_underscores(self):
        assert self._make("bible_site").display_name == "Bible Site"


class TestValidation:
    def test_empty_name(self):
        with pytest.raises(ConfigError):
            ProjectConfig.from_raw_name("", Path("/tmp"))

    def test_name_starts_with_number(self):
        with pytest.raises(ConfigError, match="must start with a letter"):
            ProjectConfig.from_raw_name("123app", Path("/tmp"))

    def test_purely_symbols(self):
        with pytest.raises(ConfigError):
            ProjectConfig.from_raw_name("---", Path("/tmp"))


class TestTargetDir:
    def test_target_dir(self):
        cfg = ProjectConfig.from_raw_name("my app", Path("/tmp"))
        assert cfg.target_dir == Path("/tmp/my_app")


class TestTemplateVars:
    def test_vars_contain_app_name(self):
        cfg = ProjectConfig.from_raw_name("bible site", Path("/tmp"))
        v = cfg.template_vars()
        assert v["app_name"] == "bible_site"
        assert v["display_name"] == "Bible Site"
        assert v["erlang_node"] == "bible_site@127.0.0.1"
        assert v["erlang_cookie"] == "bible_site_cookie"
