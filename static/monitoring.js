var latencyChart, tokenSplitChart;

function themeColors() {
    const dark = (document.documentElement.getAttribute('data-theme') || 'dark') === 'dark';
    return dark
        ? { grid: '#1e293b', text: '#94a3b8', accent: '#60a5fa', purple: '#a78bfa', red: '#f87171' }
        : { grid: '#e2e8f0', text: '#475569', accent: '#2563eb', purple: '#7c3aed', red: '#dc2626' };
}

function initMonitoringCharts() {
    const c = themeColors();

    latencyChart = new Chart(document.getElementById('latencyChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Latency (s)',
                data: [],
                backgroundColor: c.accent + '99',
                borderColor: c.accent,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: c.grid }, ticks: { color: c.text } },
                x: { grid: { display: false }, ticks: { color: c.text, maxTicksLimit: 8 } }
            }
        }
    });

    tokenSplitChart = new Chart(document.getElementById('tokenSplitChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Input Tokens', 'Output Tokens'],
            datasets: [{ data: [0, 0], backgroundColor: [c.accent, c.purple], borderWidth: 0 }]
        },
        plugins: [doughnutValueLabels, doughnutCenterTotal],
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: c.text, padding: 12 } },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const v = Number(ctx.parsed) || 0;
                            const data = ctx.dataset.data;
                            const total = data.reduce((a, b) => a + (Number(b) || 0), 0);
                            const pct = total ? ((v / total) * 100).toFixed(1) : 0;
                            return ' ' + ctx.label + ': ' + v.toLocaleString() + ' (' + pct + '%)';
                        }
                    }
                }
            }
        }
    });
}

window.onThemeChange = function (theme, colors) {
    if (latencyChart) {
        latencyChart.options.scales.y.grid.color = colors.grid;
        latencyChart.options.scales.y.ticks.color = colors.text;
        latencyChart.options.scales.x.ticks.color = colors.text;
        latencyChart.data.datasets[0].backgroundColor = colors.accent + '99';
        latencyChart.data.datasets[0].borderColor = colors.accent;
        latencyChart.update();
    }
    if (tokenSplitChart) {
        tokenSplitChart.data.datasets[0].backgroundColor = [colors.accent, colors.purple];
        tokenSplitChart.options.plugins.legend.labels.color = colors.text;
        tokenSplitChart.update();
    }
};

async function timedFetch(url) {
    const start = performance.now();
    try {
        const res = await fetch((window.API_BASE || '') + url);
        const ms = Math.round(performance.now() - start);
        return { ok: res.ok, ms, data: res.ok ? await res.json() : null };
    } catch (e) {
        return { ok: false, ms: Math.round(performance.now() - start), error: e };
    }
}

function setDot(id, up) {
    const el = document.getElementById(id);
    if (el) el.className = 'health-dot ' + (up ? 'up' : 'down');
}

function fmtNum(n) {
    n = Number(n) || 0;
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

async function refreshMonitoring() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.classList.add('loading');

    try {
        const [health, ping, metrics, inv] = await Promise.all([
            timedFetch('/health'),
            timedFetch('/ping'),
            timedFetch('/api/monitor/metrics'),
            timedFetch('/api/monitor/invocations?limit=50')
        ]);

        // Health checks
        setText('healthValue', health.ok ? 'Healthy' : 'Unhealthy');
        setText('healthLatency', health.ms + ' ms');
        setDot('healthDot', health.ok);

        const pingOk = ping.ok && ping.data && (ping.data.status === 'Healthy' || ping.data.status === 'healthy');
        setText('pingValue', pingOk ? (ping.data.status) : 'Unhealthy');
        setText('pingLatency', ping.ms + ' ms');
        setDot('pingDot', pingOk);

        if (metrics.ok && metrics.data) {
            const m = metrics.data;
            const agentOk = m.status === 'healthy';
            setText('agentValue', agentOk ? 'Connected' : 'Degraded');
            setDot('agentDot', agentOk);

            setText('kpiRequests', Number(m.total_requests).toLocaleString());
            setText('kpiTokens', fmtNum(m.total_tokens));
            setText('kpiLatency', m.avg_latency_ms + 'ms');
            setText('kpiErrors', m.error_rate + '%');
            setText('kpiSessions', m.active_sessions);
            setText('kpiUptime', m.uptime || '–');

            if (tokenSplitChart) {
                tokenSplitChart.data.datasets[0].data = [m.input_tokens || 0, m.output_tokens || 0];
                tokenSplitChart.update();
            }
        } else {
            setText('agentValue', 'Unavailable');
            setDot('agentDot', false);
        }

        if (inv.ok && inv.data) {
            const list = inv.data.invocations || [];
            renderLog(list);
            if (latencyChart) {
                latencyChart.data.labels = list.map(i => new Date(i.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
                latencyChart.data.datasets[0].data = list.map(i => i.latency || 0);
                latencyChart.update();
            }
        }
    } catch (e) {
        console.error('monitoring refresh failed', e);
    } finally {
        setText('lastUpdate', new Date().toLocaleTimeString());
        if (btn) setTimeout(() => btn.classList.remove('loading'), 600);
    }
}

function renderLog(list) {
    const table = document.getElementById('logTable');
    if (!table) return;
    if (!list.length) {
        table.innerHTML = '<tr><td colspan="5" class="empty-row">No invocations recorded yet — ask a question in Chat.</td></tr>';
        return;
    }
    table.innerHTML = list.map(item => `
        <tr>
            <td>${new Date(item.timestamp).toLocaleString()}</td>
            <td><span class="status-badge ${item.status === 'success' ? 'success' : 'error'}">${item.status}</span></td>
            <td class="query-text" title="${(item.query || '').replace(/"/g, '&quot;')}">${escapeHtml(item.query || '-')}</td>
            <td>${item.tokens || 0}</td>
            <td>${(item.latency || 0).toFixed(2)}s</td>
        </tr>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    initMonitoringCharts();
    refreshMonitoring();
    setInterval(refreshMonitoring, 30000);
});
