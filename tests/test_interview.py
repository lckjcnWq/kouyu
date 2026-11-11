"""Self-contained interview content, safe disclosure, search and read-only review."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("interview", PROJECT / "scripts" / "interview.py")
interview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interview)
SAMPLE = "int-web3-broadcast-timeout"


class InterviewTests(unittest.TestCase):
    def test_complete_self_contained_library(self):
        result = interview.validate_library()
        self.assertEqual((result["tracks"], result["scenes"]), (6, 18))
        self.assertFalse(result["learner_validated"])
        with tempfile.TemporaryDirectory() as temp:
            result = interview.validate_library(project=Path(temp))
        self.assertFalse(result["source_files_checked"])

    def test_every_scene_both_roles_levels_depths_and_pressures(self):
        for entry in interview.read_json(interview.ROOT / "index.json")["scenes"]:
            for role in interview.ROLES:
                for level in interview.LEVELS:
                    for depth in interview.DEPTHS:
                        for pressure in interview.PRESSURES:
                            with self.subTest(scene=entry["id"], role=role, level=level, depth=depth, pressure=pressure):
                                brief = interview.load_scene(entry["id"], role=role, level=level, depth=depth, pressure=pressure)
                                self.assertNotIn("coach_only", brief)
                                self.assertEqual(brief["depth"], depth)
                                self.assertEqual(brief["level"], level)
                                self.assertEqual(brief["scenario"]["category_id"], "hiring")
                                self.assertEqual(brief["role"], role)
                                self.assertEqual(brief["domain"], "business")
                                self.assertGreaterEqual(len(brief["terms"]), 8)
                                serialized = json.dumps(brief)
                                for private_key in ('"reference_answer"', '"candidate_profile"', '"rubric"', '"followups"', '"complications"', '"sources"'):
                                    self.assertNotIn(private_key, serialized)

    def test_coach_depth_filter_and_budget(self):
        for depth in interview.DEPTHS:
            for duration, budget in ((5, 1), (10, 1), (20, 3), (40, 6)):
                brief = interview.load_scene(SAMPLE, depth=depth, duration=duration, coach=True)
                teacher = brief["coach_only"]
                self.assertEqual(teacher["followup_budget"], budget)
                self.assertTrue(teacher["followups"])
                self.assertTrue(teacher["rubric"])
                for item in teacher["followups"] + teacher["rubric"]:
                    self.assertLessEqual(interview.DEPTHS.index(item["depth"]), interview.DEPTHS.index(depth))
                self.assertTrue(teacher["reference_answer"])
                self.assertNotEqual(brief["learner_brief"], teacher["counterpart"])

    def test_every_scene_coach_depth_is_nonempty_and_role_specific(self):
        for entry in interview.read_json(interview.ROOT / "index.json")["scenes"]:
            for depth in interview.DEPTHS:
                for role in interview.ROLES:
                    with self.subTest(scene=entry["id"], depth=depth, role=role):
                        teacher = interview.load_scene(entry["id"], depth=depth, role=role, coach=True)["coach_only"]
                        self.assertTrue(teacher["followups"])
                        self.assertTrue(teacher["rubric"])
                        for criterion in teacher["rubric"]:
                            self.assertTrue(criterion["interviewer_criterion"])
                            self.assertTrue(criterion["acceptable_alternatives"])
                            self.assertTrue(criterion["misconceptions"])
                            self.assertLessEqual(interview.DEPTHS.index(criterion["depth"]), interview.DEPTHS.index(depth))

    def test_search_is_learner_safe_and_matches_terms(self):
        self.assertEqual(len(interview.search_scenes(track="web3", limit=100)), 3)
        self.assertIn(SAMPLE, {entry["id"] for entry in interview.search_scenes(search="广播", limit=100)})
        self.assertTrue(interview.search_scenes(search="NONCE", limit=100))
        self.assertEqual(interview.search_scenes(search="no-such-topic-xyz"), [])
        concept = interview.read_json(interview.ROOT / "scenes" / f"{SAMPLE}.json")["concepts"][0]
        results = interview.search_scenes(concept=concept, limit=100)
        self.assertTrue(all(concept in entry["concepts"] for entry in results))
        for key in ("coach_only", "reference_answer", "candidate_profile", "rubric", "followups"):
            self.assertNotIn(key, json.dumps(results))

    def test_bad_parameters(self):
        for kwargs in ({"role": "admin"}, {"level": "expert"}, {"depth": "advanced"}, {"pressure": "abusive"}, {"duration": True}, {"duration": 0}, {"duration": 241}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                interview.load_scene(SAMPLE, **kwargs)
        with self.assertRaises(ValueError):
            interview.load_scene("../../private")
        for kwargs in ({"track": "solana"}, {"concept": "not-registered"}, {"limit": True}, {"limit": 0}, {"limit": 101}):
            with self.assertRaises(ValueError):
                interview.search_scenes(**kwargs)

    def test_invalid_content_rejected_even_without_source_root(self):
        scene = interview.read_json(interview.ROOT / "scenes" / f"{SAMPLE}.json")
        concepts = {item["id"] for item in interview.read_json(interview.ROOT / "concepts.json")}
        mutations = [lambda item: item["sources"][0].update(path="web3-go/../../secrets.md"),
                     lambda item: item["sources"][0].update(path="/private/secrets.md"),
                     lambda item: item["sources"][0].update(path="web3-go/..\\secrets.md"),
                     lambda item: item.update(concepts=["unknown-concept"]),
                     lambda item: item["coach_only"].update(rubric=[]),
                     lambda item: item["coach_only"]["followups"][0].update(id=item["coach_only"]["anchor"]["id"]),
                     lambda item: item["terms"].append(item["terms"][0]),
                     lambda item: item["roles"].pop("interviewer")]
        with tempfile.TemporaryDirectory() as temp:
            for mutate in mutations:
                broken = copy.deepcopy(scene)
                mutate(broken)
                with self.assertRaises(ValueError):
                    interview.validate_scene(broken, concepts, project=Path(temp))

    def test_public_assumptions_do_not_include_sample_recovery_solution(self):
        brief = interview.load_scene(SAMPLE)
        assumptions = " ".join(brief["assumptions"]).casefold()
        for solution_fragment in ("ready broadcast task", "commit together", "bound to one durable", "retries resend"):
            self.assertNotIn(solution_fragment, assumptions)

    def test_source_section_locators_are_verified_in_development(self):
        scene = interview.read_json(interview.ROOT / "scenes" / f"{SAMPLE}.json")
        scene["sources"] = [{"path": "web3-go/synthetic-test.md", "sections": ["nonexistent-section-locator-for-test-xyz"]}]
        concepts = {item["id"] for item in interview.read_json(interview.ROOT / "concepts.json")}
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "web3-go").mkdir()
            (project / "web3-go/synthetic-test.md").write_text("# Synthetic test source\n\n## Existing heading\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "locator"):
                interview.validate_scene(scene, concepts, project=project)
            scene["sources"][0]["sections"] = ["Existing heading"]
            interview.validate_scene(scene, concepts, project=project)

    def test_index_and_catalog_are_current(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "interview"
            shutil.copytree(interview.ROOT, root)
            interview.validate_library(root, project=Path(temp))
            (root / "catalog.md").write_text("stale", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                interview.validate_library(root, project=Path(temp))
            (root / "catalog.md").write_text(interview.catalog_markdown(interview.index_from_content(root, Path(temp))), encoding="utf-8")
            index = interview.read_json(root / "index.json")
            index["scenes"].pop()
            (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                interview.validate_library(root, project=Path(temp))

    def test_cli_works_outside_project(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, "-I", "-B", str(PROJECT / "scripts/interview.py"), "show", SAMPLE, "--depth", "system"], cwd=temp, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("coach_only", json.loads(result.stdout))

    def test_review_missing_archive_does_not_create_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "missing"
            result = interview.review(directory)
            self.assertFalse(directory.exists())
            self.assertFalse(result["archive_found"])
            self.assertEqual(result["observations"], [])

    def test_review_actual_synthetic_archive(self):
        fixture = interview.read_json(PROJECT / "tests/fixtures/interview-session.json")
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = directory / "workbench-data.json"
            payload = {"version": 2, "sessions": [fixture]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            before = path.read_bytes()
            result = interview.review(directory)
            self.assertTrue(result["read_only"])
            self.assertTrue(result["observations"])
            self.assertEqual(path.read_bytes(), before)
            cid = result["observations"][0]["concept_id"]
            filtered = interview.review(directory, concept=cid, scene=fixture["scenario"]["id"])
            self.assertTrue(all(item["concept_id"] == cid for item in filtered["observations"]))
            self.assertTrue(filtered["drills"])
            for drill in filtered["drills"]:
                self.assertTrue(drill["transfer"]["prompt"])
                self.assertTrue(drill["transfer"]["changes"])
                for candidate_id in drill["scene_ids"]:
                    teacher = interview.load_scene(candidate_id, depth=drill["depth"], role=drill["role"], coach=True)["coach_only"]
                    self.assertIn(drill["concept_id"], {criterion["concept_id"] for criterion in teacher["rubric"]})
            with self.assertRaises(ValueError):
                interview.review(directory, concept="unknown")
            with self.assertRaises(ValueError):
                interview.review(directory, scene="unknown")


if __name__ == "__main__":
    unittest.main()
