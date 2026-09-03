"""Every skill in the tree is a skill the installers actually ship.

A skill directory that no manifest declares installs nowhere, and a manifest
path with no directory behind it breaks the install for everything after it.
This is not hypothetical: `assemble-paper` sat unpublished while the author's
own agent config pointed a symlink at it.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
PLUGIN = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
README = REPO_ROOT / "README.md"


def skill_directories():
    return sorted(d.name for d in SKILLS.iterdir() if (d / "SKILL.md").is_file())


def plugin():
    return json.loads(PLUGIN.read_text())


def marketplace_entry():
    (entry,) = json.loads(MARKETPLACE.read_text())["plugins"]
    return entry


class TestPluginManifest:
    def test_declares_every_skill_in_the_tree(self):
        declared = sorted(Path(path).name for path in plugin()["skills"])

        assert declared == skill_directories()

    def test_every_declared_path_exists(self):
        missing = [
            path
            for path in plugin()["skills"]
            if not (REPO_ROOT / path / "SKILL.md").is_file()
        ]

        assert missing == []


class TestMarketplace:
    def test_declares_the_plugin_the_manifest_names(self):
        assert marketplace_entry()["name"] == plugin()["name"]

    def test_describes_the_plugin_the_way_the_plugin_describes_itself(self):
        assert marketplace_entry()["description"] == plugin()["description"]


class TestReadme:
    def test_documents_every_skill_under_its_own_heading(self):
        headings = {
            line.removeprefix("### ").strip()
            for line in README.read_text().splitlines()
            if line.startswith("### ")
        }

        assert set(skill_directories()) <= headings
