"""
Field — parses model field specifications into structured objects.

Spec formats:
    title:text                  plain column
    duration_s:integer          plain column
    book_id:belongs_to:Book     FK column + parent lookup
    teachings:has_many:Teaching reverse lookup, no column
    tag:many_to_many            tag join table + has/1
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import re


# ---------------------------------------------------------------------------
# Supported plain SQLite types
# ---------------------------------------------------------------------------
PLAIN_TYPES = {"text", "integer", "real", "blob"}

# Relationship type constants
REL_BELONGS_TO   = "belongs_to"
REL_HAS_MANY     = "has_many"
REL_MANY_TO_MANY = "many_to_many"
RELATIONSHIPS    = {REL_BELONGS_TO, REL_HAS_MANY, REL_MANY_TO_MANY}


@dataclass
class Field:
    """
    A single field spec parsed from the command line.

    Attributes:
        name         Column/relation name as given  e.g. "book_id", "tag"
        sql_type     SQLite type or None for non-column relationships
                     e.g. "text", "integer", None
        relationship One of belongs_to | has_many | many_to_many | None
        target       Target model name for belongs_to/has_many  e.g. "Book"
    """
    name:         str
    sql_type:     Optional[str]
    relationship: Optional[str]
    target:       Optional[str]

    # -----------------------------------------------------------------------
    # Derived properties
    # -----------------------------------------------------------------------

    @property
    def is_column(self) -> bool:
        """True if this field adds a column to the table."""
        return self.sql_type is not None

    @property
    def is_belongs_to(self) -> bool:
        return self.relationship == REL_BELONGS_TO

    @property
    def is_has_many(self) -> bool:
        return self.relationship == REL_HAS_MANY

    @property
    def is_many_to_many(self) -> bool:
        return self.relationship == REL_MANY_TO_MANY

    @property
    def erl_var(self) -> str:
        """
        Erlang variable name: title -> Title, book_id -> BookId,
        duration_s -> DurationS
        """
        return re.sub(r'(?:^|_)([a-z])', lambda m: m.group(1).upper(), self.name)

    @property
    def parent_module(self) -> Optional[str]:
        """
        For belongs_to: parent module name in snake_case.
        Book -> book,  BookChapter -> book_chapter
        """
        if self.target is None:
            return None
        return _camel_to_snake(self.target)

    @property
    def parent_table(self) -> Optional[str]:
        """
        Naive pluralisation of parent module for table name.
        book -> books,  book_chapter -> book_chapters
        """
        if self.parent_module is None:
            return None
        return self.parent_module + "s"

    @property
    def child_module(self) -> Optional[str]:
        """For has_many: child module name in snake_case."""
        if self.target is None:
            return None
        return _camel_to_snake(self.target)

    # -----------------------------------------------------------------------
    # Parser
    # -----------------------------------------------------------------------

    @classmethod
    def parse(cls, spec: str) -> "Field":
        """
        Parse a field spec string into a Field.

        Examples:
            Field.parse("title:text")
                -> Field(name="title", sql_type="text", relationship=None, target=None)

            Field.parse("book_id:belongs_to:Book")
                -> Field(name="book_id", sql_type="integer",
                         relationship="belongs_to", target="Book")

            Field.parse("teachings:has_many:Teaching")
                -> Field(name="teachings", sql_type=None,
                         relationship="has_many", target="Teaching")

            Field.parse("tag:many_to_many")
                -> Field(name="tag", sql_type=None,
                         relationship="many_to_many", target=None)
        """
        parts = spec.split(":")

        if len(parts) < 2:
            raise FieldParseError(
                f"Invalid field spec {spec!r} — expected name:type or name:relationship[:Target]"
            )

        name    = parts[0]
        second  = parts[1]
        third   = parts[2] if len(parts) >= 3 else None

        _validate_name(name)

        # ---- Relationship types ----------------------------------------
        if second == REL_BELONGS_TO:
            if third is None:
                raise FieldParseError(
                    f"{spec!r}: belongs_to requires a target model e.g. book_id:belongs_to:Book"
                )
            return cls(
                name=name,
                sql_type="integer",   # FK is always an integer
                relationship=REL_BELONGS_TO,
                target=third,
            )

        if second == REL_HAS_MANY:
            if third is None:
                raise FieldParseError(
                    f"{spec!r}: has_many requires a target model e.g. teachings:has_many:Teaching"
                )
            return cls(
                name=name,
                sql_type=None,        # no column on this table
                relationship=REL_HAS_MANY,
                target=third,
            )

        if second == REL_MANY_TO_MANY:
            return cls(
                name=name,
                sql_type=None,        # no column on this table
                relationship=REL_MANY_TO_MANY,
                target=None,
            )

        # ---- Plain column type -----------------------------------------
        sql_type = second.lower()
        if sql_type not in PLAIN_TYPES:
            raise FieldParseError(
                f"{spec!r}: unknown type {sql_type!r}. "
                f"Valid types: {', '.join(sorted(PLAIN_TYPES))} "
                f"or relationships: {', '.join(sorted(RELATIONSHIPS))}"
            )

        return cls(
            name=name,
            sql_type=sql_type,
            relationship=None,
            target=None,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _camel_to_snake(name: str) -> str:
    """BookChapter -> book_chapter,  Book -> book"""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return s.lower()


def _validate_name(name: str) -> None:
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise FieldParseError(
            f"Field name {name!r} must start with a lowercase letter "
            f"and contain only letters, digits, and underscores."
        )


class FieldParseError(ValueError):
    """Raised when a field spec cannot be parsed."""
    pass
