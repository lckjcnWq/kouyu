#!/usr/bin/env python3
"""Load self-contained Go / Web3 interview practice and revisit archived evidence."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "curriculum" / "interview"
TRACKS = ("architecture", "trading", "risk", "liquidity", "web3", "go")
DEPTHS = ("foundation", "implementation", "system")
ROLES = ("candidate", "interviewer")
LEVELS = ("beginner", "intermediate", "advanced")
PRESSURES = ("low", "moderate", "high")
SLUG = r"[a-z][a-z0-9-]*"
LANGUAGE_GUIDANCE = {
    "beginner": "Use short concrete sentences and reusable frames; preserve the chosen technical depth and professional boundaries.",
    "intermediate": "Use connected explanations, common technical collocations, clarification and qualified claims.",
    "advanced": "Use concise precise explanations, explicit assumptions and flexible paraphrase; jargon alone is not proficiency.",
}
DEPTH_GUIDANCE = {
    "foundation": "Explain normal flow, actors and key distinctions; do not require unselected implementation or system-level rubric items.",
    "implementation": "Explain durable identities, state transitions and a concrete failure window as applicable; include foundation criteria.",
    "system": "Probe interacting failure windows, authority boundaries, recovery and validation; accept defensible alternatives under agreed assumptions.",
}
PRESSURE_GUIDANCE = {
    "low": "Allow time to organize; ask one direct clarification at a time without technical hints unless needed or requested.",
    "moderate": "Ask for justification and one fair changed condition, within the selected depth and time budget.",
    "high": "Use a plausible time constraint and challenge assumptions fairly; never change facts, abuse or introduce unselected technical requirements.",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def strings(value, label, minimum=1, unique=False):
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{label} needs at least {minimum} items")
    for item in value:
        nonempty(item, label)
    if unique and len({item.strip() for item in value}) != len(value):
        raise ValueError(f"{label} must be unique")


def objects(value, label, minimum=1):
    if not isinstance(value, list) or len(value) < minimum or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must contain at least {minimum} objects")


def identities(path: Path, fields):
    data = read_json(path)
    objects(data, path.name)
    seen = set()
    for item in data:
        for field in fields:
            nonempty(item.get(field), f"{path.name}.{field}")
        if not re.fullmatch(SLUG, item["id"]) or item["id"] in seen:
            raise ValueError(f"invalid or duplicate id in {path.name}")
        seen.add(item["id"])
    return data


def validate_scene(scene: dict, concept_ids: set[str], project: Path = PROJECT):
    if not isinstance(scene, dict):
        raise ValueError("scene must be an object")
    sid = scene.get("id")
    if not isinstance(sid, str) or scene.get("track_id") not in TRACKS or not re.fullmatch(rf"int-{scene['track_id']}-[a-z0-9]+(?:-[a-z0-9]+)*", sid):
        raise ValueError("invalid scene id or track")
    for key in ("label", "context"):
        nonempty(scene.get(key), f"{sid}.{key}")
    strings(scene.get("assumptions"), f"{sid}.assumptions", 2)
    strings(scene.get("stages"), f"{sid}.stages", 3)
    strings(scene.get("complications"), f"{sid}.complications", 2)
    roles = scene.get("roles")
    if not isinstance(roles, dict):
        raise ValueError(f"{sid}.roles must be an object")
    for role in ROLES:
        brief = roles.get(role)
        if not isinstance(brief, dict):
            raise ValueError(f"{sid} needs both roles")
        for key in ("label", "label_en", "objective"):
            nonempty(brief.get(key), f"{sid}.{role}.{key}")
        strings(brief.get("constraints"), f"{sid}.{role}.constraints")
    objects(scene.get("terms"), f"{sid}.terms", 8)
    terms = set()
    for term in scene["terms"]:
        for key in ("en", "zh"):
            nonempty(term.get(key), f"{sid}.term.{key}")
        if term["en"].strip().casefold() in terms:
            raise ValueError(f"{sid} has duplicate terms")
        terms.add(term["en"].strip().casefold())
    objects(scene.get("targets"), f"{sid}.targets", 3)
    expressions = set()
    for target in scene["targets"]:
        for key in ("expression", "meaning_zh", "function"):
            nonempty(target.get(key), f"{sid}.target.{key}")
        if target["expression"].strip() in expressions:
            raise ValueError(f"{sid} has duplicate targets")
        expressions.add(target["expression"].strip())
    strings(scene.get("concepts"), f"{sid}.concepts", unique=True)
    if not set(scene["concepts"]) <= concept_ids:
        raise ValueError(f"{sid} has unregistered concepts")
    objects(scene.get("sources"), f"{sid}.sources")
    for source in scene["sources"]:
        path = source.get("path")
        nonempty(path, f"{sid}.source.path")
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in path or not path.startswith("web3-go/") or relative.suffix != ".md":
            raise ValueError(f"{sid} has unsafe source path")
        source_path = project / relative
        strings(source.get("sections"), f"{sid}.source.sections")
        if (project / "web3-go").exists():
            if not source_path.is_file() or not source_path.resolve().is_relative_to((project / "web3-go").resolve()):
                raise ValueError(f"{sid} source not found or outside source root: {path}")
            source_text = source_path.read_text(encoding="utf-8-sig")
            if any(section not in source_text for section in source["sections"]):
                raise ValueError(f"{sid} has an unmatched source section locator: {path}")
    coach = scene.get("coach_only")
    if not isinstance(coach, dict) or not isinstance(coach.get("anchor"), dict):
        raise ValueError(f"{sid} needs coach-only anchor")
    questions = [coach["anchor"]]
    objects(coach.get("followups"), f"{sid}.followups", 3)
    for followup in coach["followups"]:
        if followup.get("depth") not in DEPTHS:
            raise ValueError(f"{sid} invalid follow-up depth")
        nonempty(followup.get("trigger"), f"{sid}.trigger")
        questions.append(followup)
    if not any(item["depth"] == "foundation" for item in coach["followups"]):
        raise ValueError(f"{sid} needs a foundation follow-up")
    qids = set()
    for question in questions:
        qid = question.get("id")
        if not isinstance(qid, str) or not re.fullmatch(SLUG, qid) or qid in qids:
            raise ValueError(f"{sid} invalid or duplicate question id")
        qids.add(qid)
        nonempty(question.get("prompt"), f"{sid}.question.prompt")
    for key in ("reference_answer", "candidate_profile"):
        nonempty(coach.get(key), f"{sid}.{key}")
    objects(coach.get("rubric"), f"{sid}.rubric")
    covered = set()
    if not any(item.get("depth") == "foundation" for item in coach["rubric"]):
        raise ValueError(f"{sid} needs a foundation rubric criterion")
    for item in coach["rubric"]:
        if item.get("concept_id") not in scene["concepts"] or item.get("depth") not in DEPTHS:
            raise ValueError(f"{sid} invalid rubric identity or depth")
        covered.add(item["concept_id"])
        for key in ("criterion", "interviewer_criterion"):
            nonempty(item.get(key), f"{sid}.rubric.{key}")
        for key in ("acceptable_alternatives", "misconceptions"):
            strings(item.get(key), f"{sid}.rubric.{key}")
    if covered != set(scene["concepts"]):
        raise ValueError(f"{sid} rubric must cover every concept")
    transfer = coach.get("transfer")
    if not isinstance(transfer, dict):
        raise ValueError(f"{sid} needs a transfer task")
    nonempty(transfer.get("prompt"), f"{sid}.transfer.prompt")
    strings(transfer.get("changes"), f"{sid}.transfer.changes")


def library_content(root: Path = ROOT, project: Path = PROJECT):
    tracks = identities(root / "tracks.json", ("id", "label", "description"))
    if tuple(item["id"] for item in tracks) != TRACKS:
        raise ValueError("expected six ordered interview tracks")
    concepts = identities(root / "concepts.json", ("id", "label", "description"))
    scenes = []
    seen = set()
    for path in sorted((root / "scenes").glob("*.json")):
        scene = read_json(path)
        validate_scene(scene, {item["id"] for item in concepts}, project)
        if path.stem != scene["id"] or scene["id"] in seen:
            raise ValueError("scene filename mismatch or duplicate identity")
        seen.add(scene["id"])
        scenes.append(scene)
    if len(scenes) != 18 or any(sum(scene["track_id"] == track for scene in scenes) != 3 for track in TRACKS):
        raise ValueError("expected 18 scenes, three in each track")
    return tracks, concepts, scenes


def index_from_content(root: Path = ROOT, project: Path = PROJECT):
    tracks, concepts, scenes = library_content(root, project)
    labels = {item["id"]: item["label"] for item in tracks}
    concept_labels = {item["id"]: item["label"] for item in concepts}
    entries = []
    for scene in sorted(scenes, key=lambda item: (TRACKS.index(item["track_id"]), item["id"])):
        tags = [labels[scene["track_id"]], *[concept_labels[cid] for cid in scene["concepts"]]]
        tags += [word for term in scene["terms"] for word in (term["en"], term["zh"])]
        tags += [scene["roles"][role]["label"] for role in ROLES]
        entries.append({"id": scene["id"], "label": scene["label"], "track_id": scene["track_id"],
                        "track_label": labels[scene["track_id"]], "concepts": scene["concepts"],
                        "tags": list(dict.fromkeys(tags)), "path": f"scenes/{scene['id']}.json"})
    return {"version": 1, "content_status": "defined", "learner_validated": False,
            "tracks": [{**item, "count": 3} for item in tracks], "scenes": entries}


def catalog_markdown(index):
    lines = ["# Go / Web3 专业面试场景", "", "> 六条主线 · 18 个自包含模拟场景。已定义不等于真实学习者效果验证。", "",
             "招聘面试下的专业方向；英语水平、技术深度和帮助模式独立。先 list 检索，再 show 单场景，教师资料需显式 --coach。", "",
             "参见 [使用说明](README.md) 和 [技术面试协议](../../references/technical-interview.md)。", ""]
    for track in index["tracks"]:
        lines += [f"## {track['label']}", "", track["description"], "", "| 场景 ID | 任务 |", "|---|---|"]
        for scene in index["scenes"]:
            if scene["track_id"] == track["id"]:
                lines.append(f"| `{scene['id']}` | {scene['label']} |")
        lines.append("")
    lines += ["Solana 与预测市场不属于本版必修覆盖。题卡是基于本地用户资料的原创英语改编，不是生产系统认证答案。", ""]
    return "\n".join(lines)


def validate_library(root: Path = ROOT, project: Path = PROJECT, check_index=True):
    index = index_from_content(root, project)
    if check_index:
        if read_json(root / "index.json") != index:
            raise ValueError("interview index is stale; run interview.py build-index")
        if (root / "catalog.md").read_text(encoding="utf-8") != catalog_markdown(index):
            raise ValueError("interview catalog is stale; run interview.py build-index")
    return {"tracks": 6, "scenes": 18, "concepts": len(read_json(root / "concepts.json")),
            "structurally_valid": True, "learner_validated": False,
            "source_files_checked": (project / "web3-go").exists()}


def search_scenes(root=ROOT, track=None, concept=None, search="", limit=6):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    index = read_json(root / "index.json")
    if track is not None and track not in TRACKS:
        raise ValueError("unknown track")
    if concept is not None and concept not in {item["id"] for item in read_json(root / "concepts.json")}:
        raise ValueError("unknown concept")
    words = search.casefold().split()
    return [entry for entry in index["scenes"]
            if (track is None or entry["track_id"] == track) and (concept is None or concept in entry["concepts"])
            and all(word in " ".join([entry["id"], entry["label"], *entry["concepts"], *entry["tags"]]).casefold() for word in words)][:limit]


def load_scene(scene_id, root=ROOT, role="candidate", level="intermediate", depth="implementation",
               duration=20, pressure="moderate", coach=False):
    if role not in ROLES or level not in LEVELS or depth not in DEPTHS or pressure not in PRESSURES:
        raise ValueError("invalid role, level, depth or pressure")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 240:
        raise ValueError("duration must be between 1 and 240 minutes")
    index = read_json(root / "index.json")
    entry = next((item for item in index["scenes"] if item["id"] == scene_id), None)
    if not entry or not re.fullmatch(r"int-(?:" + "|".join(TRACKS) + r")-[a-z0-9]+(?:-[a-z0-9]+)*", entry["id"]):
        raise ValueError("unknown or unsafe scene id")
    # Derive the file from a checked identity, not an arbitrary path in input/index.
    scene = read_json(root / "scenes" / f"{entry['id']}.json")
    validate_scene(scene, {item["id"] for item in read_json(root / "concepts.json")}, project=root.parent.parent)
    if scene["id"] != scene_id or scene["track_id"] != entry["track_id"]:
        raise ValueError("index does not match scene")
    brief = {"domain": "business", "simulated": True,
             "scenario": {"id": scene_id, "label": scene["label"], "category_id": "hiring", "category_label": "招聘面试与入职"},
             "track": {"id": entry["track_id"], "label": entry["track_label"]},
             "context": scene["context"], "assumptions": scene["assumptions"],
             "learner_brief": scene["roles"][role], "stages": scene["stages"],
             "terms": scene["terms"], "target_suggestions": scene["targets"], "concepts": scene["concepts"],
             "role": role, "level": level, "depth": depth, "pressure": pressure, "duration_minutes": duration,
             "adaptation": {"language": LANGUAGE_GUIDANCE[level], "technical": DEPTH_GUIDANCE[depth], "pressure": PRESSURE_GUIDANCE[pressure]},
             "controls": {"start": "I'm ready.", "end": "Let's wrap up."},
             "instructions": ["Use the ordinary duration-scaled vocabulary bank; these terms are seeds, not the full preview.",
                              "Keep English level independent from technical depth; distinguish language help from technical help.",
                              "Adapt target_suggestions to the selected role; interviewers need neutral elicitation, clarification and diagnosis frames.",
                              "Do not invent personal experience or reveal coach-only reference answers in the preview."]}
    if coach:
        teacher = scene["coach_only"]
        brief["coach_only"] = {**teacher,
            "followups": [item for item in teacher["followups"] if DEPTHS.index(item["depth"]) <= DEPTHS.index(depth)],
            "rubric": [item for item in teacher["rubric"] if DEPTHS.index(item["depth"]) <= DEPTHS.index(depth)],
            "counterpart": scene["roles"]["interviewer" if role == "candidate" else "candidate"],
            "complications": scene["complications"],
            "assessment_instructions": "Assess only the depth-filtered rubric and the selected learner role's criterion. The full reference answer may include deeper context; do not require it at lower depth or copy it into learner evidence. Complications must remain within the selected depth.",
            "followup_budget": 1 if duration <= 10 else 3 if duration < 40 else 6}
    return brief


def workbench_module():
    spec = importlib.util.spec_from_file_location("kouyu_workbench", PROJECT / "scripts" / "workbench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def review(data_dir: Path, root=ROOT, concept=None, scene=None):
    wb = workbench_module()
    path = data_dir / "workbench-data.json"
    state = read_json(path) if path.exists() else {"version": 2, "sessions": []}
    wb.validate_state(state)
    sessions = state["sessions"]
    known_scenes = {entry["id"] for entry in read_json(root / "index.json")["scenes"]}
    known_scenes.update(item.get("scenario", {}).get("id") for item in sessions)
    known_concepts = {entry["id"] for entry in read_json(root / "concepts.json")}
    known_concepts.update(item["concept_id"] for session in sessions for item in session.get("interview", {}).get("observations", []))
    if scene is not None and scene not in known_scenes:
        raise ValueError("unknown scene")
    if concept is not None and concept not in known_concepts:
        raise ValueError("unknown concept")
    selected = [item for item in sessions if scene is None or item.get("scenario", {}).get("id") == scene]
    observations = [item for item in wb.latest_technical(selected) if concept is None or item["concept_id"] == concept]
    candidates = []
    for item in observations:
        matches = search_scenes(root, concept=item["concept_id"], limit=100) if item["concept_id"] in {c["id"] for c in read_json(root / "concepts.json")} else []
        matches = [match for match in matches if any(
            criterion["concept_id"] == item["concept_id"] for criterion in load_scene(
                match["id"], root=root, role=item["role"], depth=item["depth"], coach=True)["coach_only"]["rubric"])]
        matches.sort(key=lambda match: match["id"] == item["scenario_id"])
        transfer = load_scene(matches[0]["id"], root=root, role=item["role"], depth=item["depth"], coach=True)["coach_only"]["transfer"] if matches else {
            "prompt": f"Revisit {item['label']} under the same agreed assumptions. Identify one changed failure condition, then explain the relevant boundary without help.",
            "changes": ["A custom drill is needed because no bundled rubric covers this concept at the observed depth."]}
        candidates.append({"concept_id": item["concept_id"], "depth": item["depth"], "role": item["role"],
                           "independent_retest_recommended": item["status"] != "met" or item["language_support"] != "none" or item["technical_support"] != "none",
                           "scene_ids": [match["id"] for match in matches[:3]],
                           "transfer": transfer,
                           "task": ("Ask a fictional candidate the transfer prompt, then diagnose their response with one neutral follow-up; assess only your questions and reasoning. " if item["role"] == "interviewer" else "Change one failure condition; reconfirm assumptions and explain independently. ") + "Keep the prompt within the selected depth and assess only this concept's applicable criterion. Do not repeat a model answer.",
                           "availability": "matching-scenes" if matches else "custom-drill-needed-at-this-depth"})
    return {"read_only": True, "archive_found": path.exists(), "observations": observations, "drills": candidates,
            "note": "Contextual evidence by concept + depth + role, not mastery scores or an automatic review schedule."}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("tracks", "concepts", "validate", "build-index"):
        commands.add_parser(name)
    listing = commands.add_parser("list")
    listing.add_argument("--track")
    listing.add_argument("--concept")
    listing.add_argument("--search", default="")
    listing.add_argument("--limit", type=int, default=6)
    showing = commands.add_parser("show")
    showing.add_argument("id")
    showing.add_argument("--role", choices=ROLES, default="candidate")
    showing.add_argument("--level", choices=LEVELS, default="intermediate")
    showing.add_argument("--depth", choices=DEPTHS, default="implementation")
    showing.add_argument("--duration", type=int, default=20)
    showing.add_argument("--pressure", choices=PRESSURES, default="moderate")
    showing.add_argument("--coach", action="store_true")
    revisiting = commands.add_parser("review")
    revisiting.add_argument("--data-dir", type=Path, default=Path.home() / "english-speaking-workbench")
    revisiting.add_argument("--concept")
    revisiting.add_argument("--scene")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command in {"tracks", "concepts"}:
            result = read_json(ROOT / f"{args.command}.json")
        elif args.command == "list":
            result = search_scenes(track=args.track, concept=args.concept, search=args.search, limit=args.limit)
        elif args.command == "show":
            result = load_scene(args.id, role=args.role, level=args.level, depth=args.depth, duration=args.duration, pressure=args.pressure, coach=args.coach)
        elif args.command == "review":
            result = review(args.data_dir, concept=args.concept, scene=args.scene)
        elif args.command == "build-index":
            index = index_from_content()
            (ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (ROOT / "catalog.md").write_text(catalog_markdown(index), encoding="utf-8")
            result = {"indexed": len(index["scenes"]), "catalog_updated": True}
        else:
            result = validate_library()
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"interview: {error}\n")
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
    print()


if __name__ == "__main__":
    main()
