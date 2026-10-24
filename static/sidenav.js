function toggleSidenav() {
    const sidenav = document.getElementById('sidenav');
    sidenav.classList.toggle('collapsed');
    localStorage.setItem('sidenav_collapsed', sidenav.classList.contains('collapsed'));
}

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateChartColors();
}

function updateChartColors() {
    const theme = document.documentElement.getAttribute('data-theme');
    const grid = theme === 'dark' ? '#1e293b' : '#e2e8f0';
    const text = theme === 'dark' ? '#94a3b8' : '#475569';
    const accent = theme === 'dark' ? '#60a5fa' : '#2563eb';
    const purple = theme === 'dark' ? '#a78bfa' : '#7c3aed';

    if (window.requestsChart) {
        requestsChart.options.scales.y.grid.color = grid;
        requestsChart.options.scales.x.grid.color = grid;
        requestsChart.options.scales.y.ticks.color = text;
        requestsChart.options.scales.x.ticks.color = text;
        requestsChart.data.datasets[0].borderColor = accent;
        requestsChart.data.datasets[0].backgroundColor = theme === 'dark'
            ? 'rgba(96,165,250,0.1)' : 'rgba(37,99,235,0.1)';
        requestsChart.update();
    }
    if (window.tokensChart) {
        tokensChart.data.datasets[0].backgroundColor = [accent, purple];
        tokensChart.options.plugins.legend.labels.color = text;
        tokensChart.update();
    }
    if (typeof window.onThemeChange === 'function') {
        window.onThemeChange(theme, { grid, text, accent, purple });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    const collapsed = localStorage.getItem('sidenav_collapsed') === 'true';
    if (collapsed) {
        document.getElementById('sidenav').classList.add('collapsed');
    }

    updateChartColors();
});
