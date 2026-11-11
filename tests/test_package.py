"""Ensure install bundles contain library files but no private session archives."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package", ROOT / "scripts" / "package.py")
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)


class PackageTests(unittest.TestCase):
    def test_allowlisted_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "kouyu.zip"
            path, count = pkg.package(output)
            self.assertEqual(path, output)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertEqual(count, len(names))
                for name in ("kouyu/SKILL.md", "kouyu/scripts/business.py", "kouyu/curriculum/business/index.json", "kouyu/curriculum/business/catalog.md", "kouyu/curriculum/business/industries.json", "kouyu/assets/workbench/app.js", "kouyu/tests/browser_smoke.mjs", "kouyu/docs/screenshots/business-review.png"):
                    self.assertIn(name, names)
                self.assertEqual(len([name for name in names if "/business/scenarios/" in name and name.endswith(".json")]), 28)
                self.assertEqual(len([name for name in names if "/interview/scenes/" in name and name.endswith(".json")]), 18)
                for name in ("kouyu/scripts/interview.py", "kouyu/curriculum/interview/index.json", "kouyu/curriculum/interview/catalog.md", "kouyu/curriculum/interview/concepts.json", "kouyu/references/technical-interview.md"):
                    self.assertIn(name, names)
                self.assertFalse(any("__pycache__" in name or "workbench-data.json" in name or "/sessions/" in name or "/web3-go/" in name for name in names))
            with self.assertRaisesRegex(ValueError, "already exists"):
                pkg.package(output)

    def test_installed_interview_works_without_raw_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "kouyu.zip"
            pkg.package(output)
            with zipfile.ZipFile(output) as archive:
                archive.extractall(Path(temp) / "installed")
            installed = Path(temp) / "installed" / "kouyu"
            self.assertFalse((installed / "web3-go").exists())
            script = installed / "scripts" / "interview.py"
            for args in (("validate",), ("show", "int-web3-broadcast-timeout", "--coach", "--depth", "system"), ("review", "--data-dir", str(Path(temp) / "missing-archive"))):
                result = subprocess.run([sys.executable, "-I", "-B", str(script), *args], cwd=temp, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                if args[0] == "validate":
                    self.assertFalse(payload["source_files_checked"])
                if args[0] == "show":
                    self.assertTrue(payload["coach_only"]["reference_answer"])
            self.assertFalse((Path(temp) / "missing-archive").exists())
            data_dir = Path(temp) / "synthetic-installed-archive"
            archived = subprocess.run([sys.executable, "-I", "-B", str(installed / "scripts/workbench.py"), "archive", "--data-dir", str(data_dir), "--input", str(installed / "tests/fixtures/interview-session.json")], cwd=temp, text=True, capture_output=True)
            self.assertEqual(archived.returncode, 0, archived.stderr)
            reviewed = subprocess.run([sys.executable, "-I", "-B", str(script), "review", "--data-dir", str(data_dir), "--concept", "timeout-semantics"], cwd=temp, text=True, capture_output=True)
            self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
            result = json.loads(reviewed.stdout)
            self.assertEqual(result["observations"][0]["concept_id"], "timeout-semantics")
            self.assertTrue(result["drills"][0]["transfer"]["prompt"])


if __name__ == "__main__":
    unittest.main()
