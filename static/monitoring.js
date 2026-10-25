if (typeof colors === 'undefined') {
    var colors = {
        bg: '#0f172a',
        text: '#f1f5f9',
        secondary: '#94a3b8',
        accent: '#60a5fa',
        purple: '#a78bfa',
        emerald: '#10b981',
        amber: '#fbbf24',
        red: '#f87171'
    };
}

function initMonitoringCharts() {
    const reqCanvas = document.getElementById('latencyChart');
    const tokensCanvas = document.getElementById('tokenSplitChart');
    const cumCanvas = document.getElementById('cumulativeTokensChart');

    if (!reqCanvas || !tokensCanvas || !cumCanvas) {
        return;
    }

    const existingReqChart = Chart.getChart(reqCanvas);
    if (existingReqChart) existingReqChart.destroy();
    const existingTokensChart = Chart.getChart(tokensCanvas);
    if (existingTokensChart) existingTokensChart.destroy();
    const existingCumChart = Chart.getChart(cumCanvas);
    if (existingCumChart) existingCumChart.destroy();

    const reqCtx = reqCanvas.getContext('2d');
    const tokensCtx = tokensCanvas.getContext('2d');
    const cumCtx = cumCanvas.getContext('2d');

    window.reqChart = new Chart(reqCtx, {
        type: 'line',
        data: {
            labels: ['-10m', '-8m', '-6m', '-4m', '-2m', 'now'],
            datasets: [{
                label: 'Latency',
                data: [0.8, 1.2, 0.9, 1.5, 1.1, 1.3],
                borderColor: '#60a5fa',
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });

    window.tokensChart = new Chart(tokensCtx, {
        type: 'bar',
        data: {
            labels: ['Input', 'Output'],
            datasets: [{
                data: [0, 0],
                backgroundColor: ['#60a5fa', '#a78bfa']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { color: '#94a3b8' } },
                x: { ticks: { color: '#94a3b8' } }
            }
        }
    });

    window.cumChart = new Chart(cumCtx, {
        type: 'line',
        data: {
            labels: ['-10m', '-8m', '-6m', '-4m', '-2m', 'now'],
            datasets: [{
                label: 'Total Tokens',
                data: [0, 0, 0, 0, 0, 0],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });
}

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

async function refreshMonitoring() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.classList.add('loading');

    try {
        const [health, ping, metrics, invs] = await Promise.all([
            timedFetch('/health'),
            timedFetch('/ping'),
            timedFetch('/api/monitor/metrics'),
            timedFetch('/api/monitor/invocations?limit=50')
        ]);

        setDot('healthDot', health.ok);
        document.getElementById('healthValue').textContent = health.ok ? 'Healthy' : 'Down';
        document.getElementById('healthLatency').textContent = health.ms + 'ms';

        setDot('pingDot', ping.ok);
        document.getElementById('pingValue').textContent = ping.ok ? 'Healthy' : 'Down';
        document.getElementById('pingLatency').textContent = ping.ms + 'ms';

        if (metrics.ok) {
            const m = metrics.data;
            setDot('agentDot', m.status === 'healthy');
            document.getElementById('agentValue').textContent = m.status === 'healthy' ? 'Healthy' : 'Degraded';
            document.getElementById('kpiRequests').textContent = Number(m.total_requests).toLocaleString();
            document.getElementById('kpiTokens').textContent = fmtNum(m.total_tokens);
            document.getElementById('kpiLatency').textContent = m.avg_latency_ms + 'ms';
            document.getElementById('kpiErrors').textContent = m.error_rate + '%';
            document.getElementById('kpiSessions').textContent = m.active_sessions;
            document.getElementById('kpiUptime').textContent = m.uptime;
            
            if (window.tokensChart) {
                window.tokensChart.data.datasets[0].data = [m.input_tokens || 0, m.output_tokens || 0];
                window.tokensChart.update();
            }

            if (window.cumChart) {
                const total = m.total_tokens || 0;
                window.cumChart.data.datasets[0].data.push(total);
                if (window.cumChart.data.datasets[0].data.length > 6) {
                    window.cumChart.data.datasets[0].data.shift();
                }
                window.cumChart.update();
            }
        }

        if (invs.ok) {
            const data = invs.data;
            const logTable = document.getElementById('logTable');
            if (logTable) {
                logTable.innerHTML = (data.invocations || []).map(item => `
                    <tr>
                        <td>${new Date(item.timestamp).toLocaleTimeString()}</td>
                        <td><span class="status-badge ${item.status === 'success' ? 'success' : 'error'}">${item.status}</span></td>
                        <td class="query-text" title="${(item.query || '').replace(/"/g, '&quot;')}">${escapeHtml(item.query || '-')}</td>
                        <td>${item.tokens || 0}</td>
                        <td>${(item.latency || 0).toFixed(1)}s</td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error('Monitoring refresh failed:', e);
    } finally {
        if (btn) setTimeout(() => btn.classList.remove('loading'), 600);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname === '/dashboard') {
        initMonitoringCharts();
    }
    refreshMonitoring();
    setInterval(refreshMonitoring, 30000);
});
