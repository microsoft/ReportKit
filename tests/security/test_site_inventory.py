"""Synthetic, local-only tests for the metadata-only site inventory."""

from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from site_inventory import inspect_site_inventory  # noqa: E402


class SiteInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = ROOT / f".i-{uuid.uuid4().hex[:12]}"
        self.workspace.mkdir()
        self.addCleanup(shutil.rmtree, self.workspace)
        self.site = self.workspace / "site"
        self.site.mkdir()

    def create_file(self, name: str, content: str = "synthetic") -> Path:
        path = self.site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def assert_error(self, code: str, relative: str) -> None:
        _, errors = inspect_site_inventory(self.site)
        self.assertTrue(any(error["code"] == code and error["path"] == relative for error in errors), errors)
        self.assertTrue(all(set(error) == {"code", "message", "path"} for error in errors))

    def symlink(self, target: Path, link: Path, directory: bool = False) -> None:
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                self.skipTest("Windows symlink privilege is unavailable.")
            raise

    def test_all_static_suffixes_and_uppercase_html_are_inventory_only(self) -> None:
        names = [
            "index.HTML", "child.HTM", "nested/styles.CSS", "nested/image.SVG",
            "report-manifest.json", ".reportkit-output.json",
            "a.PNG", "b.JPG", "c.JPEG", "d.GIF", "e.WEBP", "f.ICO",
        ]
        for name in names:
            self.create_file(name, "<script>synthetic active content</script>")
        with patch.object(Path, "open", side_effect=AssertionError("Inventory must not open contents")):
            files, errors = inspect_site_inventory(self.site)
        self.assertEqual([], errors)
        self.assertEqual(sorted(names), [path.relative_to(self.site).as_posix() for path in files])

    def test_unknown_active_executable_and_archive_files_fail_regardless_of_manifest(self) -> None:
        names = ["a.EXE", "b.zip", "c.js", "d.mjs", "e.dll", "f.tar.gz", "g.txt", "h", "i.html.exe"]
        for name in names:
            self.create_file(name)
        for declared in [[], names]:
            with self.subTest(declared=bool(declared)):
                self.create_file("report-manifest.json", json.dumps({"files": declared}))
                files, errors = inspect_site_inventory(self.site)
                self.assertEqual(names, [error["path"] for error in errors])
                self.assertEqual({"site-file-type"}, {error["code"] for error in errors})
                self.assertEqual(len(names) + 1, len(files))

    def test_nested_and_dangling_file_and_directory_links_are_never_followed(self) -> None:
        outside = self.workspace / "outside"
        outside.mkdir()
        (outside / "hidden.EXE").write_text("synthetic", encoding="utf-8")
        nested = self.site / "nested"
        nested.mkdir()
        self.symlink(outside, nested / "linked-directory", directory=True)
        self.symlink(outside / "hidden.EXE", nested / "linked-file.html")
        self.symlink(outside / "missing-directory", nested / "dangling-directory", directory=True)
        self.symlink(outside / "missing.html", nested / "dangling.html")
        original_scandir = os.scandir
        scanned = []

        def scan(path):
            scanned.append(path)
            self.assertIn(path, [self.site, nested])
            return original_scandir(path)

        with patch("site_inventory.os.scandir", side_effect=scan):
            files, errors = inspect_site_inventory(self.site)
        self.assertEqual([], files)
        self.assertEqual(4, len(errors))
        self.assertEqual({"site-link-redirection"}, {error["code"] for error in errors})
        self.assertEqual([self.site, nested], scanned)
        self.assertTrue(all(error["path"].startswith("nested/") for error in errors))

    def test_root_link_is_rejected_without_enumeration(self) -> None:
        link = self.workspace / "root-link"
        self.symlink(self.site, link, directory=True)
        with patch("site_inventory.os.scandir", side_effect=AssertionError("Must not follow root")):
            files, errors = inspect_site_inventory(link)
        self.assertEqual([], files)
        self.assertEqual("site-link-redirection", errors[0]["code"])
        self.assertEqual(".", errors[0]["path"])

    def test_windows_reparse_attribute_rejected_without_enumeration(self) -> None:
        entry = self.site / "reparse"
        entry.mkdir()
        original_lstat = Path.lstat

        def lstat(path):
            if path == entry:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return original_lstat(path)

        with patch.object(Path, "lstat", lstat):
            self.assert_error("site-link-redirection", "reparse")

    @unittest.skipUnless(os.name == "nt", "Windows junction test.")
    def test_windows_junction_is_rejected_without_following(self) -> None:
        outside = self.workspace / "outside"
        outside.mkdir()
        (outside / "hidden.EXE").write_text("synthetic", encoding="utf-8")
        junction = self.site / "junction"
        result = subprocess.run(
            [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "mklink", "/J", str(junction), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.addCleanup(junction.rmdir)
        original_scandir = os.scandir

        def scan(path):
            self.assertEqual(self.site, path)
            return original_scandir(path)

        with patch("site_inventory.os.scandir", side_effect=scan):
            files, errors = inspect_site_inventory(self.site)
        self.assertEqual([], files)
        self.assertEqual([("site-link-redirection", "junction")], [(error["code"], error["path"]) for error in errors])
        self.assertTrue((outside / "hidden.EXE").is_file())

    @unittest.skipIf(os.name == "nt", "POSIX FIFO is unavailable on Windows.")
    def test_fifo_is_rejected_without_opening(self) -> None:
        os.mkfifo(self.site / "pipe.html")
        with patch.object(Path, "open", side_effect=AssertionError("Must not open FIFO")):
            self.assert_error("site-entry-type", "pipe.html")

    @unittest.skipIf(os.name == "nt", "POSIX filesystem socket test.")
    def test_socket_is_rejected_without_opening(self) -> None:
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(self.site / "socket.html"))
            self.assert_error("site-entry-type", "socket.html")

    def test_special_file_modes_rejected_on_all_platforms(self) -> None:
        entry = self.create_file("special.html")
        original_lstat = Path.lstat
        for mode in [stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK]:
            with self.subTest(mode=mode):
                def lstat(path):
                    if path == entry:
                        return SimpleNamespace(st_mode=mode, st_file_attributes=0)
                    return original_lstat(path)

                with patch.object(Path, "lstat", lstat):
                    self.assert_error("site-entry-type", "special.html")

    def test_lstat_permission_missing_and_other_io_errors_are_structured(self) -> None:
        entry = self.create_file("nested/blocked.html")
        original_lstat = Path.lstat
        for failure in [PermissionError("denied"), FileNotFoundError("gone"), OSError("I/O"), ValueError("bad path")]:
            with self.subTest(failure=type(failure).__name__):
                def lstat(path):
                    if path == entry:
                        raise failure
                    return original_lstat(path)

                with patch.object(Path, "lstat", lstat):
                    self.assert_error("site-inventory-io", "nested/blocked.html")

    def test_scandir_permission_errors_are_structured_and_siblings_continue(self) -> None:
        blocked = self.site / "blocked"
        blocked.mkdir()
        self.create_file("sibling.EXE")
        original_scandir = os.scandir

        def scan(path):
            if path == blocked:
                raise PermissionError("denied")
            return original_scandir(path)

        with patch("site_inventory.os.scandir", side_effect=scan):
            _, errors = inspect_site_inventory(self.site)
        self.assertEqual(
            [("site-inventory-io", "blocked"), ("site-file-type", "sibling.EXE")],
            [(error["code"], error["path"]) for error in errors],
        )

    def test_scandir_iteration_errors_are_structured(self) -> None:
        class BrokenScan:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def __iter__(self):
                raise OSError("iteration failure")

        with patch("site_inventory.os.scandir", return_value=BrokenScan()):
            self.assert_error("site-inventory-io", ".")

    def test_root_aliases_rejected_before_filesystem_access(self) -> None:
        for name in ["site.", "site ", "CON", "nul.html", "LPT1.txt", "COM¹.json", "bad\x00name"]:
            with self.subTest(name=name), patch.object(Path, "lstat", side_effect=AssertionError("Alias must not be accessed")):
                files, errors = inspect_site_inventory(self.workspace / name)
                self.assertEqual([], files)
                self.assertEqual([("site-path-alias", ".")], [(error["code"], error["path"]) for error in errors])

    @unittest.skipIf(os.name == "nt", "Windows aliases cannot be created as ordinary paths.")
    def test_unsafe_child_names_are_rejected(self) -> None:
        names = ["CON.html", "child.html.", "child.html ", "drive:stream.html", "back\\slash.html"]
        for name in names:
            self.create_file(name)
        _, errors = inspect_site_inventory(self.site)
        self.assertEqual(sorted(names), [error["path"] for error in errors])
        self.assertEqual({"site-path-alias"}, {error["code"] for error in errors})

    def test_every_normal_entry_is_lstat_inspected(self) -> None:
        leaf = self.create_file("nested/index.html")
        original_lstat = Path.lstat
        inspected = []

        def lstat(path):
            inspected.append(path)
            return original_lstat(path)

        with patch.object(Path, "lstat", lstat):
            files, errors = inspect_site_inventory(self.site)
        self.assertEqual([], errors)
        self.assertEqual([leaf], files)
        self.assertEqual([self.site, leaf.parent, leaf], inspected)

    def test_missing_and_non_directory_roots_fail(self) -> None:
        _, errors = inspect_site_inventory(self.workspace / "missing")
        self.assertEqual("site-inventory-io", errors[0]["code"])
        root_file = self.create_file("root.html")
        _, errors = inspect_site_inventory(root_file)
        self.assertEqual("site-root-type", errors[0]["code"])


if __name__ == "__main__":
    unittest.main()
