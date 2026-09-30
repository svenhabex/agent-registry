import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync  # noqa: E402


def make_skill(path, body="skill", requires=None):
    path.mkdir(parents=True)
    if requires:
        body = f"---\nname: {path.name}\nmetadata:\n  requires: {requires}\n---\n{body}"
    (path / "SKILL.md").write_text(body)


class SyncTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.home = self.root / "home"
        self.registry = self.root / "registry"
        self.project = self.root / "project"
        for d in (self.home, self.project):
            d.mkdir()

        env = mock.patch.dict(os.environ, {"HOME": str(self.home), "AGENT_REGISTRY": str(self.registry)})
        env.start()
        self.addCleanup(env.stop)

        cwd = os.getcwd()
        os.chdir(self.project)
        self.addCleanup(os.chdir, cwd)

    def run_cmd(self, *argv):
        with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
            sync.main(list(argv))


class InitGlobalTest(SyncTestCase):
    def test_creates_registry_and_links(self):
        self.run_cmd("init-global")

        self.assertEqual((self.registry / "instructions" / "CLAUDE.md").read_text(), "@~/.agents/AGENTS.md\n")
        self.assertEqual((self.registry / "instructions" / "AGENTS.md").read_text(), "")
        self.assertTrue((self.registry / "skills" / "coding-styles").is_dir())
        expected = {
            ".claude/CLAUDE.md": "instructions/CLAUDE.md",
            ".claude/skills": "skills/global",
            ".agents/AGENTS.md": "instructions/AGENTS.md",
            ".agents/skills": "skills/global",
            ".codex/AGENTS.md": "instructions/AGENTS.md",
        }
        for link, target in expected.items():
            path = self.home / link
            self.assertTrue(path.is_symlink(), link)
            self.assertEqual(path.resolve(), self.registry / target)

        command = self.home / ".local" / "bin" / "agent-registry"
        self.assertEqual(command.resolve(), Path(sync.__file__).resolve())
        self.assertTrue(os.access(command, os.X_OK))

    def test_backs_up_and_migrates_existing_skills(self):
        make_skill(self.home / ".agents" / "skills" / "grill-me")
        (self.home / ".claude" / "skills" / "synced" / "x").mkdir(parents=True)

        self.run_cmd("init-global")

        self.assertTrue((self.registry / "skills" / "global" / "grill-me" / "SKILL.md").is_file())
        self.assertFalse((self.registry / "skills" / "global" / "synced").exists())
        backups = list((self.home / ".claude").glob("skills.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "synced" / "x").is_dir())
        self.assertEqual(len(list((self.home / ".agents").glob("skills.bak-*"))), 1)

    def test_is_idempotent(self):
        self.run_cmd("init-global")
        self.run_cmd("init-global")
        self.assertEqual(list(self.home.glob("**/*.bak-*")), [])

    def test_dry_run_changes_nothing(self):
        self.run_cmd("init-global", "--dry-run")
        self.assertFalse(self.registry.exists())
        self.assertEqual(list(self.home.iterdir()), [])


class InitProjectTest(SyncTestCase):
    def test_creates_relative_symlink(self):
        self.run_cmd("init-project")

        link = self.project / ".claude" / "skills"
        self.assertEqual(os.readlink(link), os.path.join("..", ".agents", "skills"))
        self.assertEqual(link.resolve(), self.project / ".agents" / "skills")
        self.assertEqual((self.project / "AGENTS.md").read_text(), "")
        self.assertEqual((self.project / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertFalse((self.project / ".claude" / "CLAUDE.md").exists())

    def test_moves_existing_claude_skills(self):
        make_skill(self.project / ".claude" / "skills" / "local")
        self.run_cmd("init-project")
        self.assertTrue((self.project / ".agents" / "skills" / "local" / "SKILL.md").is_file())
        self.assertTrue((self.project / ".claude" / "skills").is_symlink())


class InstallTest(SyncTestCase):
    def setUp(self):
        super().setUp()
        make_skill(self.registry / "skills" / "coding-styles" / "angular")
        make_skill(self.registry / "skills" / "coding-styles" / "react")
        (self.registry / "skills" / "coding-styles" / ".gitkeep").touch()
        self.run_cmd("init-project")
        self.skills = self.project / ".agents" / "skills"

    def test_install_category(self):
        self.run_cmd("install", "coding-styles")
        self.assertEqual(sorted(p.name for p in self.skills.iterdir()), ["angular", "react"])

    def test_install_single_skill(self):
        self.run_cmd("install", "coding-styles/angular")
        self.assertEqual([p.name for p in self.skills.iterdir()], ["angular"])
        self.assertFalse((self.skills / "angular").is_symlink())

    def test_missing_path_fails(self):
        with self.assertRaises(SystemExit):
            self.run_cmd("install", "nope")

    def test_path_escape_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_cmd("install", "../instructions")

    def test_existing_requires_force(self):
        self.run_cmd("install", "coding-styles/angular")
        (self.skills / "angular" / "SKILL.md").write_text("local edit")
        self.run_cmd("install", "coding-styles")
        self.assertEqual((self.skills / "angular" / "SKILL.md").read_text(), "local edit")
        self.assertTrue((self.skills / "react").is_dir())
        self.run_cmd("install", "coding-styles", "--force")
        self.assertEqual((self.skills / "angular" / "SKILL.md").read_text(), "skill")

    def test_installs_dependencies_across_categories(self):
        skills = self.registry / "skills"
        make_skill(skills / "planning" / "grill-me", requires="grilling setup")
        make_skill(skills / "planning" / "grilling", requires="domain-modeling")
        make_skill(skills / "engineering" / "domain-modeling")
        make_skill(skills / "global" / "setup")

        self.run_cmd("install", "planning/grill-me")

        installed = sorted(p.name for p in self.skills.iterdir())
        self.assertEqual(installed, ["domain-modeling", "grill-me", "grilling"])

    def test_keeps_installed_dependency(self):
        skills = self.registry / "skills"
        make_skill(skills / "planning" / "grill-me", requires="grilling")
        make_skill(skills / "planning" / "grilling")
        make_skill(self.skills / "grilling", "local edit")

        self.run_cmd("install", "planning/grill-me")

        self.assertEqual((self.skills / "grilling" / "SKILL.md").read_text(), "local edit")

    def test_requires_init_project(self):
        os.chdir(self.root)
        with self.assertRaises(SystemExit):
            self.run_cmd("install", "coding-styles")


class PublishTest(SyncTestCase):
    def setUp(self):
        super().setUp()
        self.run_cmd("init-project")
        self.local = self.project / ".agents" / "skills" / "mine"
        make_skill(self.local, "mine")
        self.published = self.registry / "skills" / "ai-workflows" / "mine"

    def test_publish_keeps_local_copy(self):
        self.run_cmd("publish", "mine", "ai-workflows")
        self.assertEqual((self.published / "SKILL.md").read_text(), "mine")
        self.assertFalse(self.local.is_symlink())
        self.assertTrue((self.local / "SKILL.md").is_file())

    def test_publish_link(self):
        self.run_cmd("publish", "mine", "ai-workflows", "--link")
        self.assertTrue(self.local.is_symlink())
        self.assertEqual(self.local.resolve(), self.published)

    def test_existing_requires_force(self):
        self.run_cmd("publish", "mine", "ai-workflows")
        with self.assertRaises(SystemExit):
            self.run_cmd("publish", "mine", "ai-workflows")
        self.run_cmd("publish", "mine", "ai-workflows", "--force")

    def test_missing_skill_fails(self):
        with self.assertRaises(SystemExit):
            self.run_cmd("publish", "ghost", "ai-workflows")

    def test_already_linked_fails(self):
        self.run_cmd("publish", "mine", "ai-workflows", "--link")
        with self.assertRaises(SystemExit):
            self.run_cmd("publish", "mine", "other")


if __name__ == "__main__":
    unittest.main()
