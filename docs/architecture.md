# Architecture

## Object Model

Oxide uses a content-addressable DAG identical in spirit to Git's, but with SHA-256.

```
Commit → Tree → Blob(s)
  ↓
parents[]
```

Every object is hashed as `sha256("type len\0" + data)`. This means identical content always produces identical OIDs regardless of when or where it was stored.

## Storage

The default backend stores objects at `.oxide/objects/XX/YYYY...` where XX is the first two hex chars of the OID. Objects are zlib-compressed.

`StorageBackend` is an abstract class — swap in a database, S3, or in-memory backend by implementing three methods: `read`, `write`, `exists`.

## Index

The staging area is a JSON file at `.oxide/index.json`. Each entry records the file path, OID, mode, size, and mtime. Staleness detection compares mtime and size against the current filesystem state — same heuristic Git uses for its cache invalidation.

## Refs

References live as plain text files under `.oxide/refs/heads/`. HEAD is either a symref (`ref: refs/heads/main`) or a detached OID. This is identical to Git's ref layout and intentionally compatible.

## Dependency Order

```
objects → storage → index → core → cli
```

No layer imports from a layer above it. The CLI is a pure dispatch layer.

## Future: Semantic Diffs

The `oxide/diff/` engine today does line-level Myers diff. The plan is to add an AST-aware layer that understands Python, JS, and Rust syntax trees so that `oxide diff` can say "function `foo` was renamed" rather than showing raw line changes.

## Future: P2P Sync

`oxide push` and `oxide pull` will eventually operate over a direct peer protocol rather than requiring a central server. The object store's content-addressable nature makes sync straightforward: only transfer objects the peer doesn't have.
