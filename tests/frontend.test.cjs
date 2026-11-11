"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {filterSessions, groupSessions, latestTargets, latestTechnical, targetSummary, groupKey, sortSessions,
  interviewHtml, technicalReviewHtml, cardHtml, historyHtml} = require("../assets/workbench/app.js");
const fixture = name => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", `${name}.json`), "utf8"));
const business = () => fixture("business-session");
const legacy = () => fixture("legacy-session");
const interview = () => fixture("interview-session");
const newerInterview = (overrides = {}) => ({...interview(), id: "synthetic-newer-interview", created_at: "2026-11-12T11:00:00+08:00", ...overrides});


test("legacy remains unclassified; filters act on sessions before grouping", () => {
  const a = legacy(), b = business(), c = {...legacy(), id: "daily", domain: "everyday"};
  const sessions = [a, b, c];
  assert.deepEqual(filterSessions(sessions, {domain: "unclassified"}), [a]);
  assert.deepEqual(filterSessions(sessions, {domain: "business"}), [b]);
  assert.deepEqual(filterSessions(sessions, {domain: "everyday"}), [c]);
  assert.equal(filterSessions(sessions, {domain: "all"}).length, 3);
  assert.equal(filterSessions(sessions, {domain: "business", category: "negotiation", industry: "software"}).length, 1);
  assert.equal(filterSessions(sessions, {category: "not-found"}).length, 0);
});

test("search includes business evidence, roles, industry, domain and multiple words", () => {
  const sessions = [legacy(), business()];
  assert.equal(filterSessions(sessions, {search: "软件 授权"}).length, 1);
  assert.equal(filterSessions(sessions, {search: "ACCOUNT MANAGER"}).length, 1);
  assert.equal(filterSessions(sessions, {search: "未分类"}).length, 1);
  assert.equal(filterSessions(sessions, {search: "no-match-xyz"}).length, 0);
  assert.equal(filterSessions(sessions, {search: "　软件　"}).length, 1);
});

test("stable scene ID survives rename; different IDs never merge by title", () => {
  const a = business(), b = {...business(), id: "renamed", topic: {...business().topic, label: "新标题"}};
  assert.equal(groupKey(a), groupKey(b));
  assert.equal(groupSessions([a, b]).size, 1);
  b.scenario = {...b.scenario, id: "another"};
  b.topic.label = a.topic.label;
  assert.notEqual(groupKey(a), groupKey(b));
  assert.equal(groupSessions([a, b]).size, 2);
});

test("prototype-like IDs are safe Map keys", () => {
  const sessions = ["__proto__", "constructor", "toString"].map((id, i) => ({...legacy(), id: `test-${i}`, topic: {id, label: "same"}}));
  assert.equal(groupSessions(sessions).size, 3);
  assert.equal(groupSessions(sessions).get(groupKey(sessions[0])).length, 1);
});

test("missing legacy scene IDs stay distinct by archive identity", () => {
  const a = {id: "a", topic: {label: "same"}}, b = {id: "b", topic: {label: "same"}};
  assert.notEqual(groupKey(a), groupKey(b));
  assert.equal(groupSessions([a, b]).size, 2);
  assert.notEqual(groupKey({topic: {label: "a"}}), groupKey({topic: {label: "b"}}));
});

test("same phrase across scenes has independent mastery", () => {
  const targets = latestTargets([legacy(), business()]);
  const shared = targets.filter(target => target.expression === "Could you clarify that?");
  assert.equal(shared.length, 2);
  assert.deepEqual(new Set(shared.map(target => target.status)), new Set(["mastered", "needs_review"]));
  const summary = targetSummary(targets);
  assert.equal(summary.mastered, 2);
  assert.equal(summary.observed, 3);
  assert.equal(summary.unobserved, 2);
});

test("new unobserved attempt retains older observed state and actual evidence", () => {
  const old = business(), newer = structuredClone(old);
  newer.id = "newer";
  newer.created_at = "2026-11-12T10:00:00+08:00";
  newer.targets[0].status = "not_observed";
  newer.targets[0].evidence = "";
  let targets = latestTargets([old, newer]);
  assert.equal(targets[0].status, "needs_review");
  assert.equal(targets[0].evidence, old.targets[0].evidence);
  newer.targets[0].status = "mastered";
  assert.equal(latestTargets([old, newer])[0].status, "mastered");
});

test("never-observed target retains the latest unobserved record", () => {
  const old = business(), newer = structuredClone(old);
  for (const target of old.targets) target.status = "not_observed";
  for (const target of newer.targets) target.status = "not_observed";
  newer.id = "newest-unobserved";
  newer.created_at = "2026-11-12T10:00:00+08:00";
  newer.targets[0].evidence = "Synthetic newest unobserved note";
  assert.equal(latestTargets([old, newer])[0].evidence, "Synthetic newest unobserved note");
});

test("denominator excludes unobserved and future unknown statuses", () => {
  assert.equal(targetSummary([{expression: "x", status: "not_observed"}]).percent, null);
  const summary = targetSummary([
    {expression: "x", status: "mastered"}, {expression: "y", status: "not_observed"},
    {expression: "z", status: "future-state"}, {expression: "w", status: "developing"}
  ]);
  assert.equal(summary.percent, 50);
  assert.equal(summary.observed, 2);
  assert.equal(summary.unrated, 1);
  assert.equal(summary.unobserved, 1);
});

test("actual time sorting handles UTC offsets and invalid dates without mutation", () => {
  const a = {...legacy(), id: "a", created_at: "2026-11-11T10:00:00+08:00"};
  const b = {...legacy(), id: "b", created_at: "2026-11-11T03:00:00Z"};
  const c = {...legacy(), id: "c", created_at: "not-a-date"};
  const input = [c, a, b];
  assert.deepEqual(sortSessions(input).map(item => item.id), ["b", "a", "c"]);
  assert.deepEqual(input.map(item => item.id), ["c", "a", "b"]);
  assert.deepEqual(sortSessions([a, {...a, id: "same-time"}]).map(item => item.id), ["a", "same-time"]);
});

test("optional and malformed data never crash pure review helpers", () => {
  for (const value of [null, undefined, {}, [null, {}, "x", {topic: null, business: {}}]]) {
    assert.doesNotThrow(() => filterSessions(value));
    assert.doesNotThrow(() => groupSessions(value));
    assert.doesNotThrow(() => latestTargets(value));
    assert.doesNotThrow(() => latestTechnical(value));
    assert.doesNotThrow(() => technicalReviewHtml(value));
    assert.doesNotThrow(() => interviewHtml(value));
    assert.doesNotThrow(() => targetSummary(value));
  }
});

test("technical archive fixture is synthetic and language denominators remain independent", () => {
  const current = interview();
  assert.equal(current.synthetic, true);
  assert.match(current.id, /^synthetic/);
  assert.equal(current.domain, "business");
  assert.equal(current.scenario.category_id, "hiring");
  assert.equal(current.scenario.id, "int-web3-broadcast-timeout");
  assert.equal(current.interview.track.id, "web3");
  const withoutTechnical = structuredClone(current);
  delete withoutTechnical.interview;
  assert.deepEqual(latestTargets([legacy(), business(), current]), latestTargets([legacy(), business(), withoutTechnical]));
  assert.deepEqual(targetSummary(latestTargets([current])), targetSummary(latestTargets([withoutTechnical])));
  const before = structuredClone([legacy(), business(), current]);
  const entries = latestTechnical(before);
  assert.equal(entries.length, 3);
  assert.deepEqual(Object.keys(entries[0]).sort(), [...Object.keys(current.interview.observations[0]),
    "depth", "role", "track", "session_id", "created_at", "scenario_id"].sort());
  assert.deepEqual(entries[0].track, current.interview.track);
  assert.equal(entries[0].session_id, current.id);
  assert.deepEqual(before, [legacy(), business(), current]);
});

test("new unobserved technical attempt preserves older evidence and provenance in newest-first order", () => {
  const old = interview(), newer = newerInterview();
  newer.scenario.id = "int-custom-new-scene";
  const observation = newer.interview.observations[0];
  for (const key of ["evidence", "observation", "suggestion"]) delete observation[key];
  Object.assign(observation, {status: "not_observed", language_support: "none", technical_support: "none"});
  const entries = latestTechnical([old, newer]);
  assert.deepEqual(entries.map(item => item.concept_id), ["state-authority", "finality", "timeout-semantics"]);
  assert.equal(entries[0].session_id, newer.id);
  assert.equal(entries[1].session_id, newer.id);
  assert.equal(entries[1].status, "not_observed");
  assert.equal(entries[2].session_id, old.id);
  assert.equal(entries[2].created_at, old.created_at);
  assert.equal(entries[2].scenario_id, old.scenario.id);
  assert.equal(entries[2].evidence, old.interview.observations[0].evidence);
});

test("technical concepts merge across scenes but role and depth stay separate", () => {
  const old = interview(), anotherScene = newerInterview();
  anotherScene.scenario.id = "int-custom-transfer";
  const interviewer = newerInterview({id: "synthetic-interviewer"});
  interviewer.interview.role = "interviewer";
  const system = newerInterview({id: "synthetic-system"});
  system.interview.depth = "system";
  const result = latestTechnical([old, anotherScene, interviewer, system]);
  assert.equal(result.length, 9);
  assert.deepEqual(new Set(result.map(item => `${item.role}/${item.depth}`)),
    new Set(["candidate/implementation", "interviewer/implementation", "candidate/system"]));
  assert.equal(result.find(item => item.concept_id === "timeout-semantics" && item.role === "candidate" && item.depth === "implementation").scenario_id,
    "int-custom-transfer");
});

test("new assisted technical evidence never falls back to an independent old success", () => {
  const old = interview(), newer = newerInterview();
  Object.assign(old.interview.observations[0], {language_support: "none", technical_support: "none"});
  Object.assign(newer.interview.observations[0], {status: "partial", language_support: "model", technical_support: "solution"});
  const result = latestTechnical([old, newer])[0];
  assert.equal(result.session_id, newer.id);
  assert.equal(result.status, "partial");
  assert.equal(result.language_support, "model");
  assert.equal(result.technical_support, "solution");
  const rendered = technicalReviewHtml([old, newer]);
  assert.match(rendered, /语言示范（model）/);
  assert.match(rendered, /参考解答（solution）/);
  assert.match(rendered, /受提示的回答不视作独立完成/);
});

test("technical aggregation uses actual instants and retains input order at equal timestamps", () => {
  const first = newerInterview({id: "synthetic-first", created_at: "2026-11-11T03:00:00Z"});
  const equal = newerInterview({id: "synthetic-equal", created_at: "2026-11-11T11:00:00+08:00"});
  const older = newerInterview({id: "synthetic-older", created_at: "2026-11-11T10:00:00+08:00"});
  const invalid = newerInterview({id: "synthetic-invalid", created_at: "invalid"});
  assert.ok(latestTechnical([invalid, first, equal, older]).every(item => item.session_id === first.id));
  assert.ok(latestTechnical([equal, first, older]).every(item => item.session_id === equal.id));
  first.interview.observations.reverse();
  assert.deepEqual(latestTechnical([equal, first]).map(item => item.concept_id), equal.interview.observations.map(item => item.concept_id));
});

test("technical UI shows current metadata, separate support, provenance and history without feedback inflation", () => {
  const old = interview(), newer = newerInterview();
  newer.interview.role = "interviewer";
  const html = interviewHtml(newer);
  for (const expected of ["interview-review", "technical-observation", "Web3 后端", "面试官", "实现", "中", "broadcast-anchor", "超时语义", "关键词提示（keyword）", "无技术提示（none）", "定向追问（probe）", "Synthetic learner utterance", "未观察，不推断技术表现"])
    assert.ok(html.includes(expected), expected);
  const aggregate = technicalReviewHtml([legacy(), old, newer]);
  assert.ok(aggregate.includes(old.id));
  assert.ok(aggregate.includes(newer.id));
  assert.ok(aggregate.includes(old.scenario.id));
  assert.ok(aggregate.includes(newer.created_at));
  assert.match(aggregate, /technical-context/);
  assert.match(aggregate, /不计入英语表达比例/);
  const card = cardHtml([newer, old], "synthetic-heading");
  assert.equal((card.match(/class="feedback-item"/g) || []).length, 10);
  assert.match(card, /本次技术面试/);
  assert.match(card, /技术证据回顾（当前筛选内）/);
  const history = historyHtml([newer, old]);
  assert.match(history, /history-entry/);
  assert.match(history, /本次技术面试/);
  assert.ok(history.includes(old.interview.observations[0].evidence));
  assert.match(history, /候选人/);
});

test("technical review respects the selected session slice and local search", () => {
  const old = interview(), newer = newerInterview();
  newer.scenario.id = "int-custom-searchable";
  newer.interview.observations[0].evidence = "Synthetic latest exclusive-evidence-marker";
  const selected = filterSessions([legacy(), business(), old, newer], {domain: "business", category: "hiring", search: "Web3 exclusive-evidence-marker"});
  assert.deepEqual(selected, [newer]);
  const aggregate = technicalReviewHtml(selected);
  assert.ok(aggregate.includes("exclusive-evidence-marker"));
  assert.ok(!aggregate.includes(old.id));
  assert.equal(groupSessions(selected).size, 1);
  assert.equal(latestTechnical(selected).length, 3);
});

test("technical display safely escapes every arbitrary label and evidence field", () => {
  const current = interview();
  const malicious = '<img src=x onerror="alert(1)"> & \'quoted\'';
  current.interview.track.label = malicious;
  for (const key of ["label", "evidence", "observation", "suggestion"]) current.interview.observations[0][key] = malicious;
  for (const html of [interviewHtml(current), technicalReviewHtml([current]), cardHtml([current], malicious)]) {
    assert.doesNotMatch(html, /<img|<script|onerror="alert/);
    assert.ok(html.includes("&lt;img"));
    assert.ok(html.includes("&quot;alert(1)&quot;"));
    assert.ok(html.includes("&#39;quoted&#39;"));
  }
});

test("empty technical observations are explicit, and old sessions never receive fabricated sections", () => {
  const current = interview();
  current.interview.observations = [];
  current.interview.question_ids = [];
  assert.deepEqual(latestTechnical([current]), []);
  assert.match(interviewHtml(current), /未记录技术观察，不推断表现/);
  assert.match(technicalReviewHtml([current]), /未记录技术观察，不推断表现/);
  assert.equal(interviewHtml(legacy()), "");
  assert.equal(interviewHtml(business()), "");
  assert.equal(technicalReviewHtml([legacy(), business()]), "");
});

test("source keeps user text escaping and browser startup guard", () => {
  const source = fs.readFileSync(path.join(__dirname, "../assets/workbench/app.js"), "utf8");
  assert.match(source, /typeof document !== "undefined"/);
  assert.match(source, /escapeHtml\(.*?evidence/);
  assert.doesNotMatch(source, /localStorage|sessionStorage|https:\/\//);
});
