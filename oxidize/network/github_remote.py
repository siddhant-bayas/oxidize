from __future__ import annotations

import json
import os

from oxidize.core.repository import Repository
from oxidize.network.github_api import GitHubAPI
from oxidize.network.remote import TransferError
from oxidize.objects.types import Commit, FileMode


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
        from datetime import datetime, timezone

        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_github_url(url: str) -> tuple[str, str] | None:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    if url.startswith("https://github.com/"):
        parts = url[len("https://github.com/") :].split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    if url.startswith("git@github.com:"):
        parts = url[len("git@github.com:") :].split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    return None
