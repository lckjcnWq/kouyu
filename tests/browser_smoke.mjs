// Zero-dependency browser smoke. All learner data below is explicitly synthetic.
// Run: node tests/browser_smoke.mjs [absolute-project-root]
// Requires Node 22+ and local Chrome. CHROME_PATH / PYTHON override the binaries.
// Screenshots and synthetic output remain in a new OS temp directory for inspection.
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {existsSync, mkdtempSync, readFileSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

if (typeof WebSocket === 'undefined') throw new Error('Node 22+ with built-in WebSocket is required.');
const root = resolve(process.argv[2] || fileURLToPath(new URL('..', import.meta.url)));
const script = join(root, 'scripts/workbench.py');
const fixtures = join(root, 'tests/fixtures');
const business = JSON.parse(readFileSync(join(fixtures, 'business-session.json'), 'utf8'));
const legacy = JSON.parse(readFileSync(join(fixtures, 'legacy-session.json'), 'utf8'));
const interviewFixture = JSON.parse(readFileSync(join(fixtures, 'interview-session.json'), 'utf8'));
const temporary = mkdtempSync(join(tmpdir(), 'kouyu-browser-smoke-synthetic-'));
const dataDir = join(temporary, 'synthetic-only-archive');
const python = process.env.PYTHON || 'python3';
const chromePath = process.env.CHROME_PATH || [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome'
].find(existsSync);
assert(chromePath, 'Install Chrome or set CHROME_PATH; this script never installs packages.');
const children = new Set();
let socket;
let browserSession;
let sequence = 0;
const pending = new Map();
const runtimeErrors = [];
const outboundRequests = [];
let backendLog = '';

const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const duplicate = value => JSON.parse(JSON.stringify(value));
function cli(command, extra = []) {
  const result = spawnSync(python, ['-I', '-B', script, command, '--data-dir', dataDir, ...extra], {cwd: temporary, encoding: 'utf8', timeout: 15000});
  assert.equal(result.status, 0, `${command} failed: ${result.stderr || result.error || result.stdout}`);
}
function archive(session, name) {
  assert(session.id.startsWith('synthetic-'), 'Only synthetic fixture IDs may be archived.');
  const input = join(temporary, `synthetic-${name}.json`);
  writeFileSync(input, JSON.stringify(session));
  cli('archive', ['--input', input]);
}
function writeSyntheticState(sessions, version = 2) {
  writeFileSync(join(dataDir, 'workbench-data.json'), JSON.stringify({version, sessions}));
}
function start(binary, args) {
  const child = spawn(binary, args, {cwd: temporary, stdio: ['ignore', 'pipe', 'pipe']});
  children.add(child);
  child.once('exit', () => children.delete(child));
  child.once('error', () => children.delete(child));
  return child;
}
async function waitFor(check, description, timeout = 16000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await check()) return;
    await delay(50);
  }
  throw new Error(`Timed out: ${description}`);
}
async function killChild(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  const finished = once(child, 'exit');
  child.kill('SIGTERM');
  const timeout = setTimeout(() => child.kill('SIGKILL'), 3000);
  await finished;
  clearTimeout(timeout);
}
async function closeAll() {
  for (const item of pending.values()) {
    clearTimeout(item.timer);
    item.reject(new Error('Browser connection closed'));
  }
  pending.clear();
  socket?.close();
  await Promise.all([...children].map(killChild));
}
process.once('SIGINT', () => { closeAll().finally(() => process.exit(130)); });
process.once('SIGTERM', () => { closeAll().finally(() => process.exit(143)); });
function cdp(method, params = {}, session = browserSession) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error(`CDP timeout: ${method}`));}, 15000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params, ...(session ? {sessionId: session} : {})}));
  });
}
async function evaluate(expression) {
  const result = await cdp('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  assert(!result.exceptionDetails, result.exceptionDetails?.exception?.description || result.exceptionDetails?.text);
  return result.result.value;
}
const browserWait = (expression, timeout) => waitFor(() => evaluate(expression), expression, timeout);
async function refresh() {
  await evaluate(`document.querySelector('#refresh-data').click()`);
  await browserWait(`!loading`);
}
async function choose(id, value) {
  await evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(id)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('change',{bubbles:true}));})()`);
}
async function search(value) {
  await evaluate(`(()=>{const el=document.querySelector('#filter-search');el.focus();el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('input',{bubbles:true}));})()`);
}
const reset = () => evaluate(`document.querySelector('#reset-filters').click()`);
const metric = id => evaluate(`document.querySelector(${JSON.stringify(id)}).textContent`);
async function screenshot(name) {
  await evaluate(`new Promise(requestAnimationFrame)`);
  const result = await cdp('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
  const path = join(temporary, `${name}.png`);
  writeFileSync(path, Buffer.from(result.data, 'base64'));
  console.log(`Screenshot: ${path}`);
}

try {
  cli('init');
  archive(legacy, 'legacy');
  archive(business, 'business');
  const backend = start(python, ['-I', '-B', '-u', script, 'serve', '--data-dir', dataDir, '--host', '127.0.0.1', '--port', '0', '--no-open']);
  let backendError;
  backend.once('error', error => {backendError = error;});
  backend.stdout.on('data', data => {backendLog += data;});
  backend.stderr.on('data', data => {backendLog += data;});
  await waitFor(() => {
    if (backendError) throw backendError;
    if (backend.exitCode !== null) throw new Error(backendLog);
    return /Listening on (http:\/\/127\.0\.0\.1:\d+\/)/.test(backendLog);
  }, 'Python local server startup');
  const url = backendLog.match(/Listening on (http:\/\/127\.0\.0\.1:\d+\/)/)[1];
  const health = await fetch(`${url}api/health`);
  assert.deepEqual(await health.json(), {ok: true, version: 2});
  const chrome = start(chromePath, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${join(temporary, 'chrome-profile')}`,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-gpu', 'about:blank']);
  let chromeLog = '';
  let chromeError;
  chrome.stderr.on('data', data => {chromeLog += data;});
  chrome.once('error', error => {chromeError = error;});
  await waitFor(() => {
    if (chromeError) throw chromeError;
    if (chrome.exitCode !== null) throw new Error(chromeLog);
    return /DevTools listening on (ws:\/\/[^\s]+)/.test(chromeLog);
  }, 'Headless Chrome startup');
  socket = new WebSocket(chromeLog.match(/DevTools listening on (ws:\/\/[^\s]+)/)[1]);
  await once(socket, 'open');
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = pending.get(message.id);
      if (!request) return;
      clearTimeout(request.timer);
      pending.delete(message.id);
      message.error ? request.reject(new Error(JSON.stringify(message.error))) : request.resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') runtimeErrors.push(message.params.exceptionDetails);
    if (message.method === 'Network.requestWillBeSent') outboundRequests.push(message.params.request);
  });
  const target = await cdp('Target.createTarget', {url: 'about:blank'}, null);
  browserSession = (await cdp('Target.attachToTarget', {targetId: target.targetId, flatten: true}, null)).sessionId;
  await cdp('Page.enable');
  await cdp('Runtime.enable');
  await cdp('Network.enable');
  await cdp('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1120, deviceScaleFactor: 1, mobile: false});
  await cdp('Page.navigate', {url});
  await browserWait(`typeof hasLoaded !== 'undefined' && hasLoaded && !loading`);
  assert.deepEqual(await evaluate(`['#stat-sessions','#stat-scenes','#stat-mastered','#stat-review','#stat-unobserved'].map(id=>document.querySelector(id).textContent)`), ['2','2','2','1','2']);
  assert.equal(await evaluate(`document.querySelector('.business-review .status-badge').textContent.includes('待确认')`), true);
  assert.equal(await evaluate(`document.querySelectorAll('.feedback-item').length`), 5);
  await screenshot('desktop-overview');
  await evaluate(`document.querySelector('.business-review').scrollIntoView({behavior:'instant',block:'start'})`);
  await screenshot('desktop-business-evidence');
  await choose('#filter-domain', 'unclassified');
  assert.equal(await metric('#stat-sessions'), '1');
  assert.equal(await evaluate(`document.querySelector('.domain-tag').textContent`), '未分类');
  await choose('#filter-domain', 'everyday');
  assert.equal(await evaluate(`!document.querySelector('#no-results').classList.contains('hidden') && document.querySelector('#empty-review').classList.contains('hidden')`), true);
  await reset();
  const category = await evaluate(`Array.from(document.querySelector('#filter-category').options).find(o=>o.textContent.includes('商务谈判')).value`);
  const industry = await evaluate(`Array.from(document.querySelector('#filter-industry').options).find(o=>o.textContent.includes('软件')).value`);
  await choose('#filter-category', category);
  await choose('#filter-industry', industry);
  await search('APPROVAL');
  assert.equal(await metric('#stat-sessions'), '1');
  await refresh();
  assert.equal(await evaluate(`document.activeElement.id`), 'filter-search');
  assert.equal(await evaluate(`document.querySelector('#filter-search').value`), 'APPROVAL');
  await reset();
  await evaluate(`(()=>{const d=document.querySelector('details[data-detail-key="evidence"]');d.open=true;d.querySelector('summary').focus();window.__card=document.querySelector('.review-topic');window.__summary=d.querySelector('summary');})()`);
  await refresh();
  assert.equal(await evaluate(`window.__summary===document.activeElement && window.__card===document.querySelector('.review-topic') && document.activeElement.parentElement.open`), true);

  // Archive via the real CLI; wait for the normal 8-second polling cycle, no refresh click.
  const retry = duplicate(business);
  retry.id = 'synthetic-business-unobserved-retry';
  retry.created_at = '2026-11-12T04:00:00Z';
  retry.targets = retry.targets.map(target => ({...target, status: 'not_observed', evidence: 'Synthetic retry: expression was not observed.'}));
  archive(retry, 'retry');
  await browserWait(`document.querySelector('#stat-sessions').textContent==='3'`, 12000);
  assert.equal(await evaluate(`window.__card===document.querySelector('.review-topic') && document.activeElement.matches('summary[data-focus-key="evidence"]') && document.activeElement.parentElement.open`), true);
  assert.deepEqual(await evaluate(`['#stat-mastered','#stat-review','#stat-unobserved'].map(id=>document.querySelector(id).textContent)`), ['2','1','2']);
  assert.equal(await evaluate(`document.querySelector('details[data-detail-key="evidence"]').textContent.includes('Synthetic: I would need approval for that.')`), true);
  await evaluate(`document.querySelector('details[data-detail-key="history"]').open=true`);
  await search('APPROVAL');
  const added = duplicate(business);
  added.id = 'synthetic-search-focus-archive';
  added.created_at = '2026-11-13T04:00:00Z';
  added.topic.id = added.scenario.id = 'synthetic-followup';
  added.topic.label = '虚构验收：审批跟进';
  archive(added, 'search-focus');
  await browserWait(`document.querySelector('#stat-sessions').textContent==='3'`, 12000);
  assert.equal(await evaluate(`document.activeElement.id`), 'filter-search');
  assert.equal(await evaluate(`document.querySelector('details[data-detail-key="history"]').open`), true);
  await reset();

  // Valid backend fixture with deliberately hostile text; all markup must be literal.
  const hostile = duplicate(business);
  const hostileText = `"><img src=x onerror="window.__xss=1"><script>window.__xss=2</script>&'`;
  hostile.id = 'synthetic-hostile-text';
  hostile.created_at = 'invalid date: synthetic fixture';
  hostile.topic = {id: '__proto__', label: hostileText};
  hostile.scenario = {id: '__proto__', category_id: hostileText, category_label: hostileText};
  hostile.roles = {learner: hostileText, coach: hostileText};
  hostile.business = {industry: {id: hostileText, label: hostileText}, context: hostileText, constraints: [hostileText],
    outcome: {status: 'declined', summary: hostileText}, criteria: [{criterion: hostileText, status: 'unmet', evidence: hostileText}],
    feedback: [{dimension: 'clarity', observation: hostileText, evidence: hostileText, suggestion: hostileText}], next_action: hostileText};
  hostile.targets = [{expression: hostileText, status: 'not_observed', evidence: hostileText}];
  archive(hostile, 'hostile');
  const sparse = duplicate(business);
  sparse.id = 'synthetic-sparse-business';
  sparse.created_at = '2026-11-14T04:00:00Z';
  sparse.topic = {id: 'constructor', label: '虚构验收：未记录可选业务字段'};
  sparse.scenario = {id: 'constructor', category_id: 'synthetic-optional', category_label: '虚构分类：可选字段'};
  sparse.business = {};
  sparse.targets = [];
  archive(sparse, 'sparse');
  await refresh();
  assert.equal(await evaluate(`window.__xss`), undefined);
  assert.equal(await evaluate(`document.querySelectorAll('#review-list img,#review-list script').length`), 0);
  assert.equal(await evaluate(`document.querySelectorAll('.review-topic').length`), 5);
  assert.equal(await evaluate(`document.querySelector('.review-topic').textContent.includes('无可评估表达')`), true);
  await cdp('Emulation.setDeviceMetricsOverride', {width: 360, height: 1000, deviceScaleFactor: 1, mobile: true});
  await evaluate(`window.scrollTo({top:0,behavior:'instant'})`);
  await screenshot('mobile-360-overview');
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=360`), true);
  await evaluate(`document.querySelectorAll('details').forEach(d=>d.open=true)`);
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=360`), true, 'Expanded evidence must wrap at 360px');
  await evaluate(`document.querySelectorAll('details').forEach(d=>d.open=false);document.querySelectorAll('.review-topic')[1].scrollIntoView({behavior:'instant',block:'start'})`);
  await screenshot('mobile-360-business-card');
  await evaluate(`document.querySelectorAll('.review-topic')[1].querySelector('.business-review').scrollIntoView({behavior:'instant',block:'start'})`);
  await screenshot('mobile-360-feedback');

  await search('synthetic nonexistent keyword');
  assert.equal(await evaluate(`!document.querySelector('#no-results').classList.contains('hidden')`), true);
  await evaluate(`document.querySelector('#clear-no-results').click()`);
  assert.equal(await evaluate(`document.activeElement.id`), 'filter-search');

  // Failure injection touches only the freshly-created temporary archive.
  const saved = readFileSync(join(dataDir, 'workbench-data.json'), 'utf8');
  writeFileSync(join(dataDir, 'workbench-data.json'), '{synthetic corrupt JSON');
  await refresh();
  assert.equal(await evaluate(`document.querySelector('#sync-status').dataset.state`), 'stale');
  assert.equal(await evaluate(`document.querySelector('#save-status').textContent.includes('保留上次存档')`), true);
  assert.equal(await evaluate(`document.querySelectorAll('.review-topic').length`), 5);
  await cdp('Page.reload');
  await browserWait(`typeof loading !== 'undefined' && !loading && document.querySelector('#sync-status').dataset.state==='stale'`);
  assert.equal(await evaluate(`!document.querySelector('#load-unavailable').classList.contains('hidden') && document.querySelector('#empty-review').classList.contains('hidden')`), true);
  writeFileSync(join(dataDir, 'workbench-data.json'), saved);
  await refresh();
  assert.equal(await metric('#stat-sessions'), '6');
  writeSyntheticState([legacy], 1);
  await refresh();
  assert.equal(await evaluate(`document.querySelector('.domain-tag').textContent`), '未分类');
  writeSyntheticState([]);
  await refresh();
  assert.equal(await evaluate(`!document.querySelector('#empty-review').classList.contains('hidden') && document.querySelector('#no-results').classList.contains('hidden')`), true);
  assert.equal(await evaluate(`document.querySelector('#assessment-note').textContent.includes('无可评估表达')`), true);
  // Technical interviews: real archive, separate support channels and contextual review.
  archive(interviewFixture, 'interview');
  await refresh();
  assert.equal(await metric('#stat-sessions'), '1');
  assert.equal(await metric('#stat-mastered'), '0', 'Technical met must not enter English mastery counts');
  assert.equal(await evaluate(`!document.querySelector('#technical-review').classList.contains('hidden')`), true);
  assert.equal(await evaluate(`document.querySelectorAll('#technical-review .technical-observation').length`), 3);
  assert.equal(await evaluate(`document.querySelector('#technical-review').textContent.includes('keyword') || document.querySelector('#technical-review').textContent.includes('关键词')`), true);
  await cdp('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1120, deviceScaleFactor: 1, mobile: false});
  await evaluate(`document.querySelector('#technical-review').scrollIntoView({behavior:'instant',block:'start'})`);
  await screenshot('desktop-interview-technical-review');
  await cdp('Emulation.setDeviceMetricsOverride', {width: 360, height: 1000, deviceScaleFactor: 1, mobile: true});
  await evaluate(`document.querySelector('#technical-review').scrollIntoView({behavior:'instant',block:'start'})`);
  await screenshot('mobile-interview-clean');
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=360`), true);
  const unobservedInterview = duplicate(interviewFixture);
  unobservedInterview.id = 'synthetic-interview-unobserved';
  unobservedInterview.created_at = '2026-11-12T11:00:00+08:00';
  unobservedInterview.interview.observations = unobservedInterview.interview.observations.map(item => ({concept_id:item.concept_id,label:item.label,question_id:item.question_id,status:'not_observed',language_support:'none',technical_support:'none'}));
  archive(unobservedInterview, 'interview-unobserved');
  await refresh();
  assert.equal(await evaluate(`document.querySelector('#technical-review').textContent.includes('Synthetic learner utterance: A timeout means unknown, not failed.')`), true);
  await evaluate(`document.querySelectorAll('details').forEach(d=>d.open=true)`);
  assert.equal(await evaluate(`document.querySelector('.history-entry .interview-review').textContent.includes('本次技术面试')`), true);
  const crossScene = duplicate(interviewFixture);
  crossScene.id = 'synthetic-interview-cross-scene';
  crossScene.created_at = '2026-11-13T11:00:00+08:00';
  crossScene.scenario.id = crossScene.topic.id = 'int-custom-timeout-transfer';
  crossScene.topic.label = 'Synthetic / 虚构：换场景超时复练';
  crossScene.interview.observations = [{...crossScene.interview.observations[0],status:'partial',technical_support:'hint',evidence:'Synthetic newer assisted transfer evidence'}];
  archive(crossScene, 'interview-cross-scene');
  await refresh();
  assert.equal(await evaluate(`document.querySelectorAll('#technical-review .technical-observation').length`), 3, 'Same concept/depth/role merges across scenes');
  assert.equal(await evaluate(`document.querySelector('#technical-review').textContent.includes('Synthetic newer assisted transfer evidence')`), true);
  await search('广播超时后恢复付款');
  assert.equal(await metric('#stat-sessions'), '2');
  assert.equal(await evaluate(`document.querySelector('#technical-review').textContent.includes('Synthetic learner utterance: A timeout means unknown, not failed.')`), true, 'Review uses current filtered sessions');
  await reset();
  const hostileInterview = duplicate(interviewFixture);
  hostileInterview.id = 'synthetic-interview-hostile';
  hostileInterview.created_at = '2026-11-14T11:00:00+08:00';
  hostileInterview.interview.track.label = hostileText;
  for (const observation of hostileInterview.interview.observations) {
    observation.label = hostileText;
    if (observation.status !== 'not_observed') observation.evidence = observation.observation = observation.suggestion = hostileText;
  }
  archive(hostileInterview, 'interview-hostile');
  await refresh();
  assert.equal(await evaluate(`window.__xss`), undefined);
  assert.equal(await evaluate(`document.querySelectorAll('#technical-review img,#technical-review script,#review-list img,#review-list script').length`), 0);
  await cdp('Emulation.setDeviceMetricsOverride', {width: 360, height: 1000, deviceScaleFactor: 1, mobile: true});
  await evaluate(`document.querySelectorAll('details').forEach(d=>d.open=true)`);
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=360`), true, 'Technical evidence and metadata must wrap at 360px');
  await evaluate(`document.querySelector('#technical-review').scrollIntoView({behavior:'instant',block:'start'})`);
  await screenshot('mobile-interview-technical-review');
  assert.equal(runtimeErrors.length, 0, JSON.stringify(runtimeErrors));
  assert(outboundRequests.every(request => request.method === 'GET'), 'Frontend must remain read-only');
  assert(outboundRequests.every(request => request.url.startsWith(url)), 'Frontend must make no external requests');
  console.log(`PASS: real CLI/archive/health; contextual metrics; v1; filters/search/reset; 8-second auto-refresh; focus/details; original evidence; hostile text; optional fields; 360px; initial and stale load failures; empty archive; technical interview metadata/evidence/history; separate support channels; cross-scene concept review and filtered evidence; technical hostile text/360px; read-only/no external requests.\nSynthetic data and screenshots: ${temporary}`);
} catch (error) {
  console.error(error);
  console.error(`Synthetic temp output: ${temporary}\nServer log: ${backendLog}`);
  process.exitCode = 1;
} finally {
  await closeAll();
}
