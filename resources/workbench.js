/* Task Tracer workbench: read-only projections with actions delegated to the task engine. */
(() => {
    'use strict';

    const SVG_NS = 'http://www.w3.org/2000/svg';
    const ICONS = {
        check: ['M5 12l4 4L19 6'],
        plus: ['M12 5v14', 'M5 12h14'],
        minus: ['M5 12h14'],
        arrow: ['M5 12h14', 'M13 6l6 6-6 6'],
        calendar: ['M8 3v4m8-4v4', 'M4 10h16', 'M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1z'],
        folder: ['M3 7h6l2 2h10v10H3z', 'M3 7V5h6l2 2h8v2']
    };

    function node(tag, className, content) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (content !== undefined) element.textContent = String(content);
        return element;
    }

    function icon(name) {
        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('class', 'icon');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '1.8');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        for (const value of ICONS[name] || ICONS.arrow) {
            const path = document.createElementNS(SVG_NS, 'path');
            path.setAttribute('d', value);
            svg.append(path);
        }
        return svg;
    }

    function button(className, action, content) {
        const element = node('button', className, content);
        element.type = 'button';
        element.dataset.workbenchAction = action;
        return element;
    }

    function reconcile(container, desired) {
        const keep = new Set(desired);
        let cursor = container.firstChild;
        for (const element of desired) {
            if (element === cursor) cursor = cursor.nextSibling;
            else container.insertBefore(element, cursor);
        }
        for (const element of [...container.childNodes]) {
            if (!keep.has(element)) element.remove();
        }
    }

    window.createTaskTracerWorkbench = function createTaskTracerWorkbench(api) {
        const todayMount = document.getElementById('todayWorkspace');
        const projectsMount = document.getElementById('projectsWorkspace');
        if (!todayMount || !projectsMount) throw new Error('Workbench mounts are required');

        let latest = null;
        let projectGroups = [];
        let projectQuery = '';
        let projectSort = 'pending';
        let projectLimit = 24;
        let pendingLimit = 50;
        let completedLimit = 10;
        let candidateLimit = 8;
        let sequence = 0;
        let focusVisibilityFrame = 0;
        let currentDay = '';
        let collator = null;
        let collatorLanguage = '';
        const rows = new Map();
        const cards = new Map();
        const taskByKey = new Map();
        const projectByKey = new Map();
        const busy = new Set();

        const text = (key, parameters = {}) => {
            let value = String(api.t(key) || '');
            for (const [name, replacement] of Object.entries(parameters)) {
                value = value.replaceAll(`{${name}}`, () => String(replacement));
            }
            return value;
        };
        const countText = (key, count) => text(count === 1 && latest?.language === 'en' ? `${key}One` : key, { count });
        const projectName = task => typeof task.project === 'string' ? task.project.trim().replace(/\s+/g, ' ') : '';
        const taskName = task => typeof task.name === 'string' ? task.name : '';
        const taskKey = task => String(task.id);
        const safeTasks = () => Array.isArray(latest?.tasks) ? latest.tasks.filter(task => task && typeof task === 'object' && task.id !== undefined) : [];
        const isAvailable = () => latest?.storageAvailable !== false;
        const isPlanned = task => !task.archived && task.focusDate === latest.today;
        const orderOf = task => Number.isFinite(Number(task.order)) ? Number(task.order) : 0;
        const compareTaskOrder = (a, b) => orderOf(a) - orderOf(b) || collator.compare(taskKey(a), taskKey(b));
        const deadlineOrder = task => {
            const instant = task.dueAt || task.dueDate;
            const parsed = typeof instant === 'string' && instant ? Date.parse(instant) : NaN;
            if (Number.isFinite(parsed)) return parsed;
            const key = api.dueKey(task);
            return key ? Date.parse(`${key}T23:59:00Z`) : Infinity;
        };

        function header(mount, id) {
            mount.classList.add('workbench-page');
            const element = node('header', 'workbench-page-header workbench-header');
            const copy = node('div', 'workbench-heading-copy');
            const heading = node('h1', '', text(id === 'todayTitle' ? 'v5.today.title' : 'v5.projects.title'));
            heading.id = id;
            heading.tabIndex = -1;
            const subtitle = node('p', 'workbench-page-subtitle');
            copy.append(heading, subtitle);
            element.append(copy);
            const feedback = node('p', 'workbench-feedback');
            feedback.hidden = true;
            feedback.setAttribute('role', 'alert');
            mount.append(element, feedback);
            mount.setAttribute('aria-labelledby', id);
            return { element, heading, subtitle, feedback };
        }

        function section(titleId, className) {
            const element = node('section', `workbench-surface ${className}`);
            element.setAttribute('aria-labelledby', titleId);
            const headingRow = node('div', 'workbench-section-heading');
            const heading = node('h2');
            heading.id = titleId;
            heading.tabIndex = -1;
            const count = node('span', 'workbench-count');
            headingRow.append(heading, count);
            element.append(headingRow);
            return { element, heading, count };
        }

        function emptyState(symbol) {
            const element = node('div', 'workbench-empty');
            const heading = node('p', 'workbench-empty-title');
            const action = button('workbench-link', 'open-tasks');
            element.append(icon(symbol), heading, action);
            return { element, heading, action };
        }

        const todayHeader = header(todayMount, 'todayTitle');
        const todayLayout = node('div', 'today-layout');
        const plan = section('workbench-plan-heading', 'today-plan');
        const progress = node('div', 'workbench-progress');
        const progressLabel = node('p', 'workbench-progress-label');
        const progressBar = node('progress', 'workbench-progress-bar');
        progress.append(progressLabel, progressBar);
        const pendingList = node('div', 'workbench-task-list');
        const planEmpty = emptyState('check');
        const pendingMore = button('workbench-more', 'more-pending');
        const completedHeading = node('h3', 'workbench-completed-heading');
        const completedList = node('div', 'workbench-task-list workbench-completed-list');
        const completedMore = button('workbench-more', 'more-completed');
        plan.element.append(progress, planEmpty.element, pendingList, pendingMore, completedHeading, completedList, completedMore);
        const candidates = section('workbench-candidates-heading', 'today-candidates');
        const candidateList = node('div', 'workbench-task-list');
        const candidateEmpty = emptyState('calendar');
        candidateEmpty.action.hidden = true;
        const candidateMore = button('workbench-more', 'more-candidates');
        candidates.element.append(candidateEmpty.element, candidateList, candidateMore);
        todayLayout.append(plan.element, candidates.element);
        todayMount.append(todayLayout);

        const projectsHeader = header(projectsMount, 'projectsTitle');
        const tools = node('div', 'workbench-project-tools');
        const searchField = node('div', 'workbench-search-field');
        const projectSearch = node('input', 'workbench-project-search');
        projectSearch.type = 'search';
        projectSearch.id = 'workbench-project-search';
        projectSearch.autocomplete = 'off';
        searchField.append(projectSearch);
        const sortField = node('label', 'workbench-sort-field');
        const sortLabel = node('span');
        const sort = node('select', 'workbench-project-sort');
        sort.id = 'workbench-project-sort';
        sort.setAttribute('data-native-select', '');
        const sortOptions = new Map();
        for (const value of ['pending', 'name', 'due']) {
            const option = node('option');
            option.value = value;
            sortOptions.set(value, option);
            sort.append(option);
        }
        sortField.append(sortLabel, sort);
        tools.append(searchField, sortField);
        const projectGrid = node('div', 'project-grid');
        const projectsEmpty = emptyState('folder');
        const projectsMore = button('workbench-more', 'more-projects');
        projectsMount.append(tools, projectsEmpty.element, projectGrid, projectsMore);

        function newRow(key, candidate) {
            const element = node('article', `workbench-task${candidate ? ' is-candidate' : ''}`);
            element.dataset.workbenchTask = key;
            const toggle = candidate ? null : button('workbench-task-toggle', 'toggle');
            if (toggle) toggle.append(icon('check'));
            const copy = node('div', 'workbench-task-copy');
            const name = button('workbench-task-name', 'edit');
            const meta = node('div', 'workbench-task-meta');
            meta.id = `workbench-task-meta-${++sequence}`;
            const project = node('span', 'workbench-task-project');
            const due = node('span', 'workbench-task-due');
            meta.append(project, due);
            copy.append(name, meta);
            const planAction = button(candidate ? 'workbench-plan-add' : 'workbench-task-plan', 'plan');
            if (!candidate) planAction.append(icon('minus'));
            for (const control of [toggle, name, planAction].filter(Boolean)) {
                control.dataset.workbenchTaskKey = key;
                control.setAttribute('aria-describedby', meta.id);
            }
            if (toggle) element.append(toggle);
            element.append(copy, planAction);
            return { element, toggle, name, meta, project, due, planAction };
        }

        function renderRow(task, candidate = false) {
            const key = taskKey(task);
            const cacheKey = `${candidate ? 'candidate' : 'plan'}:${key}`;
            let row = rows.get(cacheKey);
            if (!row) { row = newRow(key, candidate); rows.set(cacheKey, row); }
            const disabled = !isAvailable();
            const name = taskName(task);
            row.element.classList.toggle('is-completed', Boolean(task.completed));
            row.element.classList.toggle('is-overdue', !task.completed && api.isOverdue(task));
            row.name.textContent = name;
            row.project.textContent = projectName(task) || text('v5.projects.unassigned');
            const due = api.formatDue(task);
            row.due.textContent = due;
            row.due.hidden = !due;
            if (due && typeof api.groupDue === 'function') api.groupDue(row.due, task);
            for (const control of [row.toggle, row.name, row.planAction].filter(Boolean)) {
                control.disabled = disabled;
                control.setAttribute('aria-disabled', String(disabled || busy.has(key)));
                control.setAttribute('aria-busy', String(busy.has(key)));
            }
            if (row.toggle) {
                row.toggle.setAttribute('aria-pressed', String(Boolean(task.completed)));
                const label = text(task.completed ? 'v5.today.reopenTask' : 'v5.today.completeTask', { name });
                row.toggle.setAttribute('aria-label', label);
                row.toggle.title = label;
            }
            const visiblePlanAction = text('v5.today.addToPlan');
            const planLabel = candidate ? `${visiblePlanAction}: ${name}` : text('v5.today.removeTaskFromPlan', { name });
            row.planAction.setAttribute('aria-label', planLabel);
            row.planAction.title = planLabel;
            if (candidate) row.planAction.textContent = visiblePlanAction;
            return row.element;
        }

        function setMore(control, visible, total, step) {
            control.hidden = total <= visible;
            control.textContent = text('v5.common.showMore', { count: Math.min(step, Math.max(0, total - visible)) });
        }

        function renderToday(tasks) {
            todayHeader.heading.textContent = text('v5.today.title');
            const day = new Date(`${latest.today}T12:00:00Z`);
            todayHeader.subtitle.textContent = Number.isFinite(day.getTime()) ? new Intl.DateTimeFormat(latest.language, {
                weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC'
            }).format(day) : '';
            const planned = tasks.filter(isPlanned);
            const pending = planned.filter(task => !task.completed).sort(compareTaskOrder);
            const completed = planned.filter(task => task.completed).sort((a, b) => {
                const left = Date.parse(a.completedAt || '') || 0;
                const right = Date.parse(b.completedAt || '') || 0;
                return right - left || compareTaskOrder(a, b);
            });
            const urgent = tasks.filter(task => !task.completed && !task.archived && !isPlanned(task)
                && (api.isOverdue(task) || api.dueKey(task) === latest.today));
            urgent.sort((a, b) => Number(api.isOverdue(b)) - Number(api.isOverdue(a))
                || deadlineOrder(a) - deadlineOrder(b) || compareTaskOrder(a, b));

            plan.heading.textContent = text('v5.today.plan');
            plan.count.textContent = countText('v5.today.pendingCount', pending.length);
            progress.hidden = planned.length === 0;
            const progressText = text('v5.today.progress', { completed: completed.length, total: planned.length });
            progressLabel.textContent = progressText;
            progressBar.max = Math.max(1, planned.length);
            progressBar.value = completed.length;
            progressBar.setAttribute('aria-label', progressText);
            planEmpty.element.hidden = pending.length !== 0;
            planEmpty.heading.textContent = text(!isAvailable() ? 'v5.common.storageUnavailable'
                : completed.length ? 'v5.today.planDone' : 'v5.today.planEmpty');
            planEmpty.action.textContent = text('v5.today.chooseTasks');
            planEmpty.action.hidden = !isAvailable() || planned.length > 0 || !tasks.some(task => !task.completed && !task.archived);
            reconcile(pendingList, pending.slice(0, pendingLimit).map(task => renderRow(task)));
            setMore(pendingMore, pendingLimit, pending.length, 50);
            completedHeading.hidden = completed.length === 0;
            completedHeading.textContent = text('v5.today.completedHeading', { count: completed.length });
            reconcile(completedList, completed.slice(0, completedLimit).map(task => renderRow(task)));
            setMore(completedMore, completedLimit, completed.length, 10);

            candidates.heading.textContent = text('v5.today.candidates');
            candidates.element.hidden = !isAvailable() && urgent.length === 0;
            candidates.count.textContent = countText('v5.common.taskCount', urgent.length);
            candidateEmpty.element.hidden = urgent.length !== 0;
            candidateEmpty.heading.textContent = text(isAvailable() ? 'v5.today.candidatesEmpty' : 'v5.common.storageUnavailable');
            reconcile(candidateList, urgent.slice(0, candidateLimit).map(task => renderRow(task, true)));
            setMore(candidateMore, candidateLimit, urgent.length, 8);
            const used = new Set([...pending.slice(0, pendingLimit), ...completed.slice(0, completedLimit)].map(task => `plan:${taskKey(task)}`));
            urgent.slice(0, candidateLimit).forEach(task => used.add(`candidate:${taskKey(task)}`));
            for (const key of rows.keys()) if (!used.has(key)) rows.delete(key);
        }

        function deriveProjects(tasks) {
            const groups = new Map();
            for (const task of tasks) {
                const name = projectName(task);
                const key = name ? `project:${name}` : 'unassigned';
                let group = groups.get(key);
                if (!group) {
                    group = { key, name, pending: 0, completed: 0, archived: 0, overdue: 0, next: null, nextOrder: Infinity };
                    groups.set(key, group);
                }
                if (task.archived) { group.archived += 1; continue; }
                if (task.completed) { group.completed += 1; continue; }
                group.pending += 1;
                if (api.isOverdue(task)) group.overdue += 1;
                const deadline = deadlineOrder(task);
                if (!group.next || deadline < group.nextOrder || (deadline === group.nextOrder && compareTaskOrder(task, group.next) < 0)) {
                    group.next = task;
                    group.nextOrder = deadline;
                }
            }
            return [...groups.values()];
        }

        function newCard(key) {
            const element = button('project-card', 'open-project');
            element.dataset.workbenchProjectKey = key;
            const top = node('span', 'project-card-top');
            const mark = node('span', 'project-card-mark');
            mark.append(icon('folder'));
            const name = node('strong', 'project-card-name');
            const arrow = node('span', 'project-card-arrow');
            arrow.append(icon('arrow'));
            top.append(mark, name, arrow);
            const counts = node('span', 'project-card-counts');
            const metrics = {};
            for (const kind of ['pending', 'completed', 'archived']) {
                const stat = node('span', 'project-card-stat');
                const value = node('strong');
                const label = node('span');
                stat.append(value, label);
                counts.append(stat);
                metrics[kind] = { value, label };
            }
            counts.id = `workbench-project-counts-${++sequence}`;
            const bar = node('progress', 'project-card-progress');
            bar.setAttribute('aria-hidden', 'true');
            const next = node('span', 'project-card-next');
            next.id = `workbench-project-next-${sequence}`;
            const nextLabel = node('span', 'project-card-next-label');
            const nextName = node('span', 'project-card-next-name');
            const nextDate = node('span', 'project-card-next-date');
            next.append(nextLabel, nextName, nextDate);
            const overdue = node('span', 'project-card-overdue');
            element.append(top, counts, bar, next, overdue);
            return { element, name, metrics, bar, next, nextLabel, nextName, nextDate, overdue };
        }

        function renderCard(group) {
            let card = cards.get(group.key);
            if (!card) { card = newCard(group.key); cards.set(group.key, card); }
            const name = group.name || text('v5.projects.unassigned');
            card.name.textContent = name;
            card.element.disabled = !isAvailable();
            for (const kind of ['pending', 'completed', 'archived']) {
                card.metrics[kind].value.textContent = String(group[kind]);
                card.metrics[kind].label.textContent = text(`v5.projects.${kind}`);
            }
            const total = group.pending + group.completed;
            card.bar.max = Math.max(1, total);
            card.bar.value = group.completed;
            card.bar.hidden = total === 0;
            card.nextLabel.textContent = text(group.next && Number.isFinite(group.nextOrder) ? 'v5.projects.nextDue' : 'v5.projects.nextTask');
            card.nextName.textContent = group.next ? taskName(group.next) : text(total ? 'v5.projects.allDone' : 'v5.projects.allArchived');
            card.nextDate.textContent = group.next ? api.formatDue(group.next) : '';
            card.nextDate.hidden = !card.nextDate.textContent;
            card.nextLabel.hidden = !group.next;
            card.overdue.textContent = text('v5.projects.overdue', { count: group.overdue });
            card.overdue.hidden = group.overdue === 0;
            return card.element;
        }

        function renderProjectGrid() {
            const query = projectQuery.normalize('NFKC').toLocaleLowerCase(latest.language).trim();
            const filtered = projectGroups.filter(group => (group.name || text('v5.projects.unassigned'))
                .normalize('NFKC').toLocaleLowerCase(latest.language).includes(query));
            filtered.sort((a, b) => {
                if (projectSort === 'pending' && a.pending !== b.pending) return b.pending - a.pending;
                if (projectSort === 'due' && a.nextOrder !== b.nextOrder) return a.nextOrder - b.nextOrder;
                if (!a.name || !b.name) return a.name ? -1 : b.name ? 1 : 0;
                return collator.compare(a.name, b.name);
            });
            projectsEmpty.element.hidden = filtered.length !== 0;
            projectsEmpty.heading.textContent = text(!isAvailable() ? 'v5.common.storageUnavailable'
                : projectGroups.length === 0 ? 'v5.projects.empty' : 'v5.projects.noResults');
            projectsEmpty.action.hidden = projectGroups.length === 0 || !projectQuery || !isAvailable();
            projectsEmpty.action.dataset.workbenchAction = 'clear-project-search';
            projectsEmpty.action.textContent = text('v5.projects.clearSearch');
            const visible = filtered.slice(0, projectLimit);
            reconcile(projectGrid, visible.map(renderCard));
            const used = new Set(visible.map(group => group.key));
            for (const key of cards.keys()) if (!used.has(key)) cards.delete(key);
            setMore(projectsMore, projectLimit, filtered.length, 24);
        }

        function renderProjects(tasks) {
            projectsHeader.heading.textContent = text('v5.projects.title');
            projectGroups = deriveProjects(tasks);
            const named = projectGroups.filter(group => group.name).length;
            projectsHeader.subtitle.textContent = named ? countText('v5.projects.projectCount', named) : '';
            projectsHeader.subtitle.hidden = named === 0;
            projectSearch.placeholder = text('v5.projects.search');
            projectSearch.setAttribute('aria-label', text('v5.projects.search'));
            if (projectSearch.value !== projectQuery) projectSearch.value = projectQuery;
            sortLabel.textContent = text('v5.projects.sort');
            sort.setAttribute('aria-label', text('v5.projects.sort'));
            for (const [value, option] of sortOptions) option.textContent = text(`v5.projects.sort.${value}`);
            sort.value = projectSort;
            projectByKey.clear();
            for (const group of projectGroups) projectByKey.set(group.key, group);
            renderProjectGrid();
        }

        function focusedControlViewport(rect) {
            const viewport = window.visualViewport;
            const viewportTop = Math.max(0, viewport?.offsetTop || 0);
            const viewportBottom = Math.min(window.innerHeight, viewportTop + (viewport?.height || window.innerHeight));
            let top = viewportTop + 12;
            let bottom = viewportBottom - 12;
            const topbar = document.querySelector('.workspace-topbar');
            if (topbar?.getClientRects().length) {
                const bar = topbar.getBoundingClientRect();
                const position = getComputedStyle(topbar).position;
                if (['fixed', 'sticky'].includes(position) && bar.top <= viewportTop + 1 && bar.bottom > viewportTop) top = Math.max(top, bar.bottom + 12);
            }
            const dock = document.getElementById('workspaceMobileDock');
            if (dock?.getClientRects().length) {
                const bar = dock.getBoundingClientRect();
                if (getComputedStyle(dock).position === 'fixed' && bar.top < viewportBottom && bar.bottom >= viewportBottom - 1) bottom = Math.min(bottom, bar.top - 12);
            }
            const notification = document.getElementById('notification');
            if (notification?.getClientRects().length) {
                const style = getComputedStyle(notification);
                const notice = notification.getBoundingClientRect();
                if (style.position === 'fixed' && (style.visibility === 'visible' || notification.classList.contains('show'))
                    && notice.left < rect.right && notice.right > rect.left
                    && notice.bottom <= viewportBottom && notice.top >= top + (bottom - top) * 0.4) bottom = Math.min(bottom, notice.top - 12);
            }
            return { top, bottom };
        }

        function scrollFocusedControlIntoView(target) {
            if (document.activeElement !== target || !target.isConnected || target.closest('[hidden], [inert]')) return;
            const rect = target.getBoundingClientRect();
            if (!rect.width || !rect.height) return;
            const { top, bottom } = focusedControlViewport(rect);
            if (bottom <= top) return;
            const delta = rect.height > bottom - top ? (rect.top + rect.bottom - top - bottom) / 2
                : rect.top < top ? rect.top - top : rect.bottom > bottom ? rect.bottom - bottom : 0;
            if (Math.abs(delta) >= 1) window.scrollBy({ top: delta, behavior: 'instant' });
        }

        function revealFocusedControl(mount, target) {
            scrollFocusedControlIntoView(target);
            if (focusVisibilityFrame) cancelAnimationFrame(focusVisibilityFrame);
            const screen = latest.screen;
            const scrollTop = window.scrollY;
            const scrollLeft = window.scrollX;
            focusVisibilityFrame = requestAnimationFrame(() => {
                focusVisibilityFrame = 0;
                if (latest.screen === screen && !api.isDialogOpen() && mount.contains(target)
                    && document.activeElement === target && Math.abs(window.scrollY - scrollTop) < 1
                    && Math.abs(window.scrollX - scrollLeft) < 1) scrollFocusedControlIntoView(target);
            });
        }

        function preserveFocus(mount, update) {
            const active = document.activeElement;
            const owned = active instanceof HTMLElement && mount.contains(active);
            const key = owned ? active.dataset.workbenchTaskKey : null;
            const action = owned ? active.dataset.workbenchAction : null;
            const initialRect = owned ? active.getBoundingClientRect() : null;
            const initialViewport = initialRect ? focusedControlViewport(initialRect) : null;
            const reveal = owned && (busy.has(key) || (initialRect.width > 0 && initialRect.height > 0
                && initialRect.top >= initialViewport.top && initialRect.bottom <= initialViewport.bottom));
            update();
            if (!owned || api.isDialogOpen()) return;
            if (document.activeElement === active) {
                if (reveal) revealFocusedControl(mount, active);
                return;
            }
            if (document.activeElement !== document.body) return;
            if (active.isConnected && !active.hidden && !active.disabled && active.getClientRects().length) {
                active.focus({ preventScroll: true });
                if (reveal) revealFocusedControl(mount, active);
                return;
            }
            if (key) {
                for (const row of rows.values()) {
                    if (row.element.dataset.workbenchTask !== key || !row.element.isConnected) continue;
                    const target = action === 'toggle' ? row.toggle || row.name : row.name;
                    if (target && !target.disabled && target.getClientRects().length) {
                        target.focus({ preventScroll: true });
                        if (reveal) revealFocusedControl(mount, target);
                        return;
                    }
                }
            }
            const fallback = mount === todayMount ? plan.heading : projectsHeader.heading;
            fallback.focus({ preventScroll: true });
            if (reveal) revealFocusedControl(mount, fallback);
        }

        function render(snapshot) {
            latest = snapshot;
            if (!latest || !['today', 'projects'].includes(latest.screen)) return;
            if (collatorLanguage !== latest.language) {
                collatorLanguage = latest.language;
                collator = new Intl.Collator(latest.language, { numeric: true, sensitivity: 'base' });
            }
            if (currentDay !== latest.today) {
                currentDay = latest.today;
                pendingLimit = 50; completedLimit = 10; candidateLimit = 8;
            }
            const tasks = safeTasks();
            taskByKey.clear();
            for (const task of tasks) taskByKey.set(taskKey(task), task);
            const mount = latest.screen === 'today' ? todayMount : projectsMount;
            preserveFocus(mount, () => latest.screen === 'today' ? renderToday(tasks) : renderProjects(tasks));
        }

        function runTaskAction(control, action) {
            const key = control.dataset.workbenchTaskKey;
            const task = taskByKey.get(key);
            if (!task || !isAvailable() || busy.has(key)) return;
            if (action === 'edit') { api.edit(task.id); return; }
            busy.add(key);
            todayHeader.feedback.hidden = true;
            render(latest);
            let operation;
            try { operation = action === 'toggle' ? api.toggle(task.id) : api.plan(task.id); }
            catch (error) { operation = Promise.reject(error); }
            Promise.resolve(operation).catch(() => {
                todayHeader.feedback.textContent = text('v5.common.actionFailed');
                todayHeader.feedback.hidden = false;
            }).finally(() => {
                busy.delete(key);
                render(latest);
            });
        }

        function handleClick(event) {
            const control = event.target.closest?.('button[data-workbench-action]');
            if (!control || control.disabled || api.isDialogOpen()) return;
            if (latest?.screen !== (todayMount.contains(control) ? 'today' : 'projects')) return;
            const action = control.dataset.workbenchAction;
            if (['edit', 'toggle', 'plan'].includes(action)) { runTaskAction(control, action); return; }
            if (action === 'open-project') {
                const group = projectByKey.get(control.dataset.workbenchProjectKey);
                if (group && isAvailable()) api.openProject(group.name ? { kind: 'project', name: group.name } : { kind: 'unassigned' },
                    group.pending === 0 && group.completed === 0 && group.archived > 0 ? 'archived' : 'all');
                return;
            }
            if (action === 'open-tasks') { api.openTasks('active'); return; }
            if (action === 'more-pending') pendingLimit += 50;
            else if (action === 'more-completed') completedLimit += 10;
            else if (action === 'more-candidates') candidateLimit += 8;
            else if (action === 'more-projects') projectLimit += 24;
            else if (action === 'clear-project-search') {
                projectQuery = ''; projectLimit = 24; projectSearch.value = ''; projectSearch.focus();
            } else return;
            render(latest);
        }

        todayMount.addEventListener('click', handleClick);
        projectsMount.addEventListener('click', handleClick);
        projectsMount.addEventListener('input', event => {
            if (event.target !== projectSearch || !latest || latest.screen !== 'projects') return;
            projectQuery = projectSearch.value;
            projectLimit = 24;
            preserveFocus(projectsMount, renderProjectGrid);
        });
        projectsMount.addEventListener('change', event => {
            if (event.target !== sort || !latest || latest.screen !== 'projects') return;
            projectSort = sort.value;
            projectLimit = 24;
            preserveFocus(projectsMount, renderProjectGrid);
        });

        return { render };
    };
})();
