'use strict';
let selected = null, selectedState = null, lastObservation = null, busy = false;
const $ = id => document.getElementById(id);
const TOKEN = document.querySelector('meta[name="vec1-token"]')?.content || '';
const MUTATORS = ['cloneBtn','checkpointBtn','verifyBtn','saveObject','keyframeBtn','tickBtn','ocrObserve','ocrCommit','suspendBtn','resumeBtn','retireBtn','restoreBtn','checkpointSelect'];

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function pretty(x) { return JSON.stringify(x, null, 2); }
function showResult(x, isError = false) {
  const el = $('opResult');
  el.textContent = typeof x === 'string' ? x : pretty(x);
  el.classList.toggle('err', isError);
}

async function api(path, options = {}) {
  const headers = {'Content-Type': 'application/json', 'X-VEC1-Token': TOKEN};
  const r = await fetch(path, {...options, headers, cache: 'no-store', credentials: 'same-origin'});
  let data;
  try { data = await r.json(); } catch { data = {error: r.statusText}; }
  if (!r.ok) { const e = new Error(data.detail || data.error || r.statusText); e.status = r.status; throw e; }
  return data;
}

// Every button handler goes through guard(): errors are shown, never swallowed as unhandled rejections.
function guard(fn) {
  return async (...args) => {
    if (busy) return;
    busy = true;
    try { await fn(...args); }
    catch (e) {
      showResult(`${e.status ? e.status + ' · ' : ''}${e.message}`, true);
      if (e.status === 409 && selected) { try { await selectElectron(selected, false); } catch {} }
    }
    finally { busy = false; }
  };
}

function setControls() {
  const st = selectedState?.status;
  MUTATORS.forEach(x => { $(x).disabled = !selectedState; });
  if (!selectedState) return;
  const active = st === 'ACTIVE';
  ['saveObject','keyframeBtn','tickBtn','ocrObserve','ocrCommit','suspendBtn','cloneBtn'].forEach(x => { $(x).disabled = !active; });
  $('resumeBtn').disabled = st !== 'SUSPENDED';
  $('retireBtn').disabled = st === 'RETIRED';
  $('checkpointBtn').disabled = st === 'RETIRED';
  const cps = selectedState.checkpoints || [];
  $('checkpointSelect').innerHTML = cps.length
    ? cps.map(c => `<option value="${esc(c.hash)}">tick ${esc(c.tick)} · ${esc(c.hash.slice(0, 12))}…</option>`).join('')
    : '<option value="">none</option>';
  $('restoreBtn').disabled = !cps.length;
}

async function refresh() {
  try {
    const s = await api('/api/status');
    const ledgerText = s.ledger.ok ? `ledger ${s.ledger.events} events` : `LEDGER FAULT: ${s.ledger.error}`;
    $('globalStatus').textContent = `v${s.version} · ${ledgerText}`;
    $('nodes').innerHTML = Object.entries(s.fabric_nodes).map(([n, v]) =>
      `<div class="card"><strong>${esc(n)}</strong><span class="${v.bound ? 'ok' : 'warn'}">${v.bound ? 'BOUND' : 'NOT BUILT/BOUND'}</span><div class="muted">present=${esc(v.present)} · sums=${esc(v.sums_match)}</div></div>`
    ).join('') || `<div class="card bad">${esc(s.fabric_error || 'no fabric nodes reported')}</div>`;
    const es = s.electrons || [];
    $('electrons').innerHTML = es.map(e =>
      `<div class="electron ${selected === e.electron_id ? 'selected' : ''}" data-id="${esc(e.electron_id)}" tabindex="0" role="button">` +
      `<strong>${esc(e.name ?? e.electron_id)}</strong>` +
      (e.status && e.status !== 'ACTIVE' ? `<span class="badge ${esc(e.status)}">${esc(e.status)}</span>` : '') +
      (e.integrity && e.integrity !== 'OK' ? `<span class="badge ${esc(e.integrity)}">${esc(e.integrity)}</span>` : '') +
      `<div class="muted">${esc(e.electron_id)}<br>tick ${esc(e.logical_tick)}</div></div>`
    ).join('') || '<div class="muted">No electrons yet.</div>';
    document.querySelectorAll('.electron').forEach(el => {
      const go = guard(() => selectElectron(el.dataset.id));
      el.onclick = go;
      el.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(); } };
    });
    await loadEvents();
  } catch (e) { $('globalStatus').textContent = 'error: ' + e.message; }
}

async function selectElectron(id, doRefresh = true) {
  if (selected !== id) lastObservation = null;
  selected = id;
  selectedState = await api('/api/electrons/' + encodeURIComponent(id));
  $('inspector').textContent = pretty(selectedState);
  setControls();
  if (doRefresh) await refresh();
}

async function op(method, payload = {}) {
  if (!selected) return;
  payload.expected_state_hash = selectedState?.state_hash;
  const r = await api(`/api/electrons/${encodeURIComponent(selected)}/operate`, {method: 'POST', body: JSON.stringify({method, payload})});
  selectedState = r.electron;
  if (method === 'restore') lastObservation = null;
  $('inspector').textContent = pretty(selectedState);
  showResult({result: r.result, placement: r.placement});
  setControls();
  await refresh();
  return r;
}

async function loadEvents() {
  const e = await api('/api/events?limit=40');
  $('events').textContent = e.events.length ? pretty(e.events.slice().reverse()) : 'No events yet.';
}

function num(id) {
  const v = Number($(id).value);
  if (!Number.isFinite(v)) throw new Error(`${id}: enter a number`);
  return v;
}

$('refresh').onclick = guard(refresh);
$('createElectron').onclick = guard(async () => {
  const e = await api('/api/electrons', {method: 'POST', body: JSON.stringify({name: $('newName').value})});
  await selectElectron(e.electron_id);
});
$('cloneBtn').onclick = guard(async () => {
  const c = await api(`/api/electrons/${encodeURIComponent(selected)}/clone`, {method: 'POST', body: '{}'});
  await selectElectron(c.electron_id);
});
$('checkpointBtn').onclick = guard(() => op('checkpoint', {}));
$('verifyBtn').onclick = guard(() => op('cross_target.verify', {require_all: false}));
$('suspendBtn').onclick = guard(() => op('suspend', {}));
$('resumeBtn').onclick = guard(() => op('resume', {}));
$('retireBtn').onclick = guard(async () => {
  if (!window.confirm || window.confirm('Retire this electron? It becomes immutable until a checkpoint is restored.')) await op('retire', {});
});
$('restoreBtn').onclick = guard(() => op('restore', {checkpoint_hash: $('checkpointSelect').value}));
$('saveObject').onclick = guard(() => op('object.upsert', {object_id: $('objId').value, object: {type: $('objType').value, text: $('objText').value, transform: {x: num('objX'), y: num('objY')}}}));
$('keyframeBtn').onclick = guard(() => op('animation.keyframe', {object_id: $('objId').value, property: $('animProp').value, tick: Math.trunc(num('animTick')), value: num('animValue'), interpolation: $('animInterp').value}));
$('tickBtn').onclick = guard(() => op('animation.tick', {tick: Math.trunc(num('tickValue'))}));
$('ocrObserve').onclick = guard(async () => {
  const r = await op('ocr.observe', {source_sha256: $('ocrHash').value.trim(), text: $('ocrText').value, confidence: num('ocrConfidence'), geometry: {x: 0, y: 0, w: 100, h: 20}, engine: 'external-bridge', engine_version: 'operator-supplied'});
  lastObservation = r?.result?.observation?.id || null;
});
$('ocrCommit').onclick = guard(async () => {
  if (!lastObservation) { showResult('Record an OCR observation first.', true); return; }
  await op('ocr.commit', {observation_id: lastObservation, object_id: $('ocrTarget').value});
});
$('fabricDiag').onclick = guard(async () => {
  $('fabricResult').textContent = 'running…';
  try {
    const r = await api('/api/fabric/diagnostic', {method: 'POST', body: '{}'});
    $('fabricResult').textContent = `${r.verdict ?? 'no verdict'} · ${r.nodes_bound?.length || 0}/4 nodes · ${r.replay || r.error || ''}`;
  } catch (e) { $('fabricResult').textContent = e.message; throw e; }
});
setControls();
refresh();
