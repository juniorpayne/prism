/**
 * Dashboard for Prism DNS Web Interface
 * Handles statistics, charts, and real-time updates
 */

class Dashboard {
    constructor() {
        this.stats = {};
        this.chart = null;
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.refreshIntervalMs = 15000; // 15 seconds
        
        this.initializeElements();
        this.initializeChart();
    }

    initializeElements() {
        this.elements = {
            // Stats cards
            totalHosts: document.getElementById('total-hosts'),
            onlineHosts: document.getElementById('online-hosts'),
            offlineHosts: document.getElementById('offline-hosts'),
            serverUptime: document.getElementById('server-uptime'),
            
            // Chart
            statusChart: document.getElementById('status-chart'),
            
            // Recent activity
            recentActivity: document.getElementById('recent-activity')
        };
    }

    initializeChart() {
        if (!this.elements.statusChart) return;
        
        const ctx = this.elements.statusChart.getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: [
                        '#198754', // Bootstrap success green
                        '#dc3545'  // Bootstrap danger red
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }

    async loadDashboard() {
        try {
            // Load stats and health data in parallel with fallbacks
            const [statsResult, healthResult] = await Promise.allSettled([
                this.loadStats(),
                this.loadHealth()
            ]);
            
            // Handle stats
            if (statsResult.status === 'fulfilled') {
                this.updateStatsCards(statsResult.value);
                this.updateChart(statsResult.value);
            } else {
                console.error('Failed to load stats:', statsResult.reason);
                this.updateStatsCards({ total_hosts: 0, online_hosts: 0, offline_hosts: 0 });
            }
            
            // Handle health
            if (healthResult.status === 'fulfilled') {
                this.updateServerStatus(healthResult.value);
            } else {
                console.error('Failed to load health:', healthResult.reason);
                this.updateServerStatus({ status: 'unknown', uptime_seconds: 0 });
            }
            
            // Load recent activity (non-blocking)
            this.loadRecentActivity().catch(error => {
                console.error('Failed to load recent activity:', error);
            });
            
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.showDashboardError(error.getUserMessage ? error.getUserMessage() : error.message);
        }
    }

    async loadStats() {
        try {
            const stats = await api.getStats();
            this.stats = stats;
            return stats;
        } catch (error) {
            console.error('Failed to load stats:', error);
            throw error;
        }
    }

    async loadHealth() {
        try {
            return await api.getHealth();
        } catch (error) {
            console.error('Failed to load health:', error);
            // Don't throw, health is not critical for dashboard
            return { status: 'unknown', uptime_seconds: 0 };
        }
    }

    updateStatsCards(stats) {
        // Handle both stats formats: direct stats or nested host_statistics
        const hostStats = stats.host_statistics || stats;
        const totalHosts = hostStats.total_hosts || 0;
        const onlineHosts = hostStats.online_hosts || 0;
        const offlineHosts = hostStats.offline_hosts || 0;
        
        // Animate counter updates
        this.animateCounter(this.elements.totalHosts, totalHosts);
        this.animateCounter(this.elements.onlineHosts, onlineHosts);
        this.animateCounter(this.elements.offlineHosts, offlineHosts);
    }

    updateChart(stats) {
        if (!this.chart) return;
        
        // Handle both stats formats: direct stats or nested host_statistics
        const hostStats = stats.host_statistics || stats;
        const onlineHosts = hostStats.online_hosts || 0;
        const offlineHosts = hostStats.offline_hosts || 0;
        
        this.chart.data.datasets[0].data = [onlineHosts, offlineHosts];
        this.chart.update('none'); // No animation for frequent updates
    }

    updateServerStatus(health) {
        if (this.elements.serverUptime && health.uptime_seconds !== undefined) {
            this.elements.serverUptime.textContent = formatUptime(health.uptime_seconds);
        }
    }

    async loadRecentActivity() {
        if (!this.elements.recentActivity) return;
        
        try {
            // Get recent hosts (those seen in last hour)
            const hosts = await api.getHosts();
            const recentHosts = hosts.hosts || hosts || [];
            
            // Sort by last_seen descending
            recentHosts.sort((a, b) => new Date(b.last_seen) - new Date(a.last_seen));
            
            // Take first 5 for recent activity
            const recentActivity = recentHosts.slice(0, 5);
            
            this.renderRecentActivity(recentActivity);
            
        } catch (error) {
            console.error('Failed to load recent activity:', error);
            this.elements.recentActivity.innerHTML = `
                <div class="text-center text-muted">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p class="mb-0">Failed to load recent activity</p>
                </div>
            `;
        }
    }

    renderRecentActivity(activities) {
        if (!this.elements.recentActivity) return;
        
        if (activities.length === 0) {
            this.elements.recentActivity.innerHTML = `
                <div class="text-center text-muted">
                    <i class="bi bi-clock"></i>
                    <p class="mb-0">No recent activity</p>
                </div>
            `;
            return;
        }
        
        const activityItems = activities.map(host => {
            const timeSinceLastSeen = new Date() - new Date(host.last_seen);
            const isRecent = timeSinceLastSeen < 300000; // 5 minutes
            
            return `
                <div class="d-flex align-items-center mb-3">
                    <div class="flex-shrink-0 me-3">
                        ${getStatusIcon(host.status)}
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${escapeHtml(host.hostname)}</div>
                        <div class="text-muted small">
                            ${escapeHtml(host.current_ip)} • ${formatTimestamp(host.last_seen)}
                            ${isRecent ? '<span class="text-success ms-1">• Active</span>' : ''}
                        </div>
                    </div>
                    <div class="flex-shrink-0">
                        <button class="btn btn-sm btn-outline-primary" onclick="app.showHost('${escapeHtml(host.hostname)}')" title="View Details">
                            <i class="bi bi-eye"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        this.elements.recentActivity.innerHTML = activityItems;
    }

    animateCounter(element, targetValue) {
        if (!element) return;
        
        const startValue = parseInt(element.textContent) || 0;
        const duration = 1000; // 1 second
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Ease out cubic
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            
            const currentValue = Math.floor(startValue + (targetValue - startValue) * easeProgress);
            element.textContent = currentValue.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.textContent = targetValue.toLocaleString();
            }
        };
        
        requestAnimationFrame(animate);
    }

    showDashboardError(message) {
        // Show error in all stat cards
        const errorContent = `<span class="text-danger">Error</span>`;
        
        if (this.elements.totalHosts) this.elements.totalHosts.innerHTML = errorContent;
        if (this.elements.onlineHosts) this.elements.onlineHosts.innerHTML = errorContent;
        if (this.elements.offlineHosts) this.elements.offlineHosts.innerHTML = errorContent;
        if (this.elements.serverUptime) this.elements.serverUptime.innerHTML = errorContent;
        
        // Show error in recent activity
        if (this.elements.recentActivity) {
            this.elements.recentActivity.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <strong>Dashboard Error:</strong> ${escapeHtml(message)}
                </div>
            `;
        }
        
        // Update chart with error state
        if (this.chart) {
            this.chart.data.datasets[0].data = [0, 0];
            this.chart.update();
        }
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.autoRefreshEnabled) {
            this.refreshInterval = setInterval(() => {
                this.loadDashboard();
            }, this.refreshIntervalMs);
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    setAutoRefresh(enabled) {
        this.autoRefreshEnabled = enabled;
        if (enabled) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    getStats() {
        return this.stats;
    }

    destroy() {
        this.stopAutoRefresh();
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
}

// Global dashboard instance available as window.dashboard