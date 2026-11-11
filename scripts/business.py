#!/usr/bin/env python3
"""Find and load original business role-play material without a model or network."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "curriculum" / "business"
CATEGORY_ORDER = (
    "social", "prospecting", "discovery", "demo", "solution", "pricing", "negotiation", "contracts",
    "onboarding", "success", "support", "complaints", "partnerships", "marketing",
    "meetings", "decisions", "collaboration", "presentations", "planning", "delivery", "technical",
    "procurement", "finance", "hiring", "management", "workplace", "strategy", "trade",
)
LEVELS = {
    "beginner": {
        "language": "Use concrete business words, short clauses and reusable sentence frames. Keep the business role credible; simplify expression, not professional responsibility.",
        "task": "One decision at a time; explain unfamiliar terms briefly. Never promise an unauthorized outcome.",
    },
    "intermediate": {
        "language": "Use common domain terms, connected explanations, clarification and follow-up questions.",
        "task": "Ask for reasons and trade-offs; require a clear next step and confirmation of conditions.",
    },
    "advanced": {
        "language": "Use precise register, qualified claims, concise evidence and flexible paraphrase; do not reward jargon for its own sake.",
        "task": "Probe assumptions and competing priorities; ask for defensible boundaries and unresolved items.",
    },
}


def read_json(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def nonempty(value, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def strings(value, label: str, minimum: int = 1) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{label} must contain at least {minimum} items")
    for item in value:
        nonempty(item, label)


def validate_category(category: dict) -> None:
    if not isinstance(category, dict):
        raise ValueError("category must be an object")
    nonempty(category.get("id"), "category.id")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", category["id"]):
        raise ValueError("invalid category id")
    nonempty(category.get("label"), "category.label")
    scenes = category.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 6:
        raise ValueError(f"{category['id']} must define six scenes")
    ids = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError("scene must be an object")
        sid = scene.get("id", "")
        if not isinstance(sid, str) or not re.fullmatch(rf"biz-{re.escape(category['id'])}-0[1-6]", sid) or sid in ids:
            raise ValueError(f"invalid or duplicate scene id: {sid}")
        ids.add(sid)
        for key in ("label", "context"):
            nonempty(scene.get(key), f"{sid}.{key}")
        for side in ("a", "b"):
            role = scene.get("roles", {}).get(side)
            if not isinstance(role, dict):
                raise ValueError(f"{sid} needs roles a and b")
            for key in ("label", "label_en", "objective"):
                nonempty(role.get(key), f"{sid}.{side}.{key}")
            for key in ("private_information", "constraints"):
                strings(role.get(key), f"{sid}.{side}.{key}")
            strings(scene.get("success_criteria", {}).get(side), f"{sid}.criteria.{side}", 2)
        strings(scene.get("stages"), f"{sid}.stages", 3)
        strings(scene.get("complications"), f"{sid}.complications", 2)
        strings(scene.get("tags"), f"{sid}.tags", 2)
        targets = scene.get("targets")
        if not isinstance(targets, list) or len(targets) < 3:
            raise ValueError(f"{sid} needs at least three target suggestions")
        expressions = set()
        for target in targets:
            if not isinstance(target, dict):
                raise ValueError(f"{sid}.target must be an object")
            for key in ("expression", "meaning_zh", "function"):
                nonempty(target.get(key), f"{sid}.target.{key}")
            if target["expression"].strip() in expressions:
                raise ValueError(f"{sid} has duplicate targets")
            expressions.add(target["expression"].strip())


def index_from_files(root: Path = ROOT) -> dict:
    categories, scenes, seen = [], [], set()
    order = {key: index for index, key in enumerate(CATEGORY_ORDER)}
    paths = sorted((root / "scenarios").glob("*.json"), key=lambda path: (order.get(path.stem, len(order)), path.stem))
    for path in paths:
        category = read_json(path)
        validate_category(category)
        if path.stem != category["id"]:
            raise ValueError(f"category filename mismatch: {path.name}")
        categories.append({"id": category["id"], "label": category["label"], "count": len(category["scenes"])})
        for scene in category["scenes"]:
            if scene["id"] in seen:
                raise ValueError(f"duplicate scene: {scene['id']}")
            seen.add(scene["id"])
            scenes.append({
                "id": scene["id"], "label": scene["label"],
                "category_id": category["id"], "category_label": category["label"],
                "roles": [scene["roles"][side]["label"] for side in ("a", "b")],
                "tags": scene["tags"], "path": f"scenarios/{path.name}",
            })
    return {"version": 1, "content_status": "defined", "learner_validated": False,
            "categories": categories, "scenes": scenes}


def validate_industries(root: Path = ROOT) -> list[dict]:
    industries = read_json(root / "industries.json")
    if not isinstance(industries, list) or len(industries) != 12:
        raise ValueError("expected twelve industry packs")
    ids = set()
    for item in industries:
        if not isinstance(item, dict):
            raise ValueError("industry must be an object")
        for key in ("id", "label", "scope", "safety"):
            nonempty(item.get(key), f"industry.{key}")
        if item["id"] in ids or not re.fullmatch(r"[a-z][a-z0-9-]*", item["id"]):
            raise ValueError("invalid or duplicate industry id")
        ids.add(item["id"])
        for key in ("constraints", "metrics", "questions"):
            strings(item.get(key), f"{item['id']}.{key}", 3)
        terms = item.get("terms")
        if not isinstance(terms, list) or len(terms) < 8:
            raise ValueError("industry needs at least eight concrete terms")
        for term in terms:
            if not isinstance(term, dict):
                raise ValueError("industry term must be an object")
            nonempty(term.get("en"), "term.en")
            nonempty(term.get("zh"), "term.zh")
    return industries


def catalog_markdown(index: dict, industries: list[dict]) -> str:
    lines = ["# 商务口语场景目录", "", "> 28 个大类 · 168 个原创模拟场景 · 12 个行业包。以下是定义目录，不是真实学习记录或教学效果证明。", "",
             "每个场景含双方目标与私有信息、权限约束、推进阶段、可选变化、目标表达和可观察标准。角色 A / B 均可选择；英语难度与提示模式独立调整。", "",
             "先通过 `python scripts/business.py list --search 关键词` 检索，再用 `show 场景ID` 加载一个场景；不要一次读取全部定义。使用规则见 [README](README.md) 和 [商务训练协议](../../references/business-english.md)。", ""]
    for number, category in enumerate(index["categories"], 1):
        lines += [f"## {number}. {category['label']}", "", f"类别 ID：`{category['id']}`", "", "| 场景 ID | 沟通任务 | 可选择的双方角色 |", "|---|---|---|"]
        for scene in index["scenes"]:
            if scene["category_id"] == category["id"]:
                lines.append(f"| `{scene['id']}` | {scene['label']} | {' / '.join(scene['roles'])} |")
        lines.append("")
    lines += ["## 行业补充包", "", "| 行业 ID | 行业 |", "|---|---|"]
    for industry in industries:
        lines.append(f"| `{industry['id']}` | {industry['label']} |")
    lines += ["", "## 目录外任务", "", "按同一标准生成自定义场景，使用 `biz-custom-<slug>` 和 custom 类别。只存学习者可见、已脱敏的背景；不假装自定义任务属于上述 168 个已有定义。", "",
              "## 验证状态", "", "内容状态为已定义；全库结构与角色加载可由 `python scripts/business.py validate` 和自动测试验证。真实学习者练习效果尚未验证，不能据此宣称行业认证或所有情况均已穷尽。", ""]
    return "\n".join(lines)


def validate_library(root: Path = ROOT, check_index: bool = True) -> dict:
    index = index_from_files(root)
    if tuple(item["id"] for item in index["categories"]) != CATEGORY_ORDER or len(index["scenes"]) != 168:
        raise ValueError("expected 28 categories and 168 fully defined scenes")
    industries = validate_industries(root)
    if check_index:
        if read_json(root / "index.json") != index:
            raise ValueError("scene index is stale; run business.py build-index")
        if (root / "catalog.md").read_text(encoding="utf-8") != catalog_markdown(index, industries):
            raise ValueError("scene catalog is stale; run business.py build-index")
    return {"categories": 28, "scenes": 168, "industries": len(industries),
            "structurally_valid": True, "learner_validated": False}


def search_scenes(root: Path = ROOT, category: str | None = None, search: str = "", limit: int = 12) -> list[dict]:
    index = read_json(root / "index.json")
    if category and category not in {item["id"] for item in index["categories"]}:
        raise ValueError(f"unknown category: {category}")
    words = search.casefold().split()
    results = []
    for scene in index["scenes"]:
        haystack = " ".join([scene["id"], scene["label"], scene["category_label"], *scene["roles"], *scene["tags"]]).casefold()
        if (not category or scene["category_id"] == category) and all(word in haystack for word in words):
            results.append(scene)
    return results[:limit]


def load_scene(scene_id: str, root: Path = ROOT, role: str = "a", industry: str | None = None,
               level: str = "intermediate", duration: int = 20) -> dict:
    if role not in {"a", "b"} or level not in LEVELS:
        raise ValueError("invalid role or level")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 240:
        raise ValueError("duration must be between 1 and 240 minutes")
    index = read_json(root / "index.json")
    entry = next((scene for scene in index["scenes"] if scene["id"] == scene_id), None)
    if entry is None:
        raise ValueError(f"unknown scene: {scene_id}")
    # Derive a safe path from the category identifier, never from learner input.
    category_id = entry["category_id"]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", category_id):
        raise ValueError("invalid indexed category id")
    category = read_json(root / "scenarios" / f"{category_id}.json")
    validate_category(category)
    scene = next((item for item in category["scenes"] if item["id"] == scene_id), None)
    if scene is None:
        raise ValueError("index does not match category file")
    industry_pack = None
    if industry:
        industry_pack = next((item for item in validate_industries(root) if item["id"] == industry), None)
        if industry_pack is None:
            raise ValueError(f"unknown industry: {industry}")
    coach_role = "b" if role == "a" else "a"
    return {
        "domain": "business", "scenario": {key: entry[key] for key in ("id", "label", "category_id", "category_label")},
        "simulated": True, "context": scene["context"],
        "learner_brief": scene["roles"][role], "coach_only": scene["roles"][coach_role],
        "stages": scene["stages"], "complications": scene["complications"],
        "target_suggestions": scene["targets"], "success_criteria": scene["success_criteria"][role],
        "industry": industry_pack, "level": level, "adaptation": LEVELS[level],
        "duration_minutes": duration,
        "complication_budget": 0 if duration <= 10 else 1 if duration < 40 else 2,
        "instructions": [
            "Do not display coach_only or read it aloud; share only context and the learner brief in the preview.",
            "Adapt targets to the selected learner role; the suggestions are not a full duration-scaled preview vocabulary bank.",
            "Use industry terms only when relevant; agree changed simulated facts before starting, never silently contradict the brief.",
            "Assess observable communication and justified refusal, deferral or escalation, not whether a deal was won.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("categories")
    sub.add_parser("industries")
    listing = sub.add_parser("list")
    listing.add_argument("--category")
    listing.add_argument("--search", default="")
    listing.add_argument("--limit", type=int, default=12)
    showing = sub.add_parser("show")
    showing.add_argument("id")
    showing.add_argument("--role", choices=("a", "b"), default="a")
    showing.add_argument("--industry")
    showing.add_argument("--level", choices=tuple(LEVELS), default="intermediate")
    showing.add_argument("--duration", type=int, default=20)
    sub.add_parser("validate")
    sub.add_parser("build-index")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "categories":
            result = read_json(ROOT / "index.json")["categories"]
        elif args.command == "industries":
            result = [{"id": item["id"], "label": item["label"], "scope": item["scope"]} for item in validate_industries()]
        elif args.command == "list":
            if not 1 <= args.limit <= 168:
                raise ValueError("limit must be between 1 and 168")
            result = search_scenes(category=args.category, search=args.search, limit=args.limit)
        elif args.command == "show":
            result = load_scene(args.id, role=args.role, industry=args.industry, level=args.level, duration=args.duration)
        elif args.command == "build-index":
            validate_library(check_index=False)
            index = index_from_files()
            industries = validate_industries()
            (ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (ROOT / "catalog.md").write_text(catalog_markdown(index, industries), encoding="utf-8")
            result = {"indexed": len(index["scenes"]), "catalog_updated": True}
        else:
            result = validate_library()
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"business: {error}\n")
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
