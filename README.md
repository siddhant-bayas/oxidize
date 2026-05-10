# oxide

building a barebones version control system from scratch to understand how git actually works under the hood.

not trying to replace git. just learning by doing.

**this is a learning project, not a product.**

## what it does??

tracks file snapshots using the same core ideas as git: content-addressable storage, a commit dag, and a staging index. you can init a repo, stage files, commit, and walk history.

```bash
oxide init
oxide add file.py
oxide status
oxide commit -m "first commit"
oxide log
````

## install

```bash
pip install -e ".[dev]"
```

## how it works??

every file you add gets hashed using sha-256 and stored as a blob inside `.oxide/objects/`.

a commit is just:

* a snapshot of the file tree
* metadata
* a pointer to the previous commit

that's basically the entire model. humanity invented a globally dominant version control system out of linked snapshots and filesystem paranoia. beautiful, honestly.

```txt
files → blobs → tree → commit → commit → commit
                                    ↑
                                   head
```

## structure

```txt
oxide/
├── objects/    # blob, tree, commit types + serialization
├── storage/    # content-addressable object store
├── index/      # staging area
├── core/       # repo context, refs, config
├── diff/       # myers diff engine
└── cli/        # commands
```

## what's missing

* no remotes / push / pull
* no branch switching
* no merge support
* nested directory trees are still flat

~ written by a guy who discovered hashing yesterday.