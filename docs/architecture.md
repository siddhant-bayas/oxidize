# architecture

## object model

oxidize uses a content-addressable dag identical in spirit to git's but with sha-256

```
commit -> tree -> blob(s)
  |
parents[]
```

every object is hashed as sha256("type len\0" + data) this means identical content always produces identical oids regardless of when or where it was stored

## storage

the default backend stores objects at .oxidize/objects/xx/yyyy... where xx is the first two hex chars of the oid objects are zlib-compressed

storagebackend is an abstract class -- swap in a database s3 or in-memory backend by implementing three methods read write exists

## index

the staging area is a json file at .oxidize/index.json each entry records the file path oid mode size and mtime staleness detection compares mtime and size against the current filesystem state -- same heuristic git uses for its cache invalidation

## refs

references live as plain text files under .oxidize/refs/heads/ head is either a symref (ref: refs/heads/main) or a detached oid this is identical to git's ref layout and intentionally compatible

## dependency order

```
objects -> storage -> index -> core -> cli
```

no layer imports from a layer above it the cli is a pure dispatch layer

## cli and interactive shell

both `oxidize` and `oxi` are entry points that accept the same subcommands

`oxidize` maps to the click group in cli/main.py

`oxi` maps to cli/repl.py which checks sys.argv -- if arguments are present it delegates to the click group otherwise it launches the prompt_toolkit-based repl

### repl features

- tab completion for commands file paths and branch names
- live status bar showing branch staged count and untracked count
- command history persisted to ~/.oxidize_history
- aliases s -> status c -> commit a -> add l -> log d -> diff

## security secret scanning

oxidize scan detects api keys tokens private keys and credentials using pattern matching runs automatically before commit when scan_on_commit = true patterns cover aws gcp azure github gitlab slack stripe openai anthropic and generic patterns

## structured data merge

for json yaml and toml files merge operates at the key level instead of text lines three-way merge base + ours + theirs conflicts only when both sides changed the same key

## notebook support

ipynb files are treated as structured documents not text blobs cell-level diffing automatic output stripping and execution count removal keep diffs clean

## semantic diffs (experimental)

uses tree-sitter to parse source code into asts then diffs at the entity level (functions classes methods) can track renames and moves across files

## ai agent provenance

commits can be tagged with agent metadata (--agent "claude-code") the provenance journal tracks which agent/tool/prompt produced each change

## undo system

every mutation writes to .oxidize/journal.json oxidize undo reverses the last operation oxidize redo re-applies it

## workflows

- ci.yml -- runs on push/PR to main lint (ruff) typecheck (mypy) tests (pytest) across python 3.11 3.12 3.13 then builds the package
- pypi.yml -- triggers on github release publish builds and uploads to pypi via trusted publishing (oidc)
