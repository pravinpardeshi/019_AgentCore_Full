const VIEW_META = {
    dashboard:  { title: 'Dashboard',          crumb: 'Home / Overview', display: 'block' },
    chat:       { title: 'Incidents Assistant', crumb: 'Home / Chat',     display: 'flex'  },
    monitoring: { title: 'Monitoring',         crumb: 'Home / Monitoring', display: 'block' },
};

let currentView = 'dashboard';

function switchView(name) {
    if (!VIEW_META[name] || name === currentView) return;
    currentView = name;

    // Show/hide view sections
    document.querySelectorAll('.view').forEach(el => (el.style.display = 'none'));
    const target = document.getElementById('view-' + name);
    if (target) target.style.display = VIEW_META[name].display;

    // Active nav item
    document.querySelectorAll('.sidenav-item[data-view]').forEach(a => {
        a.classList.toggle('active', a.dataset.view === name);
    });

    // Topbar
    document.getElementById('pageTitle').textContent = VIEW_META[name].title;
    document.getElementById('pageCrumb').textContent = VIEW_META[name].crumb;

    const isChat = name === 'chat';
    document.getElementById('newChatBtn').style.display = isChat ? 'flex' : 'none';
    document.getElementById('refreshBtn').style.display = isChat ? 'none' : 'flex';
    document.getElementById('lastUpdateWrap').style.display = isChat ? 'none' : 'inline';

    // Resize charts that were initialized while hidden
    if (name === 'dashboard') {
        if (window.requestsChart) requestsChart.resize();
        if (window.tokensChart) tokensChart.resize();
        if (typeof refreshDashboard === 'function') refreshDashboard();
    } else if (name === 'monitoring') {
        if (window.latencyChart) latencyChart.resize();
        if (window.tokenSplitChart) tokenSplitChart.resize();
        if (typeof refreshMonitoring === 'function') refreshMonitoring();
    }
}

function refreshCurrentView() {
    if (currentView === 'dashboard' && typeof refreshDashboard === 'function') refreshDashboard();
    else if (currentView === 'monitoring' && typeof refreshMonitoring === 'function') refreshMonitoring();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sidenav-item[data-view]').forEach(a => {
        a.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(a.dataset.view);
        });
    });

    // Deep links (#chat) still work without changing the path
    const hash = (location.hash || '').replace('#', '');
    if (VIEW_META[hash]) switchView(hash);
});
