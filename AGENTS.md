# AGENTS.md -- using oxidize (`oxi`) for version control

a guide for AI agents (claude-code, copilot, codex, aider, cursor, …) using **`oxi`** (or its full-name alias `oxidize`) as the version-control tool in a workspace.

if you are an agent reading this: follow the patterns below unless you have a good reason to deviate. they line up with the rest of the codebase and are tested end-to-end.

> ℹ **oxidize** is **not** git. it has the same conceptual surface (commits, branches, status, log) but the command surface is its own. do not run `git` commands against a `.oxidize/` repo and do not run `oxi` commands against a `.git/` repo.

---

## TL;DR -- the 80% recipe

```bash
oxidize status                                    # see what changed
oxidize add <path> ...                            # stage files (respects .oxignore)
oxidize commit -m "<short, present-tense message>" --agent <your-name>
```

the only flags most sessions ever need: `-m`, `--agent`, and the rare `-f` ("yes, really stage this `*.env`"). commit messages should be dense and present-tense: `"add retry helper"`, not `"added a bunch of stuff"`.

---

## how to identify yourself

oxidize tags every commit with the agent that wrote it. **always pass `--agent`** so reviewers can later run `oxidize log --agent <you>`.

```bash
oxidize commit -m "explain the diff" --agent claude-code
oxidize commit -m "..." --agent copilot
oxidize commit -m "..." --agent "my-custom-tool/1.4"
```

if you forget `--agent`, oxidize tries to *guess* from environment variables:

| env var | detected agent |
|---------|---------------|
| `CLAUDE_CODE` | `claude-code` |
| `GITHUB_COPILOT` | `github-copilot` |
| `CODEX_AGENT` | `codex` |
| ` Cursor` | `cursor` |
| `AIDER` | `aider` |

detection is a fallback. **explicit is better -- always pass `--agent`.**

---

## the working session

```bash
# 1. orient
cd /path/to/project
oxidize status                # nothing / clean?  you're done before starting.
oxidize log --oneline -n 5    # recent commit headlines

# 2. make changes
# ... your edits land on disk ...

# 3. stage
oxidize add path/to/file.py
oxidize add src/              # recursive
oxidize add .                 # everything (skips .oxignore)
oxidize add -f .env.local     # bypass .oxignore when truly needed

# 4. commit
oxidize commit -m "describe what & why" --agent <you>

# 5. verify
oxidize status                # expect "nothing to commit, working tree clean"
```

common flags:
- `-m "..."` -- required, the commit message
- `--agent <name>` -- strongly recommended
- `-n` / `--no-verify` -- skip hooks (rare; use sparingly)

---

## reading state

```bash
oxidize status                # current branch + staged/modified/untracked
oxidize log                   # last 20 commits, full headers
oxidize log --oneline         # one line per commit
oxidize log -n 50             # last 50
oxidize log --agent claude-code --author "Jane"   # filter
oxidize show <ref>            # object header, full commit metadata
oxidize show HEAD~2            # 2 commits ago
oxidize branch                # local branches
oxidize tag                   # local tags
oxidize stash list            # shelved work
```

status output sections:
- `staged:` -- ready to commit, shown in green
- `modified:` -- changed on disk but not staged, yellow
- `untracked:` -- new files, dim
- ignored files are **never** shown — they vanished from view on purpose

---

## branches

```bash
oxidize branch create feat-x                       # branch off HEAD
oxidize branch create feat-x <sha-or-ref>          # branch from a specific point
oxidize checkout feat-x                            # switch
oxidize checkout -b feat-x                          # create + switch in one
oxidize branch list                                  # show local branches
oxidize branch delete feat-x                        # delete (refuses if HEAD)
```

if you discover mid-task that you should have branched first, do not panic: `oxidize undo` will roll back the operation journal.

### coordination with other agents

when more than one agent is editing:

```bash
oxidize remote pull file:///shared/oxidize main    # fetch shared refs
oxidize branch create my-fix main                  # branch off freshly-pulled main
# … work, commit …
oxidize remote push file:///shared/oxidize my-fix  # publish your branch
```

the **filesystem remote** is currently the only transport (`file://` URL). network protocols are not implemented yet -- if your host has `ssh` access, mount it via a directory and use the same URL pattern.

---

## merging & conflict resolution

```bash
oxidize merge other-branch                          # three-way text merge
oxidize merge other-branch --no-commit              # leave conflicts uncommitted
```

merge correlates by walking both branches back to their lowest common ancestor ("merge base"). files mutated identically on both sides resolve to the merged content; files mutated differently produce standard `<<<<<<< OURS / ||||||| BASE / ======= THEIRS / >>>>>>>>> THEIRS` markers in the working tree.

### resolving a conflict

```bash
oxidize resolve --all                # walk each conflicted file, ours/theirs/skip/abort
oxidize resolve --all --ours         # for every conflict, take the local version
oxidize resolve --all --theirs       # for every conflict, take the incoming version
oxidize resolve path/to/file.py      # resolve a single file manually
```

after the markers are gone:

```bash
oxidize add <resolved-files>
oxidize commit -m "merge main into feat-x --agent <you>"
```

do not commit files that still contain conflict markers -- `oxidize commit` will accept them but reviewers will reject the merge.

---

## undo -- a safety net

every operation (`add`, `commit`, `branch create`, `branch delete`, …) is journaled.

```bash
oxidize undo                            # reverse the most recent operation
oxidize undo count 3                    # reverse the last 3
oxidize undo list                        # browse the full journal
oxidize undo last                       # same as `oxidize undo`
```

use it freely. if your run created four commits and you want only the last one:

```bash
oxidize undo count 3                    # roll back the earlier 3 commits
```

note: `undo` reverses the recorded operation but it does **not** rewrite the index disk content -- if you `add` an unwanted file, `undo` removes it from the index but you should also delete the file from disk yourself.

---

## never do these

```bash
# don't write .oxignore that ignores the tracked sources you were asked to edit
echo 'src/' >> .oxignore                # wrong -- this hides everything you wrote

# don't try to force-add a directory at the repo root and skip scope
oxidize add /                           # resumes full sweep; usually wrong in a session

# don't fabricate commit messages
# "wip", "x", random emoji, or copy-paste from a previous task
# -- reviewers will downgrade the work.

# don't bypass the agent flag
oxidize commit -m "..."                 # let oxidize guess?  no. pass --agent.

# don't disable .oxignore entirely
rm .oxignore                            # deletes your scope filters; the rest of the
                                        # team relies on them.
```

---

## reconnaissance cheatsheet

when you need to understand the repo fast:

```bash
oxidize status
oxidize log --oneline -n 10 --agent claude-code
oxidize branch
oxidize tag list --verify
oxidize ignores list                    # see scope filters
oxidize ignores check path/you/want.txt # is this file in scope?
oxidize stash list
oxidize undo list                       # recent activity on this branch
```

---

## piping and composability

every command exits `0` on success, non-zero on failure. every message goes to stdout; errors go to stderr (or raise `click.ClickException`).

```bash
oxidize log --oneline --agent claude-code | head -20
oxidize status --porcelain             # short format (planned alias)
oxidize ignores check .env || echo "skip" && true
```

use `oxidize status` (no flag) in script loops: exit code 0 == nothing to commit, exit code 0 with body == staged or modified work. combine with `oxidize log --oneline` to detect *what* changed if you only have one file edited.

---

## escalation paths -- when oxidize is not enough

| you need | use instead |
|----------|-------------|
| HTTP / SSH remote | file-system mount + `file://` URLs, or wait for the network-remote milestone |
| LFS / large binary blobs | crop the input, use git's LFS, or ask before retrying |
| submodules | work in a flat layout for now; submodule support is on the roadmap |
| rename-aware blame | line-level blame only; AST-aware blame is on the roadmap |
| full structured (json/yaml/toml) merge | already works, see `oxidize.merge.structured` |

before you reach for a workaround, ask the human whether the workaround is acceptable. the rules above are not negotiable without explicit sign-off.

---

## what to put in a commit message (when you are the agent)

each commit message is a single, observable effect:

| ✅ good | ❌ bad |
|---------|--------|
| `add retry helper with exponential backoff` | `update code` |
| `fix off-by-one in chunked upload` | `bug fix` |
| `refactor client to use session headers` | `stuff` |
| `remove deprecated color tokens` | `cleanup` |

rationale: `oxidize log --oneline` is the team's primary scroll. dense headlines compound.

---

## reference

quick lookup, alphabetized:

| command | purpose |
|---------|---------|
| `oxidize add <paths>` | stage files |
| `oxidize add -f <paths>` | stage ignored files anyway |
| `oxidize branch` / `branch <name>` | list / create / delete branches |
| `oxidize bisect start/good/bad/reset` | binary-search regressions |
| `oxidize blame <path>` | line-level attribution |
| `oxidize checkout <ref>` / `-b` | switch branches / create + switch |
| `oxidize commit -m "..." --agent <name>` | write a commit |
| `oxidize diff` | working-tree vs index diff |
| `oxidize diff --cached` | index vs HEAD diff |
| `oxidize hooks {list,install,run}` | manage hooks |
| `oxidize ignores {list,check}` | inspect `.oxignore` rules |
| `oxidize init` | create a new repo |
| `oxidize log` / `-n N` / `--agent` / `--author` / `--oneline` | commit history |
| `oxidize merge <branch>` | three-way merge |
| `oxidize notebook-diff <a> <b>` | cell-level notebook diff |
| `oxidize pull` / `oxidize push` (via `remote`) | sync over filesystem remote |
| `oxidize remote {clone,push,pull}` | remote ops |
| `oxidize resolve [--all] [--ours|--theirs]` | resolve conflicts |
| `oxidize scan` | pre-commit secret scanning |
| `oxidize show <ref>` | view a commit object |
| `oxidize stash {save,list,pop}` | shelve work |
| `oxidize status` | working-tree status |
| `oxidize tag {create,list,delete}` | tag commits |
| `oxidize undo [count N] / undo list` | reverse / browse operations |

see `docs/cli-reference.md` for the full table including every flag.
