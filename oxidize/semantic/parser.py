from __future__ import annotations

from typing import Any

HAS_TREE_SITTER = False
try:
    import tree_sitter_python
    from tree_sitter import Language, Parser

    HAS_TREE_SITTER = True
except ImportError:
    pass


def _build_parser() -> Any:
    if not HAS_TREE_SITTER:
        return None
    lang = Language(tree_sitter_python.language())
    return Parser(lang)


_parser: Any = None
_parser_init = False


def _get_parser() -> Any:
    global _parser, _parser_init
    if not _parser_init:
        _parser = _build_parser()
        _parser_init = True
    return _parser


def parse_source(source: str | bytes) -> Any:
    parser = _get_parser()
    if parser is None:
        return None
    if isinstance(source, str):
        source = source.encode()
    return parser.parse(source)


LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
}


def detect_language(path: str) -> str:
    import os

    _, ext = os.path.splitext(path.lower())
    return LANGUAGE_BY_EXTENSION.get(ext, "python")
