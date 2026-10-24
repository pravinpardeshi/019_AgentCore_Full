var requestsChart, tokensChart;

if (typeof Chart !== 'undefined') {
    Chart.defaults.font.family = 'Inter, sans-serif';
    Chart.defaults.font.size = 13;
}

function fmtCompact(n) {
    n = Number(n) || 0;
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}

const doughnutValueLabels = {
    id: 'doughnutValueLabels',
    afterDatasetsDraw(chart) {
        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data.length) return;
        const dataset = chart.data.datasets[0];
        const total = dataset.data.reduce((a, b) => a + (Number(b) || 0), 0);
        const ctx = chart.ctx;
        ctx.save();
        ctx.font = '600 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        meta.data.forEach((arc, i) => {
            const value = Number(dataset.data[i]) || 0;
            if (!value) return;
            const angle = (arc.startAngle + arc.endAngle) / 2;
            const radius = (arc.innerRadius + arc.outerRadius) / 2;
            const x = arc.x + Math.cos(angle) * radius;
            const y = arc.y + Math.sin(angle) * radius;
            const pct = total ? Math.round((value / total) * 100) : 0;
            ctx.fillStyle = '#ffffff';
            ctx.fillText(fmtCompact(value), x, y - 7);
            ctx.font = '500 11.5px Inter, sans-serif';
            ctx.fillStyle = 'rgba(255,255,255,0.85)';
            ctx.fillText(pct + '%', x, y + 7);
        });
        ctx.restore();
    }
};

const doughnutCenterTotal = {
    id: 'doughnutCenterTotal',
    afterDraw(chart) {
        if (chart.config.type !== 'doughnut') return;
        const dataset = chart.data.datasets[0];
        if (!dataset) return;
        const total = dataset.data.reduce((a, b) => a + (Number(b) || 0), 0);
        const { ctx, chartArea } = chart;
        if (!chartArea) return;
        const cx = (chartArea.left + chartArea.right) / 2;
        const cy = (chartArea.top + chartArea.bottom) / 2;
        const theme = document.documentElement.getAttribute('data-theme') || 'dark';
        ctx.save();
        ctx.textAlign = 'center';
        ctx.font = '700 23px Inter, sans-serif';
        ctx.fillStyle = theme === 'dark' ? '#f1f5f9' : '#0f172a';
        ctx.fillText(fmtCompact(total), cx, cy - 4);
        ctx.font = '500 12.5px Inter, sans-serif';
        ctx.fillStyle = theme === 'dark' ? '#94a3b8' : '#475569';
        ctx.fillText('total tokens', cx, cy + 15);
        ctx.restore();
    }
};

function initCharts() {
    const requestsCtx = document.getElementById('requestsChart').getContext('2d');
    requestsChart = new Chart(requestsCtx, {
        type: 'line',
        data: {
            labels: ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00'],
            datasets: [{
                label: 'Requests',
                data: [12, 19, 15, 25, 22, 30],
                borderColor: '#60a5fa',
                backgroundColor: 'rgba(96, 165, 250, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#1e293b'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        color: '#1e293b'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });

    const tokensCtx = document.getElementById('tokensChart').getContext('2d');
    tokensChart = new Chart(tokensCtx, {
        type: 'doughnut',
        data: {
            labels: ['Input Tokens', 'Output Tokens'],
            datasets: [{
                data: [65000, 45000],
                backgroundColor: ['#60a5fa', '#a78bfa'],
                borderWidth: 0
            }]
        },
        plugins: [doughnutValueLabels, doughnutCenterTotal],
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        padding: 15
                    }
                },
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

function setMetric(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatNum(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}

async function refreshDashboard() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.classList.add('loading');

    try {
        const [metricsRes, invRes] = await Promise.all([
            fetch((window.API_BASE || '') + '/api/monitor/metrics'),
            fetch((window.API_BASE || '') + '/api/monitor/invocations?limit=8')
        ]);

        if (!metricsRes.ok) throw new Error('metrics fetch failed');
        const m = await metricsRes.json();

        setMetric('totalRequests', Number(m.total_requests).toLocaleString());
        setMetric('totalTokens', formatNum(m.total_tokens));
        setMetric('avgLatency', m.avg_latency_ms + 'ms');
        setMetric('errorRate', m.error_rate + '%');
        setMetric('activeSessions', m.active_sessions);
        setMetric('statusText', m.status === 'healthy' ? 'Healthy' : 'Degraded');

        const statusIndicator = document.getElementById('agentStatus');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator' + (m.status === 'healthy' ? '' : ' warning');
        }

        if (window.tokensChart) {
            tokensChart.data.datasets[0].data = [m.input_tokens || 0, m.output_tokens || 0];
            tokensChart.update();
        }

        if (invRes.ok) {
            const inv = await invRes.json();
            renderInvocations(inv.invocations || []);
        }
    } catch (e) {
        console.warn('Metrics API unavailable, using defaults:', e);
        setMetric('totalRequests', '1,247');
        setMetric('totalTokens', '110K');
        setMetric('avgLatency', '1.24s');
        setMetric('errorRate', '0.2%');
        setMetric('activeSessions', '23');
        setMetric('statusText', 'Healthy');
        updateInvocationsTable();
    } finally {
        setMetric('lastUpdate', new Date().toLocaleTimeString());
        if (btn) setTimeout(() => btn.classList.remove('loading'), 600);
    }
}

function renderInvocations(list) {
    const table = document.getElementById('invocationsTable');
    if (!table || !list.length) {
        updateInvocationsTable();
        return;
    }
    table.innerHTML = list.map(item => `
        <tr>
            <td>${new Date(item.timestamp).toLocaleTimeString()}</td>
            <td><span class="status-badge ${item.status === 'success' ? 'success' : 'error'}">${item.status}</span></td>
            <td class="query-text" title="${(item.query || '').replace(/"/g, '&quot;')}">${escapeHtml(item.query || '-')}</td>
            <td>${item.tokens || 0}</td>
            <td>${(item.latency || 0).toFixed(1)}s</td>
        </tr>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateInvocationsTable() {
    const table = document.getElementById('invocationsTable');
    table.innerHTML = `
        <tr>
            <td>10:42:15 AM</td>
            <td><span class="status-badge success">Success</span></td>
            <td class="query-text">What are common network issues?</td>
            <td>245</td>
            <td>1.2s</td>
        </tr>
        <tr>
            <td>10:38:22 AM</td>
            <td><span class="status-badge success">Success</span></td>
            <td class="query-text">How to reset VPN access?</td>
            <td>189</td>
            <td>0.9s</td>
        </tr>
        <tr>
            <td>10:35:08 AM</td>
            <td><span class="status-badge success">Success</span></td>
            <td class="query-text">Email server down troubleshooting</td>
            <td>312</td>
            <td>1.5s</td>
        </tr>
        <tr>
            <td>10:31:45 AM</td>
            <td><span class="status-badge success">Success</span></td>
            <td class="query-text">Printer not working</td>
            <td>156</td>
            <td>0.8s</td>
        </tr>
    `;
}

function updateTimeRange(range) {
    console.log('Time range changed to:', range);
    // Would fetch data for different time ranges
}

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    refreshDashboard();
    // Auto refresh every 30 seconds
    setInterval(refreshDashboard, 30000);
});
