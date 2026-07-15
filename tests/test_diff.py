from oxidize.diff.engine import diff_lines, LineOp


def test_identical() -> None:
    result = diff_lines("abc\n", "abc\n")
    assert all(dl.op == LineOp.EQUAL for dl in result)


def test_single_insert() -> None:
    result = diff_lines("a\n", "a\nb\n")
    ops = [dl.op for dl in result]
    assert LineOp.INSERT in ops


def test_single_delete() -> None:
    result = diff_lines("a\nb\n", "a\n")
    ops = [dl.op for dl in result]
    assert LineOp.DELETE in ops


def test_empty_old() -> None:
    result = diff_lines("", "new line\n")
    assert all(dl.op == LineOp.INSERT for dl in result if dl.content.strip())


def test_empty_new() -> None:
    result = diff_lines("old line\n", "")
    assert all(dl.op == LineOp.DELETE for dl in result if dl.content.strip())
