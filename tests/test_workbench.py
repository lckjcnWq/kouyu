"""Zero-dependency regression tests; all archives use isolated temporary folders."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workbench", ROOT / "scripts" / "workbench.py")
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def fixture(name="business-session"):
    return json.loads((ROOT / "tests" / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "archive"

    def archive(self, session):
        source = self.root / "input.json"
        source.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
        wb.archive_session(self.data, source)

    def test_legacy_and_business_roundtrip(self):
        old, new = fixture("legacy-session"), fixture()
        self.archive(old)
        self.archive(new)
        state = wb.load_state(self.data)
        self.assertEqual(state["version"], 2)
        self.assertEqual(state["sessions"], [old, new])
        self.assertNotIn("domain", state["sessions"][0])
        report = (self.data / "复习台.md").read_text(encoding="utf-8")
        for expected in ("未分类", "商务英语", "待确认", "授权", "证据", "软件"):
            self.assertIn(expected, report)
        self.assertEqual(json.loads((self.data / "sessions" / f"{new['id']}.json").read_text()), new)

    def test_unknown_top_level_fields_roundtrip_unchanged(self):
        session = fixture()
        session["future_extension"] = {"nested": [False, None, {"text": "<preserve>"}]}
        wb.atomic_json(self.data / "workbench-data.json", {"version": 2, "sessions": [], "future_state": {"enabled": True}})
        self.archive(session)
        state = wb.load_state(self.data)
        self.assertEqual(state["future_state"], {"enabled": True})
        self.assertEqual(state["sessions"], [session])
        self.assertEqual(json.loads((self.data / "sessions" / f"{session['id']}.json").read_text()), session)

    def test_version_one_container_preserved(self):
        self.data.mkdir()
        old = fixture("legacy-session")
        wb.atomic_json(self.data / "workbench-data.json", {"version": 1, "sessions": [old]})
        self.assertEqual(wb.load_state(self.data)["version"], 1)
        wb.init_workbench(self.data)
        state = wb.load_state(self.data)
        self.assertEqual(state["version"], 2)
        self.assertEqual(state["sessions"], [old])

    def test_idempotent_and_conflicting_ids(self):
        session = fixture()
        self.archive(session)
        self.archive(session)
        self.assertEqual(len(wb.load_state(self.data)["sessions"]), 1)
        changed = copy.deepcopy(session)
        changed["topic"]["label"] = "different"
        with self.assertRaisesRegex(ValueError, "different data"):
            self.archive(changed)
        self.assertEqual(wb.load_state(self.data)["sessions"], [session])

    def test_conflicting_individual_file_is_protected(self):
        session = fixture()
        path = self.data / "sessions" / f"{session['id']}.json"
        wb.atomic_json(path, {"unrelated": "must not overwrite"})
        with self.assertRaisesRegex(ValueError, "file conflicts"):
            self.archive(session)
        self.assertEqual(json.loads(path.read_text()), {"unrelated": "must not overwrite"})

    def test_future_version_refused_without_overwrite(self):
        path = self.data / "workbench-data.json"
        wb.atomic_json(path, {"version": 99, "sessions": []})
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "unsupported"):
            wb.init_workbench(self.data)
        self.assertEqual(path.read_bytes(), before)

    def test_cli_from_unrelated_directory(self):
        result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "workbench.py"), "init", "--data-dir", str(self.data)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.data / "复习台.md").exists())


class ValidationTests(unittest.TestCase):
    def test_optional_business_fields(self):
        session = fixture()
        session["business"] = {}
        wb.validate_session(session)
        session.pop("scenario")
        wb.validate_session(session)

    def test_invalid_records(self):
        cases = [
            ("duration_minutes", True), ("duration_minutes", float("nan")),
            ("duration_minutes", 0), ("duration_minutes", 241),
            ("id", "../escape"), ("id", 12), ("created_at", None),
            ("domain", "commercial"), ("domain", []),
            ("level", []), ("hint_mode", "easy"), ("targets", None),
            ("business", []), ("scenario", {"id": "x"}),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                session = fixture()
                session[field] = value
                with self.assertRaises(ValueError):
                    wb.validate_session(session)

    def test_business_evidence_required_only_when_observed(self):
        session = fixture()
        session["business"]["criteria"][0].pop("evidence")
        with self.assertRaisesRegex(ValueError, "evidence"):
            wb.validate_session(session)
        session["business"]["criteria"][0]["status"] = "not_observed"
        wb.validate_session(session)

    def test_feedback_unique_valid_and_evidenced(self):
        for key, value in (("dimension", "sales-won"), ("dimension", []), ("evidence", ""), ("suggestion", None)):
            with self.subTest(key=key):
                session = fixture()
                session["business"]["feedback"][0][key] = value
                with self.assertRaises(ValueError):
                    wb.validate_session(session)
        session = fixture()
        session["business"]["feedback"].append(session["business"]["feedback"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            wb.validate_session(session)

    def test_business_requires_explicit_domain(self):
        session = fixture()
        session.pop("domain")
        with self.assertRaisesRegex(ValueError, "requires domain"):
            wb.validate_session(session)

    def test_duplicate_session_ids_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate session"):
            wb.validate_state({"version": 2, "sessions": [fixture(), fixture()]})


class AggregationTests(unittest.TestCase):
    def test_same_phrase_different_scenes_is_not_global_mastery(self):
        targets = wb.latest_targets([fixture("legacy-session"), fixture()])
        shared = [item for item in targets if item["expression"] == "Could you clarify that?"]
        self.assertEqual(len(shared), 2)
        self.assertEqual({item["status"] for item in shared}, {"mastered", "needs_review"})

    def test_new_unobserved_does_not_erase_evidence(self):
        old = fixture()
        new = copy.deepcopy(old)
        new["id"] = "newer"
        new["created_at"] = "2026-11-12T10:00:00+08:00"
        new["targets"][0]["status"] = "not_observed"
        targets = wb.latest_targets([old, new])
        self.assertEqual(targets[0]["status"], "needs_review")
        new["targets"][0]["status"] = "mastered"
        self.assertEqual(wb.latest_targets([old, new])[0]["status"], "mastered")

    def test_never_observed_keeps_newest_unobserved_record(self):
        old = fixture()
        for target in old["targets"]:
            target["status"] = "not_observed"
        new = copy.deepcopy(old)
        new["id"] = "new-unobserved"
        new["created_at"] = "2026-11-12T10:00:00+08:00"
        new["targets"][0]["evidence"] = "Synthetic newest unobserved note"
        self.assertEqual(wb.latest_targets([old, new])[0]["evidence"], "Synthetic newest unobserved note")

    def test_timestamp_offsets_sort_by_actual_instant(self):
        old = fixture()
        old["created_at"] = "2026-11-11T10:00:00+08:00"
        new = copy.deepcopy(old)
        new["id"] = "utc-newer"
        new["created_at"] = "2026-11-11T03:00:00+00:00"
        new["targets"][0]["status"] = "mastered"
        self.assertEqual(wb.latest_targets([old, new])[0]["status"], "mastered")

    def test_identity_not_display_label(self):
        old = fixture()
        renamed = copy.deepcopy(old)
        renamed["id"] = "renamed"
        renamed["topic"]["label"] = "换一个显示名字"
        renamed["created_at"] = "2026-11-12T10:00:00+08:00"
        report = wb.render_dashboard({"sessions": [old, renamed]})
        self.assertEqual(report.count("\n## "), 1)
        self.assertIn("练习次数：2", report)

    def test_same_label_different_id_kept_separate(self):
        a, b = fixture(), fixture()
        b["id"] = "second"
        b["scenario"]["id"] = "different-scene"
        self.assertEqual(wb.render_dashboard({"sessions": [a, b]}).count("\n## "), 2)

    def test_unobserved_is_not_failure(self):
        session = fixture()
        for target in session["targets"]:
            target["status"] = "not_observed"
        report = wb.render_dashboard({"sessions": [session]})
        self.assertIn("无可评估表达", report)
        self.assertIn("未观察表达：3", report)

    def test_markdown_html_and_links_escaped(self):
        session = fixture()
        session["topic"]["label"] = '<script>alert(1)</script> [click](https://example.invalid)'
        report = wb.render_dashboard({"sessions": [session]})
        self.assertNotIn("<script>", report)
        self.assertNotIn("[click](", report)
        self.assertIn("&lt;script&gt;", report)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.temp.name)
        wb.init_workbench(cls.data)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), wb.make_handler(cls.data, ROOT / "assets" / "workbench"))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def get(self, path):
        with urlopen(self.url + path, timeout=3) as response:
            return response.read().decode(), response.headers

    def test_health_and_state(self):
        body, _ = self.get("/api/health")
        self.assertEqual(json.loads(body), {"ok": True, "version": 2})
        body, headers = self.get("/api/state")
        self.assertEqual(json.loads(body)["sessions"], [])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_static_files(self):
        for path, needle in (("/", "<!doctype html>"), ("/app.js", "function"), ("/styles.css", ":root")):
            body, _ = self.get(path)
            self.assertIn(needle, body)

    def test_cross_origin_preferences_write_refused(self):
        request = Request(self.url + "/api/preferences", data=b"{}", method="PUT", headers={"Origin": "https://example.invalid"})
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=3)
        self.assertEqual(context.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
