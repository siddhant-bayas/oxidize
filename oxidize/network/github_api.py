from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any


class GitHubAPIError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"GitHub API {status}: {message}")


class GitHubAPI:
    def __init__(self, owner: str, repo: str, token: str) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"

    def _request(
        self, method: str, endpoint: str, data: dict[str, Any] | None = None
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if body is not None:
            req.add_header("Content-Type", "application/json")

        for attempt in range(5):
            try:
                with urllib.request.urlopen(req) as resp:
                    if resp.status == 204:
                        return None
                    raw: dict[str, Any] = json.loads(resp.read().decode())
                    return raw
            except urllib.error.HTTPError as e:
                if e.code in (403, 429):
                    retry_after = e.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after else 2 ** (attempt + 1)
                    time.sleep(wait)
                    continue
                body_text = ""
                try:
                    body_text = e.read().decode()
                except Exception:
                    pass
                raise GitHubAPIError(e.code, body_text or str(e)) from e
        raise GitHubAPIError(403, "rate limit exceeded after retries")

    def create_blob(self, content: bytes) -> str:
        payload: dict[str, str] = {
            "content": base64.b64encode(content).decode(),
            "encoding": "base64",
        }
        result = self._request("POST", "/git/blobs", payload)
        assert result is not None
        sha: str = result["sha"]
        return sha

    def create_tree(self, entries: list[dict[str, Any]], base_tree: str | None = None) -> str:
        payload: dict[str, Any] = {"tree": entries}
        if base_tree:
            payload["base_tree"] = base_tree
        result = self._request("POST", "/git/trees", payload)
        assert result is not None
        sha: str = result["sha"]
        return sha

    def create_commit(
        self,
        tree_sha: str,
        parent_shas: list[str],
        message: str,
        author: dict[str, str],
        committer: dict[str, str],
    ) -> str:
        payload: dict[str, Any] = {
            "message": message,
            "tree": tree_sha,
            "author": author,
            "committer": committer,
        }
        if parent_shas:
            payload["parents"] = parent_shas
        result = self._request("POST", "/git/commits", payload)
        assert result is not None
        sha: str = result["sha"]
        return sha

    def get_ref(self, ref: str) -> str | None:
        try:
            result = self._request("GET", f"/git/refs/heads/{ref}")
            if result and "object" in result:
                obj: dict[str, str] = result["object"]
                return obj["sha"]
        except GitHubAPIError as e:
            if e.status == 404:
                return None
            raise
        return None

    def create_ref(self, ref: str, sha: str) -> None:
        self._request("POST", "/git/refs", {"ref": f"refs/heads/{ref}", "sha": sha})

    def update_ref(self, ref: str, sha: str, force: bool = False) -> None:
        endpoint = f"/git/refs/heads/{ref}"
        self._request("PATCH", endpoint, {"sha": sha, "force": force})


    def get_repo(self) -> dict[str, Any]:
        # base_url already points at /repos/owner/repo
        result = self._request("GET", "")
        assert isinstance(result, dict)
        return result

    def get_branches(self) -> list[dict[str, Any]]:
        result = self._request("GET", "/branches")
        assert isinstance(result, list)
        return result

    def get_commit(self, sha: str) -> dict[str, Any]:
        result = self._request("GET", f"/git/commits/{sha}")
        assert isinstance(result, dict)
        return result

    def get_tree(self, sha: str, recursive: bool = False) -> dict[str, Any]:
        endpoint = f"/git/trees/{sha}"
        if recursive:
            endpoint += "?recursive=1"
        result = self._request("GET", endpoint)
        assert isinstance(result, dict)
        return result

    def get_blob(self, sha: str) -> bytes:
        result = self._request("GET", f"/git/blobs/{sha}")
        assert isinstance(result, dict)
        import base64 as _b64

        content = result.get("content", "")
        if result.get("encoding") == "base64":
            return _b64.b64decode(content)
        return content.encode()  # type: ignore[no-any-return]
