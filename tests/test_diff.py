from oxide.diff.engine import diff_lines, LineOp


def test_identical() -> None:
    result = diff_lines("abc\n", "abc\n")
    assert all(l.op == LineOp.EQUAL for l in result)


def test_single_insert() -> None:
    result = diff_lines("a\n", "a\nb\n")
    ops = [l.op for l in result]
    assert LineOp.INSERT in ops


def test_single_delete() -> None:
    result = diff_lines("a\nb\n", "a\n")
    ops = [l.op for l in result]
    assert LineOp.DELETE in ops


def test_empty_old() -> None:
    result = diff_lines("", "new line\n")
    assert all(l.op == LineOp.INSERT for l in result if l.content.strip())


def test_empty_new() -> None:
    result = diff_lines("old line\n", "")
    assert all(l.op == LineOp.DELETE for l in result if l.content.strip())
