# Changelog

all notable changes to this project are documented here. format follows [keep a changelog](https://keepachangelog.com).

## [unreleased]

### added
- placeholder denylist for the secret scanner (skips common fake or template tokens like `changeme`, `your_*_here`, `xxx`, `replace_me`, etc., and whole-file skip for `.env.example`, `.env.sample`, `.env.template`)
- structural-heuristic diff rewritten on top of `tree-sitter` (parse-driven extraction, qualified entity names, fallback to the regex parser when `tree-sitter` isn't installed)

### changed
- narrow feature status table in README — most of the surface is "stable", newer subsystems are "beta" or "alpha", and the previously mislabelled "AST-aware" semantic diffs are clarified as required inner state
- dead `src/main.py` stub removed
- scanner reads matching are anchored to the match's surrounding context — adjacent placeholder tokens no longer trigger false positive reports

### fixed
- cross-class method collisions in `extract_entities` are eliminated by switching from bare names (`save`, `__init__`, ...) to qualified paths (`MyClass.save`); same-named methods on different classes are now compared independently
- pyoxidize install size badge shields url corrected (shields does not accept `~` in the message slot)

## [0.2.0] — 2026-07-15

first release published to PyPI from a prior state of the codebase. rolled forward and backfilled here.

### added
- `.oxignore` matcher with full `.gitignore` syntax (negation, anchored slashes, `**/`, dir-only suffix)
- secret scanner with 23 patterns across cloud, code hosting, communication, payments, ai/ml, email, generic, and database categories
- structured three-way data merge for json/yaml/toml with proper nested-dict recursion, conflict tracking, and "ours" default
- notebook cell-level diff and cell-aware commit
- interactive REPL (`oxi`) with tab completion, command history, and live status bar
- safe undo journal for every operation
- ai agent provenance per commit (with env-var auto-detection for claude-code, copilot, codex, aider, cursor)
- branches, tags, checkout, three-way text merge, conflict resolution UI
- stash, bisect, hooks (pre-commit / post-commit / pre-add / post-add / pre-merge / post-merge)
- line-level blame
- filesystem-only remote sync (clone / push / pull against `file://` URLs)
- ``oxi blame``, ``oxi scan``, ``oxi log --agent``, ``oxi tag`` CLI surface

## [0.1.0]

early internal release, never published to PyPI.

[unreleased]: https://github.com/siddhant-bayas/oxidize/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/siddhant-bayas/oxidize/releases/tag/v0.2.0
[0.1.0]: https://github.com/siddhant-bayas/oxidize/releases/tag/v0.1.0
