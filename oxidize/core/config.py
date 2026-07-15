from __future__ import annotations

import configparser
from pathlib import Path


class Config:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._cfg = configparser.ConfigParser()
        if path.exists():
            self._cfg.read(path)

    def get(self, section: str, key: str, fallback: str | None = None) -> str | None:
        return self._cfg.get(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str) -> None:
        if not self._cfg.has_section(section):
            self._cfg.add_section(section)
        self._cfg.set(section, key, value)
        with open(self._path, "w") as f:
            self._cfg.write(f)

    @property
    def user_name(self) -> str:
        return self.get("user", "name", fallback="Unknown") or "Unknown"

    @property
    def user_email(self) -> str:
        return self.get("user", "email", fallback="unknown@example.com") or "unknown@example.com"
