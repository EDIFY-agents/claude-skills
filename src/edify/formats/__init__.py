"""The three artifact formats, plus the two registry formats.

Markdown with flat YAML frontmatter — git-native, readable on any forge, no build
step. Everything here parses; nothing here blocks. `edify check` reports what is
wrong and a person or a CI job decides what that means.
"""

from .document import Document, Section, Table, parse_document
from .finding import Finding, Level

__all__ = ["Document", "Section", "Table", "parse_document", "Finding", "Level"]
