from __future__ import annotations

import json
import os
from datetime import UTC
from pathlib import Path
from typing import Any

from oxidize.core.repository import Repository
from oxidize.network.github_api import GitHubAPI
from oxidize.network.remote import TransferError
from oxidize.objects.types import Author, Commit, FileMode, Tree, TreeEntry


class GitHubRemote:
    def __init__(self, owner: str, repo: str) -> None:
        token = os.environ.get("OXIDIZE_GITHUB_TOKEN")
        if not token:
            raise TransferError(
                "OXIDIZE_GITHUB_TOKEN environment variable not set. "
                "Create a personal access token at https://github.com/settings/tokens"
            )
        self.api = GitHubAPI(owner, repo, token)
        self.owner = owner
        self.repo = repo

    def clone(self, target: Path) -> Repository:
        from oxidize.core.repository import Repository

        target = target.resolve()
        target.mkdir(parents=True, exist_ok=True)
        repo = Repository.init(target)

        commit_map: dict[str, str] = {}
        tree_cache: dict[str, str] = {}

        branches = self.api.get_branches()
        for b in branches:
            sha = b["commit"]["sha"]
            self._import_commit(repo, sha, commit_map, tree_cache)

        for b in branches:
            name = b["name"]
            sha = b["commit"]["sha"]
            if sha not in commit_map:
                continue
            ref_path = repo.oxidize_dir / "refs" / "heads" / name
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(commit_map[sha] + "\n")

        info = self.api.get_repo()
        default = info.get("default_branch")
        if not default and branches:
            default = branches[0]["name"]
        if not default:
            default = "main"

        head_sha = None
        for b in branches:
            if b["name"] == default:
                head_sha = b["commit"]["sha"]
                break
        if head_sha is None and branches:
            head_sha = branches[0]["commit"]["sha"]
            default = branches[0]["name"]

        repo.refs.set_head_branch(default)
        (repo.oxidize_dir / "HEAD").write_text(f"ref: refs/heads/{default}\n")
        if head_sha and head_sha in commit_map:
            ref_path = repo.oxidize_dir / "refs" / "heads" / default
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(commit_map[head_sha] + "\n")
            head_commit = repo.db.load_commit(commit_map[head_sha])
            _write_tree(repo, repo.db.load_tree(head_commit.tree_oid), repo.work_tree)

        return repo

    def pull(self, repo: Repository, branch: str | None = None) -> list[str]:
        commit_map: dict[str, str] = {}
        tree_cache: dict[str, str] = {}
        branches = self.api.get_branches()
        targets = {branch} if branch else {b["name"] for b in branches}

        pulled: list[str] = []
        for b in branches:
            name = b["name"]
            if name not in targets:
                continue
            sha = b["commit"]["sha"]
            ox_oid = self._import_commit(repo, sha, commit_map, tree_cache)
            ref_path = repo.oxidize_dir / "refs" / "heads" / name
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(ox_oid + "\n")
            pulled.append(name)

        current = repo.refs.current_branch()
        if current in pulled:
            head_oid = repo.refs.read(f"refs/heads/{current}")
            if head_oid:
                hc = repo.db.load_commit(head_oid)
                _write_tree(repo, repo.db.load_tree(hc.tree_oid), repo.work_tree)

        return pulled

    def _import_commit(
        self, repo: Repository, git_sha: str, commit_map: dict[str, str], tree_cache: dict[str, str]
    ) -> str:
        if git_sha in commit_map:
            return commit_map[git_sha]
        cdata = self.api.get_commit(git_sha)
        ox_parents: list[str] = []
        for p in cdata.get("parents", []):
            ox_parents.append(self._import_commit(repo, p["sha"], commit_map, tree_cache))

        tree_sha = cdata["tree"]["sha"]
        ox_tree = self._import_tree(repo, tree_sha, tree_cache)

        author = _parse_person(cdata.get("author", {}))
        committer = _parse_person(cdata.get("committer", {}))
        message = cdata.get("message", "")

        commit = Commit(
            tree_oid=ox_tree,
            author=author,
            committer=committer,
            message=message,
            parents=ox_parents,
        )
        repo.db.store_commit(commit)
        commit_map[git_sha] = commit.oid
        return commit.oid

    def _import_tree(self, repo: Repository, git_tree_sha: str, cache: dict[str, str]) -> str:
        if git_tree_sha in cache:
            return cache[git_tree_sha]

        tree_data = self.api.get_tree(git_tree_sha, recursive=True)
        flat = tree_data.get("tree", [])

        dir_sha: dict[str, str] = {"": git_tree_sha}
        children: dict[str, list[dict[str, Any]]] = {}
        for e in flat:
            parent = "/".join(e["path"].split("/")[:-1])
            children.setdefault(parent, []).append(e)
            if e.get("type") == "tree":
                dir_sha[e["path"]] = e["sha"]
                children.setdefault(e["path"], [])

        # ensure root present
        children.setdefault("", [])

        dir_ox: dict[str, str] = {}
        # process deepest first
        for d in sorted(dir_sha.keys(), key=lambda x: x.count("/"), reverse=True):
            t = Tree()
            for e in children.get(d, []):
                name = e["path"].split("/")[-1]
                if e.get("type") == "blob":
                    data = self.api.get_blob(e["sha"])
                    oid = repo.db.store_blob(data)
                    t.add(TreeEntry(name=name, oid=oid, mode=FileMode(e.get("mode", "100644"))))
                elif e.get("type") == "tree":
                    child_ox = dir_ox.get(e["path"])
                    if child_ox is None:
                        # fallback: import subtree
                        child_ox = self._import_tree(repo, e["sha"], cache)
                    t.add(TreeEntry(name=name, oid=child_ox, mode=FileMode.DIRECTORY))
            repo.db.store_tree(t)
            dir_ox[d] = t.oid
            cache[dir_sha[d]] = t.oid

        return cache[git_tree_sha]

    def push(
        self, repo: Repository, branch: str | None = None, *, force: bool = False
    ) -> list[str]:
        branches = [branch] if branch else repo.refs.list_branches()
        commit_map, blob_map = self._load_export_map(repo)
        pushed: list[str] = []

        for b in branches:
            local_oid = repo.refs.read(f"refs/heads/{b}")
            if not local_oid:
                raise TransferError(f"local branch '{b}' not found")

            if not force:
                remote_sha = self.api.get_ref(b)
                if remote_sha and local_oid in commit_map and commit_map[local_oid] != remote_sha:
                    raise TransferError(
                        f"remote branch '{b}' has diverged from local (use --force)"
                    )

            commits = self._commits_since_last_export(repo, local_oid, commit_map)

            for commit in commits:
                tree_entries = self._walk_tree(repo, commit.tree_oid, blob_map)
                git_tree_sha = self.api.create_tree(tree_entries)
                parent_shas = [commit_map[p] for p in commit.parents if p in commit_map]
                message = commit.message
                if commit.agent:
                    message += f"\n\nOxidize-Agent: {commit.agent}"
                git_commit_sha = self.api.create_commit(
                    tree_sha=git_tree_sha,
                    parent_shas=parent_shas,
                    message=message,
                    author={
                        "name": commit.author.name,
                        "email": commit.author.email,
                        "date": self._ts_to_iso(commit.author.timestamp),
                    },
                    committer={
                        "name": commit.committer.name,
                        "email": commit.committer.email,
                        "date": self._ts_to_iso(commit.committer.timestamp),
                    },
                )
                commit_map[commit.oid] = git_commit_sha

            git_sha = commit_map.get(local_oid)
            if not git_sha:
                raise TransferError(f"failed to export commit {local_oid[:12]}")

            existing = self.api.get_ref(b)
            if existing:
                self.api.update_ref(b, git_sha, force=force)
            else:
                self.api.create_ref(b, git_sha)

            self._save_export_map(repo, commit_map, blob_map)
            pushed.append(b)

        return pushed

    def _commits_since_last_export(
        self, repo: Repository, head_oid: str, commit_map: dict[str, str]
    ) -> list[Commit]:
        commits: list[Commit] = []
        seen: set[str] = set()
        stack = [head_oid]
        while stack:
            oid = stack.pop()
            if oid in seen or oid in commit_map:
                continue
            seen.add(oid)
            try:
                commit = repo.db.load_commit(oid)
            except Exception:
                continue
            commits.append(commit)
            for p in commit.parents:
                if p not in commit_map:
                    stack.append(p)
        commits.reverse()
        return commits

    def _walk_tree(
        self, repo: Repository, tree_oid: str, blob_map: dict[str, str], path: str = ""
    ) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        try:
            tree = repo.db.load_tree(tree_oid)
        except Exception:
            return entries

        for entry in tree:
            entry_path = f"{path}/{entry.name}" if path else entry.name
            if entry.mode == FileMode.DIRECTORY:
                git_sha = self._create_tree_recursive(repo, entry.oid, blob_map, entry_path)
                entries.append(
                    {
                        "path": entry_path,
                        "mode": "040000",
                        "type": "tree",
                        "sha": git_sha,
                    }
                )
            else:
                git_blob_sha = self._get_or_create_blob(repo, entry.oid, blob_map)
                mode = "100755" if entry.mode == FileMode.EXECUTABLE else "100644"
                entries.append(
                    {
                        "path": entry_path,
                        "mode": mode,
                        "type": "blob",
                        "sha": git_blob_sha,
                    }
                )
        return entries

    def _create_tree_recursive(
        self, repo: Repository, tree_oid: str, blob_map: dict[str, str], path: str
    ) -> str:
        tree_entries = self._walk_tree(repo, tree_oid, blob_map, path)
        result = self.api.create_tree(tree_entries)
        return result

    def _get_or_create_blob(self, repo: Repository, oid: str, blob_map: dict[str, str]) -> str:
        if oid in blob_map:
            return blob_map[oid]
        blob = repo.db.load_blob(oid)
        git_sha = self.api.create_blob(blob.data)
        blob_map[oid] = git_sha
        return git_sha

    def _load_export_map(self, repo: Repository) -> tuple[dict[str, str], dict[str, str]]:
        map_path = repo.oxidize_dir / "github_export_map.json"
        if map_path.exists():
            data = json.loads(map_path.read_text())
            return data.get("commits", {}), data.get("blobs", {})
        return {}, {}

    def _save_export_map(
        self, repo: Repository, commit_map: dict[str, str], blob_map: dict[str, str]
    ) -> None:
        map_path = repo.oxidize_dir / "github_export_map.json"
        map_path.write_text(json.dumps({"commits": commit_map, "blobs": blob_map}, indent=2))

    @staticmethod
    def _ts_to_iso(ts: int) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_github_url(url: str) -> tuple[str, str] | None:
    url = url.rstrip("/")
    url = url.removesuffix(".git")

    if url.startswith("https://github.com/"):
        parts = url[len("https://github.com/") :].split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    if url.startswith("git@github.com:"):
        parts = url[len("git@github.com:") :].split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    return None


def _parse_person(person: dict[str, Any]) -> Author:
    from datetime import datetime

    name = person.get("name", "")
    email = person.get("email", "")
    date_str = person.get("date")
    ts = 0
    if date_str:
        try:
            dt = datetime.fromisoformat(date_str)
            ts = int(dt.timestamp())
        except ValueError:
            ts = 0
    return Author(name=name, email=email, timestamp=ts)


def _write_tree(repo: Any, tree: Any, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for entry in tree:
        target = root / entry.name
        if entry.mode.value == "040000":
            child = repo.db.load_tree(entry.oid)
            _write_tree(repo, child, target)
        else:
            try:
                from oxidize import lfs

                data = lfs.load_blob_data(repo, entry.oid)
            except KeyError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
