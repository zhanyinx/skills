"""Test harness for the `render-paper` CLI.

The CLI is the only seam these tests use: `render-paper` is invoked as a
subprocess over a fixture paper, and the tests assert on the exit code, the
emitted document (stdout) and the verdict report (stderr). No test imports the
script or reaches into a parse tree.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
REPO_ROOT = TESTS.parent
SCRIPT = REPO_ROOT / "skills" / "render-paper" / "scripts" / "render_paper.py"
FIXTURES = TESTS / "fixtures"
GOLDEN = TESTS / "golden"


class Rendered:
    """What one `render-paper` invocation produced."""

    def __init__(self, exit_code, document, report, paper):
        self.exit_code = exit_code
        self.document = document
        self.report = report
        self.paper = paper


@pytest.fixture
def paper(tmp_path):
    """Copy a fixture paper into a temp dir and return it, so a test can give
    it one defect before rendering.

    The copy is made once per test, so a mode that writes into the source can
    be invoked twice and the second invocation sees the first one's writes.
    """

    def make(case):
        destination = tmp_path / case
        if not destination.exists():
            shutil.copytree(FIXTURES / case, destination)
        return destination

    return make


@pytest.fixture
def run_in():
    """Invoke `render-paper` inside a paper directory."""

    def run(paper, *args):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=paper,
            capture_output=True,
            text=True,
        )
        return Rendered(proc.returncode, proc.stdout, proc.stderr, paper)

    return run


@pytest.fixture
def render(paper, run_in):
    """Invoke `render-paper` over a fixture paper, as it comes."""

    def run(case, *args):
        return run_in(paper(case), *args)

    return run


@pytest.fixture
def golden():
    """Read a golden file verbatim."""

    def read(name):
        return (GOLDEN / name).read_text()

    return read


# Every setting a commit needs, supplied per invocation rather than written into
# the repository: the tests must produce the same commit whatever the machine's
# own git configuration says, and `add -f` is what keeps a global excludes file
# from quietly leaving a fixture file out of the tree the old render reads.
GIT_SETTINGS = (
    "-c",
    "user.name=render-paper tests",
    "-c",
    "user.email=tests@example.invalid",
    "-c",
    "commit.gpgsign=false",
)


@pytest.fixture
def versioned(paper):
    """A fixture paper in a git repository of its own, committed once, and the
    commit ref that first state closed at.

    The supersession diff reconstructs the old side from git, so the old side
    here is a real commit rather than a second directory on disk: the fixture
    commits the paper as drafted, and the test then revises the working tree the
    way a `revise` ticket does.
    """

    def make(case):
        root = paper(case)
        git(root, "init", "-q")
        git(root, "add", "-A", "-f")
        git(root, "commit", "-qm", "the draft ticket closed here")
        return root, git(root, "rev-parse", "HEAD").strip()

    return make


@pytest.fixture
def commit():
    """Commit a versioned paper's working tree, and return the ref it closed at.

    A second commit, for the shape where the old ref is not the first state a
    paper was ever in: a unit revised after its neighbours were already
    promoted.
    """

    def make(root, message="a later state"):
        git(root, "add", "-A", "-f")
        git(root, "commit", "-qm", message)
        return git(root, "rev-parse", "HEAD").strip()

    return make


def git(root, *args):
    """One git command inside a paper, or an assertion failure naming it."""
    proc = subprocess.run(
        ["git", "-C", str(root), *GIT_SETTINGS, *args],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, "git %s: %s" % (" ".join(args), proc.stderr)
    return proc.stdout
