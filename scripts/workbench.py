#!/usr/bin/env python3
"""Persist speaking sessions and serve the local, review-only workbench."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import tempfile
import threading
import webbrowser
from collections import defaultdict
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

VERSION = 2
MAX_BODY = 2 * 1024 * 1024
ALLOWED_STATUS = {"mastered", "developing", "needs_review", "not_observed"}
ALLOWED_SUPPORT = {"independent", "intent_hint", "keyword_hint", "model", "none"}
DOMAINS = {"business": "商务英语", "everyday": "日常英语", "other": "其他", "unclassified": "未分类"}
OUTCOMES = {"completed": "已完成", "partial": "部分完成", "deferred": "待确认", "declined": "合理拒绝 / 退出", "not_observed": "未观察"}
CRITERIA = {"met": "已做到", "partial": "部分做到", "unmet": "尚未做到", "not_observed": "未观察"}
DIMENSIONS = {"clarity": "清晰准确", "register": "语气得体", "interaction": "澄清与回应", "boundaries": "条件与授权边界", "closure": "收尾与下一步"}
INTERVIEW_ROLES = {"candidate": "候选人", "interviewer": "面试官"}
INTERVIEW_DEPTHS = {"foundation": "基础", "implementation": "实现", "system": "系统"}
INTERVIEW_PRESSURES = {"low": "低", "moderate": "中", "high": "高"}
LANGUAGE_SUPPORTS = {"none": "无语言提示", "intent": "意图提示", "keyword": "关键词提示", "model": "语言示范"}
TECHNICAL_SUPPORTS = {"none": "无技术提示", "probe": "定向追问", "hint": "技术思路提示", "solution": "参考解答"}


def empty_state() -> dict:
    return {"version": VERSION, "preferences": {"level": "intermediate", "hint_mode": "guided"}, "sessions": []}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def load_state(data_dir: Path) -> dict:
    path = data_dir / "workbench-data.json"
    if not path.exists():
        state = empty_state()
        atomic_json(path, state)
        return state
    with path.open(encoding="utf-8-sig") as handle:
        state = json.load(handle)
    validate_state(state)
    return state


def require(value: object, expected: type, label: str) -> None:
    if not isinstance(value, expected):
        raise ValueError(f"{label} must be {expected.__name__}")


def text(value: object, label: str, nonempty: bool = True) -> None:
    require(value, str, label)
    if nonempty and not value.strip():
        raise ValueError(f"{label} must not be empty")


def string_list(value: object, label: str) -> None:
    require(value, list, label)
    for item in value:
        text(item, label)


def choice(value: object, options, label: str) -> None:
    text(value, label)
    if value not in options:
        raise ValueError(f"{label} is invalid")


def validate_business(business: dict) -> None:
    require(business, dict, "business")
    if "industry" in business:
        require(business["industry"], dict, "business.industry")
        text(business["industry"].get("id"), "business.industry.id")
        text(business["industry"].get("label"), "business.industry.label")
    for field in ("context", "next_action"):
        if field in business:
            text(business[field], f"business.{field}")
    if "constraints" in business:
        string_list(business["constraints"], "business.constraints")
    if "outcome" in business:
        outcome = business["outcome"]
        require(outcome, dict, "business.outcome")
        choice(outcome.get("status"), OUTCOMES, "business.outcome.status")
        text(outcome.get("summary"), "business.outcome.summary")
    criteria = business.get("criteria", [])
    require(criteria, list, "business.criteria")
    for item in criteria:
        require(item, dict, "business.criteria item")
        text(item.get("criterion"), "business.criteria.criterion")
        choice(item.get("status"), CRITERIA, "business.criteria.status")
        if item["status"] != "not_observed":
            text(item.get("evidence"), "business.criteria.evidence")
        elif "evidence" in item:
            text(item["evidence"], "business.criteria.evidence", nonempty=False)
    feedback = business.get("feedback", [])
    require(feedback, list, "business.feedback")
    if len(feedback) > 5:
        raise ValueError("business.feedback may contain at most five items")
    seen = set()
    for item in feedback:
        require(item, dict, "business.feedback item")
        dimension = item.get("dimension")
        choice(dimension, DIMENSIONS, "business.feedback.dimension")
        if dimension in seen:
            raise ValueError("duplicate business feedback dimension")
        seen.add(dimension)
        for field in ("observation", "evidence", "suggestion"):
            text(item.get(field), f"business.feedback.{field}")


def descriptive_id(value: object, label: str) -> None:
    text(value, label)
    if not re.fullmatch(r"[a-z][a-z0-9-]*", value):
        raise ValueError(f"{label} must be a safe descriptive slug")


def validate_interview(interview: dict) -> None:
    require(interview, dict, "interview")
    track = interview.get("track")
    require(track, dict, "interview.track")
    descriptive_id(track.get("id"), "interview.track.id")
    text(track.get("label"), "interview.track.label")
    choice(interview.get("role"), INTERVIEW_ROLES, "interview.role")
    choice(interview.get("depth"), INTERVIEW_DEPTHS, "interview.depth")
    choice(interview.get("pressure"), INTERVIEW_PRESSURES, "interview.pressure")
    question_ids = interview.get("question_ids")
    require(question_ids, list, "interview.question_ids")
    questions = set()
    for question_id in question_ids:
        descriptive_id(question_id, "interview.question_ids item")
        if question_id in questions:
            raise ValueError("duplicate interview question id")
        questions.add(question_id)
    observations = interview.get("observations")
    require(observations, list, "interview.observations")
    concepts = set()
    for item in observations:
        require(item, dict, "interview.observations item")
        descriptive_id(item.get("concept_id"), "interview.observations.concept_id")
        if item["concept_id"] in concepts:
            raise ValueError("duplicate interview concept observation")
        concepts.add(item["concept_id"])
        text(item.get("label"), "interview.observations.label")
        descriptive_id(item.get("question_id"), "interview.observations.question_id")
        if item["question_id"] not in questions:
            raise ValueError("interview observation question_id must occur in question_ids")
        choice(item.get("status"), CRITERIA, "interview.observations.status")
        choice(item.get("language_support"), LANGUAGE_SUPPORTS, "interview.observations.language_support")
        choice(item.get("technical_support"), TECHNICAL_SUPPORTS, "interview.observations.technical_support")
        unobserved = item["status"] == "not_observed"
        if unobserved and (item["language_support"] != "none" or item["technical_support"] != "none"):
            raise ValueError("not_observed interview observations require supports none")
        for field in ("evidence", "observation", "suggestion"):
            if not unobserved:
                text(item.get(field), f"interview.observations.{field}")
            elif field in item:
                text(item[field], f"interview.observations.{field}", nonempty=False)
                if item[field].strip():
                    raise ValueError(f"not_observed interview {field} must be absent or empty")


def validate_session(session: dict) -> None:
    require(session, dict, "session")
    for key in ("id", "created_at", "topic", "duration_minutes", "level", "hint_mode", "targets"):
        if key not in session:
            raise ValueError(f"missing required field: {key}")
    text(session["id"], "id")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", session["id"]):
        raise ValueError("id may contain only letters, digits, dot, underscore, and hyphen")
    text(session["created_at"], "created_at")
    require(session["topic"], dict, "topic")
    text(session["topic"].get("id"), "topic.id")
    text(session["topic"].get("label"), "topic.label")
    duration = session["duration_minutes"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 1 <= duration <= 240:
        raise ValueError("duration_minutes must be between 1 and 240")
    choice(session["level"], {"beginner", "intermediate", "advanced"}, "level")
    choice(session["hint_mode"], {"immersion", "guided", "learning"}, "hint_mode")
    require(session["targets"], list, "targets")
    for index, target in enumerate(session["targets"]):
        require(target, dict, f"targets[{index}]")
        text(target.get("expression"), f"targets[{index}].expression")
        choice(target.get("status"), ALLOWED_STATUS, f"targets[{index}].status")
        choice(target.get("support", "none"), ALLOWED_SUPPORT, f"targets[{index}].support")
        for key in ("evidence", "meaning_zh"):
            if key in target:
                text(target[key], f"targets[{index}].{key}", nonempty=False)
    repairs = session.get("repairs", [])
    require(repairs, list, "repairs")
    for index, repair in enumerate(repairs):
        require(repair, dict, f"repairs[{index}]")
        for key in ("learner", "natural", "reason_zh"):
            text(repair.get(key), f"repairs[{index}].{key}")
    string_list(session.get("focus_next", []), "focus_next")
    if "next_drill" in session:
        text(session["next_drill"], "next_drill", nonempty=False)
    if "mission_completed" in session:
        require(session["mission_completed"], bool, "mission_completed")
    if "domain" in session:
        choice(session["domain"], {"business", "everyday", "other"}, "domain")
    if "scenario" in session:
        require(session["scenario"], dict, "scenario")
        for key in ("id", "category_id", "category_label"):
            text(session["scenario"].get(key), f"scenario.{key}")
    if "roles" in session:
        require(session["roles"], dict, "roles")
        for key in ("learner", "coach"):
            text(session["roles"].get(key), f"roles.{key}")
    if "business" in session:
        if session.get("domain") != "business":
            raise ValueError("business data requires domain business")
        validate_business(session["business"])
    if "interview" in session:
        if session.get("domain") != "business":
            raise ValueError("interview data requires domain business")
        if "scenario" not in session:
            raise ValueError("interview data requires a nonempty scenario")
        descriptive_id(session["scenario"]["id"], "interview scenario.id")
        validate_interview(session["interview"])
    if "pronunciation" in session:
        require(session["pronunciation"], dict, "pronunciation")
        choice(session["pronunciation"].get("status"), {"observed", "not_observed"}, "pronunciation.status")
        string_list(session["pronunciation"].get("notes", []), "pronunciation.notes")


def validate_state(state: dict) -> None:
    require(state, dict, "state")
    version = state.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version not in {1, VERSION}:
        raise ValueError("unsupported workbench version; preserve the file and upgrade the skill")
    require(state.get("sessions"), list, "sessions")
    ids = set()
    for session in state["sessions"]:
        validate_session(session)
        if session["id"] in ids:
            raise ValueError(f"duplicate session id: {session['id']}")
        ids.add(session["id"])


def group_key(session: dict) -> tuple[str, str]:
    return (session.get("domain") or "unclassified", session.get("scenario", {}).get("id") or session["topic"]["id"])


def session_time(session: dict) -> float:
    try:
        stamp = datetime.fromisoformat(session.get("created_at", "").replace("Z", "+00:00"))
        return (stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)).timestamp()
    except (ValueError, TypeError, OverflowError, OSError):
        return float("-inf")


def latest_targets(items: list[dict]) -> list[dict]:
    """Use newest evidence per scene; an unobserved attempt does not erase evidence."""
    latest: dict[tuple, dict] = {}
    for session in sorted(items, key=session_time, reverse=True):
        for target in session.get("targets", []):
            expression = target.get("expression", "").strip()
            key = (*group_key(session), expression)
            if expression and (key not in latest or (latest[key].get("status") == "not_observed" and target.get("status") != "not_observed")):
                latest[key] = target
    return list(latest.values())


def latest_technical(sessions: list[dict]) -> list[dict]:
    """Latest contextual observation per concept, depth and learner role, across scenes."""
    latest: dict[tuple, tuple[tuple[int, int], dict]] = {}
    for session_rank, session in enumerate(sorted(sessions, key=session_time, reverse=True)):
        interview = session.get("interview")
        if not interview:
            continue
        for observation_rank, observation in enumerate(interview["observations"]):
            rank = (session_rank, observation_rank)
            key = (observation["concept_id"], interview["depth"], interview["role"])
            previous = latest.get(key)
            if previous is None or (previous[1]["status"] == "not_observed" and observation["status"] != "not_observed"):
                latest[key] = (rank, {
                    **observation,
                    "depth": interview["depth"],
                    "role": interview["role"],
                    "track": {"id": interview["track"]["id"], "label": interview["track"]["label"]},
                    "session_id": session["id"],
                    "created_at": session["created_at"],
                    "scenario_id": session["scenario"]["id"],
                })
    return [entry for _, entry in sorted(latest.values(), key=lambda item: item[0])]


def recent_repairs(items: list[dict], limit: int = 3) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    result = []
    for session in items:
        for repair in session.get("repairs", []):
            key = (repair["learner"], repair["natural"])
            if key not in seen:
                seen.add(key)
                result.append(repair)
                if len(result) == limit:
                    return result
    return result


def md(value: object) -> str:
    value = html.escape(str(value), quote=False).replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def render_business(business: dict) -> list[str]:
    lines = []
    if business.get("industry"):
        lines.append(f"- 行业：{md(business['industry']['label'])}")
    if business.get("context"):
        lines.append(f"- 模拟背景：{md(business['context'])}")
    for constraint in business.get("constraints", []):
        lines.append(f"- 条件与边界：{md(constraint)}")
    if business.get("outcome"):
        outcome = business["outcome"]
        lines.append(f"- 商务结果：{OUTCOMES[outcome['status']]}；{md(outcome['summary'])}")
    if business.get("criteria"):
        lines += ["", "### 沟通任务证据", ""]
        for item in business["criteria"]:
            evidence = f"；证据：{md(item['evidence'])}" if item.get("evidence") else ""
            lines.append(f"- {CRITERIA[item['status']]} · {md(item['criterion'])}{evidence}")
    if business.get("feedback"):
        lines += ["", "### 商务沟通反馈", ""]
        for item in business["feedback"]:
            lines += [f"- {DIMENSIONS[item['dimension']]}：{md(item['observation'])}",
                      f"  - 证据：{md(item['evidence'])}", f"  - 下次尝试：{md(item['suggestion'])}"]
    if business.get("next_action"):
        lines += ["", f"- 下一步：{md(business['next_action'])}"]
    return lines


def render_technical_observation(item: dict) -> list[str]:
    lines = [f"- {md(item['label'])}（{md(item['concept_id'])}）：{CRITERIA[item['status']]}；问题：{md(item['question_id'])}",
             f"  - 支持：{LANGUAGE_SUPPORTS[item['language_support']]}；{TECHNICAL_SUPPORTS[item['technical_support']]}（language_support={md(item['language_support'])}；technical_support={md(item['technical_support'])}）"]
    if item["status"] != "not_observed":
        lines += [f"  - 证据：{md(item['evidence'])}", f"  - 观察：{md(item['observation'])}", f"  - 建议：{md(item['suggestion'])}"]
    return lines


def render_interview(session: dict) -> list[str]:
    interview = session.get("interview")
    if not interview:
        return []
    lines = ["", "### 本次技术面试", "",
             f"- 方向：{md(interview['track']['label'])}（{md(interview['track']['id'])}）",
             f"- 技术角色：{INTERVIEW_ROLES[interview['role']]}；技术深度：{INTERVIEW_DEPTHS[interview['depth']]}；压力：{INTERVIEW_PRESSURES[interview['pressure']]}",
             f"- 问题 ID：{'、'.join(md(item) for item in interview['question_ids']) or '未记录'}",
             "- 技术评价独立于英语表达；仅为当前条件、角色与深度下的观察，不推断通用掌握度。"]
    for observation in interview["observations"]:
        lines.extend(render_technical_observation(observation))
    if not interview["observations"]:
        lines.append("- 本次未记录技术观察，不推断表现。")
    return lines


def render_technical_review(sessions: list[dict]) -> list[str]:
    if not any("interview" in session for session in sessions):
        return []
    lines = ["## 跨场景技术回顾", "", "> 按概念、技术深度与角色分别保留最新证据；未观察不覆盖旧证据，受提示的回答不视作独立完成。不计入英语表达比例。", ""]
    entries = latest_technical(sessions)
    for entry in entries:
        lines += [f"### {md(entry['label'])} · {INTERVIEW_DEPTHS[entry['depth']]} · {INTERVIEW_ROLES[entry['role']]}", "",
                  f"- 方向：{md(entry['track']['label'])}（{md(entry['track']['id'])}）",
                  f"- 来源场景：{md(entry['scenario_id'])}；归档：{md(entry['session_id'])}；时间：{md(entry['created_at'])}"]
        lines.extend(render_technical_observation(entry))
        lines.append("")
    if not entries:
        lines += ["尚无技术观察，不推断表现。", ""]
    return lines


def render_dashboard(state: dict) -> str:
    sessions = sorted(state["sessions"], key=session_time, reverse=True)
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for session in sessions:
        grouped[group_key(session)].append(session)
    lines = ["# 口语复习台", "", f"> 已归档 {len(sessions)} 次练习。掌握度按场景区分；未观察不计入已评估表达。", ""]
    if not sessions:
        lines += ["还没有练习记录。完成第一次场景对话后，这里会自动生成复习内容。", ""]
    for (domain, _), items in grouped.items():
        latest = items[0]
        targets = latest_targets(items)
        observed = [target for target in targets if target["status"] != "not_observed"]
        mastered = sum(target["status"] == "mastered" for target in observed)
        review = [target["expression"] for target in observed if target["status"] in {"developing", "needs_review"}]
        title = f"{latest['topic'].get('emoji', '💬')} {latest['topic']['label']}"
        lines += [f"## {md(title)}", "", f"- 领域：{DOMAINS[domain]}", f"- 练习次数：{len(items)}",
                  f"- 已掌握表达：{mastered}/{len(observed)}（已观察）" if observed else "- 表达状态：无可评估表达",
                  f"- 未观察表达：{len(targets) - len(observed)}", f"- 最近练习：{md(latest['created_at'])}"]
        if latest.get("scenario"):
            lines.append(f"- 业务类别：{md(latest['scenario']['category_label'])}")
        if latest.get("roles"):
            lines.append(f"- 本次角色：{md(latest['roles']['learner'])}")
        if review:
            lines.append(f"- 下次复习：{'、'.join(md(item) for item in dict.fromkeys(review))}")
        if latest.get("business"):
            lines.extend(render_business(latest["business"]))
        elif "mission_completed" in latest:
            lines.append(f"- 任务状态：{'已完成' if latest['mission_completed'] else '未完成'}")
        lines.extend(render_interview(latest))
        if latest.get("focus_next"):
            lines.append(f"- 下次重点：{'、'.join(md(item) for item in latest['focus_next'][:3])}")
        if latest.get("next_drill"):
            lines.append(f"- 迁移练习：{md(latest['next_drill'])}")
        repairs = recent_repairs(items)
        if repairs:
            lines += ["", "### 表达回顾", ""]
            for repair in repairs:
                lines.append(f"- {md(repair['learner'])} → {md(repair['natural'])}：{md(repair['reason_zh'])}")
        lines.append("")
    lines.extend(render_technical_review(sessions))
    lines += ["---", "", f"更新时间：{datetime.now().astimezone().isoformat(timespec='seconds')}", ""]
    return "\n".join(lines)


def save_state(data_dir: Path, state: dict) -> None:
    validate_state(state)
    state["version"] = VERSION
    atomic_json(data_dir / "workbench-data.json", state)
    (data_dir / "复习台.md").write_text(render_dashboard(state), encoding="utf-8")


def init_workbench(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    save_state(data_dir, load_state(data_dir))
    print(f"Workbench ready: {data_dir.resolve()}")


def archive_session(data_dir: Path, input_path: Path) -> None:
    with input_path.open(encoding="utf-8-sig") as handle:
        session = json.load(handle)
    validate_session(session)
    state = load_state(data_dir)
    existing = next((item for item in state["sessions"] if item["id"] == session["id"]), None)
    if existing is not None and existing != session:
        raise ValueError(f"session id already exists with different data: {session['id']}")
    sessions_dir = data_dir / "sessions"
    session_path = sessions_dir / f"{session['id']}.json"
    if session_path.exists():
        with session_path.open(encoding="utf-8-sig") as handle:
            if json.load(handle) != session:
                raise ValueError(f"individual session file conflicts: {session['id']}")
    if existing is None:
        state["sessions"].append(session)
    atomic_json(session_path, session)
    save_state(data_dir, state)
    print(f"Archived: {session['id']}")


def make_handler(data_dir: Path, static_dir: Path):
    state_lock = threading.Lock()

    class WorkbenchHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static_dir), **kwargs)

        def send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/health":
                self.send_json({"ok": True, "version": VERSION})
                return
            if path == "/api/state":
                try:
                    self.send_json(load_state(data_dir))
                except Exception as error:
                    self.send_json({"error": str(error)}, 500)
                return
            super().do_GET()

        def do_PUT(self):
            if urlparse(self.path).path != "/api/preferences":
                self.send_error(404)
                return
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                self.send_json({"error": "cross-origin writes are not allowed"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY:
                    raise ValueError("invalid request size")
                preferences = json.loads(self.rfile.read(length).decode("utf-8"))
                require(preferences, dict, "preferences")
                with state_lock:
                    state = load_state(data_dir)
                    state["preferences"] = preferences
                    save_state(data_dir, state)
                self.send_json({"ok": True})
            except (ValueError, UnicodeError) as error:
                self.send_json({"error": str(error)}, 400)
            except Exception as error:
                self.send_json({"error": str(error)}, 500)

        def log_message(self, format_string, *args):
            print(f"[{self.log_date_time_string()}] {format_string % args}")

    return WorkbenchHandler


def serve(data_dir: Path, host: str, port: int, open_browser: bool) -> None:
    init_workbench(data_dir)
    static_dir = Path(__file__).resolve().parent.parent / "assets" / "workbench"
    if not (static_dir / "index.html").exists():
        raise FileNotFoundError(f"workbench UI missing: {static_dir}")
    server = ThreadingHTTPServer((host, port), make_handler(data_dir, static_dir))
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}/"
    print(f"Listening on {url}")
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "archive"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--data-dir", type=Path, default=Path.home() / "english-speaking-workbench")
        if command == "archive":
            sub.add_argument("--input", type=Path, required=True)
    sub = subparsers.add_parser("serve")
    sub.add_argument("--data-dir", type=Path, default=Path.home() / "english-speaking-workbench")
    sub.add_argument("--host", default="127.0.0.1")
    sub.add_argument("--port", type=int, default=8765)
    sub.add_argument("--no-open", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_workbench(args.data_dir)
        elif args.command == "archive":
            archive_session(args.data_dir, args.input)
        else:
            serve(args.data_dir, args.host, args.port, not args.no_open)
    except (ValueError, OSError) as error:
        parser.exit(2, f"workbench: {error}\n")


if __name__ == "__main__":
    main()
