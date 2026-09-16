import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repairlam.tools.edit import apply_edit


def write(tmp, text):
    f = tmp / "T.java"
    f.write_text(text)
    return f


def test_applied(tmp_path):
    f = write(tmp_path, "int a = 1;\nint b = 2;\n")
    r = apply_edit(f, "int a = 1;", "int a = 99;")
    assert r.ok and r.status == "applied" and r.line == 1
    assert "int a = 99;" in f.read_text()


def test_not_found(tmp_path):
    f = write(tmp_path, "int a = 1;\n")
    r = apply_edit(f, "int z = 0;", "x")
    assert not r.ok and r.status == "not_found"


def test_ambiguous(tmp_path):
    f = write(tmp_path, "return null;\nreturn null;\n")
    r = apply_edit(f, "return null;", "return 0;")
    assert not r.ok and r.status == "ambiguous" and r.occurrences == 2
    assert f.read_text() == "return null;\nreturn null;\n"


def test_too_large(tmp_path):
    f = write(tmp_path, "int a = 1;\n")
    r = apply_edit(f, "int a = 1;", "\n".join(["x"] * 200))
    assert not r.ok and r.status == "too_large"


def test_no_file(tmp_path):
    r = apply_edit(tmp_path / "missing.java", "a", "b")
    assert not r.ok and r.status == "no_file"


def test_line_number(tmp_path):
    f = write(tmp_path, "a\nb\nTARGET\nd\n")
    r = apply_edit(f, "TARGET", "FIXED")
    assert r.line == 3
