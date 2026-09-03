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
