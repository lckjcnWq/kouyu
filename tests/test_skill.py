"""Check progressive-disclosure links and packaging-neutral skill instructions."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SkillTests(unittest.TestCase):
    def test_frontmatter_and_small_entrypoint(self):
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(content, r"\A---\nname: kouyu\ndescription: [^\n]+\n---")
        self.assertLess(len(content.split()), 2000)
        self.assertIn("business.py", content)
        self.assertNotIn("ANTHROPIC_API_KEY", content)

    def test_relative_markdown_links_resolve(self):
        paths = [ROOT / "README.md", ROOT / "SKILL.md", *list((ROOT / "references").glob("*.md")), *list((ROOT / "curriculum").rglob("*.md"))]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", content):
                if link.startswith(("http:", "https:", "#", "mailto:")):
                    continue
                target = (path.parent / link.split("#")[0]).resolve()
                with self.subTest(file=str(path.relative_to(ROOT)), link=link):
                    self.assertTrue(target.exists(), f"broken relative link {target}")

    def test_business_rules_have_boundaries_and_evidence(self):
        content = (ROOT / "references" / "business-english.md").read_text(encoding="utf-8")
        for marker in ("coach_only", "learner_brief", "not_observed", "declined", "beginner", "immersion", "custom", "Privacy"):
            self.assertIn(marker, content)

    def test_technical_routing_and_evidence_contract(self):
        entry = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("interview.py", entry)
        protocol = (ROOT / "references/technical-interview.md").read_text(encoding="utf-8")
        for marker in ("--coach", "language_support", "technical_support", "not_observed", "interviewer", "independent", "confidential", "readiness"):
            self.assertIn(marker, protocol)
        contract = (ROOT / "references/interview-contract.md").read_text(encoding="utf-8")
        self.assertIn("concept_id, depth, role", contract)
        self.assertIn("self-contained", contract)


if __name__ == "__main__":
    unittest.main()
