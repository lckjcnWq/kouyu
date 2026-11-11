"""Technical archive contract regression tests; records are synthetic and temporary."""

import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("interview_archive_workbench", ROOT / "scripts" / "workbench.py")
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def fixture(name="interview-session"):
    return json.loads((ROOT / "tests" / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


def attempt(session_id="synthetic-interview-newer", created_at="2026-11-12T11:00:00+08:00", **metadata):
    session = fixture()
    session["id"] = session_id
    session["created_at"] = created_at
    session["interview"].update(metadata)
    return session


class InterviewValidationTests(unittest.TestCase):
    def test_fixture_is_synthetic_and_uses_real_scene_identity(self):
        session = fixture()
        self.assertTrue(session["synthetic"])
        self.assertTrue(session["id"].startswith("synthetic"))
        self.assertEqual(session["domain"], "business")
        self.assertEqual(session["scenario"]["category_id"], "hiring")
        self.assertEqual(session["scenario"]["id"], "int-web3-broadcast-timeout")
        self.assertEqual(session["interview"]["track"]["id"], "web3")
        wb.validate_session(session)

    def test_optional_extension_does_not_change_old_sessions(self):
        for name in ("legacy-session", "business-session"):
            session = fixture(name)
            before = copy.deepcopy(session)
            wb.validate_session(session)
            self.assertEqual(session, before)
            self.assertNotIn("interview", session)

    def test_interview_requires_business_and_nonempty_safe_scenario(self):
        for field, value in (("domain", "everyday"), ("domain", None), ("scenario", None),
                             ("scenario", {}), ("scenario", {"id": "", "category_id": "hiring", "category_label": "Hiring"})):
            with self.subTest(field=field, value=value):
                session = fixture()
                if value is None:
                    session.pop(field)
                else:
                    session[field] = value
                with self.assertRaises(ValueError):
                    wb.validate_session(session)
        session = fixture()
        session["scenario"]["id"] = "../int-web3-broadcast-timeout"
        with self.assertRaisesRegex(ValueError, "slug"):
            wb.validate_session(session)

    def test_all_interview_metadata_required(self):
        for field in ("track", "role", "depth", "pressure", "question_ids", "observations"):
            with self.subTest(field=field):
                session = fixture()
                session["interview"].pop(field)
                with self.assertRaises(ValueError):
                    wb.validate_session(session)

    def test_invalid_metadata_and_observation_values(self):
        cases = [
            (("interview",), None), (("interview", "track"), []),
            (("interview", "track", "id"), "../web3"), (("interview", "track", "id"), "Web3"),
            (("interview", "track", "label"), " "), (("interview", "role"), "coach"),
            (("interview", "role"), []), (("interview", "depth"), "advanced"),
            (("interview", "pressure"), "extreme"), (("interview", "question_ids"), "broadcast-anchor"),
            (("interview", "question_ids"), [""]), (("interview", "question_ids"), ["q/1"]),
            (("interview", "observations"), {}), (("interview", "observations"), [None]),
            (("interview", "observations", 0, "concept_id"), "state_authority"),
            (("interview", "observations", 0, "concept_id"), "<script>"),
            (("interview", "observations", 0, "label"), ""),
            (("interview", "observations", 0, "status"), "mastered"),
            (("interview", "observations", 0, "language_support"), "independent"),
            (("interview", "observations", 0, "technical_support"), "keyword"),
            (("interview", "observations", 0, "question_id"), "unknown-question"),
        ]
        for keys, value in cases:
            with self.subTest(keys=keys, value=value):
                session = fixture()
                parent = session
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                with self.assertRaises(ValueError):
                    wb.validate_session(session)

    def test_observed_requires_evidence_observation_and_suggestion(self):
        for status in ("met", "partial", "unmet"):
            for field in ("evidence", "observation", "suggestion", "language_support", "technical_support", "question_id", "concept_id", "label"):
                for value in (None, "", " \n ", [], 1):
                    with self.subTest(status=status, field=field, value=value):
                        session = fixture()
                        item = session["interview"]["observations"][0]
                        item["status"] = status
                        if value is None:
                            item.pop(field)
                        else:
                            item[field] = value
                        with self.assertRaises(ValueError):
                            wb.validate_session(session)

    def test_unobserved_has_no_hints_or_invented_text(self):
        session = fixture()
        item = session["interview"]["observations"][-1]
        wb.validate_session(session)
        for field in ("evidence", "observation", "suggestion"):
            item[field] = ""
        wb.validate_session(session)
        for field, values in (("language_support", ["intent", "keyword", "model"]),
                              ("technical_support", ["probe", "hint", "solution"]),
                              ("evidence", ["Synthetic invented evidence", None]),
                              ("observation", ["Synthetic invented observation"]),
                              ("suggestion", ["Synthetic invented suggestion"])):
            for value in values:
                with self.subTest(field=field, value=value):
                    invalid = copy.deepcopy(session)
                    invalid["interview"]["observations"][-1][field] = value
                    with self.assertRaises(ValueError):
                        wb.validate_session(invalid)

    def test_questions_are_unique_and_owned_and_concepts_not_duplicated(self):
        session = fixture()
        session["interview"]["question_ids"].append("broadcast-anchor")
        with self.assertRaisesRegex(ValueError, "duplicate.*question"):
            wb.validate_session(session)
        session = fixture()
        session["interview"]["question_ids"].remove("broadcast-anchor")
        with self.assertRaisesRegex(ValueError, "question_id"):
            wb.validate_session(session)
        session = fixture()
        repeated = copy.deepcopy(session["interview"]["observations"][0])
        repeated["question_id"] = "broadcast-unknown"
        session["interview"]["observations"].append(repeated)
        with self.assertRaisesRegex(ValueError, "duplicate.*concept"):
            wb.validate_session(session)

    def test_custom_ids_and_empty_observations_supported_without_curriculum_lookup(self):
        session = fixture()
        session["scenario"]["id"] = "int-custom-future-scene"
        session["interview"]["track"]["id"] = "future-track"
        session["interview"]["observations"][0]["concept_id"] = "custom-future-concept"
        wb.validate_session(session)
        session["interview"]["observations"] = []
        session["interview"]["question_ids"] = []
        wb.validate_session(session)
        self.assertEqual(wb.latest_technical([session]), [])
        self.assertIn("本次未记录技术观察", wb.render_dashboard({"sessions": [session]}))


class InterviewAggregationTests(unittest.TestCase):
    def test_result_keys_and_mixed_records_do_not_change_language_aggregation(self):
        old, business, interview = fixture("legacy-session"), fixture("business-session"), fixture()
        before = copy.deepcopy([old, business, interview])
        entries = wb.latest_technical([old, business, interview])
        self.assertEqual(len(entries), 3)
        expected_keys = set(interview["interview"]["observations"][0]) | {"depth", "role", "track", "session_id", "created_at", "scenario_id"}
        self.assertEqual(set(entries[0]), expected_keys)
        self.assertEqual(entries[0]["track"], {"id": "web3", "label": "Web3 后端"})
        self.assertEqual(entries[0]["session_id"], interview["id"])
        self.assertEqual([old, business, interview], before)
        without_technical = copy.deepcopy(interview)
        without_technical.pop("interview")
        self.assertEqual(wb.latest_targets([old, business, interview]), wb.latest_targets([old, business, without_technical]))

    def test_unobserved_does_not_erase_evidence_or_its_source_and_results_are_newest_first(self):
        old, newer = fixture(), attempt()
        newer["scenario"]["id"] = "int-custom-other-scene"
        item = newer["interview"]["observations"][0]
        for field in ("evidence", "observation", "suggestion"):
            item.pop(field)
        item.update(status="not_observed", language_support="none", technical_support="none")
        result = wb.latest_technical([old, newer])
        self.assertEqual([item["concept_id"] for item in result], ["state-authority", "finality", "timeout-semantics"])
        recovered = result[-1]
        self.assertEqual(recovered["session_id"], old["id"])
        self.assertEqual(recovered["created_at"], old["created_at"])
        self.assertEqual(recovered["scenario_id"], old["scenario"]["id"])
        self.assertEqual(recovered["evidence"], old["interview"]["observations"][0]["evidence"])
        self.assertEqual(result[1]["status"], "not_observed")
        self.assertEqual(result[1]["session_id"], newer["id"])

    def test_concept_aggregates_across_scenes_not_across_depth_or_role(self):
        base = fixture()
        different_scene = attempt()
        different_scene["scenario"]["id"] = "int-custom-same-concept"
        interviewer = attempt("synthetic-interviewer", role="interviewer")
        system = attempt("synthetic-system", depth="system")
        result = wb.latest_technical([base, different_scene, interviewer, system])
        self.assertEqual(len(result), 9)
        self.assertEqual({(item["role"], item["depth"]) for item in result},
                         {("candidate", "implementation"), ("interviewer", "implementation"), ("candidate", "system")})
        latest_candidate = next(item for item in result if item["concept_id"] == "timeout-semantics" and item["role"] == "candidate" and item["depth"] == "implementation")
        self.assertEqual(latest_candidate["scenario_id"], different_scene["scenario"]["id"])

    def test_assisted_latest_does_not_fall_back_to_old_independent_success(self):
        old, newer = fixture(), attempt()
        old["interview"]["observations"][0].update(language_support="none", technical_support="none")
        newer["interview"]["observations"][0].update(language_support="model", technical_support="solution", status="partial")
        result = wb.latest_technical([old, newer])[0]
        self.assertEqual(result["session_id"], newer["id"])
        self.assertEqual(result["technical_support"], "solution")
        self.assertEqual(result["language_support"], "model")
        self.assertEqual(result["status"], "partial")

    def test_actual_time_equal_time_and_invalid_time_order(self):
        first = attempt("synthetic-first", "2026-11-11T03:00:00Z")
        equal = attempt("synthetic-equal", "2026-11-11T11:00:00+08:00")
        older = attempt("synthetic-older", "2026-11-11T10:00:00+08:00")
        invalid = attempt("synthetic-invalid", "not-a-date")
        self.assertTrue(all(item["session_id"] == first["id"] for item in wb.latest_technical([invalid, first, equal, older])))
        self.assertTrue(all(item["session_id"] == equal["id"] for item in wb.latest_technical([equal, first, older])))

    @unittest.skipUnless(shutil.which("node"), "Node is needed for cross-runtime contract parity")
    def test_python_javascript_results_are_identical(self):
        old, newer = fixture(), attempt()
        observation = newer["interview"]["observations"][0]
        for key in ("evidence", "observation", "suggestion"):
            observation.pop(key)
        observation.update(status="not_observed", language_support="none", technical_support="none")
        interviewer = attempt("synthetic-role-reversal", role="interviewer")
        interviewer["interview"]["observations"].reverse()
        sessions = [fixture("legacy-session"), old, newer, interviewer, attempt("synthetic-system-depth", depth="system")]
        source = "const fs = require('node:fs'); const {latestTechnical} = require(process.argv[1]); process.stdout.write(JSON.stringify(latestTechnical(JSON.parse(fs.readFileSync(0, 'utf8')))));"
        result = subprocess.run([shutil.which("node"), "-e", source, str(ROOT / "assets" / "workbench" / "app.js")], input=json.dumps(sessions), capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), wb.latest_technical(sessions))


class InterviewArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "archive"

    def archive(self, session):
        source = self.root / "synthetic-input.json"
        source.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
        wb.archive_session(self.data, source)

    def test_mixed_roundtrip_preserves_unknown_top_level_fields_and_old_records(self):
        old, business, interview = fixture("legacy-session"), fixture("business-session"), fixture()
        interview["future_extension"] = {"nested": [None, False, {"payload": "<uninterpreted>"}]}
        interview["interview"]["future_metadata"] = {"keep": True}
        wb.atomic_json(self.data / "workbench-data.json", {"version": 1, "sessions": [old], "future_state": {"retain": [1, 2]}})
        for session in (business, interview, interview):
            self.archive(session)
        state = wb.load_state(self.data)
        self.assertEqual(state["version"], 2)
        self.assertEqual(state["future_state"], {"retain": [1, 2]})
        self.assertEqual(state["sessions"], [old, business, interview])
        self.assertNotIn("interview", state["sessions"][0])
        self.assertNotIn("domain", state["sessions"][0])
        self.assertNotIn("interview", state["sessions"][1])
        self.assertEqual(json.loads((self.data / "sessions" / f"{interview['id']}.json").read_text(encoding="utf-8")), interview)

    def test_conflicting_interview_payload_is_refused_without_archive_changes(self):
        session = fixture()
        self.archive(session)
        before = {str(path): path.read_bytes() for path in self.data.rglob("*") if path.is_file()}
        changed = copy.deepcopy(session)
        changed["interview"]["observations"][0]["technical_support"] = "hint"
        with self.assertRaisesRegex(ValueError, "different data"):
            self.archive(changed)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.data.rglob("*") if path.is_file()})

    def test_invalid_input_does_not_create_archive(self):
        session = fixture()
        session["interview"]["observations"][0].pop("evidence")
        with self.assertRaisesRegex(ValueError, "evidence"):
            self.archive(session)
        self.assertFalse(self.data.exists())

    def test_markdown_current_session_metadata_and_cross_scene_latest_assistance(self):
        old, newer = fixture(), attempt()
        newer["scenario"]["id"] = "int-custom-latest-scene"
        newer["interview"]["observations"][0].update(technical_support="solution", language_support="model")
        report = wb.render_dashboard({"sessions": [fixture("legacy-session"), fixture("business-session"), old, newer]})
        for expected in ("本次技术面试", "跨场景技术回顾", "技术角色：候选人", "技术深度：实现", "压力：中", "Web3 后端", "broadcast", "state", "language_support=model", "technical_support=solution", "不计入英语表达比例", "int\\-custom\\-latest\\-scene"):
            self.assertIn(expected, report)
        self.assertIn("已掌握表达：0/1（已观察）", report)
        review = report.split("## 跨场景技术回顾", 1)[1]
        self.assertNotIn("归档：synthetic\\-interview\\-web3", review)
        self.assertIn("参考解答", review)

    def test_markdown_technical_arbitrary_text_is_escaped(self):
        session = fixture()
        malicious = '<img src=x onerror="alert(1)"> [click](javascript:bad)'
        session["interview"]["track"]["label"] = malicious
        for key in ("label", "evidence", "observation", "suggestion"):
            session["interview"]["observations"][0][key] = malicious
        wb.validate_session(session)
        report = wb.render_dashboard({"sessions": [session]})
        self.assertNotIn("<img", report)
        self.assertNotIn("[click](", report)
        self.assertIn("&lt;img", report)
        self.assertIn("\\[click\\]", report)


if __name__ == "__main__":
    unittest.main()
