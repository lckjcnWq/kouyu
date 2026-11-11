"""Validate the entire defined catalog, not only one hand-picked scene."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("business", ROOT / "scripts" / "business.py")
biz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biz)


class LibraryTests(unittest.TestCase):
    def test_complete_library_and_current_index(self):
        result = biz.validate_library()
        self.assertEqual((result["categories"], result["scenes"], result["industries"]), (28, 168, 12))
        self.assertFalse(result["learner_validated"])

    def test_every_scene_both_roles_and_three_levels(self):
        index = biz.read_json(biz.ROOT / "index.json")
        for entry in index["scenes"]:
            for role in ("a", "b"):
                for level in biz.LEVELS:
                    with self.subTest(scene=entry["id"], role=role, level=level):
                        scene = biz.load_scene(entry["id"], role=role, level=level)
                        self.assertEqual(scene["scenario"]["id"], entry["id"])
                        self.assertEqual(scene["level"], level)
                        self.assertNotEqual(scene["learner_brief"]["objective"], scene["coach_only"]["objective"])
                        self.assertGreaterEqual(len(scene["success_criteria"]), 2)
                        self.assertEqual(scene["complication_budget"], 1)

    def test_industry_overlay_is_selected_not_dumped(self):
        for item in biz.validate_industries():
            scene = biz.load_scene("biz-negotiation-01", industry=item["id"])
            self.assertEqual(scene["industry"]["id"], item["id"])
            self.assertIsInstance(scene["industry"], dict)
            self.assertGreaterEqual(len(scene["industry"]["terms"]), 8)

    def test_show_matches_role_specific_source(self):
        scene = biz.load_scene("biz-negotiation-01", role="b")
        source = biz.read_json(biz.ROOT / "scenarios" / "negotiation.json")["scenes"][0]
        self.assertEqual(scene["learner_brief"], source["roles"]["b"])
        self.assertEqual(scene["coach_only"], source["roles"]["a"])
        self.assertEqual(scene["success_criteria"], source["success_criteria"]["b"])

    def test_focused_search_and_limit(self):
        items = biz.search_scenes(category="negotiation", limit=3)
        self.assertEqual(len(items), 3)
        self.assertTrue(all(item["category_id"] == "negotiation" for item in items))
        items = biz.search_scenes(search="报价", limit=168)
        self.assertTrue(items)
        self.assertEqual(biz.search_scenes(search="no-such-scene-xyz"), [])
        self.assertNotIn("coach_only", json.dumps(items))
        self.assertNotIn("private_information", json.dumps(items))

    def test_bad_id_and_parameters(self):
        cases = [
            {"scene_id": "../../workbench-data"}, {"scene_id": "unknown"},
            {"scene_id": "biz-negotiation-01", "role": "seller"},
            {"scene_id": "biz-negotiation-01", "industry": "unknown"},
            {"scene_id": "biz-negotiation-01", "duration": 0},
            {"scene_id": "biz-negotiation-01", "duration": True},
            {"scene_id": "biz-negotiation-01", "level": "expert"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    biz.load_scene(**kwargs)
        with self.assertRaises(ValueError):
            biz.search_scenes(category="unknown")

    def test_duration_complications(self):
        for minutes, expected in ((5, 0), (10, 0), (20, 1), (40, 2)):
            self.assertEqual(biz.load_scene("biz-negotiation-01", duration=minutes)["complication_budget"], expected)

    def test_incomplete_scene_rejected(self):
        category = biz.read_json(biz.ROOT / "scenarios" / "negotiation.json")
        invalid = copy.deepcopy(category)
        invalid["scenes"][0]["roles"]["b"].pop("constraints")
        with self.assertRaises(ValueError):
            biz.validate_category(invalid)
        invalid = copy.deepcopy(category)
        invalid["scenes"][0]["targets"] = []
        with self.assertRaises(ValueError):
            biz.validate_category(invalid)
        invalid = copy.deepcopy(category)
        invalid["scenes"][1]["id"] = invalid["scenes"][0]["id"]
        with self.assertRaises(ValueError):
            biz.validate_category(invalid)

    def test_cli_independent_of_current_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "business.py"), "show", "biz-negotiation-01", "--role", "b", "--industry", "software"], cwd=temp, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["industry"]["id"], "software")

    def test_stale_catalog_or_index_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scenarios").mkdir()
            for path in (biz.ROOT / "scenarios").glob("*.json"):
                (root / "scenarios" / path.name).write_bytes(path.read_bytes())
            for name in ("industries.json", "index.json", "catalog.md"):
                (root / name).write_bytes((biz.ROOT / name).read_bytes())
            biz.validate_library(root)
            (root / "catalog.md").write_text("stale catalog", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "catalog is stale"):
                biz.validate_library(root)
            (root / "catalog.md").write_bytes((biz.ROOT / "catalog.md").read_bytes())
            index = biz.read_json(root / "index.json")
            index["scenes"][0]["label"] = "stale title"
            (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "index is stale"):
                biz.validate_library(root)

    def test_catalog_lists_exact_scene_ids(self):
        import re
        content = (biz.ROOT / "catalog.md").read_text(encoding="utf-8")
        ids = re.findall(r"`(biz-[a-z0-9-]+-0[1-6])`", content)
        self.assertEqual(len(ids), 168)
        self.assertEqual(set(ids), {item["id"] for item in biz.read_json(biz.ROOT / "index.json")["scenes"]})


if __name__ == "__main__":
    unittest.main()
