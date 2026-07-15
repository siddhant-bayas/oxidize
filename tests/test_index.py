from pathlib import Path
from oxidize.index.staging import Index


def test_add_and_retrieve(tmp_path: Path) -> None:
    f = tmp_path / "hello.py"
    f.write_text("print('hi')")
    idx = Index(tmp_path / "index.json")
    idx.add("hello.py", "a" * 64, f)
    assert "hello.py" in idx
    assert idx.get("hello.py") is not None


def test_persistence(tmp_path: Path) -> None:
    f = tmp_path / "file.py"
    f.write_text("x = 1")
    idx_path = tmp_path / "index.json"
    idx = Index(idx_path)
    idx.add("file.py", "b" * 64, f)
    idx2 = Index(idx_path)
    assert "file.py" in idx2


def test_stale_detection(tmp_path: Path) -> None:
    import time

    f = tmp_path / "a.py"
    f.write_text("old")
    idx = Index(tmp_path / "index.json")
    idx.add("a.py", "c" * 64, f)
    time.sleep(0.01)
    f.write_text("new content")
    entry = idx.get("a.py")
    assert entry is not None
    assert entry.is_stale(f)
