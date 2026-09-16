"""Exercise the artifact gate in isolated Git repositories, never the checkout index."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check-generated-clean.py"
SCOPES = (
    "templates",
    "showcase",
    "examples/operational-snapshot/generated",
    "examples/custom-template-project/generated",
    "docs/assets/screenshots",
)


class GeneratedCleanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".generated-clean-test-", dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "--quiet")
        self.git("config", "user.name", "ReportKit test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.excludesFile", str(self.root / "empty-global-ignore"))
        for scope in SCOPES:
            self.write(f"{scope}/baseline.txt", "baseline\n")
        self.write("unrelated.txt", "baseline\n")
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "test baseline")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True, capture_output=True, text=True,
        ).stdout

    def write(self, relative, text):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def check(self, expected):
        before = self.git("status", "--porcelain", "--untracked-files=all")
        result = subprocess.run(
            [sys.executable, "-B", str(CHECKER), "--root", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        self.assertEqual(before, self.git("status", "--porcelain", "--untracked-files=all"))
        return result

    def test_clean_checkout_passes(self):
        self.check(0)

    def test_unrelated_tracked_and_untracked_changes_are_allowed(self):
        self.write("unrelated.txt", "modified\n")
        self.write("docs/notes.txt", "untracked\n")
        self.write("showcase-other/not-generated.txt", "untracked\n")
        self.git("add", "unrelated.txt")
        self.check(0)

    def test_untracked_nested_output_is_rejected_in_every_scope(self):
        for scope in SCOPES:
            with self.subTest(scope=scope):
                relative = f"{scope}/new nested/page with spaces.html"
                self.write(relative, "unexpected\n")
                result = self.check(1)
                self.assertIn("page with spaces.html", result.stderr)
                (self.root / relative).unlink()

    def test_tracked_modification_is_rejected(self):
        self.write("showcase/baseline.txt", "changed\n")
        self.check(1)

    def test_tracked_deletion_is_rejected(self):
        (self.root / "templates/baseline.txt").unlink()
        self.check(1)

    def test_staged_modification_is_rejected(self):
        self.write("docs/assets/screenshots/baseline.txt", "changed\n")
        self.git("add", "docs/assets/screenshots/baseline.txt")
        self.check(1)

    def test_staged_new_output_is_rejected(self):
        self.write("showcase/new.html", "new\n")
        self.git("add", "showcase/new.html")
        self.check(1)

    def test_staged_rename_out_of_scope_is_rejected(self):
        self.git("mv", "templates/baseline.txt", "moved.txt")
        self.check(1)

    def test_non_repository_root_fails_closed(self):
        result = subprocess.run(
            [sys.executable, "-B", str(CHECKER), "--root", str(self.root / "showcase")],
            capture_output=True, text=True,
        )
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
