"use strict";

const DOMAIN_LABELS = new Map([
  ["business", "商务英语"], ["everyday", "日常英语"], ["other", "其他"], ["unclassified", "未分类"]
]);
const TARGET_STATUSES = new Map([
  ["mastered", {label: "已掌握", symbol: "✓", className: "met"}],
  ["developing", {label: "形成中", symbol: "◐", className: "partial"}],
  ["needs_review", {label: "待复习", symbol: "↻", className: "unmet"}],
  ["not_observed", {label: "未观察", symbol: "—", className: "neutral"}]
]);
const OUTCOME_STATUSES = new Map([
  ["completed", {label: "任务已完成", symbol: "✓", className: "met"}],
  ["partial", {label: "部分完成", symbol: "◐", className: "partial"}],
  ["deferred", {label: "待确认", symbol: "→", className: "neutral"}],
  ["declined", {label: "合理拒绝 / 退出", symbol: "—", className: "neutral"}],
  ["not_observed", {label: "未观察", symbol: "—", className: "neutral"}]
]);
const CRITERION_STATUSES = new Map([
  ["met", {label: "已达成", symbol: "✓", className: "met"}],
  ["partial", {label: "部分达成", symbol: "◐", className: "partial"}],
  ["unmet", {label: "未达成", symbol: "×", className: "unmet"}],
  ["not_observed", {label: "未观察", symbol: "—", className: "neutral"}]
]);
const FEEDBACK_DIMENSIONS = new Map([
  ["clarity", "表达清晰度"], ["register", "语域得体"], ["interaction", "互动推进"],
  ["boundaries", "边界管理"], ["closure", "收口闭环"]
]);
const SUPPORT_LABELS = new Map([
  ["independent", "独立表达"], ["intent_hint", "意图提示"], ["keyword_hint", "关键词提示"],
  ["model", "示范句提示"], ["none", "无提示记录"]
]);
const INTERVIEW_ROLES = new Map([["candidate", "候选人"], ["interviewer", "面试官"]]);
const INTERVIEW_DEPTHS = new Map([["foundation", "基础"], ["implementation", "实现"], ["system", "系统"]]);
const INTERVIEW_PRESSURES = new Map([["low", "低"], ["moderate", "中"], ["high", "高"]]);
const LANGUAGE_SUPPORTS = new Map([["none", "无语言提示"], ["intent", "意图提示"], ["keyword", "关键词提示"], ["model", "语言示范"]]);
const TECHNICAL_SUPPORTS = new Map([["none", "无技术提示"], ["probe", "定向追问"], ["hint", "技术思路提示"], ["solution", "参考解答"]]);
const HISTORY_LIMIT = 8;
const isRecord = value => value !== null && typeof value === "object" && !Array.isArray(value);
const record = value => isRecord(value) ? value : {};
const list = value => Array.isArray(value) ? value : [];
const text = value => typeof value === "string" ? value.trim() : "";
const strings = value => list(value).map(text).filter(Boolean);
const HTML_ESCAPES = new Map([
  ["&", "&amp;"], ["<", "&lt;"], [">", "&gt;"], ["'", "&#39;"], ['"', "&quot;"]
]);
const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => HTML_ESCAPES.get(char));

// Canonical snapshots ignore JSON property order, but preserve archive array order.
function stableSerialize(value) {
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableSerialize(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

function domainOf(session) {
  const domain = record(session).domain;
  return DOMAIN_LABELS.has(domain) ? domain : "unclassified";
}

// IDs, not display labels, define a scene. Unidentified legacy records stay separate
// by archive ID (or full content if even that ID is absent), never by a shared title.
function groupKey(session) {
  const item = record(session);
  const id = text(record(item.scenario).id) || text(record(item.topic).id);
  if (id) return JSON.stringify([domainOf(item), "scene", id]);
  const archiveId = text(item.id);
  return JSON.stringify([domainOf(item), archiveId ? "legacy-session" : "legacy-content", archiveId || stableSerialize(item)]);
}

function dateValue(value) {
  if (!text(value)) return null;
  const time = Date.parse(value);
  return Number.isFinite(time) ? time : null;
}

function sortSessions(sessions) {
  return list(sessions).filter(isRecord).map((session, index) => ({session, index, time: dateValue(session.created_at)}))
    .sort((a, b) => {
      if (a.time === null && b.time !== null) return 1;
      if (b.time === null && a.time !== null) return -1;
      return (a.time !== null && b.time !== null ? b.time - a.time : 0) || a.index - b.index;
    }).map(item => item.session);
}

function formatDate(value) {
  const time = dateValue(value);
  if (time === null) return text(value) ? `时间未知（${text(value)}）` : "时间未记录";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
  }).format(time);
}

// Returns a Map<groupKey, newest-first session[]> in latest-practice order.
function groupSessions(sessions) {
  const grouped = new Map();
  for (const session of sortSessions(sessions)) {
    const key = groupKey(session);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(session);
  }
  return grouped;
}

function latestTargets(sessions) {
  const latest = new Map();
  for (const session of sortSessions(sessions)) {
    for (const target of list(session.targets).filter(isRecord)) {
      const expression = text(target.expression);
      const key = JSON.stringify([groupKey(session), expression]);
      if (!expression) continue;
      const previous = latest.get(key);
      const observed = ["mastered", "developing", "needs_review"].includes(target.status);
      // An unobserved retry carries no new assessment: keep looking for the
      // newest observed evidence in this same scene, never across scenes.
      if (!previous || (previous.status === "not_observed" && observed)) latest.set(key, target);
    }
  }
  return [...latest.values()];
}

// Technical evidence is contextual, independent of English expression aggregation.
// Keep the actual source session when a newer unobserved attempt is skipped.
function latestTechnical(sessions) {
  const latest = new Map();
  sortSessions(sessions).forEach((session, rank) => {
    const interview = record(session.interview);
    for (const [observationRank, observation] of list(interview.observations).filter(isRecord).entries()) {
      if (!text(observation.concept_id)) continue;
      const key = JSON.stringify([observation.concept_id, interview.depth, interview.role]);
      const previous = latest.get(key);
      const observed = ["met", "partial", "unmet"].includes(observation.status);
      if (!previous || (previous.entry.status === "not_observed" && observed)) {
        latest.set(key, {rank, observationRank, entry: {
          ...observation,
          depth: interview.depth,
          role: interview.role,
          track: {id: record(interview.track).id, label: record(interview.track).label},
          session_id: session.id,
          created_at: session.created_at,
          scenario_id: record(session.scenario).id
        }});
      }
    }
  });
  return [...latest.values()].sort((a, b) => a.rank - b.rank || a.observationRank - b.observationRank).map(item => item.entry);
}

// Only the three observed states enter the denominator. A missing assessment is
// null, not a fabricated 0% score. Unknown future states are separately unrated.
function targetSummary(targets) {
  const summary = {total: 0, observed: 0, mastered: 0, developing: 0, needsReview: 0, review: 0, unobserved: 0, unrated: 0, percent: null};
  for (const target of list(targets).filter(isRecord)) {
    if (!text(target.expression)) continue;
    summary.total += 1;
    switch (target.status) {
      case "mastered": summary.mastered += 1; break;
      case "developing": summary.developing += 1; break;
      case "needs_review": summary.needsReview += 1; break;
      case "not_observed": summary.unobserved += 1; break;
      default: summary.unrated += 1;
    }
  }
  summary.review = summary.developing + summary.needsReview;
  summary.observed = summary.mastered + summary.review;
  summary.percent = summary.observed ? Math.round(summary.mastered / summary.observed * 100) : null;
  return summary;
}

function categoryKey(session) {
  const scenario = record(record(session).scenario);
  const id = text(scenario.category_id);
  const label = text(scenario.category_label);
  return id || label ? JSON.stringify([domainOf(session), id ? "id" : "label", id || label]) : "missing";
}

function industryKey(session) {
  const industry = record(record(record(session).business).industry);
  const id = text(industry.id);
  const label = text(industry.label);
  return id || label ? JSON.stringify([id ? "id" : "label", id || label]) : "missing";
}

function searchText(value) {
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(searchText).join(" ");
  if (isRecord(value)) return Object.values(value).map(searchText).join(" ");
  return "";
}

const normalizeSearch = value => text(value).normalize("NFKC").toLocaleLowerCase("zh-CN");

// Category/industry filters accept the select's opaque key, or a raw schema ID.
// Filtering selects sessions before grouping: all counts and evidence share a slice.
function filterSessions(sessions, filters = {}) {
  const settings = record(filters);
  const words = normalizeSearch(settings.search).split(/\s+/u).filter(Boolean);
  return list(sessions).filter(isRecord).filter(session => {
    if (settings.domain && settings.domain !== "all" && domainOf(session) !== settings.domain) return false;
    if (settings.category && settings.category !== "all" && settings.category !== categoryKey(session)
      && settings.category !== text(record(session.scenario).category_id)) return false;
    if (settings.industry && settings.industry !== "all" && settings.industry !== industryKey(session)
      && settings.industry !== text(record(record(session.business).industry).id)) return false;
    if (!words.length) return true;
    const haystack = normalizeSearch(`${DOMAIN_LABELS.get(domainOf(session))} ${searchText(session)}`);
    return words.every(word => haystack.includes(word));
  });
}

function statusInfo(statuses, status) {
  return statuses.get(status) || {label: text(status) ? `未评级（${text(status)}）` : "未记录", symbol: "—", className: "neutral"};
}

function statusBadge(info) {
  return `<span class="status-badge ${info.className}"><span aria-hidden="true">${info.symbol}</span>${escapeHtml(info.label)}</span>`;
}

function targetTag(target) {
  const info = statusInfo(TARGET_STATUSES, target.status);
  return `<span class="target-tag ${info.className}"><b>${escapeHtml(target.expression)}</b><small><span aria-hidden="true">${info.symbol}</span> ${escapeHtml(info.label)}</small></span>`;
}

function recentRepairs(sessions, limit = 3) {
  const seen = new Set();
  const repairs = [];
  for (const session of sessions) {
    for (const repair of list(session.repairs).filter(isRecord)) {
      const key = JSON.stringify([text(repair.learner), text(repair.natural)]);
      if (!seen.has(key) && (text(repair.learner) || text(repair.natural))) {
        seen.add(key);
        repairs.push(repair);
        if (repairs.length >= limit) return repairs;
      }
    }
  }
  return repairs;
}

function latestFocus(sessions) {
  for (const session of sessions) {
    const focus = strings(session.focus_next);
    if (focus.length) return focus.slice(0, 3);
  }
  return [];
}

function latestDrill(sessions) {
  return text(sessions.find(session => text(session.next_drill))?.next_drill);
}

function repairHtml(repairs, heading = "重点纠正") {
  if (!repairs.length) return "";
  return `<section class="review-detail"><h3>${escapeHtml(heading)}</h3><div class="repair-list">${repairs.map(repair => `
    <div class="repair-item">
      <p><span>原表达</span><span>${escapeHtml(repair.learner || "未记录原表达")}</span></p>
      <p class="natural"><span>更自然</span><span>${escapeHtml(repair.natural || "未记录改写")}</span></p>
      ${text(repair.reason_zh) ? `<p class="repair-reason">${escapeHtml(repair.reason_zh)}</p>` : ""}
    </div>`).join("")}</div></section>`;
}

function practiceHtml(focus, drill) {
  return `${focus.length ? `<section class="review-detail"><h3>下次重点</h3><ul class="focus-list">${focus.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
    ${drill ? `<section class="next-drill"><h3>迁移练习</h3><p>${escapeHtml(drill)}</p></section>` : ""}`;
}

function feedbackHtml(feedback) {
  const entries = list(feedback).filter(isRecord);
  if (!entries.length) return '<p class="detail-empty">本次未记录五维反馈，不推断表现。</p>';
  const grouped = new Map([...FEEDBACK_DIMENSIONS.keys()].map(key => [key, []]));
  for (const item of entries) {
    const dimension = text(item.dimension) || "unknown";
    if (!grouped.has(dimension)) grouped.set(dimension, []);
    grouped.get(dimension).push(item);
  }
  return `<div class="feedback-grid">${[...grouped].map(([dimension, items]) => `
    <section class="feedback-item"><h4>${escapeHtml(FEEDBACK_DIMENSIONS.get(dimension) || `其他维度 · ${dimension}`)}</h4>
      ${items.length ? items.map(item => `<dl class="evidence-lines">
        <div><dt>观察</dt><dd>${escapeHtml(text(item.observation) || "未记录观察")}</dd></div>
        <div><dt>证据</dt><dd class="verbatim">${escapeHtml(text(item.evidence) || "未记录证据")}</dd></div>
        <div><dt>建议</dt><dd>${escapeHtml(text(item.suggestion) || "未记录建议")}</dd></div>
      </dl>`).join("") : '<p class="detail-empty">未记录此维度反馈</p>'}
    </section>`).join("")}</div>`;
}

function isBusinessSession(session) {
  return domainOf(session) === "business" || isRecord(session.business);
}

function businessHtml(session) {
  if (!isBusinessSession(session)) return "";
  const business = record(session.business);
  const outcome = record(business.outcome);
  const criteria = list(business.criteria).filter(isRecord);
  return `<section class="business-review review-detail">
    <div class="detail-heading"><h3>本次沟通结果</h3>${statusBadge(statusInfo(OUTCOME_STATUSES, outcome.status))}</div>
    <p class="outcome-summary verbatim">${escapeHtml(text(outcome.summary) || "本次未记录任务结果摘要。")}</p>
    <p class="detail-note">结果按归档原样展示；待确认或合理拒绝不等于沟通失败，是否成交也不等于表达掌握。</p>
    <section class="criteria-section"><h3>任务标准</h3>${criteria.length ? `<ul class="criteria-list">${criteria.map(item => `
      <li><div class="criterion-heading"><b>${escapeHtml(text(item.criterion) || "未命名标准")}</b>${statusBadge(statusInfo(CRITERION_STATUSES, item.status))}</div>
      <dl class="evidence-lines"><div><dt>证据</dt><dd class="verbatim">${escapeHtml(text(item.evidence) || "未记录证据")}</dd></div></dl></li>`).join("")}</ul>` : '<p class="detail-empty">本次未记录任务标准。</p>'}</section>
    <section class="feedback-section"><h3>五维沟通反馈</h3>${feedbackHtml(business.feedback)}</section>
    ${text(business.next_action) ? `<section class="next-action"><h3>下一步行动</h3><p class="verbatim">${escapeHtml(business.next_action)}</p></section>` : ""}
  </section>`;
}

function technicalEvidenceHtml(entries, withContext = false) {
  if (!entries.length) return '<p class="detail-empty">未记录技术观察，不推断表现。</p>';
  return `<ul class="technical-evidence criteria-list">${entries.map(item => {
    const observed = ["met", "partial", "unmet"].includes(item.status);
    const language = LANGUAGE_SUPPORTS.get(item.language_support) || text(item.language_support) || "未记录";
    const technical = TECHNICAL_SUPPORTS.get(item.technical_support) || text(item.technical_support) || "未记录";
    const track = record(item.track);
    return `<li class="technical-observation"><div class="criterion-heading"><b>${escapeHtml(text(item.label) || item.concept_id)} · ${escapeHtml(item.concept_id)}</b>${statusBadge(statusInfo(CRITERION_STATUSES, item.status))}</div>
      ${withContext ? `<dl class="session-metadata technical-context">
        <div><dt>角色 / 深度</dt><dd>${escapeHtml(INTERVIEW_ROLES.get(item.role) || item.role)} / ${escapeHtml(INTERVIEW_DEPTHS.get(item.depth) || item.depth)}</dd></div>
        <div><dt>方向</dt><dd>${escapeHtml(track.label)} · ${escapeHtml(track.id)}</dd></div>
        <div><dt>来源场景 / 归档</dt><dd class="verbatim">${escapeHtml(item.scenario_id)} / ${escapeHtml(item.session_id)}</dd></div>
        <div><dt>证据时间</dt><dd class="verbatim">${escapeHtml(item.created_at)}</dd></div></dl>` : ""}
      <p class="detail-note">问题 ID：${escapeHtml(item.question_id)}</p>
      <dl class="evidence-lines technical-support">
        <div><dt>语言</dt><dd>${escapeHtml(language)}（${escapeHtml(item.language_support)}）</dd></div>
        <div><dt>技术</dt><dd>${escapeHtml(technical)}（${escapeHtml(item.technical_support)}）</dd></div>
        ${observed ? `<div><dt>证据</dt><dd class="verbatim">${escapeHtml(item.evidence)}</dd></div>
        <div><dt>观察</dt><dd class="verbatim">${escapeHtml(item.observation)}</dd></div>
        <div><dt>建议</dt><dd class="verbatim">${escapeHtml(item.suggestion)}</dd></div>` : '<div><dt>观察</dt><dd>未观察，不推断技术表现。</dd></div>'}
      </dl></li>`;
  }).join("")}</ul>`;
}

function interviewHtml(session) {
  const interview = record(record(session).interview);
  if (!isRecord(record(session).interview)) return "";
  const track = record(interview.track);
  const rows = [
    ["方向", `${text(track.label)} · ${text(track.id)}`],
    ["技术角色", INTERVIEW_ROLES.get(interview.role) || text(interview.role) || "未记录"],
    ["技术深度", INTERVIEW_DEPTHS.get(interview.depth) || text(interview.depth) || "未记录"],
    ["压力", INTERVIEW_PRESSURES.get(interview.pressure) || text(interview.pressure) || "未记录"],
    ["问题 ID", strings(interview.question_ids).join("、") || "未记录"]
  ];
  return `<section class="interview-review review-detail"><h3>本次技术面试</h3>
    <dl class="session-metadata">${rows.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd class="verbatim">${escapeHtml(value)}</dd></div>`).join("")}</dl>
    <p class="detail-note">技术评价独立于英语表达，仅反映本次条件、角色与深度下的证据；不推断通用掌握度。</p>
    ${technicalEvidenceHtml(list(interview.observations).filter(isRecord))}</section>`;
}

function technicalReviewHtml(sessions) {
  if (!list(sessions).some(session => isRecord(record(session).interview))) return "";
  return `<section class="interview-review review-detail"><h3>技术证据回顾（当前筛选内）</h3>
    <p class="detail-note">跨所选场景按概念、技术深度与角色分别取最新证据；未观察不覆盖旧证据。受提示的回答不视作独立完成，技术观察不计入英语表达比例。</p>
    ${technicalEvidenceHtml(latestTechnical(sessions), true)}</section>`;
}

function detailsHtml(key, label, body, className = "") {
  return `<details class="archive-details ${className}" data-detail-key="${escapeHtml(key)}"><summary data-focus-key="${escapeHtml(key)}">${escapeHtml(label)}</summary><div class="details-body">${body}</div></details>`;
}

function contextHtml(session) {
  const business = record(session.business);
  const constraints = strings(business.constraints);
  if (!text(business.context) && !constraints.length) return "";
  return detailsHtml("context", "情境与边界", `
    ${text(business.context) ? `<h3>业务情境</h3><p class="verbatim">${escapeHtml(business.context)}</p>` : ""}
    ${constraints.length ? `<h3>约束条件</h3><ul class="constraint-list">${constraints.map(item => `<li class="verbatim">${escapeHtml(item)}</li>`).join("")}</ul>` : ""}`);
}

function sessionMetadataHtml(session) {
  const roles = record(session.roles);
  const duration = Number(session.duration_minutes);
  const level = new Map([["beginner", "初级"], ["intermediate", "中级"], ["advanced", "高级"]]);
  const hints = new Map([["immersion", "沉浸式"], ["guided", "引导式"], ["learning", "学习式"]]);
  const mission = session.mission_completed === true ? "已完成" : session.mission_completed === false ? "未完成" : "未记录";
  const rows = [
    ["归档编号", text(session.id) || "未记录"], ["归档时间", text(session.created_at) || "未记录"],
    ["领域", DOMAIN_LABELS.get(domainOf(session))],
    ["场景分类", text(record(session.scenario).category_label) || text(record(session.scenario).category_id) || "未标注分类"],
    ["行业", text(record(record(session.business).industry).label) || text(record(record(session.business).industry).id) || "未标注行业"],
    ["场景 ID", text(record(session.scenario).id) || text(record(session.topic).id) || "未记录（按归档独立展示）"],
    ["学习者角色", text(roles.learner) || "未记录"], ["对练角色", text(roles.coach) || "未记录"],
    ["练习时长", duration > 0 && Number.isFinite(duration) ? `${duration} 分钟` : "未记录"],
    ["语言水平", level.get(session.level) || text(session.level) || "未记录"],
    ["提示模式", hints.get(session.hint_mode) || text(session.hint_mode) || "未记录"],
    ["沟通任务", text(session.mission) || "未记录"]
  ];
  if (!isBusinessSession(session)) rows.push(["原任务状态", mission]);
  return `<dl class="session-metadata">${rows.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd class="verbatim">${escapeHtml(value)}</dd></div>`).join("")}</dl>`;
}

function targetEvidenceHtml(targets, heading = "本次表达原始证据") {
  const entries = list(targets).filter(item => isRecord(item) && text(item.expression));
  return `<section class="review-detail"><h3>${escapeHtml(heading)}</h3>${entries.length ? `<ul class="target-evidence">${entries.map(target => `
    <li><div class="criterion-heading"><b>${escapeHtml(target.expression)}</b>${statusBadge(statusInfo(TARGET_STATUSES, target.status))}</div>
      ${text(target.meaning_zh) ? `<p>${escapeHtml(target.meaning_zh)}</p>` : ""}
      <dl class="evidence-lines"><div><dt>证据</dt><dd class="verbatim">${escapeHtml(text(target.evidence) || "未记录原始证据")}</dd></div>
      ${text(target.support) ? `<div><dt>提示</dt><dd>${escapeHtml(SUPPORT_LABELS.get(target.support) || target.support)}</dd></div>` : ""}</dl>
    </li>`).join("")}</ul>` : '<p class="detail-empty">本次未记录表达证据。</p>'}</section>`;
}

function sessionEvidenceHtml(session) {
  return `${sessionMetadataHtml(session)}${targetEvidenceHtml(session.targets)}
    ${repairHtml(list(session.repairs).filter(isRecord), "本次全部纠正")}
    ${practiceHtml(strings(session.focus_next), text(session.next_drill))}`;
}

function historyHtml(sessions) {
  if (sessions.length <= 1) return "";
  const history = sessions.slice(1, HISTORY_LIMIT + 1);
  const occurrences = new Map();
  const body = history.map(session => {
    const identity = text(session.id) ? JSON.stringify([session.id]) : stableSerialize(session);
    const occurrence = occurrences.get(identity) || 0;
    occurrences.set(identity, occurrence + 1);
    const key = JSON.stringify(["archive", identity, occurrence]);
    const outcome = isBusinessSession(session) ? statusInfo(OUTCOME_STATUSES, record(record(session.business).outcome).status).label : "练习归档";
    // Nested detail keys are scoped to this archive, not to its position in history.
    const content = `${businessHtml(session)}${interviewHtml(session)}${contextHtml(session)}${sessionEvidenceHtml(session)}`;
    return detailsHtml(key, `${formatDate(session.created_at)} · ${outcome}`, content, "history-entry");
  }).join("");
  const more = sessions.length - 1 - history.length;
  return detailsHtml("history", `历史归档 · ${sessions.length - 1} 次`, `${body}${more > 0 ? `<p class="detail-note">这里只展开最近 ${HISTORY_LIMIT} 次历史归档；更早的 ${more} 次原始记录仍保存在本地存档中。</p>` : ""}`);
}

function sceneTitle(session) {
  return text(record(session.topic).label) || text(record(session.scenario).id) || text(record(session.topic).id) || "未命名练习";
}

function cardHtml(sessions, headingId) {
  const latest = sessions[0];
  const targets = latestTargets(sessions);
  const summary = targetSummary(targets);
  const scenario = record(latest.scenario);
  const industry = record(record(latest.business).industry);
  const business = isBusinessSession(latest);
  const category = text(scenario.category_label) || text(scenario.category_id);
  const industryLabel = text(industry.label) || text(industry.id);
  const assessment = summary.observed ? `已掌握 ${summary.mastered} / ${summary.observed} 个已观察表达 · ${summary.percent}%` : "无可评估表达";
  const mission = latest.mission_completed === true ? "任务已完成" : latest.mission_completed === false ? "任务未完成" : "已归档";
  return `<div class="scene-labels"><span class="domain-tag">${escapeHtml(DOMAIN_LABELS.get(domainOf(latest)))}</span>
      ${category || business ? `<span class="metadata-tag">分类 · ${escapeHtml(category || "未标注分类")}</span>` : ""}
      ${industryLabel || business ? `<span class="metadata-tag">行业 · ${escapeHtml(industryLabel || "未标注行业")}</span>` : ""}</div>
    <div class="review-topic-header"><h2 id="${escapeHtml(headingId)}">${escapeHtml(sceneTitle(latest))}</h2><span class="archive-count">${sessions.length} 次练习</span></div>
    <p class="review-meta">最近 ${escapeHtml(formatDate(latest.created_at))}${business ? "" : ` · ${mission}`}</p>
    ${business ? `<p class="learner-role"><b>你的角色</b> ${escapeHtml(text(record(latest.roles).learner) || "未记录")}${text(record(latest.roles).coach) ? ` <span class="role-divider" aria-hidden="true">/</span> <b>对练角色</b> ${escapeHtml(latest.roles.coach)}` : ""}</p>` : ""}
    <section class="review-detail target-section"><div class="detail-heading"><h3>场景内表达状态</h3><span class="assessment-summary">${escapeHtml(assessment)}</span></div>
      <p class="detail-note">当前筛选内取最近一次已观察状态；无观察证据时保留未观察 · 未观察 ${summary.unobserved}${summary.unrated ? ` · 未评级 ${summary.unrated}` : ""}</p>
      <div class="target-tags">${targets.map(targetTag).join("") || '<span class="detail-empty">尚无表达记录</span>'}</div></section>
    ${businessHtml(latest)}
    ${interviewHtml(latest)}
    ${technicalReviewHtml(sessions)}
    ${repairHtml(recentRepairs(sessions))}
    ${practiceHtml(latestFocus(sessions), latestDrill(sessions))}
    ${contextHtml(latest)}
    ${detailsHtml("evidence", "原始证据与练习信息", `${targetEvidenceHtml(targets, "汇总状态所依据的原始证据（当前筛选内）")}${sessionEvidenceHtml(latest)}`)}
    ${historyHtml(sessions)}`;
}

let state = {version: 2, sessions: []};
let loading = false;
let hasLoaded = false;
let lastSync = "";
let contentSnapshot = null;
const filters = {domain: "all", category: "all", industry: "all", search: ""};
const ui = {cards: new Map(), groupIds: new Map(), nextId: 1, optionSnapshots: new Map()};
const $ = selector => document.querySelector(selector);

function setText(selector, value) {
  const node = $(selector);
  const next = String(value);
  if (node.textContent !== next) node.textContent = next;
}

function filterOptions(sessions, kind) {
  const options = new Map();
  for (const session of sortSessions(sessions)) {
    const scenario = record(session.scenario);
    const industry = record(record(session.business).industry);
    const key = kind === "category" ? categoryKey(session) : industryKey(session);
    let label;
    if (kind === "category") {
      label = key === "missing" ? "未标注分类" : `${text(scenario.category_label) || text(scenario.category_id)} · ${DOMAIN_LABELS.get(domainOf(session))}`;
    } else {
      label = key === "missing" ? "未标注行业" : text(industry.label) || text(industry.id);
    }
    if (!options.has(key)) options.set(key, label);
  }
  return [...options].sort((a, b) => a[1].localeCompare(b[1], "zh-CN") || a[0].localeCompare(b[0]));
}

function updateFilterOptions() {
  for (const kind of ["category", "industry"]) {
    const select = $(`#filter-${kind}`);
    const options = filterOptions(state.sessions, kind);
    const selected = filters[kind];
    if (selected !== "all" && !options.some(([key]) => key === selected)) {
      const old = [...select.options].find(option => option.value === selected);
      options.push([selected, `${old?.textContent?.replace(/（已无归档）$/, "") || "原筛选"}（已无归档）`]);
    }
    const html = `<option value="all">全部${kind === "category" ? "分类" : "行业"}</option>`
      + options.map(([key, label]) => `<option value="${escapeHtml(key)}">${escapeHtml(label)}</option>`).join("");
    if (ui.optionSnapshots.get(kind) !== html) {
      select.innerHTML = html;
      select.value = selected;
      ui.optionSnapshots.set(kind, html);
    }
  }
}

// Paths include parent <details> keys so nested history disclosures do not collide.
function detailPath(detail, root) {
  const path = [];
  let current = detail;
  while (current && current !== root) {
    if (current.matches("details[data-detail-key]")) path.unshift(current.dataset.detailKey);
    current = current.parentElement;
  }
  return JSON.stringify(path);
}

function updateCard(node, html) {
  const opened = new Map([...node.querySelectorAll("details[data-detail-key]")].map(detail => [detailPath(detail, node), detail.open]));
  const active = document.activeElement;
  const focusPath = node.contains(active) && active.matches("summary[data-focus-key]") ? detailPath(active.parentElement, node) : null;
  node.innerHTML = html;
  let focusTarget = null;
  for (const detail of node.querySelectorAll("details[data-detail-key]")) {
    const path = detailPath(detail, node);
    if (opened.has(path)) detail.open = opened.get(path);
    if (path === focusPath) focusTarget = detail.querySelector("summary");
  }
  if (focusTarget) focusTarget.focus({preventScroll: true});
}

function renderReview() {
  const sessions = filterSessions(state.sessions, filters);
  const grouped = groupSessions(sessions);
  const summary = targetSummary(latestTargets(sessions));
  const technicalReview = $("#technical-review");
  if (technicalReview) {
    const html = technicalReviewHtml(sessions);
    if (technicalReview.innerHTML !== html) technicalReview.innerHTML = html;
    technicalReview.classList.toggle("hidden", !sessions.some(session => isRecord(session.interview)));
  }
  setText("#stat-sessions", sessions.length);
  setText("#stat-scenes", grouped.size);
  setText("#stat-mastered", summary.mastered);
  setText("#stat-review", summary.review);
  setText("#stat-unobserved", summary.unobserved);
  setText("#session-count", state.sessions.length ? `累计归档 ${state.sessions.length} 次` : "从第 1 次开始");
  setText("#result-count", `找到 ${sessions.length} / ${state.sessions.length} 次练习 · ${grouped.size} 个场景`);
  setText("#assessment-note", `当前筛选 · ${summary.observed ? `已掌握 ${summary.mastered} / ${summary.observed} 个已观察表达（${summary.percent}%）` : "无可评估表达"}。未观察 ${summary.unobserved}${summary.unrated ? `，未评级 ${summary.unrated}` : ""}，不计入比例；同一句表达按领域和场景分别记录。`);
  $("#empty-review").classList.toggle("hidden", state.sessions.length > 0);
  $("#no-results").classList.toggle("hidden", state.sessions.length === 0 || sessions.length > 0);
  $("#load-unavailable").classList.add("hidden");

  for (const [key, card] of ui.cards) {
    if (!grouped.has(key)) {
      card.node.remove();
      ui.cards.delete(key);
    }
  }
  const container = $("#review-list");
  let position = 0;
  for (const [key, items] of grouped) {
    if (!ui.groupIds.has(key)) ui.groupIds.set(key, `scene-${ui.nextId++}`);
    const headingId = `${ui.groupIds.get(key)}-title`;
    const html = cardHtml(items, headingId);
    let card = ui.cards.get(key);
    if (!card) {
      const node = document.createElement("article");
      node.className = "review-topic paper-card";
      node.setAttribute("aria-labelledby", headingId);
      card = {node, html: ""};
      ui.cards.set(key, card);
    }
    if (card.html !== html) {
      updateCard(card.node, html);
      card.html = html;
    }
    const atPosition = container.children[position];
    if (atPosition !== card.node) {
      // Moving a focused card can blur its summary; restore only that same focus.
      const active = card.node.contains(document.activeElement) ? document.activeElement : null;
      container.insertBefore(card.node, atPosition || null);
      if (active) active.focus({preventScroll: true});
    }
    position += 1;
  }
}

function syncStatus(failed, reason = "") {
  $("#sync-status").dataset.state = failed ? "stale" : "synced";
  setText("#save-status", failed
    ? hasLoaded ? `同步中断 · 保留上次存档（${lastSync}）${reason}` : `无法读取存档${reason} · 请重试`
    : `本地存档已同步 · ${lastSync}`);
}

async function loadState() {
  if (loading) return;
  loading = true;
  $("#refresh-data").setAttribute("aria-busy", "true");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch("/api/state", {cache: "no-store", signal: controller.signal});
    if (!response.ok) throw new Error("connection");
    const next = await response.json();
    if (!isRecord(next) || !Array.isArray(next.sessions) || !next.sessions.every(isRecord)) throw new Error("invalid");
    if (next.version !== undefined && next.version !== 1 && next.version !== 2) throw new Error("version");
    const snapshot = stableSerialize(next.sessions);
    if (!hasLoaded || snapshot !== contentSnapshot) {
      state = {...next, version: next.version ?? 1};
      updateFilterOptions();
      renderReview();
      contentSnapshot = snapshot;
    }
    hasLoaded = true;
    lastSync = new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"});
    syncStatus(false);
  } catch (error) {
    const reason = error.message === "version" ? " · 存档版本不受支持" : error.message === "invalid" ? " · 存档格式异常" : "";
    syncStatus(true, reason);
    if (!hasLoaded) {
      $("#load-unavailable").classList.remove("hidden");
      setText("#result-count", "存档未载入，暂不统计");
    }
  } finally {
    clearTimeout(timeout);
    loading = false;
    $("#refresh-data").removeAttribute("aria-busy");
  }
}

function resetFilters() {
  Object.assign(filters, {domain: "all", category: "all", industry: "all", search: ""});
  for (const kind of ["domain", "category", "industry"]) $(`#filter-${kind}`).value = "all";
  $("#filter-search").value = "";
  if (hasLoaded) {
    updateFilterOptions();
    renderReview();
  }
}

function startWorkbench() {
  if (!$("#review-list")) return;
  $("#refresh-data").addEventListener("click", loadState);
  $("#review-filters").addEventListener("submit", event => event.preventDefault());
  $("#review-filters").addEventListener("reset", event => {
    event.preventDefault();
    resetFilters();
  });
  for (const kind of ["domain", "category", "industry"]) {
    $(`#filter-${kind}`).addEventListener("change", event => {
      filters[kind] = event.target.value;
      if (hasLoaded) renderReview();
    });
  }
  $("#filter-search").addEventListener("input", event => {
    filters.search = event.target.value;
    if (hasLoaded) renderReview();
  });
  $("#clear-no-results").addEventListener("click", () => {
    resetFilters();
    $("#filter-search").focus();
  });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loadState(); });
  loadState();
  setInterval(loadState, 8000);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {filterSessions, groupSessions, latestTargets, latestTechnical, targetSummary, groupKey, sortSessions,
    interviewHtml, technicalReviewHtml, cardHtml, historyHtml};
}
if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startWorkbench, {once: true});
  else startWorkbench();
}
