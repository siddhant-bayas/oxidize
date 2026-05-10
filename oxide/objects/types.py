from __future__ import annotations

import hashlib
import stat
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class ObjectType(str, Enum):
    BLOB = "blob"
    TREE = "tree"
    COMMIT = "commit"


def hash_object(type: ObjectType, data: bytes) -> str:
    header = f"{type.value} {len(data)}\x00".encode()
    return hashlib.sha256(header + data).hexdigest()


@dataclass(frozen=True)
class Blob:
    data: bytes
    oid: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "oid", hash_object(ObjectType.BLOB, self.data))

    def serialize(self) -> bytes:
        return self.data

    @classmethod
    def deserialize(cls, data: bytes) -> "Blob":
        return cls(data=data)


class FileMode(str, Enum):
    REGULAR = "100644"
    EXECUTABLE = "100755"
    DIRECTORY = "040000"

    @classmethod
    def from_stat(cls, st_mode: int) -> "FileMode":
        if stat.S_ISDIR(st_mode):
            return cls.DIRECTORY
        if st_mode & stat.S_IXUSR:
            return cls.EXECUTABLE
        return cls.REGULAR


@dataclass(frozen=True)
class TreeEntry:
    name: str
    oid: str
    mode: FileMode


@dataclass
class Tree:
    entries: list[TreeEntry] = field(default_factory=list)
    oid: str = field(init=False, default="")

    def add(self, entry: TreeEntry) -> None:
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.name)
        self.oid = hash_object(ObjectType.TREE, self.serialize())

    def serialize(self) -> bytes:
        parts: list[bytes] = []
        for e in sorted(self.entries, key=lambda x: x.name):
            parts.append(f"{e.mode.value} {e.name}\x00".encode() + bytes.fromhex(e.oid))
        return b"".join(parts)

    @classmethod
    def deserialize(cls, data: bytes) -> "Tree":
        tree = cls()
        i = 0
        while i < len(data):
            null = data.index(b"\x00", i)
            mode_name = data[i:null].decode()
            mode_str, name = mode_name.split(" ", 1)
            oid = data[null + 1 : null + 33].hex()
            tree.entries.append(TreeEntry(name=name, oid=oid, mode=FileMode(mode_str)))
            i = null + 33
        tree.oid = hash_object(ObjectType.TREE, data)
        return tree

    def __iter__(self) -> Iterator[TreeEntry]:
        return iter(self.entries)


@dataclass(frozen=True)
class Author:
    name: str
    email: str
    timestamp: int = field(default_factory=lambda: int(time.time()))
    tz_offset: str = "+0000"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> {self.timestamp} {self.tz_offset}"

    @classmethod
    def from_str(cls, s: str) -> "Author":
        # "Name <email> timestamp tz"
        lt = s.index("<")
        gt = s.index(">")
        name = s[:lt].strip()
        email = s[lt + 1 : gt]
        rest = s[gt + 1 :].strip().split()
        return cls(name=name, email=email, timestamp=int(rest[0]), tz_offset=rest[1])


@dataclass
class Commit:
    tree_oid: str
    author: Author
    committer: Author
    message: str
    parents: list[str] = field(default_factory=list)
    oid: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.oid = hash_object(ObjectType.COMMIT, self.serialize())

    def serialize(self) -> bytes:
        lines = [f"tree {self.tree_oid}"]
        for p in self.parents:
            lines.append(f"parent {p}")
        lines.append(f"author {self.author}")
        lines.append(f"committer {self.committer}")
        lines.append("")
        lines.append(self.message)
        return "\n".join(lines).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> "Commit":
        text = data.decode()
        header, _, message = text.partition("\n\n")
        fields: dict[str, str] = {}
        parents: list[str] = []
        for line in header.splitlines():
            key, _, val = line.partition(" ")
            if key == "parent":
                parents.append(val)
            else:
                fields[key] = val
        author = Author.from_str(fields["author"])
        committer = Author.from_str(fields["committer"])
        c = cls(
            tree_oid=fields["tree"],
            author=author,
            committer=committer,
            message=message,
            parents=parents,
        )
        return c
