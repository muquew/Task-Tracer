(() => {
    'use strict';

    const namespace = window.TaskTracer || (window.TaskTracer = {});

    namespace.createReviewView = function createReviewView(options) {
        const { document, translate, translateCount, createIcon, projectLabel, formatDateKey } = options;
        for (const [name, value] of Object.entries({ translate, translateCount, createIcon, projectLabel, formatDateKey })) {
            if (typeof value !== 'function') throw new TypeError(`Review view requires ${name}`);
        }
        if (!document || typeof document.createElement !== 'function') throw new TypeError('Review view requires a document');

        function render(stats, { inventoryOpen = true } = {}) {
            const view = document.createElement('section');
            view.className = 'stats-view';
            view.setAttribute('aria-label', translate('stats.title'));
            view.append(createStatsReview(stats));
            const projects = createStatsProjects(stats);
            if (projects) view.appendChild(projects);
            view.append(createStatsWorkload(stats), createStatsInventory(stats, inventoryOpen));
            return view;
        }

        function createStatsHeading(key) {
            const heading = document.createElement('h2');
            heading.className = 'stats-section-heading';
            heading.textContent = translate(key);
            return heading;
        }
        function createStatsWorkload(stats) {
            const section = document.createElement('section');
            section.className = 'stats-workload';
            const grid = document.createElement('div');
            grid.className = 'stats-action-grid';
            grid.append(
                createStatsActionCard('overdue', stats.overdue, 'statsInsights.overdueTitle'),
                createStatsActionCard('today', stats.dueToday, 'statsInsights.todayTitle'),
                createStatsActionCard('undated', stats.undated, 'statsInsights.undatedTitle')
            );
            section.append(createStatsHeading('statsInsights.workloadTitle'), grid);
            if (stats.pending === 0) {
                const empty = document.createElement('p');
                empty.className = 'stats-workload-empty';
                empty.textContent = translate(stats.recordCount === 0 ? 'statsInsights.emptyWorkspace' : 'statsInsights.clearWorkload');
                section.appendChild(empty);
            }
            return section;
        }
        function createStatsActionCard(action, count, labelKey) {
            const card = document.createElement('button');
            card.type = 'button';
            card.className = `stats-action-card ${action}`;
            card.dataset.statsAction = action;
            card.disabled = count === 0;
            const label = document.createElement('span');
            label.className = 'stats-action-label';
            label.textContent = translate(labelKey);
            const value = document.createElement('strong');
            value.className = 'stats-action-value';
            value.textContent = String(count);
            card.append(label, value);
            if (count) {
                card.title = translate('stats.openFilter').replace('{label}', label.textContent).replace('{count}', count);
                card.appendChild(createIcon('icon-chevron-right', 'icon icon-sm stats-action-arrow'));
            }
            return card;
        }
        function createStatsReview(stats) {
            const section = document.createElement('section');
            section.className = 'stats-review';
            const header = document.createElement('div');
            header.className = 'stats-review-header';
            const heading = createStatsHeading('statsInsights.reviewTitle');
            heading.classList.add('stats-trend-title');
            const total = document.createElement('button');
            total.type = 'button';
            total.className = 'stats-review-total';
            total.dataset.statsAction = 'review-week';
            total.disabled = stats.completedWeek === 0;
            total.textContent = translateCount('statsInsights.reviewCompleted', stats.completedWeek).replace('{count}', stats.completedWeek);
            total.setAttribute('aria-label', `${total.textContent} · ${translate('statsInsights.openReviewWeek').replace('{count}', stats.completedWeek)}`);
            if (stats.completedWeek) total.append(createIcon('icon-chevron-right', 'icon icon-sm'));
            header.append(heading, total);
            const range = document.createElement('p');
            range.className = 'stats-review-range';
            range.textContent = `${formatDateKey(stats.completionTrend[0].key)} – ${formatDateKey(stats.completionTrend[6].key)}`;
            const meta = document.createElement('p');
            meta.className = 'stats-review-meta';
            meta.textContent = translateCount('stats.streakDetail', stats.streakDays).replace('{count}', stats.streakDays);
            meta.hidden = stats.completedWeek === 0;
            section.append(header, range, createStatsTrend(stats.completionTrend), meta);
            return section;
        }
        function createStatsProjects(stats) {
            if (!stats.projectRows.length) return null;
            const section = document.createElement('section');
            section.className = 'stats-projects';
            section.appendChild(createStatsHeading('statsInsights.projectsTitle'));
            stats.projectRows.slice(0, 6).forEach(project => {
                const row = document.createElement('button');
                row.type = 'button';
                row.className = 'stats-project-row';
                row.dataset.statsAction = 'project';
                row.dataset.statsProject = JSON.stringify(project.scope);
                const name = document.createElement('span');
                name.className = 'stats-project-name';
                name.textContent = projectLabel(project.scope);
                const pending = document.createElement('strong');
                pending.className = 'stats-project-pending';
                pending.textContent = translateCount('statsInsights.projectPending', project.pending).replace('{count}', project.pending);
                const overdue = document.createElement('span');
                overdue.className = 'stats-project-overdue';
                overdue.textContent = project.overdue ? translateCount('statsInsights.projectOverdue', project.overdue).replace('{count}', project.overdue) : '';
                overdue.hidden = project.overdue === 0;
                const bar = document.createElement('span');
                bar.className = 'stats-project-bar';
                bar.setAttribute('aria-hidden', 'true');
                bar.style.setProperty('--project-share', `${Math.round(project.pending / stats.pending * 100)}%`);
                row.append(name, pending, overdue, bar);
                section.appendChild(row);
            });
            if (stats.projectRows.length > 6) {
                const remaining = stats.projectRows.length - 6;
                const more = document.createElement('button');
                more.type = 'button';
                more.className = 'stats-project-remainder';
                more.dataset.statsAction = 'pending';
                more.textContent = translateCount('statsInsights.moreProjects', remaining).replace('{count}', remaining);
                section.appendChild(more);
            }
            return section;
        }
        function createStatsInventory(stats, open) {
            const details = document.createElement('details');
            details.className = 'stats-inventory';
            details.open = open;
            const summary = document.createElement('summary');
            summary.textContent = translate('statsInsights.inventoryTitle');
            const layout = document.createElement('div');
            layout.className = 'stats-inventory-layout';
            const breakdown = document.createElement('div');
            breakdown.className = 'stats-inventory-breakdown';
            breakdown.append(
                createStatsDetailGrid(stats),
                createStatCard('stats.overdueRate', stats.deadlineTasks ? formatPercent(stats.overdueRate) : '—', stats.overdueDetail, stats.deadlineTasks ? stats.overdueRate : null, 'warning')
            );
            layout.append(
                createStatCard('stats.completionRate', stats.total ? formatPercent(stats.completionRate) : '—', stats.completedDetail, stats.total ? stats.completionRate : null, 'success'),
                breakdown
            );
            details.append(summary, layout);
            return details;
        }

        function createStatCard(labelKey, value, detail, ratio, tone) {
            const card = document.createElement('article');
            const completion = tone === 'success';
            card.className = `stat-card ${tone} ${completion ? 'stats-completion-summary' : 'stats-overdue-summary'}`;
            const labelText = translate(labelKey);
            const label = document.createElement('div');
            label.className = 'stat-label';
            label.textContent = labelText;
            const valueEl = document.createElement('div');
            valueEl.className = 'stat-value';
            valueEl.textContent = value;
            const detailEl = document.createElement('div');
            detailEl.className = 'stat-detail';
            detailEl.textContent = detail;
            if (completion) {
                const ring = document.createElement('div');
                ring.className = 'stats-completion-ring';
                ring.style.setProperty('--progress', `${ratio === null ? 0 : Math.round(ratio * 100)}%`);
                ring.setAttribute('role', 'img');
                ring.setAttribute('aria-label', `${labelText}: ${value}`);
                label.setAttribute('aria-hidden', 'true');
                ring.appendChild(valueEl);
                card.append(label, ring, detailEl);
                return card;
            }
            card.append(label, valueEl, detailEl);
            if (ratio !== null) {
                const bar = document.createElement('div');
                bar.className = 'stat-bar';
                bar.setAttribute('role', 'meter');
                bar.setAttribute('aria-label', `${labelText}: ${value}`);
                bar.setAttribute('aria-valuemin', '0');
                bar.setAttribute('aria-valuemax', '100');
                bar.setAttribute('aria-valuenow', String(Math.round(ratio * 100)));
                const fill = document.createElement('div');
                fill.className = 'stat-fill';
                fill.style.setProperty('--stat-value', `${Math.round(ratio * 100)}%`);
                bar.appendChild(fill);
                card.appendChild(bar);
            }
            return card;
        }

        function createStatsDetailGrid(stats) {
            const grid = document.createElement('div');
            grid.className = 'stats-detail-grid stats-inventory-rows';
            [
                ['statsInsights.inventoryTotal', stats.total, 'all'],
                ['statsInsights.inventoryCompleted', stats.completed, 'completed'],
                ['stats.overdueTasks', stats.overdue, 'overdue'],
                ['stats.archivedTasks', stats.archived, 'archived']
            ].forEach(([key, value, filter]) => grid.appendChild(createStatsMini(key, value, filter)));
            return grid;
        }
        function createStatsMini(labelKey, value, filter) {
            const labelText = translate(labelKey);
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'stats-mini';
            item.dataset.statsFilter = filter;
            item.dataset.statsAction = `inventory-${filter}`;
            item.disabled = value === 0;
            item.title = translate('stats.openFilter').replace('{label}', labelText).replace('{count}', value);
            const strong = document.createElement('strong');
            strong.textContent = String(value);
            const label = document.createElement('span');
            label.textContent = labelText;
            item.append(label, strong, createIcon('icon-list', 'icon icon-sm stats-mini-action'));
            return item;
        }
        function createStatsTrend(trend) {
            const section = document.createElement('div');
            section.className = 'stats-trend';
            if (!trend.some(day => day.count > 0)) {
                const empty = document.createElement('p');
                empty.className = 'stats-trend-empty';
                empty.textContent = translate('usability.statsEmpty');
                section.appendChild(empty);
                return section;
            }
            const bars = document.createElement('div');
            bars.className = 'stats-trend-bars';
            const maxCount = Math.max(1, ...trend.map(day => day.count));
            trend.forEach(day => bars.appendChild(createStatsTrendItem(day, maxCount)));
            section.appendChild(bars);
            return section;
        }
        function createStatsTrendItem(day, maxCount) {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = `stats-trend-item${day.count === 0 ? ' is-zero' : ''}`;
            item.dataset.statsAction = 'review-day';
            item.dataset.statsDate = day.key;
            item.disabled = day.count === 0;
            const labelText = translate('statsInsights.openReviewDay').replace('{date}', day.fullLabel).replace('{count}', day.count);
            item.setAttribute('aria-label', `${day.label} · ${labelText}`);
            item.title = labelText;
            const count = document.createElement('strong');
            count.className = 'stats-trend-count';
            count.textContent = String(day.count);
            count.setAttribute('aria-hidden', 'true');
            const track = document.createElement('span');
            track.className = 'stats-trend-track';
            const bar = document.createElement('span');
            bar.className = 'stats-trend-bar';
            bar.dataset.trendCount = String(day.count);
            bar.style.setProperty('--trend-value', `${Math.round(day.count / maxCount * 100)}%`);
            bar.setAttribute('aria-hidden', 'true');
            track.appendChild(bar);
            const label = document.createElement('span');
            label.className = 'stats-trend-label';
            label.textContent = day.label;
            label.title = day.fullLabel;
            item.append(count, track, label);
            return item;
        }
        function formatPercent(value) {
            return `${Math.round(value * 100)}%`;
        }

        return Object.freeze({ render });
    };
})();
