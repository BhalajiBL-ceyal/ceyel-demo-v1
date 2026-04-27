/**
 * Ceyel Dashboard — app.js
 * All frontend logic: API integration, D3 DFG graph, Chart.js charts,
 * navigation, toasts, and data rendering.
 */

const API = '';  // Same origin — FastAPI serves this file

// ── Chart instances (kept for re-render) ───────────────────────────────────
let chartCycleTime = null;
let chartActivity  = null;
let chartRisk      = null;

// ══════════════════════════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════════════════════════

function navigate(page) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const sec = document.getElementById(`sec-${page}`);
  const nav = document.getElementById(`nav-${page}`);
  if (sec) sec.classList.add('active');
  if (nav) nav.classList.add('active');

  // Lazy-load data for each section
  const loaders = {
    overview:    refreshAll,
    mining:      loadDFG,
    variants:    loadVariants,
    conformance: runDefaultConformance,
    prediction:  loadPredictions,
    trust:       () => { loadTrustRoot(); loadHashes(); },
    blockchain:  loadChain,
    events:      loadEvents,
  };
  if (loaders[page]) loaders[page]();
}

// ══════════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════════════════

function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ══════════════════════════════════════════════════════════════════════════
// API HELPERS
// ══════════════════════════════════════════════════════════════════════════

async function apiFetch(path, options = {}) {
  const res = await fetch(API + path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API error');
  }
  return res.json();
}

// ══════════════════════════════════════════════════════════════════════════
// OVERVIEW — refresh all summary data
// ══════════════════════════════════════════════════════════════════════════

async function refreshAll() {
  try {
    const [stats, cycleTime, conformance, predictions] = await Promise.all([
      apiFetch('/api/mining/stats'),
      apiFetch('/api/mining/cycle-time'),
      apiFetch('/api/conformance/default'),
      apiFetch('/api/prediction').catch(() => []),
    ]);

    // Stat cards
    document.getElementById('stat-events').textContent     = stats.total_events;
    document.getElementById('stat-cases').textContent      = stats.total_cases;
    document.getElementById('stat-cycle').textContent      = stats.average_cycle_time_hours + 'h';
    document.getElementById('stat-fitness').textContent    = (conformance.fitness_score * 100).toFixed(0) + '%';
    document.getElementById('stat-variants').textContent   = stats.process_variants_count;
    document.getElementById('stat-activities').textContent = stats.unique_activities;

    // Cycle time chart
    renderCycleTimeChart(cycleTime.per_case);

    // High risk cases
    renderRiskList(predictions);

  } catch (e) {
    toast('Could not load overview: ' + e.message, 'error');
  }
}

function renderCycleTimeChart(perCase) {
  const canvas = document.getElementById('chart-cycletime');
  const ctx = canvas.getContext('2d');
  const labels = Object.keys(perCase);
  const values = Object.values(perCase);

  if (chartCycleTime) chartCycleTime.destroy();

  chartCycleTime = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Cycle Time (h)',
        data: values,
        backgroundColor: values.map(v => v > 72 ? 'rgba(239,68,68,0.7)' : v > 48 ? 'rgba(245,158,11,0.7)' : 'rgba(99,132,255,0.7)'),
        borderColor: values.map(v => v > 72 ? '#ef4444' : v > 48 ? '#f59e0b' : '#6384ff'),
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(99,132,255,0.06)' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
        y: { grid: { color: 'rgba(99,132,255,0.06)' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
      }
    }
  });
}

function renderRiskList(predictions) {
  const el = document.getElementById('risk-list');
  const high = predictions.filter(p => p.delay_risk > 0.5).slice(0, 6);

  if (!high.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">✅</div><p>No high-risk cases detected</p></div>';
    return;
  }

  el.innerHTML = `
    <table>
      <thead><tr><th>Case</th><th>Risk</th><th>Level</th></tr></thead>
      <tbody>
        ${high.map(p => `
          <tr>
            <td><strong>${p.case_id}</strong></td>
            <td>
              <div class="progress-bar-wrap ${p.delay_risk > 0.7 ? 'progress-red' : 'progress-amber'}">
                <div class="progress-bar-fill" style="width:${(p.delay_risk * 100).toFixed(0)}%"></div>
              </div>
              <small style="color:var(--text-muted)">${(p.delay_risk * 100).toFixed(0)}%</small>
            </td>
            <td><span class="chip ${p.delay_risk_level === 'HIGH' ? 'chip-red' : 'chip-amber'}">${p.delay_risk_level}</span></td>
          </tr>
        `).join('')}
      </tbody>
    </table>`;
}

// ══════════════════════════════════════════════════════════════════════════
// PROCESS GRAPH — D3 Force-Directed DFG
// ══════════════════════════════════════════════════════════════════════════

async function loadDFG() {
  const container = document.getElementById('dfg-container');
  container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Building graph…</div>';

  try {
    const [dfg, stats] = await Promise.all([
      apiFetch('/api/mining/dfg'),
      apiFetch('/api/mining/stats'),
    ]);

    document.getElementById('dfg-edge-count').textContent = dfg.edges.length + ' edges';
    renderDFG(dfg, container);
    renderActivityChart(dfg.nodes);
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><p>No events loaded yet. Load sample data first.</p></div>';
    toast('DFG error: ' + e.message, 'error');
  }
}

function renderDFG(dfg, container) {
  container.innerHTML = '';
  const W = container.clientWidth  || 800;
  const H = container.clientHeight || 480;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', W)
    .attr('height', H)
    .attr('id', 'dfg-svg');

  // Arrow marker
  svg.append('defs').append('marker')
    .attr('id', 'arrowhead')
    .attr('markerWidth', 10)
    .attr('markerHeight', 7)
    .attr('refX', 36)
    .attr('refY', 3.5)
    .attr('orient', 'auto')
    .append('polygon')
    .attr('points', '0 0, 10 3.5, 0 7')
    .attr('fill', 'rgba(99,132,255,0.45)');

  const maxFreq  = Math.max(...dfg.nodes.map(n => n.frequency), 1);
  const maxEdge  = Math.max(...dfg.edges.map(e => e.frequency), 1);

  const nodeMap = {};
  dfg.nodes.forEach(n => { nodeMap[n.id] = n; });

  const links = dfg.edges.map(e => ({
    source: e.from,
    target: e.to,
    freq:   e.frequency,
  }));

  const simulation = d3.forceSimulation(dfg.nodes)
    .force('link',   d3.forceLink(links).id(d => d.id).distance(120))
    .force('charge', d3.forceManyBody().strength(-320))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(50));

  // Edges
  const link = svg.append('g').selectAll('line')
    .data(links)
    .join('line')
    .attr('class', 'dfg-edge')
    .attr('stroke-width', d => 1 + (d.freq / maxEdge) * 4)
    .attr('marker-end', 'url(#arrowhead)');

  // Edge labels
  const edgeLabel = svg.append('g').selectAll('text')
    .data(links)
    .join('text')
    .attr('class', 'dfg-edge-label')
    .text(d => d.freq);

  // Nodes group
  const node = svg.append('g').selectAll('g')
    .data(dfg.nodes)
    .join('g')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag',  (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on('end',   (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }));

  // Node rectangles
  node.append('rect')
    .attr('class', 'dfg-node')
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('width',  d => 80 + (d.frequency / maxFreq) * 40)
    .attr('height', 34)
    .attr('x',      d => -(40 + (d.frequency / maxFreq) * 20))
    .attr('y', -17);

  // Node text
  node.append('text')
    .attr('class', 'dfg-node-text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .text(d => d.label.length > 18 ? d.label.slice(0, 17) + '…' : d.label);

  // Frequency badge
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '1.6em')
    .attr('font-size', '9px')
    .attr('fill', 'rgba(99,132,255,0.6)')
    .text(d => `×${d.frequency}`);

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    edgeLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 5);

    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

function renderActivityChart(nodes) {
  const canvas = document.getElementById('chart-activity');
  const ctx = canvas.getContext('2d');
  const sorted = [...nodes].sort((a, b) => b.frequency - a.frequency);

  if (chartActivity) chartActivity.destroy();

  chartActivity = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: sorted.map(n => n.label),
      datasets: [{
        label: 'Frequency',
        data: sorted.map(n => n.frequency),
        backgroundColor: 'rgba(34,211,238,0.6)',
        borderColor: '#22d3ee',
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(99,132,255,0.06)' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
        y: { grid: { color: 'rgba(99,132,255,0.06)' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
      }
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════
// VARIANTS
// ══════════════════════════════════════════════════════════════════════════

async function loadVariants() {
  try {
    const variants = await apiFetch('/api/mining/variants');
    document.getElementById('variant-count').textContent = variants.length;
    const total = variants.reduce((s, v) => s + v.count, 0);
    const tbody = document.getElementById('variants-tbody');
    tbody.innerHTML = variants.map((v, i) => `
      <tr>
        <td><strong style="color:var(--accent-blue)">#${i + 1}</strong></td>
        <td>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            ${v.variant.map((act, idx) => `
              <span style="display:inline-flex;align-items:center;gap:4px">
                <span class="chip chip-blue" style="font-size:10px">${act}</span>
                ${idx < v.variant.length - 1 ? '<span style="color:var(--text-muted)">→</span>' : ''}
              </span>
            `).join('')}
          </div>
        </td>
        <td><strong>${v.count}</strong></td>
        <td style="font-size:12px;color:var(--text-muted)">${v.cases.join(', ')}</td>
        <td>
          <div class="progress-bar-wrap progress-blue" style="width:80px">
            <div class="progress-bar-fill" style="width:${((v.count / total) * 100).toFixed(0)}%"></div>
          </div>
          <small style="color:var(--text-muted)">${((v.count / total) * 100).toFixed(0)}%</small>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    toast('Variants error: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// CONFORMANCE
// ══════════════════════════════════════════════════════════════════════════

async function runDefaultConformance() {
  const result = await apiFetch('/api/conformance/default').catch(e => null);
  if (result) renderConformance(result);
}

async function runConformance() {
  const raw = document.getElementById('ref-sequence').value;
  const seq = raw.split(',').map(s => s.trim()).filter(Boolean);
  if (!seq.length) { toast('Enter at least one activity', 'error'); return; }

  try {
    const result = await apiFetch('/api/conformance/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reference_sequence: seq }),
    });
    renderConformance(result);
  } catch (e) {
    toast('Conformance error: ' + e.message, 'error');
  }
}

function renderConformance(result) {
  document.getElementById('conformance-summary').style.display = 'block';
  document.getElementById('conformance-results-card').style.display = 'block';

  document.getElementById('conf-total').textContent   = result.total_cases;
  document.getElementById('conf-ok').textContent      = result.conforming_cases;
  document.getElementById('conf-dev').textContent     = result.deviating_cases;
  document.getElementById('conf-fitness').textContent = (result.fitness_score * 100).toFixed(1) + '%';

  const tbody = document.getElementById('conformance-tbody');
  tbody.innerHTML = result.deviations.map(d => `
    <tr>
      <td><strong>${d.case_id}</strong></td>
      <td><span class="chip ${d.is_conforming ? 'chip-green' : 'chip-red'}">${d.is_conforming ? '✓ Conforming' : '✗ Deviating'}</span></td>
      <td>${d.missing_steps.length ? d.missing_steps.map(s => `<span class="chip chip-amber" style="margin-right:4px">${s}</span>`).join('') : '<span style="color:var(--text-muted)">—</span>'}</td>
      <td>${d.extra_steps.length   ? d.extra_steps.map(s   => `<span class="chip chip-purple" style="margin-right:4px">${s}</span>`).join('') : '<span style="color:var(--text-muted)">—</span>'}</td>
      <td>${d.order_violations.length ? d.order_violations.map(v => `<span class="chip chip-red" style="margin-right:4px;font-size:10px">${v}</span>`).join('') : '<span style="color:var(--text-muted)">—</span>'}</td>
    </tr>
  `).join('');
}

// ══════════════════════════════════════════════════════════════════════════
// PREDICTION
// ══════════════════════════════════════════════════════════════════════════

async function loadPredictions() {
  try {
    const preds = await apiFetch('/api/prediction');
    document.getElementById('pred-count').textContent = preds.length;

    const tbody = document.getElementById('prediction-tbody');
    tbody.innerHTML = preds.map(p => `
      <tr>
        <td><strong>${p.case_id}</strong></td>
        <td>
          <div class="progress-bar-wrap progress-blue" style="width:80px;display:inline-block">
            <div class="progress-bar-fill" style="width:${p.progress_pct || 0}%"></div>
          </div>
          <small style="color:var(--text-muted);margin-left:6px">${p.progress_pct || 0}%</small>
        </td>
        <td style="color:var(--text-secondary)">${p.elapsed_hours}h</td>
        <td style="color:var(--accent-cyan);font-weight:600">${p.remaining_time_hours}h</td>
        <td>
          <div class="progress-bar-wrap ${p.delay_risk > 0.7 ? 'progress-red' : p.delay_risk > 0.4 ? 'progress-amber' : 'progress-green'}" style="width:80px;display:inline-block">
            <div class="progress-bar-fill" style="width:${(p.delay_risk * 100).toFixed(0)}%"></div>
          </div>
          <small style="color:var(--text-muted);margin-left:6px">${(p.delay_risk * 100).toFixed(0)}%</small>
        </td>
        <td><span class="chip ${p.delay_risk_level === 'HIGH' ? 'chip-red' : p.delay_risk_level === 'MEDIUM' ? 'chip-amber' : 'chip-green'}">${p.delay_risk_level}</span></td>
      </tr>
    `).join('');

    renderRiskChart(preds);
  } catch (e) {
    toast('Prediction error: ' + e.message, 'error');
  }
}

function renderRiskChart(preds) {
  const canvas = document.getElementById('chart-risk');
  const ctx = canvas.getContext('2d');

  const low    = preds.filter(p => p.delay_risk_level === 'LOW').length;
  const medium = preds.filter(p => p.delay_risk_level === 'MEDIUM').length;
  const high   = preds.filter(p => p.delay_risk_level === 'HIGH').length;

  if (chartRisk) chartRisk.destroy();

  chartRisk = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Low Risk', 'Medium Risk', 'High Risk'],
      datasets: [{
        data: [low, medium, high],
        backgroundColor: ['rgba(16,185,129,0.7)', 'rgba(245,158,11,0.7)', 'rgba(239,68,68,0.7)'],
        borderColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          labels: { color: '#94a3b8', font: { size: 12 } },
        }
      },
      cutout: '60%',
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════
// TRUST LAYER
// ══════════════════════════════════════════════════════════════════════════

async function loadTrustRoot() {
  try {
    const data = await apiFetch('/api/trust/root');
    document.getElementById('global-merkle-root').textContent = data.merkle_root;
    document.getElementById('trust-event-count').textContent  = `${data.total_events} events committed`;
  } catch (e) {
    document.getElementById('global-merkle-root').textContent = 'Error loading root';
  }
}

async function lookupProof() {
  const caseId = document.getElementById('proof-case-id').value.trim();
  if (!caseId) { toast('Enter a Case ID', 'error'); return; }

  const resultEl = document.getElementById('proof-result');
  resultEl.innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Generating proof…</div>';

  try {
    const data = await apiFetch(`/api/trust/proof/${encodeURIComponent(caseId)}`);
    resultEl.innerHTML = `
      <div style="margin-bottom:12px">
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px">MERKLE ROOT</div>
        <div class="hash-box">${data.merkle_root}</div>
      </div>
      <div style="font-size:14px;color:var(--text-secondary);margin-bottom:12px">
        ${data.event_count} events in case <strong>${data.case_id}</strong>
      </div>
      ${data.proofs.map((p, i) => `
        <div style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius-md);padding:14px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <strong>${p.activity}</strong>
            <span class="chip ${p.valid ? 'chip-green' : 'chip-red'}">${p.valid ? '✓ VALID' : '✗ INVALID'}</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">Event Hash:</div>
          <div class="hash-box" style="font-size:11px">${p.event_hash}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:8px">${p.proof_steps.length} proof steps</div>
        </div>
      `).join('')}
    `;
  } catch (e) {
    resultEl.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
  }
}

async function loadHashes() {
  try {
    const hashes = await apiFetch('/api/trust/hashes');
    const tbody = document.getElementById('hash-tbody');
    tbody.innerHTML = hashes.map(h => `
      <tr>
        <td>${h.id}</td>
        <td><strong>${h.case_id}</strong></td>
        <td>${h.activity}</td>
        <td><code style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent-cyan)">${h.hash.slice(0, 20)}…${h.hash.slice(-8)}</code></td>
      </tr>
    `).join('');
  } catch (e) {
    toast('Error loading hashes: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// BLOCKCHAIN
// ══════════════════════════════════════════════════════════════════════════

async function loadChain() {
  try {
    const data = await apiFetch('/api/blockchain/chain');
    document.getElementById('chain-length').textContent = data.length + ' blocks';
    const el = document.getElementById('blockchain-blocks');

    if (!data.chain.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon">⛓</div><p>No blocks yet. Click "Commit New Block" to create the genesis block.</p></div>';
      return;
    }

    el.innerHTML = [...data.chain].reverse().map(block => `
      <div class="block-card">
        <div class="block-id">⬡ Block #${block.block_id}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px">
          <div>
            <div style="color:var(--text-muted);margin-bottom:4px">Merkle Root</div>
            <div class="block-hash-short">${block.merkle_root.slice(0, 24)}…</div>
          </div>
          <div>
            <div style="color:var(--text-muted);margin-bottom:4px">Block Hash</div>
            <div class="block-hash-short">${block.block_hash.slice(0, 24)}…</div>
          </div>
          <div>
            <div style="color:var(--text-muted);margin-bottom:4px">Previous Hash</div>
            <div class="block-hash-short">${block.prev_hash.slice(0, 24)}…</div>
          </div>
          <div>
            <div style="color:var(--text-muted);margin-bottom:4px">Timestamp</div>
            <div style="color:var(--text-secondary)">${new Date(block.timestamp).toLocaleString()}</div>
          </div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    toast('Chain error: ' + e.message, 'error');
  }
}

async function commitBlock() {
  try {
    const data = await apiFetch('/api/blockchain/commit', { method: 'POST' });
    toast(`⛓ Block #${data.block.block_id} committed!`, 'success');
    if (document.getElementById('sec-blockchain').classList.contains('active')) {
      loadChain();
    }
  } catch (e) {
    toast('Failed to commit block: ' + e.message, 'error');
  }
}

async function verifyChain() {
  try {
    const data = await apiFetch('/api/blockchain/verify');
    const el = document.getElementById('chain-integrity-result');
    if (data.valid) {
      el.innerHTML = `<div class="chip chip-green" style="padding:8px 16px;font-size:13px">✅ Chain is valid — ${data.chain_length} blocks verified</div>`;
    } else {
      el.innerHTML = `<div class="chip chip-red" style="padding:8px 16px;font-size:13px">❌ Chain integrity broken at block #${data.broken_at}: ${data.reason}</div>`;
    }
    toast(data.valid ? 'Chain integrity verified ✓' : 'Chain integrity BROKEN!', data.valid ? 'success' : 'error');
  } catch (e) {
    toast('Verify error: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// EVENT LOG
// ══════════════════════════════════════════════════════════════════════════

async function loadEvents() {
  try {
    const events = await apiFetch('/api/events');
    document.getElementById('events-count').textContent = events.length;
    const tbody = document.getElementById('events-tbody');
    tbody.innerHTML = events.map(e => `
      <tr>
        <td>${e.id}</td>
        <td><strong>${e.case_id}</strong></td>
        <td>${e.activity}</td>
        <td style="color:var(--text-muted)">${e.actor || '—'}</td>
        <td style="font-size:12px;color:var(--text-muted)">${new Date(e.timestamp).toLocaleString()}</td>
        <td>$${e.cost.toFixed(2)}</td>
        <td>${e.duration} min</td>
        <td><code style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent-cyan)">${e.event_hash.slice(0, 14)}…</code></td>
      </tr>
    `).join('');
  } catch (e) {
    toast('Error loading events: ' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// INGESTION FORM
// ══════════════════════════════════════════════════════════════════════════

async function ingestEvent(e) {
  e.preventDefault();
  const event = {
    case_id:   document.getElementById('ev-case-id').value.trim(),
    activity:  document.getElementById('ev-activity').value.trim(),
    timestamp: document.getElementById('ev-timestamp').value,
    actor:     document.getElementById('ev-actor').value.trim(),
    cost:      parseFloat(document.getElementById('ev-cost').value) || 0,
    duration:  parseFloat(document.getElementById('ev-duration').value) || 0,
  };

  try {
    const result = await apiFetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    });
    toast(`✅ Event ingested (ID ${result.id}) — Hash: ${result.event_hash.slice(0, 12)}…`, 'success');
    clearForm();
  } catch (err) {
    toast('Ingestion failed: ' + err.message, 'error');
  }
}

function clearForm() {
  ['ev-case-id','ev-activity','ev-timestamp','ev-actor'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('ev-cost').value     = '0';
  document.getElementById('ev-duration').value = '0';
}

// ══════════════════════════════════════════════════════════════════════════
// LOAD SAMPLE DATA
// ══════════════════════════════════════════════════════════════════════════

async function loadSampleData() {
  toast('📥 Loading sample events…', 'info');
  try {
    const res = await fetch('/data/sample_events.json');
    if (!res.ok) throw new Error('Sample file not found at /data/sample_events.json');
    const events = await res.json();

    const result = await apiFetch('/api/events/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(events),
    });

    toast(`✅ Loaded ${result.ingested} events (${result.failed} skipped)`, 'success');

    // Auto-commit genesis block
    await commitBlock();

    // Refresh current view
    refreshAll();
  } catch (err) {
    toast('Sample load error: ' + err.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  // Pre-fill timestamp to now
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  const input = document.getElementById('ev-timestamp');
  if (input) input.value = now.toISOString().slice(0, 16);

  // Load overview data
  refreshAll();
});
