from __future__ import annotations

HAS_TREE_SITTER = False
try:
    from tree_sitter import Language, Parser  # type: ignore[import-untyped]
    import tree_sitter_python  # type: ignore[import-untyped]

    HAS_TREE_SITTER = True
except ImportError:
    pass


def _build_parser() -> object | None:
    if not HAS_TREE_SITTER:
        return None
    lang = Language(tree_sitter_python.language())  # type: ignore[union-attr]
    return Parser(lang)  # type: ignore[return-value]


_parser: object | None = None
_parser_init = False


def _get_parser() -> object | None:
    global _parser, _parser_init
    if not _parser_init:
        _parser = _build_parser()
        _parser_init = True
    return _parser


def parse_source(source: str | bytes) -> object | None:
    parser = _get_parser()
    if parser is None:
        return None
    if isinstance(source, str):
        source = source.encode()
    return parser.parse(source)  # type: ignore[union-attr]
