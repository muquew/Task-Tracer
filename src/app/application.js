(function (namespace) {
    'use strict';
    namespace.start = function startApplication(CONFIG, ports) {
        const TaskInput = ports.taskInput;
        const createWorkbench = ports.createWorkbench;
        const reviewView = ports.createReviewView({
            document, translate: key => utils.translate(key), translateCount, createIcon,
            projectLabel: getProjectFilterLabel,
            formatDateKey: key => new Intl.DateTimeFormat(state.currentLanguage,
                { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(`${key}T12:00:00Z`))
        });
        const LocalCalendar = ports.localCalendar;
        const getCurrentTimeZone = LocalCalendar.getCurrentTimeZone;
        const TaskDates = ports.taskDates.create({ defaultTime: CONFIG.DEFAULTS.TIME, getCurrentTimeZone, localCalendar: LocalCalendar });
        const {
            normalizeDueDateValue, normalizeDueTimeValue, normalizeTimeZoneName, isValidTimeZoneName,
            getInstantWallPartsInTimeZone, getTimeZoneOffsetMs, createWallDate, legacyStoredDueDateToLocalDate,
            createDueFields, clearDueFields, normalizeTaskDueFields, createDueFieldsFromDate,
            createDueFieldsFromInstant, getTaskDueTimeZone, getTaskDueDateKey, getTaskDueTimeValue,
            hasTaskDueDate, getTaskDueLocalDate, getTaskDueInstant, getTaskDueSortValue,
            normalizeStoredDate, isValidDate, normalizeTaskRepeatType, normalizeTaskRepeatInterval,
            normalizeTaskRepeatWeekdays, getTaskRepeatRule, getTaskRepeatWeekdays, getWeekdayDisplayIndex,
            hasTaskRepeat, calculateNextRepeatDueFields, getNextWeeklyRepeatDate, getLastDayOfNextMonth,
            addMonthsClamped, getDaysInMonth
        } = TaskDates;
        const calculateTaskTimeLeft = task => TaskDates.calculateTaskTimeLeft(task, Date.now());
        const { tokenizeTaskInput, readTaskInputValue, normalizeTaskProject, normalizeTaskTags,
            parseTagsInput, formatTagsInput, normalizeSearchQuery, matchesSearchAlias, renameProjectQuery } = TaskInput;
        const state = {
            db: null,
            taskRevision: 0,
            tasks: [],
            filter: 'active',
            sort: 'smart',
            projectFilter: { kind: 'all' },
            viewMode: 'list',
            toolsDrawerCollapsed: false,
            toolsDrawerPinned: true,
            focusMode: false,
            calendarMonthDate: getCalendarTodayDate(),
            searchQuery: '',
            searchParseKey: null,
            searchParseValue: null,
            searchParseTasks: null,
            searchParseRevision: -1,
            searchTexts: new WeakMap(),
            listRenderLimit: 100,
            listPageKey: '',
            savedViews: [],
            batchMode: false,
            selectedTaskIds: new Set(),
            editingTaskId: null,
            editingTaskSnapshot: null,
            currentLanguage: 'zh-CN',
            translations: {},
            tempSubtasks: [],
            editingSubtaskIndex: -1,
            modalMode: 'form',
            progressInterval: null,
            timeViewBoundary: null,
            timeViewDay: '',
            timeViewOffset: null,
            timeViewCheckedAt: 0,
            timeViewRefreshPending: false,
            timeViewRefreshFrame: null,
            timeViewEventsBound: false,
            notificationHideTimer: null,
            notificationHideDeadline: 0,
            notificationRemaining: 0,
            notificationHovered: false,
            notificationTaskId: null,
            notificationReturnFocus: null,
            taskFormSaving: false,
            taskFormSession: null,
            recoverableTaskDrafts: [],
            taskDraftRecoverySequence: 0,
            pendingTaskImportReader: null,
            quickAddSaving: false,
            quickAddCaptureDraft: null,
            composingInputs: new WeakSet(),
            pendingTaskActions: new Set(),
            elementToFocusOnClose: null,
            calendarDetailDateKey: '',
            calendarDetailRenderLimit: 100,
            calendarSearchQuery: '',
            calendarSearchNeedsSync: false,
            dateTimeFormatters: {},
            notificationsEnabled: false,
            notifiedTasks: new Set(),
            pendingNotificationKeys: new Set(),
            themeTransitionInProgress: false,
            serviceWorkerRegistration: null,
            serviceWorkerRegistrationPromise: null,
            watchedWorkerRegistrations: new WeakSet(),
            watchedUpdateWorkers: new WeakSet(),
            updateChecking: false,
            updateAvailable: false,
            updateWorker: null,
            updateCheckStatus: 'idle',
            updateCheckMessageKey: '',
            updatePromptDismissed: false,
            refreshingForUpdate: false,
            deferredInstallPrompt: null,
            commandPaletteItems: [],
            commandPaletteActiveIndex: 0,
            commandPaletteReturnFocus: null,
            undoAction: null,
            storageAvailable: true,
            storageError: null,
            storageFallbackTasks: [],
            storageFailureEventsBound: false,
            essentialEventsBound: false,
            toolsDrawerEventsBound: false,
            eventsBound: false
        };
        const DOM = {};
        const workspaceUI = { statsDrilldown: null, planning: false, captureOpen: false, captureDateKey: '', captureFormText: null, settingsSection: 'settingsAppearance', screen: 'today', lastScreen: 'today', settingsReturnFocus: null, pageScopes: { tasks: null, review: null }, pageScroll: {}, pageFocus: {}, workbench: null, moduleWarningShown: false, taskScrollY: 0, taskReturnFocus: null, viewportHeight: 0, navigationOpen: false, scheduleOpen: false, month: getCalendarTodayDate(), selectedDate: '', calendarSignature: '', projectSignature: '', upcomingSignature: '', scheduleOpener: null, themeBound: false, pluralRules: new Map() };
        function normalizedAccentPreference(value) {
            return ['iris', 'ocean', 'pine', 'berry'].includes(value) ? value : 'iris';
        }
        function setAccentPreference(value, { persist = true } = {}) {
            const accent = normalizedAccentPreference(value);
            document.documentElement.setAttribute('data-accent', accent);
            if (persist) safeSetStorageItem('localStorage', CONFIG.STORAGE.ACCENT, accent);
            syncAccentChoiceControls(accent);
            if (window.__TASK_TRACER_SET_THEME_CHROME__) window.__TASK_TRACER_SET_THEME_CHROME__(document.documentElement.getAttribute('data-theme'));
        }
        function syncAccentChoiceControls(accent) {
            if (DOM.accentSelect) DOM.accentSelect.value = accent;
            document.querySelectorAll('input[name="workspaceTheme"]').forEach(input => { input.checked = input.value === accent; });
        }
        function normalizedThemePreference(value) {
            return ['light', 'dark', 'system'].includes(value) ? value : 'system';
        }
        function resolvedThemePreference(preference) {
            return preference === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : preference;
        }
        function syncThemePreferenceSelect() {
            const preference = normalizedThemePreference(document.documentElement.getAttribute('data-theme-preference'));
            for (const select of [DOM.themeBtn]) if (select) select.value = preference;
        }
        function setThemePreference(value, { persist = true } = {}) {
            const preference = normalizedThemePreference(value);
            document.documentElement.setAttribute('data-theme-preference', preference);
            if (persist) safeSetStorageItem('localStorage', CONFIG.STORAGE.THEME, preference);
            utils.applyTheme(resolvedThemePreference(preference));
            syncThemePreferenceSelect();
        }
        function bindThemePreferenceEvents() {
            if (workspaceUI.themeBound) return;
            workspaceUI.themeBound = true;
            setThemePreference(safeGetStorageItem('localStorage', CONFIG.STORAGE.THEME), { persist: false });
            setAccentPreference(safeGetStorageItem('localStorage', CONFIG.STORAGE.ACCENT), { persist: false });
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
                if (document.documentElement.getAttribute('data-theme-preference') === 'system') setThemePreference('system', { persist: false });
            });
            window.addEventListener('storage', event => {
                if (event.storageArea && event.storageArea !== getWebStorage('localStorage')) return;
                if (event.key === CONFIG.STORAGE.THEME || event.key === null) setThemePreference(event.newValue, { persist: false });
                if (event.key === CONFIG.STORAGE.ACCENT || event.key === null) setAccentPreference(event.newValue, { persist: false });
            });
        }
        function translateCount(key, count) {
            let rules = workspaceUI.pluralRules.get(state.currentLanguage);
            if (!rules) { rules = new Intl.PluralRules(state.currentLanguage); workspaceUI.pluralRules.set(state.currentLanguage, rules); }
            const oneKey = `${key}One`;
            return utils.translate(rules.select(Number(count)) === 'one' && state.translations[state.currentLanguage]?.[oneKey] !== undefined ? oneKey : key);
        }

        function captureWorkspaceScope() {
            return { viewMode: state.viewMode, filter: state.filter, sort: state.sort,
                projectFilter: normalizeProjectFilter(state.projectFilter), focusMode: state.focusMode,
                batchMode: state.batchMode, selectedTaskIds: [...state.selectedTaskIds],
                searchQuery: normalizeSearchQuery(DOM.inputs.search.value), rawQuery: DOM.inputs.search.value,
                listPageKey: state.listPageKey, listRenderLimit: state.listRenderLimit,
                calendarMonthDate: state.calendarMonthDate ? new Date(state.calendarMonthDate) : null,
                calendarDetailDateKey: state.calendarDetailDateKey, calendarDetailRenderLimit: state.calendarDetailRenderLimit,
                calendarSearchQuery: state.calendarSearchQuery, calendarSearchNeedsSync: state.calendarSearchNeedsSync };
        }
        function restoreWorkspaceScope(screen) {
            const saved = workspaceUI.pageScopes[screen] || { viewMode: screen === 'review' ? 'stats' : 'list',
                filter: 'all', sort: 'smart', projectFilter: { kind: 'all' }, focusMode: false,
                batchMode: false, searchQuery: '', rawQuery: '' };
            Object.assign(state, { viewMode: screen === 'review' ? 'stats' : saved.viewMode === 'stats' ? 'list' : saved.viewMode,
                filter: saved.filter, sort: saved.sort, projectFilter: normalizeProjectFilter(saved.projectFilter),
                focusMode: screen === 'tasks' && saved.focusMode, batchMode: screen === 'tasks' && saved.batchMode,
                searchQuery: saved.searchQuery,
                selectedTaskIds: new Set(screen === 'tasks' ? saved.selectedTaskIds || [] : []),
                listPageKey: saved.listPageKey || '', listRenderLimit: saved.listRenderLimit || 100,
                calendarMonthDate: saved.calendarMonthDate ? new Date(saved.calendarMonthDate) : getCalendarTodayDate(),
                calendarDetailDateKey: saved.calendarDetailDateKey || '', calendarDetailRenderLimit: saved.calendarDetailRenderLimit || 100,
                calendarSearchQuery: saved.calendarSearchQuery || '', calendarSearchNeedsSync: Boolean(saved.calendarSearchNeedsSync) });
            DOM.inputs.search.value = saved.rawQuery;
            syncSearchClearButton();
            syncDropdowns();
        }
        function workspacePageElement(screen) {
            return document.getElementById({ today: 'todayWorkspace', projects: 'projectsWorkspace',
                tasks: 'tasksWorkspace', review: 'tasksWorkspace', settings: 'settingsWorkspace' }[screen]);
        }
        function isWorkspaceFocusReachable(element) {
            if (!isFocusableReturnElement(element)) return false;
            const rect = element.getBoundingClientRect();
            const shell = element.closest('.workspace-sidebar, #workspaceMobileDock, .workspace-topbar');
            const dock = document.getElementById('workspaceMobileDock').getBoundingClientRect();
            const top = shell ? 0 : document.querySelector('.workspace-topbar').getBoundingClientRect().bottom;
            const bottom = shell || !dock.height || dock.top >= window.innerHeight ? window.innerHeight : dock.top;
            if (rect.left < 0 || rect.right > window.innerWidth || rect.top < top || rect.bottom > bottom) return false;
            const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
            return Boolean(hit && (hit === element || element.contains(hit)));
        }
        function setWorkspaceScreen(screen, { focus = false, restoreFocus = false, render = true, planning = null } = {}) {
            if (!['today', 'tasks', 'projects', 'review', 'settings'].includes(screen)) return false;
            if (screen !== workspaceUI.screen) closeMobileFilters({ restoreFocus: false });
            if (isDialogOpen()) return false;
            if (['today', 'projects'].includes(screen) && typeof createWorkbench !== 'function') screen = 'tasks';
            const previous = workspaceUI.screen;
            const changed = previous !== screen;
            const wasPlanning = workspaceUI.planning;
            workspaceUI.planning = screen === 'tasks' && (planning === true || (planning !== false && wasPlanning));
            const planningChanged = wasPlanning !== workspaceUI.planning;
            const returningFromSettings = previous === 'settings' && screen === workspaceUI.lastScreen;
            if (changed) {
                workspaceUI.pageScroll[previous] = window.scrollY;
                if (workspacePageElement(previous)?.contains(document.activeElement)) workspaceUI.pageFocus[previous] = captureFocusReturnTarget();
                if (['tasks', 'review'].includes(previous)) workspaceUI.pageScopes[previous] = captureWorkspaceScope();
                if (screen === 'settings') {
                    workspaceUI.lastScreen = previous;
                    workspaceUI.settingsReturnFocus = captureFocusReturnTarget();
                }
                closeAllDropdowns();
                closeAllCustomSelects();
                closeTaskActionMenus(false);
                if (['tasks', 'review'].includes(screen)) restoreWorkspaceScope(screen);
            }
            setWorkspaceNavigationOpen(false);
            workspaceUI.screen = screen;
            syncWorkspaceScreen();
            if (screen === 'settings') syncSettingsStatus();
            if ((changed || planningChanged) && render) {
                if (screen === 'today' || screen === 'projects') syncWorkbenchPages();
                else if (screen !== 'settings' && (!returningFromSettings || document.getElementById('tasksWorkspace').dataset.planning !== String(workspaceUI.planning))) renderTaskList();
            }
            if (changed) window.scrollTo({ top: workspaceUI.pageScroll[screen] || 0, behavior: 'instant' });
            if (focus || restoreFocus) {
                const headings = { today: 'todayTitle', projects: 'projectsTitle', settings: 'settingsTitle', tasks: 'workspaceTitle', review: 'workspaceTitle' };
                const opener = previous === 'settings' && restoreFocus
                    ? resolveFocusReturnElement(workspaceUI.settingsReturnFocus) : null;
                const remembered = resolveFocusReturnElement(workspaceUI.pageFocus[screen]);
                const heading = document.getElementById(headings[screen]);
                const navigation = Array.from(document.querySelectorAll('[data-workbench-screen]')).find(button =>
                    button.dataset.workbenchScreen === screen && isWorkspaceFocusReachable(button));
                const fallback = screen === 'settings' ? document.getElementById('workspaceSettingsBtn') : navigation || DOM.openModalBtn;
                const target = [opener, remembered, heading, fallback, DOM.openModalBtn].find(isWorkspaceFocusReachable);
                target?.focus({ preventScroll: true });
            }
            return true;
        }
        function syncPrimaryNavigation() {
            document.querySelectorAll('[data-workbench-screen]').forEach(button => {
                const active = button.dataset.workbenchScreen === workspaceUI.screen;
                button.classList.toggle('active', active);
                button.classList.toggle('selected', active);
                if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
                if (button.hasAttribute('aria-pressed')) button.setAttribute('aria-pressed', String(active));
            });
        }
        function syncWorkspaceScreen() {
            if (['today', 'projects'].includes(workspaceUI.screen) && typeof createWorkbench !== 'function') {
                workspaceUI.screen = 'tasks';
                if (!workspaceUI.moduleWarningShown && state.translations[state.currentLanguage]) {
                    workspaceUI.moduleWarningShown = true;
                    utils.notify(utils.translate('v5.moduleUnavailable'), 'error');
                }
            }
            const screen = workspaceUI.screen;
            const visible = { todayWorkspace: screen === 'today', projectsWorkspace: screen === 'projects',
                tasksWorkspace: screen === 'tasks' || screen === 'review', settingsWorkspace: screen === 'settings' };
            for (const [id, shown] of Object.entries(visible)) {
                const section = document.getElementById(id);
                section.hidden = !shown;
                section.inert = !shown;
            }
            document.body.dataset.workspaceScreen = screen;
            const settings = screen === 'settings';
            const settingsButton = document.getElementById('workspaceSettingsBtn');
            if (settings) settingsButton.setAttribute('aria-current', 'page'); else settingsButton.removeAttribute('aria-current');
            document.getElementById('settingsBackBtn').hidden = !settings;
            const backKey = `v5.back.${workspaceUI.lastScreen}`;
            const back = document.getElementById('settingsBackBtn');
            back.setAttribute('data-i18n-aria-label', backKey);
            back.querySelector('span').setAttribute('data-i18n', backKey);
            back.querySelector('span').textContent = utils.translate(backKey);
            back.setAttribute('aria-label', utils.translate(backKey));
            document.getElementById('openMenuBtn').hidden = true;
            setSettingsSection(workspaceUI.settingsSection);
            syncPrimaryNavigation();
            syncViewSwitcher();
            syncWorkspaceOverviewVisibility();
        }
        function openWorkbenchProject(project, status = 'all') {
            if (!canRunAppAction('project.filter') || isDialogOpen()) return false;
            setWorkspaceScreen('tasks', { render: false, planning: false });
            DOM.inputs.search.value = '';
            state.searchQuery = '';
            state.filter = status === 'archived' ? 'archived' : 'all';
            state.focusMode = false;
            state.viewMode = 'list';
            syncSearchClearButton();
            const opened = runAppAction('project.filter', { value: project, options: { exitFocus: true } });
            window.scrollTo({ top: 0, behavior: 'instant' });
            document.getElementById('workspaceTitle').focus({ preventScroll: true });
            return opened;
        }
        function renameProjectReferences(value, previous, next, names) {
            if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
            const updated = { ...value };
            if ('projectFilter' in value) {
                const scope = normalizeProjectFilter(value.projectFilter);
                if (scope.kind === 'project' && scope.name === previous) updated.projectFilter = { kind: 'project', name: next };
            }
            for (const key of ['rawQuery', 'searchQuery', 'calendarSearchQuery', 'query']) {
                if (typeof value[key] !== 'string') continue;
                const query = renameProjectQuery(value[key], previous, next, names);
                if (query !== value[key]) updated[key] = key === 'rawQuery' ? query : normalizeSearchQuery(query);
            }
            return updated;
        }
        function renameProjectWorkspaceReferences(previous, next, names, restore = null) {
            const changes = {};
            const update = (key, value) => {
                const updated = renameProjectReferences(value, previous, next, names);
                for (const field of ['rawQuery', 'searchQuery', 'calendarSearchQuery', 'query']) {
                    if (restore?.[key] && typeof value[field] === 'string' && value[field] === restore[key].after[field]) {
                        updated[field] = restore[key].before[field];
                    }
                }
                changes[key] = { before: value, after: updated };
                return updated;
            };
            const current = update('current', { projectFilter: state.projectFilter, rawQuery: DOM.inputs.search.value });
            state.projectFilter = normalizeProjectFilter(current.projectFilter);
            DOM.inputs.search.value = current.rawQuery;
            state.searchQuery = normalizeSearchQuery(current.rawQuery);
            state.listPageKey = '';
            for (const screen of ['tasks', 'review']) {
                if (!workspaceUI.pageScopes[screen]) continue;
                workspaceUI.pageScopes[screen] = { ...update(screen, workspaceUI.pageScopes[screen]), listPageKey: '' };
            }
            const drilldown = workspaceUI.statsDrilldown;
            if (drilldown) {
                drilldown.origin = update('origin', drilldown.origin);
                drilldown.target = update('target', drilldown.target);
                const control = drilldown.origin.control;
                if (control?.project) {
                    try {
                        const updated = renameProjectReferences({ projectFilter: JSON.parse(control.project) }, previous, next, names);
                        control.project = projectFilterKey(updated.projectFilter);
                    } catch {}
                }
            }
            syncSearchClearButton();
            return changes;
        }
        function writeProjectRename(previous, next, undo = null) {
            return dbActions.renameProject(previous, next, undo);
        }
        function registerProjectRenameUndo(receipt) {
            state.undoAction = {
                label: utils.translate('v5.projects.renameUndo'),
                run: async () => {
                    if (state.taskRevision !== receipt.taskRevision) throw new DOMException('Tasks changed after project rename', 'TaskConflictError');
                    const restored = await writeProjectRename(receipt.next, receipt.previous, receipt);
                    state.savedViews = normalizeSavedViews(restored.views);
                    renameProjectWorkspaceReferences(receipt.next, receipt.previous, restored.names, receipt.uiReferences);
                    workspaceUI.workbench?.projectRenamed(receipt.next, receipt.previous);
                    clearNotificationDeliveryState();
                    await refreshTasks();
                    if (workspaceUI.screen === 'projects') workspaceUI.workbench?.focusProject(receipt.previous);
                }
            };
            syncUndoControls();
        }
        function promptProjectRename(previous, returnTarget) {
            if (!ensureStorageAvailable() || !previous || isDialogOpen()) return;
            const expectedRevision = state.taskRevision;
            const content = document.createElement('div');
            content.className = 'confirm-details project-rename-form';
            const label = document.createElement('label');
            label.className = 'form-field';
            const caption = document.createElement('span');
            caption.textContent = utils.translate('v5.projects.nameLabel');
            const input = document.createElement('input');
            input.id = 'projectRenameInput';
            input.type = 'text';
            input.value = previous;
            input.required = true;
            input.autocomplete = 'off';
            input.setAttribute('aria-describedby', 'projectRenameError');
            const errorText = document.createElement('p');
            errorText.id = 'projectRenameError';
            errorText.className = 'field-error';
            errorText.setAttribute('role', 'alert');
            errorText.hidden = true;
            label.append(caption, input);
            content.append(label, errorText);
            const invalid = key => {
                errorText.textContent = utils.translate(key);
                errorText.hidden = false;
                input.setAttribute('aria-invalid', 'true');
                input.focus();
                return false;
            };
            input.addEventListener('input', () => { errorText.hidden = true; input.removeAttribute('aria-invalid'); });
            utils.confirm(utils.translate('v5.projects.renameTitle'), content, async () => {
                if (hasActiveComposition(DOM.form)) return false;
                const next = normalizeTaskProject(input.value);
                if (!next) return invalid('v5.projects.nameRequired');
                if (next === previous) return true;
                if (state.taskRevision !== expectedRevision) {
                    utils.notify(utils.translate('storage.staleConfirmation'), 'warning');
                    return false;
                }
                if (state.tasks.some(task => normalizeTaskProject(task.project) === next)) return invalid('v5.projects.nameExists');
                try {
                    const receipt = await writeProjectRename(previous, next);
                    state.savedViews = normalizeSavedViews(receipt.views);
                    receipt.uiReferences = renameProjectWorkspaceReferences(previous, next, receipt.names);
                    workspaceUI.workbench?.projectRenamed(previous, next);
                    await refreshTasks();
                    if (state.taskRevision === receipt.taskRevision) registerProjectRenameUndo(receipt);
                    utils.notify(utils.translate('v5.projects.renamed').replace('{name}', next), 'success', { undo: true });
                    return true;
                } catch (error) {
                    if (error?.name === 'ProjectNameConflictError') return invalid('v5.projects.nameExists');
                    handleStorageOperationError(error, 'v5.projects.renameFailed');
                    return false;
                }
            });
            DOM.submitBtn.textContent = utils.translate('actions.updateTask');
            state.elementToFocusOnClose = returnTarget;
            requestAnimationFrame(() => { input.focus(); input.select(); });
        }
        function syncWorkbenchPages() {
            if (typeof createWorkbench !== 'function') return;
            if (!workspaceUI.workbench) workspaceUI.workbench = createWorkbench({
                t: key => utils.translate(key), dueKey: task => getTaskDueDateKey(task),
                formatDue: task => formatTaskDueDate(task), groupDue: (element, task) => groupTaskDeadlineClock(element, task),
                isOverdue: task => !task.completed && !task.archived && hasTaskDueDate(task) && calculateTaskTimeLeft(task) < 0,
                edit: id => runAppAction('task.edit', { taskId: id }),
                toggle: id => toggleTaskComplete(id), plan: id => toggleTaskFocus(id),
                openProject: openWorkbenchProject,
                renameProject: (name, control) => runAppAction('project.rename', { name, returnTarget: captureFocusReturnTarget(control) }),
                openReview: () => {
                    if (!canRunAppAction('view.set') || isDialogOpen()) return false;
                    clearStatsDrilldown();
                    workspaceUI.pageScopes.review = { viewMode: 'stats', filter: 'all', sort: 'smart',
                        projectFilter: { kind: 'all' }, focusMode: false, batchMode: false,
                        searchQuery: '', rawQuery: '' };
                    const opened = runAppAction('view.set', { view: 'stats' });
                    document.getElementById('workspaceTitle').focus({ preventScroll: true });
                    return opened;
                },
                openTasks: (filter = 'active', options = {}) => {
                    if (!canRunAppAction('filter.set')) return false;
                    if (!setWorkspaceScreen('tasks', { render: false, planning: options.planning === true })) return false;
                    DOM.inputs.search.value = '';
                    state.searchQuery = '';
                    syncSearchClearButton();
                    state.projectFilter = { kind: 'all' };
                    state.focusMode = false;
                    state.viewMode = 'list';
                    if (options.planning === true) {
                        state.batchMode = false;
                        state.selectedTaskIds.clear();
                    }
                    const opened = runAppAction('filter.set', { value: filter });
                    window.scrollTo({ top: 0, behavior: 'instant' });
                    document.getElementById('workspaceTitle').focus({ preventScroll: true });
                    return opened;
                },
                isDialogOpen: () => isDialogOpen()
            });
            workspaceUI.workbench.render({ tasks: state.tasks, language: state.currentLanguage,
                today: getTodayPlanDateKey(), screen: workspaceUI.screen, storageAvailable: state.storageAvailable });
        }
        function syncSettingsStatus() {
            document.getElementById('settingsVersion').textContent = CONFIG.APP.VERSION;
            syncThemePreferenceSelect();
            syncAccentChoiceControls(normalizedAccentPreference(document.documentElement.getAttribute('data-accent')));
            syncLanguageSelect();
            updateNotificationBtnUI();
            syncInstallEntry();
            syncMaintenanceStatus();
            if (state.storageAvailable) updateBackupHealthStatus().catch(handleBackgroundStorageFailure);
        }
        function syncMaintenanceStatus() {
            const section = document.getElementById('settingsCleanup');
            if (!section) return;
            const count = state.tasks.filter(task => task.completed && !task.archived).length;
            let summary = document.getElementById('maintenanceStatus');
            if (!summary) {
                summary = document.createElement('p');
                summary.id = 'maintenanceStatus';
                summary.className = 'settings-inline-status';
                summary.setAttribute('role', 'status');
                section.prepend(summary);
            }
            summary.textContent = count ? utils.translate('dataReview.maintenanceCount').replace('{count}', count)
                : utils.translate('dataReview.maintenanceEmpty');
            for (const id of ['archiveCompletedBtn', 'clearCompletedBtn']) {
                const button = document.getElementById(id);
                if (!button) continue;
                button.disabled = !state.storageAvailable || count === 0;
                button.setAttribute('aria-disabled', String(button.disabled));
                button.setAttribute('aria-describedby', 'maintenanceStatus');
            }
        }

        function syncWorkspaceViewNavigation() {
            const host = document.getElementById('workspaceViewNavHost');
            if (DOM.viewSwitcher.parentElement !== host) host.append(DOM.viewSwitcher);
            host.hidden = workspaceUI.screen !== 'tasks' || workspaceUI.planning;
        }
        function syncWorkspaceKeyboard() {
            const viewport = window.visualViewport;
            const mobile = !window.matchMedia('(min-width: 780px)').matches;
            const editing = isEditableElement(document.activeElement);
            if (!editing || !workspaceUI.viewportHeight) workspaceUI.viewportHeight = Math.max(window.innerHeight, viewport?.height || 0);
            const keyboard = Boolean(mobile && editing && viewport && viewport.height < workspaceUI.viewportHeight - 150);
            document.body.classList.toggle('workspace-keyboard-open', keyboard);
        }
        function bindWorkspaceEvents() {
            DOM.openModalBtn.addEventListener('click', () => runAppAction('task.new'));
            DOM.quickCaptureBtn.addEventListener('click', () => runAppAction('capture.toggle'));
            DOM.menu.btn.addEventListener('click', handleMainMenuClick);
            document.getElementById('statsReturnBtn').addEventListener('click', () => returnToStatsDrilldown({ focus: true }));
            document.getElementById('captureCloseBtn').addEventListener('click', () => setCaptureShelf(false, { restoreFocus: true }));
            document.getElementById('captureDetailsBtn').addEventListener('click', openCaptureDetails);
            document.getElementById('planningDoneBtn').addEventListener('click', () => {
                setWorkspaceScreen('today', { focus: true });
            });
            document.getElementById('settingsDiagnosticsBtn').addEventListener('click', () => openDiagnostics(document.getElementById('settingsDiagnosticsBtn')).catch(() => utils.notify(utils.translate('help.diagnosticError'), 'error')));
            document.getElementById('settingsWorkspace').querySelector('[role="tablist"]').addEventListener('keydown', handleSettingsTabsKeydown);
            DOM.taskList.addEventListener('click', event => {
                const reset = event.target.closest('[data-reset-filters]');
                if (reset) resetWorkspaceFilters({ preserveTodayPlan: reset.dataset.resetFilters === 'today' });
            });
            document.getElementById('workspaceSettingsBtn').addEventListener('click', () => setWorkspaceScreen('settings', { focus: true }));
            document.getElementById('settingsBackBtn').addEventListener('click', () => setWorkspaceScreen(workspaceUI.lastScreen, { restoreFocus: true }));
            document.getElementById('settingsWorkspace').addEventListener('click', event => {
                const button = event.target.closest('[data-settings-section]');
                if (!button) return;
                setSettingsSection(button.dataset.settingsSection);
            });
            DOM.menu.installBtn.addEventListener('click', handleInstallAppClick);
            window.visualViewport?.addEventListener('resize', syncWorkspaceKeyboard);
            document.addEventListener('focusin', syncWorkspaceKeyboard);
            document.addEventListener('focusin', event => {
                if (workspacePageElement(workspaceUI.screen)?.contains(event.target)) workspaceUI.pageFocus[workspaceUI.screen] = captureFocusReturnTarget(event.target);
            });
            document.addEventListener('focusout', () => requestAnimationFrame(syncWorkspaceKeyboard));
            syncWorkspaceKeyboard();
            syncWorkspaceViewNavigation();
            document.getElementById('workspaceNotificationClose').addEventListener('click', () => hideNotification({ restoreFocus: true }));
            document.getElementById('notificationOpenTaskBtn').addEventListener('click', openSavedTaskFromNotification);
            DOM.notification.el.addEventListener('mouseenter', () => { state.notificationHovered = true; pauseNotificationTimer(); });
            DOM.notification.el.addEventListener('mouseleave', () => { state.notificationHovered = false; resumeNotificationTimer(); });
            DOM.notification.el.addEventListener('focusin', pauseNotificationTimer);
            DOM.notification.el.addEventListener('focusout', () => requestAnimationFrame(resumeNotificationTimer));
            document.getElementById('workspaceNavToggle').addEventListener('click', () => setWorkspaceNavigationOpen(!workspaceUI.navigationOpen));
            document.getElementById('workspaceNavBackdrop').addEventListener('click', () => setWorkspaceNavigationOpen(false, { restoreFocus: true }));
            document.querySelectorAll('[data-workbench-screen]').forEach(button => button.addEventListener('click', () => {
                const screen = button.dataset.workbenchScreen;
                if (screen === 'review') setViewMode('stats');
                else setWorkspaceScreen(screen, { focus: true, planning: false });
            }));
            document.getElementById('searchShortcutKey').textContent = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘ K' : 'Ctrl K';
            workspaceUI.pageScopes.tasks = captureWorkspaceScope();
            document.getElementById('workspaceProjects').addEventListener('click', event => {
                const button = event.target.closest('[data-workspace-project]');
                if (!button) return;
                try { if (openWorkbenchProject(JSON.parse(button.dataset.workspaceProject))) setWorkspaceNavigationOpen(false); } catch {}
            });
            DOM.focusModeToggleBtn.addEventListener('click', () => setWorkspaceNavigationOpen(false));
            document.getElementById('workspacePreviousMonth').addEventListener('click', () => shiftWorkspaceMonth(-1));
            document.getElementById('workspaceNextMonth').addEventListener('click', () => shiftWorkspaceMonth(1));
            document.getElementById('workspaceOpenCalendar').addEventListener('click', () => runAppAction('view.set', { view: 'calendar' }));
            document.getElementById('workspaceCalendarGrid').addEventListener('click', event => {
                const day = event.target.closest('[data-workspace-date]');
                if (day) openWorkspaceDate(day.dataset.workspaceDate);
            });
            document.getElementById('workspaceCalendarGrid').addEventListener('keydown', handleWorkspaceCalendarKeydown);
            document.getElementById('workspaceUpcomingList').addEventListener('click', event => {
                const button = event.target.closest('[data-workspace-task]');
                if (button) runAppAction('task.edit', { taskId: Number(button.dataset.workspaceTask) });
            });
            document.getElementById('workspaceScheduleToggle').addEventListener('click', openWorkspaceSchedule);
            document.getElementById('workspaceScheduleClose').addEventListener('click', closeWorkspaceSchedule);
            document.getElementById('workspaceScheduleDialog').addEventListener('close', finishWorkspaceSchedule);
            window.matchMedia('(min-width: 1180px)').addEventListener('change', syncWorkspaceOverviewVisibility);
            window.matchMedia('(min-width: 1001px)').addEventListener('change', syncSettingsTabsOrientation);
            window.matchMedia('(min-width: 780px)').addEventListener('change', () => {
                setWorkspaceNavigationOpen(false);
                syncWorkspaceViewNavigation();
                syncWorkspaceKeyboard();
                if (state.storageAvailable && state.viewMode === 'calendar') renderTaskList();
            });
            document.addEventListener('click', event => { if (!event.target.closest('.task-actions')) closeTaskActionMenus(false); });
            document.addEventListener('keydown', event => {
                if (isCompositionKey(event) || isTaskDialogOpen() || isCommandPaletteOpen() || document.getElementById('workspaceScheduleDialog').open) return;
                if (!workspaceUI.navigationOpen) return;
                if (event.key === 'Tab') trapFocusInElement(document.getElementById('workspaceSidebar'), event);
                else if (event.key === 'Escape') { event.preventDefault(); setWorkspaceNavigationOpen(false, { restoreFocus: true }); }
                else if ((event.ctrlKey || event.metaKey) && ['k', 'p', 'i', 'm', 'z'].includes(event.key.toLowerCase())) setWorkspaceNavigationOpen(false);
            });
            setWorkspaceNavigationOpen(false);
            syncWorkspaceScreen();
            syncWorkspaceOverviewVisibility();
        }
        function setWorkspaceNavigationOpen(open, { restoreFocus = false } = {}) {
            if (open && isDialogOpen()) return;
            const sidebar = document.getElementById('workspaceSidebar');
            const button = document.getElementById('workspaceNavToggle');
            const mobile = !window.matchMedia('(min-width: 780px)').matches;
            workspaceUI.navigationOpen = Boolean(open && mobile);
            document.querySelector('.container').classList.toggle('workspace-navigation-open', workspaceUI.navigationOpen);
            button.setAttribute('aria-expanded', String(workspaceUI.navigationOpen));
            sidebar.hidden = mobile && !workspaceUI.navigationOpen;
            sidebar.inert = mobile && !workspaceUI.navigationOpen;
            document.querySelector('.workspace-stage').inert = workspaceUI.navigationOpen;
            sidebar.setAttribute('aria-hidden', String(mobile && !workspaceUI.navigationOpen));
            document.getElementById('workspaceNavBackdrop').hidden = !workspaceUI.navigationOpen;
            if (workspaceUI.navigationOpen) requestAnimationFrame(() => {
                if (!workspaceUI.navigationOpen) return;
                const target = (workspaceUI.screen === 'settings' ? document.getElementById('workspaceSettingsBtn') : sidebar.querySelector('.workspace-scope-navigation [aria-current="page"]') || sidebar.querySelector('.workspace-nav-button[aria-pressed="true"]'))
                    || document.getElementById('workspaceAllTasks');
                target.focus({ preventScroll: true });
                if (document.getElementById('workspaceSidebarScroll').contains(target)) target.scrollIntoView({ block: 'nearest', inline: 'nearest' });
            });
            else if (restoreFocus || (mobile && sidebar.contains(document.activeElement))) button.focus({ preventScroll: true });
        }

        function syncWorkspaceOverviewVisibility() {
            const overview = document.getElementById('workspaceOverview');
            overview.hidden = true;
            overview.inert = true;
            document.getElementById('workspaceScheduleToggle').hidden = true;
            document.getElementById('workspaceDayStrip').hidden = true;
            document.querySelector('.workspace-content-grid').classList.remove('workspace-has-overview');
            syncWorkspaceViewNavigation();
        }
        function openWorkspaceSchedule() {
            const dialog = document.getElementById('workspaceScheduleDialog');
            if (dialog.open || !canRunAppAction('view.set')) return;
            beginDialogFeedbackContext();
            workspaceUI.scheduleOpener = document.activeElement;
            workspaceUI.scheduleOpen = true;
            document.getElementById('workspaceScheduleCalendarHost').appendChild(document.querySelector('.workspace-mini-calendar'));
            dialog.showModal();
            document.getElementById('workspaceScheduleToggle').setAttribute('aria-expanded', 'true');
            syncPageModalOpenState();
            requestAnimationFrame(() => document.getElementById('workspaceCalendarGrid').querySelector('[aria-current="date"]')?.focus());
        }
        function closeWorkspaceSchedule() {
            const dialog = document.getElementById('workspaceScheduleDialog');
            if (dialog.open) dialog.close();
        }
        function finishWorkspaceSchedule() {
            const calendar = document.querySelector('.workspace-mini-calendar');
            if (calendar) document.getElementById('workspaceOverview').prepend(calendar);
            workspaceUI.scheduleOpen = false;
            document.getElementById('workspaceScheduleToggle').setAttribute('aria-expanded', 'false');
            syncPageModalOpenState();
            if (workspaceUI.scheduleOpener?.isConnected && isFocusableReturnElement(workspaceUI.scheduleOpener)) workspaceUI.scheduleOpener.focus({ preventScroll: true });
            workspaceUI.scheduleOpener = null;
            syncWorkspaceOverviewVisibility();
        }
        function syncWorkspace() {
            if (!state.translations[state.currentLanguage]) return;
            if (state.viewMode !== 'list') workspaceUI.planning = false;
            syncStatsDrilldownReturn();
            const activeTasks = state.tasks.filter(task => !task.archived);
            const visibleTasks = state.storageAvailable ? state.tasks.filter(isTaskVisible) : [];
            const count = state.viewMode === 'stats' ? getStatsScopeTasks().length : visibleTasks.length;
            const scope = normalizeProjectFilter(state.projectFilter);
            const title = workspaceUI.planning ? utils.translate('v5.planning.title') : workspaceUI.screen === 'review' ? utils.translate('v5.nav.review') : state.focusMode ? utils.translate('focus.title') : scope.kind === 'all' ? utils.translate('workspace.allTasks') : getProjectFilterLabel(scope);
            document.getElementById('workspaceTitle').textContent = title;
            document.getElementById('tasksWorkspace').dataset.planning = String(workspaceUI.planning);
            document.getElementById('planningDoneBtn').hidden = !workspaceUI.planning;
            const countText = translateCount('workspace.taskCount', count).replace('{count}', count);
            document.getElementById('workspaceSummary').textContent = countText;
            document.getElementById('workspaceDayStrip').hidden = true;
            document.querySelector('.workspace-list-footer').hidden = state.viewMode === 'stats';
            document.getElementById('filterDropdown').hidden = state.viewMode === 'stats';
            document.getElementById('sortDropdown').hidden = state.viewMode !== 'list';
            DOM.batchModeBtn.hidden = state.viewMode === 'stats';
            DOM.batchToolbar.hidden = !state.batchMode || state.viewMode === 'stats';
            document.body.dataset.taskView = state.viewMode;
            syncFilterToggleSummary();
            document.getElementById('workspaceAllCount').textContent = String(activeTasks.length);
            const all = document.getElementById('workspaceAllTasks');
            const allSelected = workspaceUI.screen === 'tasks';
            all.classList.toggle('active', allSelected);
            all.removeAttribute('aria-current');
            all.setAttribute('aria-pressed', String(allSelected));
            const completed = activeTasks.filter(task => task.completed).length;
            document.getElementById('workspaceCompletionSummary').textContent = translateCount('focus.summary', activeTasks.length).replace('{completed}', completed).replace('{total}', activeTasks.length);
            syncWorkspaceProjects(activeTasks);
            syncWorkspaceCalendar(visibleTasks);
            syncWorkspaceUpcoming(visibleTasks);
            syncWorkspaceOverviewVisibility();
            syncPrimaryNavigation();
            syncWorkbenchPages();
            if (workspaceUI.captureOpen) syncCapturePreview();
            DOM.focusModeToggleBtn.hidden = workspaceUI.screen !== 'tasks';
        }
        function workspaceProjectTone(value) {
            let hash = 2166136261;
            for (const character of String(value || '')) hash = Math.imul(hash ^ character.codePointAt(0), 16777619) >>> 0;
            return hash % 3;
        }
        function syncWorkspaceProjects(tasks) {
            const counts = new Map();
            tasks.forEach(task => { const name = normalizeTaskProject(task.project); counts.set(name, (counts.get(name) || 0) + 1); });
            const scope = normalizeProjectFilter(state.projectFilter);
            const names = [...counts.keys()].filter(Boolean).sort((a, b) => a.localeCompare(b, state.currentLanguage));
            const shown = [...names];
            if (scope.kind === 'project' && !shown.includes(scope.name)) shown.push(scope.name);
            const options = shown.map(name => ({ value: { kind: 'project', name }, text: name, count: counts.get(name) || 0 }));
            if (counts.has('') || scope.kind === 'unassigned') options.push({ value: { kind: 'unassigned' }, text: utils.translate('projects.none'), count: counts.get('') || 0 });
            const signature = JSON.stringify([options, scope, state.focusMode]);
            if (signature === workspaceUI.projectSignature) return;
            workspaceUI.projectSignature = signature;
            const nav = document.getElementById('workspaceProjects');
            const fragment = document.createDocumentFragment();
            options.forEach((option, index) => {
                const button = document.createElement('button');
                button.type = 'button'; button.className = 'workspace-nav-button'; button.dataset.workspaceProject = projectFilterKey(option.value);
                const dot = document.createElement('span'); dot.className = `workspace-project-dot workspace-project-tone-${workspaceProjectTone(option.value.name)}`; dot.setAttribute('aria-hidden', 'true');
                const text = document.createElement('span'); text.className = 'workspace-project-name'; text.textContent = option.text;
                const count = document.createElement('span'); count.className = 'workspace-nav-count'; count.textContent = option.count;
                const selected = !state.focusMode && projectFilterKey(scope) === projectFilterKey(option.value);
                button.classList.toggle('active', selected); button.setAttribute('aria-pressed', String(selected));
                button.append(dot, text, count); fragment.appendChild(button);
            });
            nav.replaceChildren(fragment);
            nav.closest('.workspace-sidebar-section').hidden = options.length === 0;
        }
        function syncWorkspaceCalendar(tasks) {
            const today = getCalendarTodayDate();
            const todayKey = getCalendarDateKey(today);
            const dueCounts = new Map();
            tasks.forEach(task => { if (hasTaskDueDate(task)) { const key = getTaskDueDateKey(task); dueCounts.set(key, (dueCounts.get(key) || 0) + 1); } });
            const date = document.getElementById('workspaceDate');
            date.dateTime = todayKey;
            date.textContent = new Intl.DateTimeFormat(state.currentLanguage, { month: 'long', day: 'numeric', weekday: 'short', timeZone: 'UTC' }).format(today);
            document.getElementById('workspaceDueTodayCount').textContent = String(tasks.filter(task => !task.completed && getTaskDueDateKey(task) === todayKey).length);
            const month = workspaceUI.month;
            const signature = JSON.stringify([state.currentLanguage, getCalendarDateKey(month), todayKey, workspaceUI.selectedDate, getCalendarDays(month).map(day => [getCalendarDateKey(day), dueCounts.get(getCalendarDateKey(day)) || 0])]);
            if (signature === workspaceUI.calendarSignature) return;
            workspaceUI.calendarSignature = signature;
            document.getElementById('workspaceCalendarHeading').textContent = formatCalendarMonthTitle(month);
            const weekdays = document.getElementById('workspaceCalendarWeekdays'); weekdays.textContent = '';
            getWeekdayLabels().forEach(label => { const day = document.createElement('span'); day.textContent = label; weekdays.appendChild(day); });
            const grid = document.getElementById('workspaceCalendarGrid');
            const focused = grid.contains(document.activeElement) ? document.activeElement.dataset.workspaceDate : '';
            const fragment = document.createDocumentFragment();
            getCalendarDays(month).forEach(day => {
                const key = getCalendarDateKey(day), count = dueCounts.get(key) || 0;
                const button = document.createElement('button'); button.type = 'button'; button.className = 'workspace-mini-day'; button.dataset.workspaceDate = key;
                button.textContent = String(day.getUTCDate()); button.classList.toggle('outside', day.getUTCMonth() !== month.getUTCMonth()); button.classList.toggle('has-tasks', count > 0); button.classList.toggle('selected', key === workspaceUI.selectedDate);
                button.setAttribute('aria-pressed', String(key === workspaceUI.selectedDate)); button.setAttribute('aria-label', formatCalendarDayLabel(day, count));
                if (key === todayKey) button.setAttribute('aria-current', 'date');
                fragment.appendChild(button);
            });
            grid.replaceChildren(fragment);
            if (focused) grid.querySelector(`[data-workspace-date="${focused}"]`)?.focus({ preventScroll: true });
        }
        function syncWorkspaceUpcoming(tasks) {
            const next = tasks.filter(task => !task.archived && !task.completed && hasTaskDueDate(task) && getTaskDueSortValue(task) >= Date.now()).sort((a, b) => getTaskDueSortValue(a) - getTaskDueSortValue(b)).slice(0, 3);
            const signature = JSON.stringify([state.currentLanguage, next.map(task => [task.id, task.name, task.project, task.dueAt, task.dueLocalDate, task.dueLocalTime, task.dueTimeZone])]);
            if (signature === workspaceUI.upcomingSignature) return;
            workspaceUI.upcomingSignature = signature;
            const list = document.getElementById('workspaceUpcomingList'); list.textContent = '';
            if (!next.length) { const empty = document.createElement('p'); empty.className = 'workspace-upcoming-empty'; empty.textContent = utils.translate('workspace.noUpcoming'); list.appendChild(empty); return; }
            next.forEach(task => {
                const button = document.createElement('button'); button.type = 'button'; button.className = 'workspace-upcoming-task'; button.dataset.workspaceTask = String(task.id);
                const day = parseDateKey(getTaskDueDateKey(task));
                const mark = document.createElement('span'); mark.className = 'workspace-upcoming-date';
                const month = document.createElement('small'); month.textContent = new Intl.DateTimeFormat(state.currentLanguage, { month: 'short', timeZone: 'UTC' }).format(day);
                const number = document.createElement('strong'); number.textContent = String(day.getUTCDate()); mark.append(month, number);
                const copy = document.createElement('span'); copy.className = 'workspace-upcoming-copy';
                const name = document.createElement('strong'); name.textContent = task.name;
                const due = document.createElement('span'); due.textContent = formatTaskDueDate(task);
                copy.append(name, due); button.append(mark, copy); list.appendChild(button);
            });
        }
        function shiftWorkspaceMonth(delta) {
            const month = new Date(workspaceUI.month); month.setUTCDate(1); month.setUTCMonth(month.getUTCMonth() + delta); workspaceUI.month = month;
            syncWorkspaceCalendar(state.tasks.filter(isTaskVisible));
        }
        function openWorkspaceDate(key) {
            if (!canRunAppAction('view.set')) return;
            clearStatsDrilldown();
            closeWorkspaceSchedule();
            setWorkspaceScreen('tasks');
            workspaceUI.selectedDate = key;
            workspaceUI.month = parseDateKey(key);
            state.viewMode = 'calendar'; state.focusMode = false; state.calendarMonthDate = parseDateKey(key); state.calendarDetailDateKey = key; state.calendarDetailRenderLimit = 100;
            renderTaskList(); announceTaskViewSummary();
            requestAnimationFrame(() => {
                if (focusCalendarMoreButton(key)) return;
                const target = [document.getElementById('viewTab-calendar'), DOM.openModalBtn, DOM.toolsDrawerToggleBtn, DOM.retryStorageBtn].find(isFocusableReturnElement);
                target?.focus({ preventScroll: true });
            });
        }
        function handleWorkspaceCalendarKeydown(event) {
            const button = event.target.closest('[data-workspace-date]');
            const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
            if (!button || !delta) return;
            event.preventDefault(); const day = parseDateKey(button.dataset.workspaceDate); day.setUTCDate(day.getUTCDate() + delta); const key = getCalendarDateKey(day);
            let target = document.querySelector(`[data-workspace-date="${key}"]`);
            if (!target) { workspaceUI.month = day; syncWorkspaceCalendar(state.tasks.filter(isTaskVisible)); target = document.querySelector(`[data-workspace-date="${key}"]`); }
            target?.focus();
        }
        function closeTaskActionMenus(restoreFocus = false) {
            DOM.taskList?.querySelectorAll('.task-action-menu:not([hidden])').forEach(menu => {
                menu.hidden = true; const button = menu.parentElement.querySelector('.task-more-toggle'); button?.setAttribute('aria-expanded', 'false'); if (restoreFocus) button?.focus();
            });
        }
        function toggleTaskActionMenu(button) {
            const menu = button.parentElement.querySelector('.task-action-menu'); if (!menu) return;
            const opening = menu.hidden; closeTaskActionMenus(false); if (!opening) return;
            menu.hidden = false; button.setAttribute('aria-expanded', 'true');
            positionTaskActionMenu(button, menu);
            menu.querySelector('button:not([hidden]):not([disabled])')?.focus({ preventScroll: true });
        }
        function positionTaskActionMenu(button, menu) {
            const margin = 8, gap = 4;
            const width = document.documentElement.clientWidth, height = window.innerHeight;
            menu.style.top = '0px'; menu.style.left = 'auto'; menu.style.right = '0px';
            menu.style.maxHeight = `${Math.max(0, height - margin * 2)}px`;
            menu.scrollTop = 0;
            const trigger = button.getBoundingClientRect();
            const parent = menu.offsetParent.getBoundingClientRect();
            const naturalHeight = menu.getBoundingClientRect().height;
            const above = Math.max(0, trigger.top - margin - gap);
            const below = Math.max(0, height - margin - trigger.bottom - gap);
            const placeAbove = naturalHeight > below && above > below;
            menu.style.maxHeight = `${placeAbove ? above : below}px`;
            const bounds = menu.getBoundingClientRect();
            const top = Math.max(margin, Math.min(placeAbove ? trigger.top - gap - bounds.height : trigger.bottom + gap, height - margin - bounds.height));
            const left = Math.max(margin, Math.min(trigger.right - bounds.width, width - margin - bounds.width));
            menu.style.top = `${top - parent.top}px`; menu.style.left = `${left - parent.left}px`; menu.style.right = 'auto';
        }
        function handleTaskActionMenuKeydown(event) {
            const menu = event.target.closest('.task-action-menu'); if (!menu || isCompositionKey(event)) return;
            if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeTaskActionMenus(true); return; }
            if (event.key === 'Tab') { const button = menu.parentElement.querySelector('.task-more-toggle'); closeTaskActionMenus(false); button?.focus(); return; }
            if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault(); const buttons = [...menu.querySelectorAll('button')].filter(button => !button.hidden && !button.disabled); if (!buttons.length) return;
            const current = buttons.indexOf(document.activeElement); let next = current;
            if (event.key === 'Home') next = 0; else if (event.key === 'End') next = buttons.length - 1; else next = (current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
            buttons[next].focus();
        }

        function cacheDOM() {
            DOM.taskList = document.getElementById('taskList');
            DOM.taskPagination = document.getElementById('taskPagination');
            DOM.taskPaginationSummary = document.getElementById('taskPaginationSummary');
            DOM.loadMoreTasksBtn = document.getElementById('loadMoreTasksBtn');
            DOM.taskTemplate = document.getElementById('task-template');
            DOM.taskTagSuggestions = document.getElementById('taskTagSuggestions');
            DOM.viewSwitcher = document.getElementById('viewSwitcher');
            DOM.themeBtn = document.getElementById('themeToggleBtn');
            DOM.accentSelect = document.getElementById('accentSelect');
            DOM.languageSelect = document.getElementById('languageSelect');
            DOM.backToTopBtn = document.getElementById('backToTopBtn');
            DOM.storageUnavailableBanner = document.getElementById('storageUnavailableBanner');
            DOM.retryStorageBtn = document.getElementById('retryStorageBtn');
            DOM.emergencyBackupBtn = document.getElementById('emergencyBackupBtn');
            DOM.taskDraftRecoveryBanner = document.getElementById('taskDraftRecoveryBanner');
            DOM.taskDraftRecoveryDownloadBtn = document.getElementById('taskDraftRecoveryDownloadBtn');
            DOM.taskDraftRecoveryRestoreBtn = document.getElementById('taskDraftRecoveryRestoreBtn');
            DOM.taskDraftRecoveryDiscardBtn = document.getElementById('taskDraftRecoveryDiscardBtn');
            DOM.clearRecoveryBtn = document.getElementById('clearRecoveryBtn');
            DOM.toolsDrawer = document.getElementById('toolsDrawer');
            DOM.toolsDrawerContent = document.getElementById('toolsDrawerContent');
            DOM.toolsDrawerInlineAnchor = document.getElementById('toolsDrawerInlineAnchor');
            DOM.toolsDrawerToggleBtn = document.getElementById('toolsDrawerToggleBtn');
            DOM.toolsDrawerPinBtn = document.getElementById('toolsDrawerPinBtn');
            DOM.mobileFiltersDialog = document.getElementById('mobileFiltersDialog');
            DOM.mobileFiltersBody = document.getElementById('mobileFiltersBody');
            DOM.mobileFiltersTitle = document.getElementById('mobileFiltersTitle');
            DOM.mobileFiltersCloseBtn = document.getElementById('mobileFiltersCloseBtn');
            DOM.mobileFiltersDoneBtn = document.getElementById('mobileFiltersDoneBtn');
            DOM.clearCompletedBtn = document.getElementById('clearCompletedBtn');
            DOM.clearSearchBtn = document.getElementById('clearSearchBtn');
            DOM.savedViewsBar = document.getElementById('savedViewsBar');
            DOM.savedViewsList = document.getElementById('savedViewsList');
            DOM.saveSmartViewBtn = document.getElementById('saveSmartViewBtn');
            DOM.focusModeBar = document.getElementById('focusModeBar');
            DOM.focusModeSummary = document.getElementById('focusModeSummary');
            DOM.exitFocusModeBtn = document.getElementById('exitFocusModeBtn');
            DOM.focusModeToggleBtn = document.getElementById('focusModeToggleBtn');
            DOM.focusModeToggleText = document.getElementById('focusModeToggleText');
            DOM.batchToolbar = document.getElementById('batchToolbar');
            DOM.batchSelectionSummary = document.getElementById('batchSelectionSummary');
            DOM.batchSelectVisibleBtn = document.getElementById('batchSelectVisibleBtn');
            DOM.batchClearSelectionBtn = document.getElementById('batchClearSelectionBtn');
            DOM.batchFocusBtn = document.getElementById('batchFocusBtn');
            DOM.batchCompleteBtn = document.getElementById('batchCompleteBtn');
            DOM.batchArchiveBtn = document.getElementById('batchArchiveBtn');
            DOM.batchDeleteBtn = document.getElementById('batchDeleteBtn');
            DOM.batchMoveProjectBtn = document.getElementById('batchMoveProjectBtn');
            DOM.exitBatchModeBtn = document.getElementById('exitBatchModeBtn');
            DOM.notificationToggleBtn = document.getElementById('notificationToggleBtn');
            DOM.quickAddForm = document.getElementById('quickAddForm');
            DOM.quickAddInput = document.getElementById('quickAddInput');
            DOM.modal = document.getElementById('taskModal');
            DOM.form = document.getElementById('taskForm');
            DOM.openModalBtn = document.getElementById('openModalBtn');
            DOM.quickCaptureBtn = document.getElementById('quickCaptureBtn');
            DOM.batchModeBtn = document.getElementById('batchModeBtn');
            DOM.undoBtn = document.getElementById('undoBtn');
            DOM.closeModalBtn = document.getElementById('closeModalBtn');
            DOM.cancelBtn = document.getElementById('cancelBtn');
            DOM.modalTitle = document.getElementById('modalTitle');
            DOM.submitBtn = document.getElementById('submitBtn');
            DOM.deadlineFields = document.getElementById('deadlineFields');
            DOM.reminderGroup = document.getElementById('reminderGroup');
            DOM.repeatGroup = document.getElementById('repeatGroup');
            DOM.inputs = {
                name: document.getElementById('taskName'),
                desc: document.getElementById('taskDesc'),
                project: document.getElementById('taskProject'),
                tags: document.getElementById('taskTags'),
                date: document.getElementById('dueDate'),
                time: document.getElementById('dueTime'),
                noDeadline: document.getElementById('noDeadline'),
                reminderOffset: document.getElementById('reminderOffset'),
                reminderRepeat: document.getElementById('reminderRepeat'),
                repeatType: document.getElementById('repeatType'),
                repeatInterval: document.getElementById('repeatInterval'),
                repeatCustomRow: document.getElementById('repeatCustomRow'),
                repeatWeekdaysRow: document.getElementById('repeatWeekdaysRow'),
                repeatWeekdayInputs: Array.from(document.querySelectorAll('.repeat-weekday-input')),
                repeatPauseRow: document.getElementById('repeatPauseRow'),
                repeatPaused: document.getElementById('repeatPaused'),
                search: document.getElementById('searchInput'),
                subtask: document.getElementById('subtaskInput')
            };
            DOM.formGroups = document.querySelectorAll('.form-group');
            DOM.addSubtaskBtn = document.getElementById('addSubtaskBtn');
            DOM.subtaskListPreview = document.getElementById('subtaskListPreview');
            DOM.menu = {
                container: document.getElementById('menu'),
                btn: document.getElementById('openMenuBtn'),
                backupBtn: document.getElementById('backupBtn'),
                exportCsvBtn: document.getElementById('exportCsvBtn'),
                backupHealth: document.getElementById('backupHealth'),
                backupHealthText: document.getElementById('backupHealthText'),
                importBtn: document.getElementById('importBtn'),
                recoveryBtn: document.getElementById('recoveryBtn'),
                storageHealthBtn: document.getElementById('storageHealthBtn'),
                installBtn: document.getElementById('installAppBtn'),
                archiveCompletedBtn: document.getElementById('archiveCompletedBtn'),
                fileInput: document.getElementById('importFile')
            };
            DOM.dropdowns = {
                project: { container: document.getElementById('projectDropdown'), btn: document.getElementById('projectFilterBtn') },
                filter: { container: document.getElementById('filterDropdown'), btn: document.getElementById('filterBtn') },
                sort: { container: document.getElementById('sortDropdown'), btn: document.getElementById('sortBtn') }
            };
            DOM.notification = {
                el: document.getElementById('notification'),
                text: document.getElementById('notificationText'),
                undoBtn: document.getElementById('notificationUndoBtn')
            };
            DOM.updatePrompt = {
                el: document.getElementById('updatePrompt'),
                reloadBtn: document.getElementById('updateNowBtn'),
                dismissBtn: document.getElementById('dismissUpdateBtn')
            };
            DOM.commandPalette = {
                el: document.getElementById('commandPalette'),
                input: document.getElementById('commandPaletteInput'),
                list: document.getElementById('commandPaletteList'),
                closeBtn: document.getElementById('closeCommandPaletteBtn')
            };
            DOM.srStatus = document.getElementById('srStatus');
        }
        document.addEventListener('DOMContentLoaded', initApp);
        async function initApp() {
            cacheDOM();
            try {
                await loadTranslations();
                createLangButtons();
                if (!(await initializeStorageOrFallback())) return;
                await loadSettings();
                restoreToolsDrawerState();
                initLanguage();
                syncToolsDrawer();
                enhanceSelectControls();
                markDecorativeIcons();
                state.tasks = await loadNormalizedTasks();
                bindEvents();
                renderTaskList();
                await handleLaunchCapture();
                startProgressTimer();
                scheduleBackupReminder().catch(handleBackgroundStorageFailure);
                initInstallPrompt();
            } catch (error) {
                console.error('初始化失败:', error);
                utils.notify(utils.translate('messages.initDBError'), 'error');
            }
        }
        async function initializeStorageOrFallback() {
            try {
                await initPersistentStorage();
                return true;
            } catch (error) {
                console.error('本地存储初始化失败:', error);
                if (!shouldUseStorageUnavailableMode(error)) throw error;
                if (state.db) {
                    try { state.tasks = await dbActions.getAllTasks(); } catch (readError) {}
                }
                handleStorageUnavailable(error);
                return false;
            }
        }
        async function initPersistentStorage() {
            if (state.db) { state.db.close(); state.db = null; }
            await initDB();
            await verifyPersistentStorage();
            state.storageAvailable = true;
            state.storageError = null;
            state.storageFallbackTasks = [];
        }
        async function verifyPersistentStorage() {
            const stamp = new Date().toISOString();
            await dbActions.setConfig(CONFIG.STORAGE.PROBE, stamp);
            await dbActions.deleteConfig(CONFIG.STORAGE.PROBE);
        }
        function shouldUseStorageUnavailableMode(error) {
            if (!error) return !state.db;
            const name = String(error.name || '');
            const message = String(error.message || '');
            return !state.db || /SecurityError|InvalidStateError|UnknownError|QuotaExceededError|AbortError|VersionError|NotFoundError|NotAllowedError|StorageUpgradeBlockedError|StorageVersionChangedError/i.test(`${name} ${message}`);
        }
        function getStorageUnavailableLanguage() {
            if (state.eventsBound && isSupportedLanguage(state.currentLanguage)) return state.currentLanguage;
            return resolvePreferredLanguage(getBrowserLanguageCodes());
        }
        function handleStorageUnavailable(error) {
            preserveTaskDraftForRecovery();
            state.storageAvailable = false;
            state.storageError = error;
            captureStorageFallbackSnapshot();
            state.tasks = [];
            state.notificationsEnabled = false;
            state.currentLanguage = getStorageUnavailableLanguage();
            closeAllCustomSelects();
            closeAllDropdowns();
            closeMenu();
            if (isTaskDialogOpen()) closeDialog();
            if (isCommandPaletteOpen()) closeCommandPalette({ restoreFocus: false });
            initLanguage();
            enhanceSelectControls();
            markDecorativeIcons();
            restoreToolsDrawerState();
            syncToolsDrawer();
            bindStorageUnavailableEvents();
            syncStorageAvailabilityUI();
            renderStorageUnavailableState();
            utils.notify(utils.translate('storage.unavailable.short'), 'error');
            if (state.recoverableTaskDrafts.length) DOM.taskDraftRecoveryDownloadBtn.focus();
        }
        function handleStorageOperationError(error, messageKey = 'messages.task.updateError') {
            if (error?.name === 'TaskConflictError') {
                state.undoAction = null;
                syncUndoControls();
                refreshTasks().catch(handleBackgroundStorageFailure);
                utils.notify(utils.translate('storage.conflict'), 'warning');
                return true;
            }
            if (shouldUseStorageUnavailableMode(error)) {
                handleStorageUnavailable(error);
                return true;
            }
            utils.notify(utils.translate(messageKey), 'error');
            return false;
        }
        function bindStorageUnavailableEvents() {
            if (state.storageFailureEventsBound) return;
            state.storageFailureEventsBound = true;
            bindEssentialEvents();
            if (!state.eventsBound) bindToolsDrawerEvents();
            DOM.retryStorageBtn.addEventListener('click', retryStorageAvailability);
            if (DOM.emergencyBackupBtn) DOM.emergencyBackupBtn.addEventListener('click', downloadEmergencyBackup);
            DOM.clearRecoveryBtn.addEventListener('click', clearRecoveryHistoryForQuota);
        }
        function clearRecoveryHistoryForQuota() {
            if (!state.db || state.storageError?.name !== 'QuotaExceededError') return;
            utils.confirm(utils.translate('storage.clearRecovery'), utils.translate('storage.clearRecoveryConfirm'), async () => {
                try {
                    await dbActions.deleteConfig('recoveryHistory');
                    await retryStorageAvailability();
                } catch (error) {
                    utils.notify(utils.translate('storage.clearRecoveryError'), 'error');
                    return false;
                }
            });
            DOM.submitBtn.classList.add('btn-danger');
        }
        function handleBackgroundStorageFailure(error) {
            console.error('后台存储状态刷新失败:', error);
            handleStorageOperationError(error);
        }
        async function retryStorageAvailability() {
            if (!DOM.retryStorageBtn || DOM.retryStorageBtn.disabled) return;
            DOM.retryStorageBtn.disabled = true;
            DOM.retryStorageBtn.textContent = utils.translate('storage.unavailable.retrying');
            try {
                await initPersistentStorage();
                if (state.recoverableTaskDrafts.length || hasUnsavedQuickAddText()) {
                    await loadSettings();
                    state.tasks = await loadNormalizedTasks();
                    initLanguage();
                    enhanceSelectControls();
                    syncStorageAvailabilityUI();
                    renderTaskList();
                    if (state.recoverableTaskDrafts.length) {
                        utils.notify(utils.translate('drafts.recoveryReady'));
                        DOM.taskDraftRecoveryRestoreBtn.focus();
                    } else {
                        utils.notify(utils.translate('drafts.quickAddReady'));
                        setWorkspaceScreen('tasks');
                        setCaptureShelf(true, { focus: true });
                    }
                    return;
                }
                window.location.reload();
            } catch (error) {
                if ((state.recoverableTaskDrafts.length || hasUnsavedQuickAddText()) && state.storageAvailable) handleStorageUnavailable(error);
                state.storageError = error;
                DOM.retryStorageBtn.disabled = false;
                DOM.retryStorageBtn.textContent = utils.translate('storage.unavailable.retry');
                utils.notify(utils.translate('storage.unavailable.retryFailed'), 'error');
            }
        }
        function renderStorageUnavailableState() {
            if (!DOM.taskList) return;
            if (DOM.taskPagination) DOM.taskPagination.hidden = true;
            syncViewSwitcher();
            if (DOM.savedViewsBar) DOM.savedViewsBar.hidden = true;
            if (DOM.focusModeBar) DOM.focusModeBar.hidden = true;
            if (DOM.batchToolbar) DOM.batchToolbar.hidden = true;
            renderProjectFilterOptions();
            updateFilterCounts();
            syncDropdowns();
            removeInitialLoader();
            const title = utils.translate('storage.unavailable.title');
            const description = hasStorageFallbackSnapshot()
                ? translateCount('storage.unavailable.snapshotDescription', state.storageFallbackTasks.length).replace('{count}', state.storageFallbackTasks.length)
                : utils.translate('storage.unavailable.emptyDescription');
            DOM.taskList.innerHTML = `<div class="empty-state storage-empty-state"><svg class="icon icon-lg" aria-hidden="true" focusable="false"><use href="#icon-backup"></use></svg><h2>${title}</h2><p>${description}</p></div>`;
        }
        function syncStorageAvailabilityUI() {
            const unavailable = !state.storageAvailable;
            document.body.classList.toggle('storage-unavailable', unavailable);
            const captureUnavailable = unavailable && !hasUnsavedQuickAddText();
            DOM.openModalBtn.disabled = captureUnavailable;
            DOM.openModalBtn.setAttribute('aria-disabled', String(captureUnavailable));
            document.getElementById('quickCaptureBtn').disabled = captureUnavailable;
            if (DOM.storageUnavailableBanner) DOM.storageUnavailableBanner.hidden = !unavailable;
            const quickAddRetainedMessage = document.getElementById('quickAddRetainedMessage');
            if (quickAddRetainedMessage) quickAddRetainedMessage.hidden = !unavailable || !hasUnsavedQuickAddText();
            const storageMessage = document.getElementById('storageUnavailableMessage');
            if (storageMessage) {
                const key = state.storageError?.name === 'StorageUpgradeBlockedError' ? 'storage.upgradeBlocked'
                    : state.storageError?.name === 'StorageVersionChangedError' ? 'storage.versionChanged'
                    : state.storageError?.name === 'QuotaExceededError' ? 'storage.quotaExceeded'
                    : 'storage.unavailable.message';
                storageMessage.setAttribute('data-i18n', key);
                storageMessage.textContent = utils.translate(key);
            }
            if (DOM.retryStorageBtn) {
                DOM.retryStorageBtn.disabled = false;
                DOM.retryStorageBtn.textContent = utils.translate('storage.unavailable.retry');
            }
            if (DOM.emergencyBackupBtn) {
                const canExportSnapshot = unavailable && hasStorageFallbackSnapshot();
                DOM.emergencyBackupBtn.hidden = !canExportSnapshot;
                DOM.emergencyBackupBtn.disabled = !canExportSnapshot;
            }
            DOM.clearRecoveryBtn.hidden = !unavailable || state.storageError?.name !== 'QuotaExceededError' || !state.db;
            const controls = [
                document.getElementById('captureDetailsBtn'),
                DOM.notificationToggleBtn,
                DOM.batchModeBtn,
                DOM.undoBtn,
                DOM.quickAddInput,
                DOM.quickAddForm?.querySelector('button[type="submit"]'),
                DOM.saveSmartViewBtn,
                document.getElementById('statsReturnBtn'),
                DOM.focusModeToggleBtn,
                DOM.exitFocusModeBtn,
                DOM.batchSelectVisibleBtn,
                DOM.batchClearSelectionBtn,
                DOM.batchFocusBtn,
                DOM.batchCompleteBtn,
                DOM.batchArchiveBtn,
                DOM.batchDeleteBtn,
                DOM.batchMoveProjectBtn,
                DOM.exitBatchModeBtn,
                DOM.languageSelect,
                DOM.inputs.search,
                DOM.clearSearchBtn,
                DOM.menu.backupBtn,
                DOM.menu.exportCsvBtn,
                DOM.menu.importBtn,
                DOM.menu.recoveryBtn,
                DOM.menu.storageHealthBtn,
                document.getElementById('savedViewsTransferBtn'),
                document.getElementById('savedViewsImportFile'),
                DOM.menu.fileInput,
                DOM.menu.archiveCompletedBtn,
                DOM.clearCompletedBtn,
                DOM.dropdowns.project?.btn,
                DOM.dropdowns.filter?.btn,
                DOM.dropdowns.sort?.btn,
                ...Array.from(DOM.viewSwitcher?.querySelectorAll('.view-tab') || [])
            ];
            controls.filter(Boolean).forEach(control => {
                control.disabled = unavailable;
                control.setAttribute('aria-disabled', String(unavailable));
            });
            setQuickAddSaving(state.quickAddSaving);
            syncUndoControls();
            syncTaskDraftRecoveryUI();
            syncMaintenanceStatus();
        }
        function ensureStorageAvailable(options = {}) {
            if (state.storageAvailable) return true;
            syncStorageAvailabilityUI();
            if (options.notify !== false) utils.notify(utils.translate('storage.unavailable.actionsDisabled'), 'warning');
            return false;
        }
        const STORAGE_GATED_ACTIONS = new Set([
            'archive.completed',
            'batch.clearSelection',
            'batch.selectVisible',
            'batch.toggle',
            'batch.update',
            'capture.toggle',
            'command.open',
            'data.backup',
            'data.csv',
            'data.import.file',
            'data.import.open',
            'data.recovery',
            'data.health',
            'dropdown.open',
            'dropdown.toggle',
            'filter.set',
            'focus.enter',
            'focus.exit',
            'focus.toggle',
            'language.switch',
            'notifications.toggle',
            'order.save',
            'project.filter',
            'project.rename',
            'quickAdd.focus',
            'savedView.apply',
            'savedView.delete',
            'savedView.promptSave',
            'savedView.transfer',
            'savedView.export',
            'savedView.importFile',
            'search.clear',
            'search.focus',
            'sort.set',
            'subtask.toggle',
            'task.action',
            'task.edit',
            'task.new',
            'task.quickAddSubmit',
            'task.save',
            'tasks.clearCompleted',
            'undo.perform',
            'view.set'
        ]);
        function canRunAppAction(action, options = {}) {
            if (action === 'capture.toggle' && hasUnsavedQuickAddText()) return true;
            if (action === 'task.new' && !state.storageAvailable && hasUnsavedQuickAddText()) {
                setCaptureShelf(true, { focus: true });
                return false;
            }
            if (!STORAGE_GATED_ACTIONS.has(action)) return true;
            if (state.storageAvailable) return true;
            if (options.closeSurfaces !== false) closeStorageBlockedSurfaces();
            ensureStorageAvailable({ notify: options.notify });
            return false;
        }
        function closeStorageBlockedSurfaces() {
            closeMenu();
            closeAllDropdowns();
            closeAllCustomSelects();
            if (isCommandPaletteOpen()) closeCommandPalette({ restoreFocus: false });
            if (isTaskDialogOpen()) closeDialog();
        }
        function runAppAction(action, payload = {}, options = {}) {
            if (DOM.mobileFiltersDialog?.open && ![
                'dropdown.open', 'dropdown.toggle', 'filter.set', 'project.filter', 'sort.set',
                'focus.enter', 'focus.exit', 'focus.toggle', 'tools.drawer.toggle', 'tools.drawer.pin'
            ].includes(action)) closeMobileFilters({ restoreFocus: false });
            if (!canRunAppAction(action, options)) return false;
            if (['filter.set', 'project.filter', 'savedView.apply', 'focus.enter', 'focus.exit', 'focus.toggle'].includes(action)) clearStatsDrilldown();
            if (['focus.enter', 'focus.exit', 'focus.toggle'].includes(action)) setWorkspaceScreen('tasks', { render: false });
            if (['filter.set', 'project.filter', 'search.clear', 'search.focus', 'sort.set'].includes(action)
                && !['tasks', 'review'].includes(workspaceUI.screen)) setWorkspaceScreen('tasks', { render: false });
            switch (action) {
                case 'capture.toggle': setCaptureShelf(!workspaceUI.captureOpen, { focus: true }); break;
                case 'archive.completed': handleArchiveCompleted(); break;
                case 'batch.clearSelection': clearBatchSelection(); break;
                case 'batch.selectVisible': selectVisibleTasksForBatch(); break;
                case 'batch.toggle': {
                    const enabled = payload.enabled ?? (workspaceUI.screen !== 'tasks' || !state.batchMode);
                    if (enabled) setWorkspaceScreen('tasks', { render: false });
                    setBatchMode(enabled);
                    break;
                }
                case 'batch.update': runBatchTaskUpdate(payload.batchAction); break;
                case 'command.open': openCommandPalette(); break;
                case 'data.backup': backupTasks(); break;
                case 'data.csv': exportTasksCsv(); break;
                case 'data.recovery': openRecoveryHistory(); break;
                case 'data.health': openStorageHealth(); break;
                case 'help.open': openHelp(); break;
                case 'data.import.file': importTasks(payload.file); break;
                case 'data.import.open': DOM.menu.fileInput.click(); break;
                case 'dropdown.open': openDropdownAndFocusOption(payload.dropdown, payload.key); break;
                case 'dropdown.toggle': toggleDropdown(payload.dropdown); break;
                case 'filter.set': applyTaskFilter(payload.value); break;
                case 'focus.enter': enterFocusMode(); break;
                case 'focus.exit': exitFocusMode(); break;
                case 'focus.toggle': toggleFocusMode(); break;
                case 'language.switch': switchLanguage(payload.code); break;
                case 'menu.toggle': toggleMainMenu(); break;
                case 'notifications.toggle':
                    if (!supportsNotifications() || Notification.permission === 'denied') openNotificationHelp();
                    else toggleNotifications().catch(handleNotificationToggleError);
                    break;
                case 'order.save': saveNewOrder(); break;
                case 'project.filter': applyProjectFilter(payload.value, payload.options); break;
                case 'project.rename': promptProjectRename(payload.name, payload.returnTarget); break;
                case 'quickAdd.focus': setCaptureShelf(true, { focus: true }); break;
                case 'savedView.apply': applySavedView(payload.id); break;
                case 'savedView.delete': deleteSavedView(payload.id).catch(error => {
                    console.error('删除保存视图失败:', error);
                    handleStorageOperationError(error, 'savedViews.updateError');
                }); break;
                case 'savedView.promptSave': promptSaveSmartView(); break;
                case 'savedView.transfer': openSavedViewsTransfer(); break;
                case 'savedView.export': exportSavedViews(); break;
                case 'savedView.importFile': importSavedViewsFile(payload.file); break;
                case 'scroll.top': scrollToTop(); break;
                case 'search.clear': clearSearchInput(payload.options || {}); break;
                case 'search.focus': expandToolsDrawerForFocus(); DOM.inputs.search.focus(); break;
                case 'sort.set': applyTaskSort(payload.value); break;
                case 'subtask.toggle': toggleSubtaskComplete(payload.taskId, payload.subtaskId); break;
                case 'task.action': runTaskAction(payload.taskAction, payload.taskId, payload.returnTarget); break;
                case 'task.edit': editTask(payload.taskId); break;
                case 'task.new': if (payload.options) openModal(null, payload.options); else openNewTaskEditor(); break;
                case 'tasks.clearCompleted': handleClearCompleted(); break;
                case 'theme.toggle': utils.toggleTheme(); break;
                case 'tools.drawer.pin': toggleToolsDrawerPin(); break;
                case 'tools.drawer.toggle': toggleToolsDrawer(); break;
                case 'undo.perform': performUndo(); break;
                case 'view.set': setViewMode(payload.view); break;
                default: return false;
            }
            return true;
        }
        function captureStorageFallbackSnapshot() {
            if (Array.isArray(state.tasks) && state.tasks.length > 0) {
                state.storageFallbackTasks = cloneTaskSnapshot(state.tasks);
            }
        }
        function hasStorageFallbackSnapshot() {
            return Array.isArray(state.storageFallbackTasks) && state.storageFallbackTasks.length > 0;
        }
        function cloneTaskSnapshot(tasks) {
            try {
                return JSON.parse(JSON.stringify(Array.isArray(tasks) ? tasks : []));
            } catch (error) {
                return Array.isArray(tasks) ? tasks.map(task => ({ ...task })) : [];
            }
        }
        function confirmTaskChanges(title, message, onConfirm) {
            const returnTarget = captureFocusReturnTarget();
            const expectedRevision = state.taskRevision;
            utils.confirm(title, message, async () => {
                if (state.taskRevision !== expectedRevision) {
                    utils.notify(utils.translate('storage.staleConfirmation'), 'warning');
                    return;
                }
                return onConfirm();
            });
            state.elementToFocusOnClose = returnTarget;
        }
        function captureUndoSnapshot() {
            const snapshot = cloneTaskSnapshot(state.tasks);
            const persistedSnapshot = dbActions.readTaskSnapshot();
            persistedSnapshot.catch(() => {});
            Object.defineProperties(snapshot, {
                persistedSnapshot: { value: persistedSnapshot },
                undoTaskRevision: { value: state.taskRevision }
            });
            return snapshot;
        }
        function registerUndoSnapshot(label, beforeTasks) {
            const previousRevision = beforeTasks.undoTaskRevision;
            const revision = previousRevision + 1;
            if (state.taskRevision !== revision) {
                state.undoAction = null;
                syncUndoControls();
                return;
            }
            const before = beforeTasks.persistedSnapshot || Promise.resolve({
                tasks: cloneTaskSnapshot(beforeTasks), taskRevision: previousRevision
            });
            const after = dbActions.readTaskSnapshot();
            const snapshots = Promise.all([before, after]);
            snapshots.catch(() => {});
            state.undoAction = {
                label,
                run: async () => {
                    const [previous, saved] = await snapshots;
                    if (previous.taskRevision !== previousRevision || saved.taskRevision !== revision || revision !== state.taskRevision) {
                        throw new DOMException('Tasks changed after this action', 'TaskConflictError');
                    }
                    await dbActions.undoTaskChanges(previous.tasks, saved.tasks);
                    clearNotificationDeliveryState();
                    await refreshTasks();
                }
            };
            syncUndoControls();
        }
        async function performUndo() {
            if (!state.undoAction || !ensureStorageAvailable()) return;
            const fromControl = document.activeElement === DOM.undoBtn || document.activeElement === DOM.notification.undoBtn;
            const action = state.undoAction;
            state.undoAction = null;
            syncUndoControls();
            try {
                await action.run();
                closeMenu();
                if (fromControl && !isDialogOpen() && (document.activeElement === document.body || DOM.notification.el.contains(document.activeElement) || document.activeElement === DOM.undoBtn)) {
                    const target = (state.batchMode ? DOM.taskList.querySelector('.task-select-checkbox:not([disabled])') : null)
                        || DOM.taskList.querySelector('.task-more-toggle:not([disabled])') || DOM.openModalBtn;
                    target.focus();
                }
                utils.notify(utils.translate('undo.restored').replace('{action}', action.label));
            } catch (error) {
                console.error('撤销失败:', error);
                handleStorageOperationError(error, 'undo.error');
            }
        }
        function syncUndoControls() {
            const disabled = !state.undoAction || !state.storageAvailable;
            if (DOM.undoBtn) {
                const label = disabled
                    ? utils.translate('undo.unavailableTitle')
                    : utils.translate('undo.availableTitle').replace('{action}', state.undoAction.label);
                DOM.undoBtn.hidden = disabled;
                DOM.undoBtn.disabled = disabled;
                DOM.undoBtn.setAttribute('aria-disabled', String(disabled));
                DOM.undoBtn.setAttribute('aria-label', label);
                DOM.undoBtn.title = label;
            }
            if (DOM.notification?.undoBtn) DOM.notification.undoBtn.hidden = true;
        }
        async function loadSettings() {
            await restoreLanguageSetting();
            await restoreSavedViews();
            await restoreNotificationSetting(await dbActions.getConfig(CONFIG.STORAGE.NOTIFICATIONS));
            updateNotificationBtnUI();
            restoreNotifiedTasks();
        }
        async function restoreSavedViews() {
            state.savedViews = normalizeSavedViews(await dbActions.getConfig(CONFIG.STORAGE.SAVED_VIEWS));
        }
        async function restoreLanguageSetting() {
            const savedLang = await dbActions.getConfig(CONFIG.STORAGE.LANG);
            if (isSupportedLanguage(savedLang)) {
                state.currentLanguage = savedLang;
                return;
            }
            state.currentLanguage = resolvePreferredLanguage(getBrowserLanguageCodes());
            await dbActions.setConfig(CONFIG.STORAGE.LANG, state.currentLanguage);
        }
        function isSupportedLanguage(code) {
            return CONFIG.LANGUAGES.some(lang => lang.code === code);
        }
        function getBrowserLanguageCodes() {
            return (Array.isArray(navigator.languages) && navigator.languages.length)
                ? navigator.languages
                : [navigator.language];
        }
        function resolvePreferredLanguage(languageCodes) {
            for (const code of languageCodes) {
                const exact = findLanguageByCode(code);
                if (exact) return exact.code;
                const baseMatch = findLanguageByBase(code);
                if (baseMatch) return baseMatch.code;
            }
            return CONFIG.DEFAULTS.LANG;
        }
        function findLanguageByCode(code) {
            const normalized = normalizeLanguageCode(code);
            if (!normalized) return null;
            return CONFIG.LANGUAGES.find(lang => normalizeLanguageCode(lang.code) === normalized) || null;
        }
        function findLanguageByBase(code) {
            const base = normalizeLanguageCode(code).split('-')[0];
            if (!base) return null;
            return CONFIG.LANGUAGES.find(lang => normalizeLanguageCode(lang.code).split('-')[0] === base) || null;
        }
        function normalizeLanguageCode(code) {
            return typeof code === 'string' ? code.trim().toLowerCase() : '';
        }
        function getWebStorage(kind) {
            try {
                return window[kind];
            } catch (error) {
                return null;
            }
        }
        function safeGetStorageItem(kind, key) {
            const storage = getWebStorage(kind);
            if (!storage) return null;
            try {
                return storage.getItem(key);
            } catch (error) {
                return null;
            }
        }
        function safeSetStorageItem(kind, key, value) {
            const storage = getWebStorage(kind);
            if (!storage) return false;
            try {
                storage.setItem(key, value);
                return true;
            } catch (error) {
                return false;
            }
        }
        function safeRemoveStorageItem(kind, key) {
            const storage = getWebStorage(kind);
            if (!storage) return false;
            try {
                storage.removeItem(key);
                return true;
            } catch (error) {
                return false;
            }
        }
        function readStoredBoolean(key, fallback) {
            const value = safeGetStorageItem('localStorage', key);
            if (value === 'true') return true;
            if (value === 'false') return false;
            return fallback;
        }
        function restoreToolsDrawerState() {
            state.toolsDrawerPinned = false;
            state.toolsDrawerCollapsed = readStoredBoolean(CONFIG.STORAGE.TOOLS_DRAWER_COLLAPSED, true);
        }
        function persistToolsDrawerState() {
            safeSetStorageItem('localStorage', CONFIG.STORAGE.TOOLS_DRAWER_PINNED, String(state.toolsDrawerPinned));
            safeSetStorageItem('localStorage', CONFIG.STORAGE.TOOLS_DRAWER_COLLAPSED, String(state.toolsDrawerCollapsed));
        }
        function setToolsDrawerState(options = {}) {
            const nextPinned = typeof options.pinned === 'boolean' ? options.pinned : state.toolsDrawerPinned;
            let nextCollapsed = typeof options.collapsed === 'boolean' ? options.collapsed : state.toolsDrawerCollapsed;
            if (nextPinned) nextCollapsed = false;
            state.toolsDrawerPinned = nextPinned;
            state.toolsDrawerCollapsed = nextCollapsed;
            if (options.persist !== false) persistToolsDrawerState();
            syncToolsDrawer();
        }
        function toggleToolsDrawer() {
            if (usesMobileFiltersDialog()) {
                if (DOM.mobileFiltersDialog.open) closeMobileFilters();
                else openMobileFilters();
                return;
            }
            const nextCollapsed = !state.toolsDrawerCollapsed;
            setToolsDrawerState({
                collapsed: nextCollapsed,
                pinned: nextCollapsed ? false : state.toolsDrawerPinned
            });
        }
        function toggleToolsDrawerPin() {
            const nextPinned = !state.toolsDrawerPinned;
            setToolsDrawerState({
                pinned: nextPinned,
                collapsed: nextPinned ? false : state.toolsDrawerCollapsed
            });
        }
        function expandToolsDrawerForFocus() {
            if (usesMobileFiltersDialog()) return;
            if (state.toolsDrawerCollapsed) {
                setToolsDrawerState({ collapsed: false, persist: false });
            }
        }
        function setTranslatedControlLabel(element, key) {
            if (!element) return;
            const label = utils.translate(key);
            element.setAttribute('data-i18n-aria-label', key);
            element.setAttribute('data-i18n-title', key);
            element.setAttribute('aria-label', label);
            element.title = label;
        }
        function syncFilterToggleSummary() {
            const summary = document.getElementById('filterCurrentSummary');
            if (!summary || !DOM.toolsDrawerToggleBtn) return;
            const collapsed = usesMobileFiltersDialog() ? !DOM.mobileFiltersDialog.open : state.toolsDrawerCollapsed;
            const showStatus = state.viewMode !== 'stats' && Boolean(collapsed) && state.filter !== 'all';
            const key = state.filter === 'no-deadline' ? 'noDeadline' : state.filter;
            const label = utils.translate(`filters.${key}`);
            summary.textContent = label;
            summary.hidden = !showStatus;
        }
        function syncToolsDrawer() {
            if (!DOM.toolsDrawer || !DOM.toolsDrawerContent) return;
            const mobile = usesMobileFiltersDialog();
            if (!mobile && DOM.mobileFiltersDialog?.open) closeMobileFilters({ restoreFocus: false, sync: false });
            const sheetOpen = mobile && DOM.mobileFiltersDialog.open;
            const contentHost = sheetOpen ? DOM.mobileFiltersBody : DOM.toolsDrawerInlineAnchor?.parentElement;
            if (contentHost && DOM.toolsDrawerContent.parentElement !== contentHost) {
                if (sheetOpen) contentHost.append(DOM.toolsDrawerContent);
                else DOM.toolsDrawerInlineAnchor.after(DOM.toolsDrawerContent);
            }
            const collapsed = mobile ? !sheetOpen : Boolean(state.toolsDrawerCollapsed);
            const pinned = Boolean(state.toolsDrawerPinned);
            DOM.toolsDrawer.classList.toggle('is-collapsed', collapsed);
            DOM.toolsDrawer.classList.toggle('is-pinned', pinned);
            DOM.toolsDrawerContent.hidden = collapsed;
            DOM.toolsDrawerContent.setAttribute('aria-hidden', String(collapsed));
            if ('inert' in DOM.toolsDrawerContent) DOM.toolsDrawerContent.inert = collapsed;
            if (DOM.toolsDrawerToggleBtn) {
                DOM.toolsDrawerToggleBtn.setAttribute('aria-expanded', String(!collapsed));
                DOM.toolsDrawerToggleBtn.setAttribute('aria-controls', mobile ? 'mobileFiltersDialog' : 'toolsDrawerContent');
                if (mobile) DOM.toolsDrawerToggleBtn.setAttribute('aria-haspopup', 'dialog');
                else DOM.toolsDrawerToggleBtn.removeAttribute('aria-haspopup');
            }
            syncFilterToggleSummary();
            if (DOM.toolsDrawerPinBtn) {
                DOM.toolsDrawerPinBtn.setAttribute('aria-pressed', String(pinned));
                setTranslatedControlLabel(DOM.toolsDrawerPinBtn, pinned ? 'tools.unpin' : 'tools.pin');
            }
            if (collapsed) {
                closeAllDropdowns();
                if (DOM.toolsDrawerContent.contains(document.activeElement)) DOM.toolsDrawerToggleBtn?.focus();
            }
        }
        function usesMobileFiltersDialog() {
            return window.matchMedia('(max-width: 779px)').matches && typeof DOM.mobileFiltersDialog?.showModal === 'function';
        }
        function openMobileFilters() {
            if (!usesMobileFiltersDialog() || isDialogOpen()) return;
            closeAllDropdowns();
            closeAllCustomSelects();
            DOM.mobileFiltersBody.append(DOM.toolsDrawerContent);
            DOM.toolsDrawerContent.hidden = false;
            DOM.toolsDrawerContent.inert = false;
            DOM.toolsDrawerContent.setAttribute('aria-hidden', 'false');
            DOM.mobileFiltersDialog.showModal();
            syncToolsDrawer();
            DOM.mobileFiltersTitle.focus({ preventScroll: true });
        }
        function closeMobileFilters({ restoreFocus = true, sync = true } = {}) {
            if (!DOM.mobileFiltersDialog?.open) return;
            closeAllDropdowns();
            closeAllCustomSelects();
            DOM.mobileFiltersDialog.close();
            if (sync) syncToolsDrawer();
            if (restoreFocus && DOM.toolsDrawerToggleBtn?.isConnected) DOM.toolsDrawerToggleBtn.focus({ preventScroll: true });
        }
        function restoreNotifiedTasks() {
            try {
                const notified = safeGetStorageItem('sessionStorage', CONFIG.STORAGE.NOTIFIED_TASKS);
                if (notified) {
                    state.notifiedTasks = new Set(JSON.parse(notified));
                }
            } catch (e) { console.error('Failed to load notified tasks', e); }
        }
        function clearNotificationDeliveryState() {
            state.notifiedTasks.clear();
            state.pendingNotificationKeys.clear();
            safeRemoveStorageItem('sessionStorage', CONFIG.STORAGE.NOTIFIED_TASKS);
        }
        function clearTaskNotificationDeliveryState(taskId) {
            [...state.notifiedTasks].forEach(key => {
                if (String(key).startsWith(`${taskId}|`)) state.notifiedTasks.delete(key);
            });
            [...state.pendingNotificationKeys].forEach(key => {
                if (String(key).startsWith(`${taskId}|`)) state.pendingNotificationKeys.delete(key);
            });
            safeSetStorageItem('sessionStorage', CONFIG.STORAGE.NOTIFIED_TASKS, JSON.stringify([...state.notifiedTasks]));
        }
        function bindEvents() {
            bindGlobalEvents();
            bindToolsDrawerEvents();
            bindDialogEvents();
            bindFormEvents();
            bindSearchEvents();
            bindViewEvents();
            bindNotificationEvents();
            setupDropdowns();
            bindMenuEvents();
            bindSavedViewEvents();
            bindFocusModeEvents();
            bindBatchModeEvents();
            bindQuickAddEvents();
            bindCommandPaletteEvents();
            bindTaskListEvents();
            bindSubtaskInputEvents();
            bindSubtaskPreviewEvents();
            setupDragAndDrop();
            syncUndoControls();
            state.eventsBound = true;
        }
        function bindEssentialEvents() {
            if (state.essentialEventsBound) return;
            state.essentialEventsBound = true;
            DOM.themeBtn.addEventListener('change', () => setThemePreference(DOM.themeBtn.value));
            DOM.accentSelect.addEventListener('change', () => setAccentPreference(DOM.accentSelect.value));
            document.getElementById('workspaceThemeChoices').addEventListener('change', event => {
                if (event.target.matches('input[name="workspaceTheme"]') && event.target.checked) setAccentPreference(event.target.value);
            });
            DOM.languageSelect.addEventListener('change', () => {
                runAppAction('language.switch', { code: DOM.languageSelect.value });
                syncLanguageSelect();
            });
            bindWorkspaceEvents();
            bindUpdatePromptEvents();
            initServiceWorkerUpdates();
            bindThemePreferenceEvents();
            document.addEventListener('keydown', handleKeyboardShortcuts);
            document.addEventListener('compositionstart', e => state.composingInputs.add(e.target), true);
            document.addEventListener('compositionend', e => state.composingInputs.delete(e.target), true);
            document.getElementById('helpMenuBtn').addEventListener('click', () => runAppAction('help.open'));
            DOM.closeModalBtn.addEventListener('click', requestCloseTaskDialog);
            DOM.cancelBtn.addEventListener('click', requestCloseTaskDialog);
            DOM.modal.addEventListener('click', e => { if (e.target === DOM.modal) requestCloseTaskDialog(); });
            window.addEventListener('beforeunload', handleTaskDraftBeforeUnload);
            DOM.taskDraftRecoveryDownloadBtn.addEventListener('click', downloadRecoverableTaskDrafts);
            DOM.taskDraftRecoveryRestoreBtn.addEventListener('click', restoreRecoverableTaskDraft);
            DOM.taskDraftRecoveryDiscardBtn.addEventListener('click', discardRecoverableTaskDraft);
            DOM.form.addEventListener('focusin', e => {
                const session = state.taskFormSession;
                if (session && state.modalMode === 'form' && !session.prompt && e.target.closest('.form-group')) session.lastFocus = e.target;
            });
        }
        function bindGlobalEvents() {
            bindEssentialEvents();
            DOM.batchModeBtn.addEventListener('click', () => runAppAction('batch.toggle'));
            DOM.undoBtn.addEventListener('click', () => runAppAction('undo.perform'));
            window.addEventListener('scroll', () => DOM.backToTopBtn.classList.toggle(CONFIG.UI.CLASSES.SHOW, window.scrollY > 300));
            DOM.backToTopBtn.addEventListener('click', () => runAppAction('scroll.top'));
            document.addEventListener('click', closeCustomSelectsOnOutsideClick);
            document.addEventListener('visibilitychange', handleVisibilityChange);
        }
        function bindToolsDrawerEvents() {
            if (state.toolsDrawerEventsBound) return;
            state.toolsDrawerEventsBound = true;
            DOM.toolsDrawerToggleBtn?.addEventListener('click', () => runAppAction('tools.drawer.toggle'));
            DOM.toolsDrawerPinBtn?.addEventListener('click', () => runAppAction('tools.drawer.pin'));
            DOM.mobileFiltersCloseBtn?.addEventListener('click', () => closeMobileFilters());
            DOM.mobileFiltersDoneBtn?.addEventListener('click', () => closeMobileFilters());
            DOM.mobileFiltersDialog?.addEventListener('cancel', event => {
                event.preventDefault();
                const dropdown = Object.values(DOM.dropdowns).find(item => isElementOpen(item.container));
                if (dropdown) {
                    closeDropdown(dropdown);
                    dropdown.btn.focus();
                    return;
                }
                if (closeOpenCustomSelect(DOM.mobileFiltersDialog)) return;
                closeMobileFilters();
            });
            DOM.mobileFiltersDialog?.addEventListener('click', event => {
                if (event.target !== DOM.mobileFiltersDialog) return;
                const bounds = DOM.mobileFiltersDialog.getBoundingClientRect();
                if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeMobileFilters();
            });
            DOM.mobileFiltersDialog?.addEventListener('close', syncToolsDrawer);
            window.matchMedia('(max-width: 779px)').addEventListener('change', syncToolsDrawer);
        }
        function bindDialogEvents() {
            DOM.form.addEventListener('submit', handleTaskSave);
            DOM.form.addEventListener('invalid', event => {
                if (event.target === DOM.inputs.date) {
                    event.preventDefault();
                    showEditorFieldError(DOM.inputs.date, 'dueDateError');
                } else if (event.target === DOM.inputs.repeatInterval) {
                    event.preventDefault();
                    showEditorFieldError(DOM.inputs.repeatInterval, 'repeatIntervalError');
                }
            }, true);
        }
        function bindFormEvents() {
            bindTaskTagSuggestionEvents();
            DOM.form.addEventListener('invalid', event => {
                if (!(event.target instanceof HTMLElement)) return;
                let disclosure = event.target.closest('details');
                while (disclosure) { disclosure.open = true; disclosure = disclosure.parentElement?.closest('details'); }
            }, true);
            let pointerFocus = false;
            const releasePointerFocus = () => { pointerFocus = false; };
            DOM.form.addEventListener('pointerdown', () => { pointerFocus = true; }, true);
            DOM.form.addEventListener('keydown', releasePointerFocus, true);
            document.addEventListener('pointerup', releasePointerFocus, true);
            document.addEventListener('pointercancel', releasePointerFocus, true);
            window.addEventListener('blur', releasePointerFocus);
            DOM.inputs.noDeadline.addEventListener('change', function() {
                syncDeadlineDependentSections();
                syncReminderRepeatControl();
                syncRepeatControls();
            });
            DOM.form.addEventListener('focusin', event => {
                const target = event.target;
                if (pointerFocus) return;
                if (!target.closest('#taskEditor') || target.closest('.custom-select-menu')) return;
                requestAnimationFrame(() => {
                    if (!state.taskFormSaving && document.activeElement === target) revealEditorElement(target.closest('.repeat-weekday-option') || target);
                });
            });
            window.addEventListener('resize', () => {
                const target = document.activeElement;
                if (!target?.closest('#taskEditor')) return;
                requestAnimationFrame(() => {
                    if (!state.taskFormSaving && document.activeElement === target) revealEditorElement(target.closest('.repeat-weekday-option') || target);
                });
            });
            DOM.inputs.date.addEventListener('input', () => {
                syncEditorDatePresets();
                if (normalizeDueDateValue(DOM.inputs.date.value)) clearEditorFieldError(DOM.inputs.date, 'dueDateError');
            });
            DOM.inputs.repeatInterval.addEventListener('input', () => {
                if (isValidFormRepeatInterval()) clearEditorFieldError(DOM.inputs.repeatInterval, 'repeatIntervalError');
            });
            DOM.form.addEventListener('click', event => {
                const button = event.target.closest('[data-task-date-preset]');
                if (!button || state.modalMode !== 'form' || state.taskFormSaving) return;
                const preset = button.dataset.taskDatePreset;
                DOM.inputs.noDeadline.checked = false;
                if (preset !== 'pick') DOM.inputs.date.value = getRelativeDateKey(Number(preset));
                DOM.inputs.noDeadline.dispatchEvent(new Event('change', { bubbles: true }));
                if (preset === 'pick') {
                    DOM.inputs.date.focus();
                    try { DOM.inputs.date.showPicker?.(); } catch {}
                }
            });
            DOM.inputs.repeatWeekdayInputs.forEach(input => input.addEventListener('change', () => {
                if (getSelectedRepeatWeekdays().length) clearRepeatWeekdayError();
            }));
            DOM.inputs.reminderOffset.addEventListener('change', syncReminderRepeatControl);
            DOM.inputs.repeatType.addEventListener('change', syncRepeatControls);
        }
        const taskTagSuggestions = { items: [], active: -1 };
        function bindTaskTagSuggestionEvents() {
            const input = DOM.inputs.tags;
            input.addEventListener('input', updateTaskTagSuggestions);
            input.addEventListener('focus', updateTaskTagSuggestions);
            input.addEventListener('click', updateTaskTagSuggestions);
            input.addEventListener('blur', closeTaskTagSuggestions);
            input.addEventListener('compositionstart', closeTaskTagSuggestions);
            input.addEventListener('compositionend', updateTaskTagSuggestions);
            input.addEventListener('keydown', handleTaskTagSuggestionKeydown);
            input.addEventListener('keyup', event => {
                if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key) && !isCompositionKey(event)) updateTaskTagSuggestions();
            });
            DOM.taskTagSuggestions.addEventListener('mousedown', event => {
                if (event.target.closest('[data-tag-suggestion]')) event.preventDefault();
            });
            DOM.taskTagSuggestions.addEventListener('click', event => {
                const option = event.target.closest('[data-tag-suggestion]');
                if (option) chooseTaskTagSuggestion(Number(option.dataset.tagSuggestion));
            });
            DOM.form.addEventListener('reset', closeTaskTagSuggestions);
            DOM.form.addEventListener('scroll', positionTaskTagSuggestions, { passive: true });
            const reposition = () => requestAnimationFrame(() => {
                if (!DOM.taskTagSuggestions.hidden) revealTaskTagInput();
                positionTaskTagSuggestions();
            });
            window.addEventListener('resize', reposition);
            window.visualViewport?.addEventListener('resize', reposition);
            window.visualViewport?.addEventListener('scroll', reposition);
        }
        function getTaskTagInputToken() {
            const input = DOM.inputs.tags;
            const value = input.value;
            const caret = input.selectionStart ?? value.length;
            let start = 0;
            let quoted = false;
            let end = value.length;
            for (let index = 0; index < value.length; index += 1) {
                if (value[index] === '"') {
                    if (quoted && value[index + 1] === '"') { index += 1; continue; }
                    if (quoted || !value.slice(start, index).trim()) quoted = !quoted;
                } else if (value[index] === ',' && !quoted) {
                    if (caret <= index) { end = index; break; }
                    start = index + 1;
                }
            }
            if ((input.selectionEnd ?? caret) > end) return null;
            const raw = value.slice(start, end);
            const text = raw.trim();
            const query = text.startsWith('"') && !/^"(?:[^"]|"")*"$/.test(text)
                ? normalizeTaskTags([text.slice(1).replace(/""/g, '"')])[0] || ''
                : parseTagsInput(raw)[0] || '';
            return { start, end, raw, query };
        }
        function closeTaskTagSuggestions() {
            taskTagSuggestions.items = [];
            taskTagSuggestions.active = -1;
            DOM.taskTagSuggestions.hidden = true;
            DOM.taskTagSuggestions.replaceChildren();
            DOM.taskTagSuggestions.removeAttribute('role');
            DOM.taskTagSuggestions.removeAttribute('aria-label');
            DOM.inputs.tags.setAttribute('aria-expanded', 'false');
            DOM.inputs.tags.removeAttribute('aria-activedescendant');
        }
        function updateTaskTagSuggestions() {
            const input = DOM.inputs.tags;
            if (document.activeElement !== input || !isTaskDialogOpen() || state.modalMode !== 'form'
                || state.taskFormSaving || state.taskFormSession?.prompt || state.composingInputs.has(input)) {
                closeTaskTagSuggestions();
                return;
            }
            const token = getTaskTagInputToken();
            if (!token) { closeTaskTagSuggestions(); return; }
            const query = token.query.toLocaleLowerCase(state.currentLanguage);
            const selected = new Set(parseTagsInput(input.value.slice(0, token.start) + input.value.slice(token.end)).map(tag => tag.toLocaleLowerCase(state.currentLanguage)));
            const items = getTaskInputNames().tags.filter(tag => {
                const name = tag.toLocaleLowerCase(state.currentLanguage);
                return !selected.has(name) && name !== query && name.includes(query);
            }).sort((a, b) => a.localeCompare(b, state.currentLanguage));
            closeTaskTagSuggestions();
            if (!items.length) return;
            taskTagSuggestions.items = items;
            const fragment = document.createDocumentFragment();
            items.forEach((tag, index) => {
                const option = document.createElement('div');
                option.id = `task-tag-suggestion-${index}`;
                option.className = 'task-tag-option';
                option.dataset.tagSuggestion = String(index);
                option.setAttribute('role', 'option');
                option.setAttribute('aria-selected', 'false');
                option.textContent = tag;
                fragment.append(option);
            });
            DOM.taskTagSuggestions.append(fragment);
            DOM.taskTagSuggestions.setAttribute('role', 'listbox');
            DOM.taskTagSuggestions.setAttribute('aria-label', utils.translate('form.tags.label'));
            DOM.taskTagSuggestions.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            revealTaskTagInput();
            positionTaskTagSuggestions();
        }
        function revealTaskTagInput() {
            if (document.activeElement !== DOM.inputs.tags) return;
            revealEditorElement(DOM.inputs.tags);
            const viewport = window.visualViewport;
            if (!viewport) return;
            const input = DOM.inputs.tags.getBoundingClientRect();
            const top = viewport.offsetTop + 12;
            const bottom = viewport.offsetTop + viewport.height - 12;
            if (input.bottom > bottom) DOM.form.scrollTop += input.bottom - bottom;
            else if (input.top < top) DOM.form.scrollTop += input.top - top;
        }
        function positionTaskTagSuggestions() {
            const menu = DOM.taskTagSuggestions;
            if (menu.hidden) return;
            const input = DOM.inputs.tags.getBoundingClientRect();
            const host = DOM.inputs.tags.closest('.editor-property-tags').getBoundingClientRect();
            const form = DOM.form.getBoundingClientRect();
            const actions = DOM.form.querySelector('.dialog-actions').getBoundingClientRect();
            const viewport = window.visualViewport;
            const top = Math.max(form.top, viewport?.offsetTop || 0) + 6;
            const bottom = Math.min(form.bottom, actions.top, viewport ? viewport.offsetTop + viewport.height : innerHeight) - 6;
            const above = Math.max(0, input.top - top - 6);
            const below = Math.max(0, bottom - input.bottom - 6);
            const opensUp = below < Math.min(menu.scrollHeight, 240) && above > below;
            const available = opensUp ? above : below;
            if (available < 56) { closeTaskTagSuggestions(); return; }
            menu.style.maxHeight = `${Math.min(240, available)}px`;
            menu.style.top = opensUp ? 'auto' : `${input.bottom - host.top + 6}px`;
            menu.style.bottom = opensUp ? `${host.bottom - input.top + 6}px` : 'auto';
        }
        function handleTaskTagSuggestionKeydown(event) {
            if (isCompositionKey(event)) return;
            if (event.key === 'Escape' && !DOM.taskTagSuggestions.hidden) {
                event.preventDefault();
                event.stopPropagation();
                closeTaskTagSuggestions();
                return;
            }
            if (event.key === 'Tab') { closeTaskTagSuggestions(); return; }
            if (!['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key) || event.altKey || event.ctrlKey || event.metaKey) return;
            if (DOM.taskTagSuggestions.hidden && event.key !== 'Enter') updateTaskTagSuggestions();
            if (DOM.taskTagSuggestions.hidden) return;
            if (event.key === 'Enter') {
                if (taskTagSuggestions.active < 0) { closeTaskTagSuggestions(); return; }
                event.preventDefault();
                event.stopPropagation();
                chooseTaskTagSuggestion(taskTagSuggestions.active);
                return;
            }
            event.preventDefault();
            const length = taskTagSuggestions.items.length;
            taskTagSuggestions.active = (taskTagSuggestions.active + (event.key === 'ArrowDown' ? 1 : taskTagSuggestions.active < 0 ? 0 : -1) + length) % length;
            DOM.taskTagSuggestions.querySelectorAll('[role="option"]').forEach((option, index) => {
                option.setAttribute('aria-selected', String(index === taskTagSuggestions.active));
            });
            const active = DOM.taskTagSuggestions.children[taskTagSuggestions.active];
            DOM.inputs.tags.setAttribute('aria-activedescendant', active.id);
            active.scrollIntoView({ block: 'nearest' });
        }
        function chooseTaskTagSuggestion(index) {
            const input = DOM.inputs.tags;
            const tag = taskTagSuggestions.items[index];
            const token = getTaskTagInputToken();
            if (!tag || !token || state.composingInputs.has(input)) return;
            const leading = token.raw.match(/^\s*/)[0];
            const encoded = leading + formatTagsInput([tag]);
            const suffix = input.value.slice(token.end);
            const value = input.value.slice(0, token.start) + encoded;
            input.value = value + (suffix || ', ');
            const caret = value.length + (suffix ? 0 : 2);
            input.focus({ preventScroll: true });
            input.setSelectionRange(caret, caret);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            closeTaskTagSuggestions();
        }
        function bindSearchEvents() {
            const renderSearch = utils.debounce((screen, query) => {
                if (!state.storageAvailable || workspaceUI.screen !== screen || state.searchQuery !== query) return;
                renderTaskList();
                announceTaskViewSummary();
            }, 300);
            workspaceUI.cancelSearchRender = renderSearch.cancel;
            DOM.inputs.search.addEventListener('input', () => {
                clearStatsDrilldown();
                state.searchQuery = normalizeSearchQuery(DOM.inputs.search.value);
                syncSearchClearButton();
                renderSearch(workspaceUI.screen, state.searchQuery);
            });
            DOM.clearSearchBtn.addEventListener('click', () => runAppAction('search.clear'));
            syncSearchClearButton();
            DOM.clearCompletedBtn.addEventListener('click', () => runAppAction('tasks.clearCompleted'));
        }
        function bindViewEvents() {
            DOM.loadMoreTasksBtn.addEventListener('click', () => {
                if (!ensureStorageAvailable()) return;
                const previousIds = new Set(Array.from(DOM.taskList.querySelectorAll('.task-item'), task => task.dataset.taskId));
                state.listRenderLimit += 100;
                renderTaskList();
                const firstNewTask = Array.from(DOM.taskList.querySelectorAll('.task-item')).find(task => !previousIds.has(task.dataset.taskId));
                const target = (state.batchMode ? firstNewTask?.querySelector('.task-select-checkbox') : null) || firstNewTask?.querySelector('button:not([disabled])');
                if (target) target.focus();
            });
            DOM.viewSwitcher.addEventListener('click', (e) => {
                const tab = e.target.closest('.view-tab');
                if (!tab) return;
                runAppAction('view.set', { view: tab.dataset.view });
            });
            DOM.viewSwitcher.addEventListener('keydown', handleViewSwitcherKeydown);
        }
        function bindSavedViewEvents() {
            DOM.saveSmartViewBtn.addEventListener('click', () => runAppAction('savedView.promptSave'));
            DOM.savedViewsList.addEventListener('click', handleSavedViewListClick);
            document.getElementById('savedViewsTransferBtn').addEventListener('click', () => runAppAction('savedView.transfer'));
            document.getElementById('savedViewsImportFile').addEventListener('change', event => {
                const file = event.target.files[0];
                event.target.value = '';
                runAppAction('savedView.importFile', { file });
            });
        }
        function bindFocusModeEvents() {
            DOM.focusModeToggleBtn.addEventListener('click', () => runAppAction('focus.toggle'));
            DOM.exitFocusModeBtn.addEventListener('click', () => runAppAction('focus.exit'));
        }
        function bindBatchModeEvents() {
            DOM.batchSelectVisibleBtn.addEventListener('click', () => runAppAction('batch.selectVisible'));
            DOM.batchClearSelectionBtn.addEventListener('click', () => runAppAction('batch.clearSelection'));
            DOM.batchFocusBtn.addEventListener('click', () => runAppAction('batch.update', { batchAction: 'focus' }));
            DOM.batchCompleteBtn.addEventListener('click', () => runAppAction('batch.update', { batchAction: 'complete' }));
            DOM.batchArchiveBtn.addEventListener('click', () => runAppAction('batch.update', { batchAction: 'archive' }));
            DOM.batchDeleteBtn.addEventListener('click', () => runAppAction('batch.update', { batchAction: 'delete' }));
            DOM.batchMoveProjectBtn.addEventListener('click', () => runAppAction('batch.update', { batchAction: 'move-project' }));
            DOM.exitBatchModeBtn.addEventListener('click', () => runAppAction('batch.toggle', { enabled: false }));
            const more = document.getElementById('batchMoreActions');
            more.addEventListener('toggle', () => { if (more.open) requestAnimationFrame(positionBatchMoreActions); });
            more.addEventListener('keydown', event => {
                if (event.key !== 'Escape' || !more.open || isDialogOpen()) return;
                event.preventDefault(); event.stopPropagation(); more.open = false;
                more.querySelector('summary').focus({ preventScroll: true });
            });
            document.addEventListener('pointerdown', event => {
                if (more.open && !isDialogOpen() && !more.contains(event.target)) more.open = false;
            });
            window.addEventListener('resize', () => { if (more.open) positionBatchMoreActions(); });
            window.addEventListener('scroll', () => { if (more.open && !isDialogOpen()) more.open = false; }, { passive: true });
        }
        function positionBatchMoreActions() {
            const more = document.getElementById('batchMoreActions');
            if (!more?.open) return;
            const panel = more.querySelector('.batch-more-panel');
            const toolbar = DOM.batchToolbar.getBoundingClientRect();
            const headerBottom = document.querySelector('.workspace-topbar')?.getBoundingClientRect().bottom || 0;
            const dock = document.querySelector('.workspace-mobile-dock')?.getBoundingClientRect();
            const viewportBottom = dock && dock.width > 0 && dock.height > 0 && dock.top < window.innerHeight ? dock.top : window.innerHeight;
            const below = Math.max(0, viewportBottom - toolbar.bottom - 18);
            const above = Math.max(0, toolbar.top - Math.max(12, headerBottom) - 6);
            const opensUp = below < panel.scrollHeight && above > below;
            more.classList.toggle('opens-up', opensUp);
            panel.style.maxHeight = `${Math.max(72, Math.min(264, opensUp ? above : below))}px`;
        }
        function bindQuickAddEvents() {
            DOM.quickAddForm.addEventListener('submit', handleQuickAddSubmit);
            DOM.quickAddInput.addEventListener('input', handleQuickAddInput);
        }
        function bindCommandPaletteEvents() {
            DOM.commandPalette.closeBtn.addEventListener('click', () => closeCommandPalette());
            DOM.commandPalette.el.addEventListener('click', (e) => { if (e.target === DOM.commandPalette.el) closeCommandPalette(); });
            DOM.commandPalette.input.addEventListener('input', handleCommandPaletteSearchInput);
            DOM.commandPalette.input.addEventListener('keydown', handleCommandPaletteInputKeydown);
            DOM.commandPalette.list.addEventListener('click', handleCommandPaletteListClick);
        }
        function handleViewSwitcherKeydown(e) {
            const mobile = !window.matchMedia('(min-width: 780px)').matches;
            const previous = e.key === 'ArrowUp' ? 'ArrowUp' : 'ArrowLeft';
            const next = e.key === 'ArrowDown' ? 'ArrowDown' : 'ArrowRight';
            if (![previous, next, 'Home', 'End'].includes(e.key) || isCompositionKey(e)) return;
            const buttons = getViewTabs().filter(button => !button.disabled);
            if (!buttons.length) return;
            const current = Math.max(0, buttons.indexOf(e.target.closest('.view-tab')));
            const index = e.key === 'Home' ? 0 : e.key === 'End' ? buttons.length - 1
                : (current + (e.key === previous ? -1 : 1) + buttons.length) % buttons.length;
            e.preventDefault();
            buttons[index].focus();
            runAppAction('view.set', { view: buttons[index].dataset.view });
        }
        function getViewTabs() {
            return Array.from(DOM.viewSwitcher.querySelectorAll('.view-tab'));
        }
        function clearStatsDrilldown() {
            workspaceUI.statsDrilldown = null;
            const bar = document.getElementById('statsReturnBar');
            if (bar) bar.hidden = true;
        }
        function matchesStatsDrilldownTarget() {
            const target = workspaceUI.statsDrilldown?.target;
            return Boolean(target && state.searchQuery === target.query
                && normalizeSearchQuery(DOM.inputs.search.value) === target.query
                && projectFilterKey(state.projectFilter) === projectFilterKey(target.projectFilter)
                && state.filter === target.filter);
        }
        function syncStatsDrilldownReturn() {
            const bar = document.getElementById('statsReturnBar');
            if (!bar) return;
            if (workspaceUI.statsDrilldown && !matchesStatsDrilldownTarget()) clearStatsDrilldown();
            bar.hidden = !matchesStatsDrilldownTarget();
            const button = document.getElementById('statsReturnBtn');
            button.disabled = !state.storageAvailable;
            button.setAttribute('aria-disabled', String(button.disabled));
        }
        function returnToStatsDrilldown({ focus = false } = {}) {
            if (!matchesStatsDrilldownTarget()) { clearStatsDrilldown(); return false; }
            if (!ensureStorageAvailable()) return false;
            const origin = workspaceUI.statsDrilldown.origin;
            clearStatsDrilldown();
            setWorkspaceScreen('review', { render: false });
            DOM.inputs.search.value = origin.rawQuery;
            state.searchQuery = origin.query;
            state.projectFilter = normalizeProjectFilter(origin.projectFilter);
            state.filter = origin.filter;
            state.focusMode = false;
            syncSearchClearButton();
            setViewMode('stats');
            syncDropdowns();
            if (focus) {
                const isOriginScope = () => workspaceUI.screen === 'review' && state.viewMode === 'stats'
                    && state.searchQuery === origin.query && state.filter === origin.filter
                    && projectFilterKey(state.projectFilter) === projectFilterKey(origin.projectFilter);
                requestAnimationFrame(() => {
                    if (!isOriginScope()) return;
                    const source = origin.control;
                    const target = source && Array.from(DOM.taskList.querySelectorAll('[data-stats-action], [data-stats-filter]')).find(button =>
                        (button.dataset.statsAction || '') === source.action && (button.dataset.statsFilter || '') === source.filter
                        && (button.dataset.statsProject || '') === source.project && (button.dataset.statsDate || '') === (source.date || ''));
                    const requestedScroll = origin.scrollY || 0;
                    window.scrollTo({ top: requestedScroll, behavior: 'instant' });
                    if (isFocusableReturnElement(target)) {
                        target.focus({ preventScroll: true });
                        const rect = target.getBoundingClientRect();
                        const top = document.querySelector('.workspace-topbar').getBoundingClientRect().bottom + 12;
                        const dock = document.getElementById('workspaceMobileDock').getBoundingClientRect();
                        const bottom = dock.height && dock.top < window.innerHeight ? dock.top - 12 : window.innerHeight - 12;
                        if (rect.top < top || rect.bottom > bottom) target.scrollIntoView({ block: 'center', behavior: 'instant' });
                    } else document.getElementById('workspaceTitle').focus({ preventScroll: true });
                });
            }
            return true;
        }

        function setViewMode(viewMode) {
            if (!ensureStorageAvailable() || !['list', 'calendar', 'timeline', 'stats'].includes(viewMode)) return;
            if (viewMode === 'stats' && workspaceUI.statsDrilldown) {
                if (matchesStatsDrilldownTarget()) { returnToStatsDrilldown(); return; }
                clearStatsDrilldown();
            }
            const screen = viewMode === 'stats' ? 'review' : 'tasks';
            setWorkspaceScreen(screen, { render: false, planning: viewMode === 'list' ? null : false });
            if (state.viewMode !== viewMode) state.focusMode = false;
            state.viewMode = viewMode;
            if (viewMode === 'stats') { state.focusMode = false; state.batchMode = false; }
            if (viewMode === 'calendar') syncCalendarMonthToVisibleTasks();
            syncViewSwitcher();
            renderTaskList();
            window.scrollTo({ top: 0, behavior: 'instant' });
            announceTaskViewSummary();
        }
        function syncViewSwitcher() {
            syncWorkspaceViewNavigation();
            syncPrimaryNavigation();
            DOM.viewSwitcher.querySelectorAll('.view-tab').forEach(button => {
                const selected = button.dataset.view === state.viewMode;
                const current = selected && workspaceUI.screen === 'tasks';
                button.classList.toggle(CONFIG.UI.CLASSES.SELECTED, current);
                button.removeAttribute('aria-selected');
                button.tabIndex = 0;
                if (current) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
                if (selected && button.id) DOM.taskList.setAttribute('aria-labelledby', button.id);
                if (workspaceUI.screen === 'review' || workspaceUI.planning) DOM.taskList.setAttribute('aria-labelledby', 'workspaceTitle');
            });
        }
        function normalizeSavedViews(rawViews) {
            if (!Array.isArray(rawViews)) return [];
            const usedIds = new Set();
            return rawViews.map((view, index) => normalizeSavedView(view, index, usedIds)).filter(Boolean).slice(0, 12);
        }
        function normalizeSavedView(view, index, usedIds) {
            if (!view || typeof view !== 'object') return null;
            const id = normalizeSavedViewId(view.id, usedIds);
            const name = String(view.name || '').trim().replace(/\s+/g, ' ').slice(0, 48) || utils.translate('savedViews.defaultName').replace('{index}', index + 1);
            const snapshot = normalizeSmartViewSnapshot(view);
            const projectFilter = typeof view.projectFilter === 'string' && view.projectFilter ? view.projectFilter : snapshot.projectFilter;
            return { id, name, ...snapshot, projectFilter };
        }
        function normalizeSavedViewId(value, usedIds) {
            const base = String(value || '').trim() || `view-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
            let id = base;
            let counter = 2;
            while (usedIds.has(id)) id = `${base}-${counter++}`;
            usedIds.add(id);
            return id;
        }
        function normalizeSmartViewSnapshot(view) {
            const validFilters = new Set(['all', 'active', 'completed', 'archived', 'overdue', 'no-deadline']);
            const validSorts = new Set(['smart', 'created-desc', 'due-asc', 'alpha-asc', 'manual']);
            const validViews = new Set(['list', 'calendar', 'timeline', 'stats']);
            return {
                searchQuery: normalizeSearchQuery(view.searchQuery || ''),
                filter: validFilters.has(view.filter) ? view.filter : 'active',
                projectFilter: normalizeProjectFilter(view.projectFilter),
                sort: validSorts.has(view.sort) ? view.sort : 'smart',
                viewMode: validViews.has(view.viewMode) ? view.viewMode : 'list'
            };
        }
        function normalizeProjectFilter(value) {
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                if (value.kind === 'unassigned') return { kind: 'unassigned' };
                if (value.kind === 'project') {
                    const name = normalizeTaskProject(value.name);
                    if (name) return { kind: 'project', name };
                }
                return { kind: 'all' };
            }
            if (value === '__none__') return { kind: 'unassigned' };
            if (value === 'all' || !value) return { kind: 'all' };
            const name = normalizeTaskProject(value);
            return name ? { kind: 'project', name } : { kind: 'all' };
        }
        function isValidProjectFilter(value) {
            if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
            if (value.kind === 'all' || value.kind === 'unassigned') return Object.keys(value).length === 1;
            return value.kind === 'project' && Object.keys(value).length === 2 &&
                typeof value.name === 'string' && !!value.name && value.name === normalizeTaskProject(value.name);
        }
        function projectFilterKey(value) {
            return JSON.stringify(normalizeProjectFilter(value));
        }
        function getCurrentSmartViewSnapshot() {
            return normalizeSmartViewSnapshot({
                searchQuery: DOM.inputs.search.value,
                filter: state.filter,
                projectFilter: state.projectFilter,
                sort: state.sort,
                viewMode: state.viewMode
            });
        }
        function openSavedViewsTransfer() {
            if (!ensureStorageAvailable()) return;
            const returnTarget = captureFocusReturnTarget();
            closeMenu();
            const content = document.createElement('div');
            content.id = 'savedViewsTransferContent';
            content.className = 'help-guide';
            const views = normalizeSavedViews(state.savedViews);
            const summary = document.createElement('p');
            summary.id = 'savedViewsTransferSummary';
            summary.setAttribute('role', 'status');
            summary.hidden = views.length === 0;
            summary.textContent = utils.translate('dataReview.viewsCount').replace('{count}', views.length);
            const empty = document.createElement('p');
            empty.id = 'savedViewsTransferEmpty';
            empty.hidden = views.length !== 0;
            empty.textContent = utils.translate('dataReview.viewsEmpty');
            const actions = document.createElement('div');
            actions.className = 'help-actions';
            const exportButton = document.createElement('button');
            exportButton.id = 'savedViewsExportBtn';
            exportButton.type = 'button';
            exportButton.className = 'btn btn-secondary';
            exportButton.textContent = utils.translate('viewsTransfer.export');
            exportButton.disabled = views.length === 0;
            exportButton.addEventListener('click', () => runAppAction('savedView.export'));
            const importButton = document.createElement('button');
            importButton.id = 'savedViewsImportBtn';
            importButton.type = 'button';
            importButton.className = 'btn btn-secondary';
            importButton.textContent = utils.translate('viewsTransfer.import');
            importButton.addEventListener('click', () => document.getElementById('savedViewsImportFile').click());
            actions.append(exportButton, importButton);
            content.append(summary, empty, actions);
            utils.confirm(utils.translate('viewsTransfer.title'), content, () => {});
            DOM.cancelBtn.hidden = true;
            DOM.submitBtn.textContent = utils.translate('viewsTransfer.close');
            state.elementToFocusOnClose = returnTarget;
        }
        async function exportSavedViews() {
            if (!ensureStorageAvailable()) return;
            const button = document.getElementById('savedViewsExportBtn');
            if (button?.disabled) return;
            if (button) button.disabled = true;
            try {
                const savedViews = normalizeSavedViews(await dbActions.getConfig(CONFIG.STORAGE.SAVED_VIEWS))
                    .map(view => ({ ...view, ...normalizeSmartViewSnapshot(view) }));
                const payload = { app: 'Task Tracer', type: 'saved-views', version: '1.1', date: new Date().toISOString(), savedViews };
                payload.checksum = createTaskDataChecksum(payload);
                if (new Blob([JSON.stringify(payload, null, 2)]).size > 1024 * 1024) {
                    utils.notify(utils.translate('viewsTransfer.fileTooLarge'), 'error');
                    return;
                }
                downloadJsonPayload(payload, `task-tracer-saved-views-${payload.date.replace(/[:.]/g, '-')}.json`);
                utils.notify(translateCount('viewsTransfer.exported', savedViews.length).replace('{count}', savedViews.length));
            } catch (error) {
                handleStorageOperationError(error, 'viewsTransfer.error');
            } finally {
                if (button?.isConnected) button.disabled = false;
            }
        }
        function validateSavedViewsTransferPayload(payload) {
            const fields = ['app', 'type', 'version', 'date', 'savedViews', 'checksum'];
            if (!payload || typeof payload !== 'object' || Array.isArray(payload) || Object.keys(payload).length !== fields.length || fields.some(key => !Object.hasOwn(payload, key))) return null;
            if (payload.app !== 'Task Tracer' || payload.type !== 'saved-views' || !['1.0', '1.1'].includes(payload.version)) return null;
            if (typeof payload.date !== 'string' || Number.isNaN(Date.parse(payload.date))) return null;
            if (!Array.isArray(payload.savedViews) || payload.savedViews.length > 12 || typeof payload.checksum !== 'string' || payload.checksum !== createTaskDataChecksum(payload)) return null;
            const viewFields = ['id', 'name', 'searchQuery', 'filter', 'projectFilter', 'sort', 'viewMode'];
            const incoming = [];
            for (const view of payload.savedViews) {
                if (!view || typeof view !== 'object' || Array.isArray(view) || Object.keys(view).length !== viewFields.length || viewFields.some(key => !Object.hasOwn(view, key))) return null;
                if (typeof view.id !== 'string' || !view.id.trim() || typeof view.name !== 'string' || !view.name.trim() || view.name.length > 48) return null;
                if (typeof view.searchQuery !== 'string') return null;
                if (payload.version === '1.0') {
                    if (typeof view.projectFilter !== 'string' || !view.projectFilter.trim()) return null;
                } else if (!isValidProjectFilter(view.projectFilter)) return null;
                const snapshot = normalizeSmartViewSnapshot(view);
                if (snapshot.filter !== view.filter || snapshot.sort !== view.sort || snapshot.viewMode !== view.viewMode) return null;
                incoming.push({ ...view, name: view.name.trim().replace(/\s+/g, ' '), ...snapshot });
            }
            return incoming;
        }
        function planSavedViewsMerge(existing, incoming) {
            const merged = [...existing];
            const seen = [...existing];
            const usedIds = new Set(existing.map(view => view.id));
            let added = 0;
            let duplicate = 0;
            let capacity = 0;
            for (const view of incoming) {
                if (seen.some(current => isSameSmartView(current, view))) { duplicate++; continue; }
                seen.push(view);
                if (merged.length >= 12) { capacity++; continue; }
                merged.push(normalizeSavedView({ ...view, id: createSavedViewId() }, merged.length, usedIds));
                added++;
            }
            return { views: merged, added, duplicate, capacity };
        }
        function savedViewsPreviewSnapshot(views) {
            return stableStringify(views.map(view => ({ name: view.name, ...normalizeSmartViewSnapshot(view) })));
        }
        let savedViewsImportRequest = 0;
        async function importSavedViewsFile(file) {
            const requestId = ++savedViewsImportRequest;
            if (!file || !ensureStorageAvailable()) return;
            const source = document.getElementById('savedViewsTransferContent');
            const returnTarget = state.elementToFocusOnClose;
            const isCurrent = () => requestId === savedViewsImportRequest && isTaskDialogOpen() && state.modalMode === 'confirm' && source?.isConnected;
            if (!isCurrent()) return;
            if (file.size > 1024 * 1024) {
                utils.notify(utils.translate('viewsTransfer.fileTooLarge'), 'error');
                return;
            }
            try {
                const text = await file.text();
                if (!isCurrent()) return;
                const payload = JSON.parse(text);
                const incoming = validateSavedViewsTransferPayload(payload);
                if (!incoming) { utils.notify(utils.translate('viewsTransfer.invalid'), 'error'); return; }
                const existing = normalizeSavedViews(await dbActions.getConfig(CONFIG.STORAGE.SAVED_VIEWS));
                if (!isCurrent()) return;
                showSavedViewsImportPreview(incoming, existing, returnTarget);
            } catch (error) {
                if (!isCurrent()) return;
                if (error instanceof SyntaxError) utils.notify(utils.translate('viewsTransfer.invalid'), 'error');
                else handleStorageOperationError(error, 'viewsTransfer.error');
            }
        }
        function showSavedViewsImportPreview(incoming, existing, returnTarget) {
            const content = document.createElement('div');
            content.id = 'savedViewsImportPreview';
            const summary = document.createElement('p');
            summary.id = 'savedViewsImportSummary';
            summary.setAttribute('role', 'status');
            const list = document.createElement('ul');
            incoming.forEach(view => {
                const item = document.createElement('li');
                item.style.overflowWrap = 'anywhere';
                const filterLabel = utils.translate(`filters.${view.filter === 'no-deadline' ? 'noDeadline' : view.filter}`);
                const sortKey = { 'created-desc': 'created', 'due-asc': 'due', 'alpha-asc': 'alpha' }[view.sort] || view.sort;
                item.textContent = `${view.name} · ${view.searchQuery || '—'} · ${getProjectFilterLabel(view.projectFilter)} · ${filterLabel} · ${utils.translate(`sort.${sortKey}`)} · ${utils.translate(`views.${view.viewMode}`)}`;
                list.appendChild(item);
            });
            content.append(summary, list);
            let expected = savedViewsPreviewSnapshot(existing);
            let plan = planSavedViewsMerge(existing, incoming);
            const refreshPreview = current => {
                expected = savedViewsPreviewSnapshot(current);
                plan = planSavedViewsMerge(current, incoming);
                summary.textContent = utils.translate('viewsTransfer.previewSummary').replace('{incoming}', incoming.length).replace('{add}', plan.added).replace('{duplicate}', plan.duplicate).replace('{capacity}', plan.capacity);
                DOM.cancelBtn.hidden = !plan.added;
                DOM.submitBtn.textContent = plan.added ? translateCount('viewsTransfer.confirm', plan.added).replace('{count}', plan.added) : utils.translate('viewsTransfer.close');
            };
            utils.confirm(utils.translate('viewsTransfer.previewTitle'), content, async () => {
                if (!plan.added) return;
                try {
                    let committedPlan;
                    const committed = await dbActions.updateSavedViews(current => {
                        if (savedViewsPreviewSnapshot(current) !== expected) {
                            const error = new Error('Saved views changed after import preview');
                            error.name = 'SavedViewsPreviewChangedError';
                            error.currentViews = current;
                            throw error;
                        }
                        committedPlan = planSavedViewsMerge(current, incoming);
                        return committedPlan.views;
                    });
                    state.savedViews = committed;
                    renderSavedViews();
                    utils.notify(translateCount('viewsTransfer.imported', committedPlan.added).replace('{count}', committedPlan.added));
                } catch (error) {
                    if (error?.name === 'SavedViewsPreviewChangedError') {
                        refreshPreview(error.currentViews);
                        utils.notify(utils.translate('viewsTransfer.changed'), 'warning');
                    } else handleStorageOperationError(error, 'viewsTransfer.error');
                    return false;
                }
            });
            refreshPreview(existing);
            state.elementToFocusOnClose = returnTarget;
        }
        function promptSaveSmartView() {
            if (!ensureStorageAvailable()) return;
            const t = state.translations[state.currentLanguage];
            const matching = state.savedViews.find(view => isSameSmartView(view, getCurrentSmartViewSnapshot()));
            const wrapper = document.createElement('div');
            wrapper.className = 'confirm-details';
            const row = document.createElement('label');
            row.className = 'form-field';
            const label = document.createElement('span');
            label.textContent = t['savedViews.nameLabel'];
            const input = document.createElement('input');
            input.id = 'savedViewNameInput';
            input.type = 'text';
            input.maxLength = 48;
            input.value = matching?.name || getDefaultSavedViewName();
            input.setAttribute('aria-label', t['savedViews.nameLabel']);
            input.placeholder = t['savedViews.namePlaceholder'];
            row.append(label, input);
            wrapper.appendChild(row);
            utils.confirm(matching ? utils.translate('craft.viewUpdateTitle') : t['savedViews.saveTitle'], wrapper, async () => {
                try { return await saveSmartView(input.value); }
                catch (error) { handleStorageOperationError(error, 'savedViews.updateError'); return false; }
            });
            DOM.submitBtn.textContent = matching ? utils.translate('craft.viewUpdateAction') : t['savedViews.saveCurrent'];
            requestAnimationFrame(() => input.focus());
        }
        function getDefaultSavedViewName() {
            const t = state.translations[state.currentLanguage];
            const projectName = getProjectFilterLabel(state.projectFilter);
            const filterName = utils.translate(`filters.${state.filter === 'no-deadline' ? 'noDeadline' : state.filter}`);
            const viewName = t[`views.${state.viewMode}`] || state.viewMode;
            const query = normalizeSearchQuery(DOM.inputs.search.value);
            if (query) return t['savedViews.nameFromSearch'].replace('{query}', query);
            return `${projectName} · ${filterName} · ${viewName}`;
        }
        async function saveSmartView(name) {
            if (!ensureStorageAvailable()) return false;
            const snapshot = getCurrentSmartViewSnapshot();
            let updated = false;
            try {
                const committed = await dbActions.updateSavedViews(views => {
                    const matching = views.find(view => isSameSmartView(view, snapshot));
                    updated = Boolean(matching);
                    if (!matching && views.length >= 12) {
                        const error = new Error('Saved views limit reached');
                        error.name = 'SavedViewsLimitError';
                        error.currentViews = views;
                        throw error;
                    }
                    const usedIds = new Set(views.filter(view => view.id !== matching?.id).map(view => view.id));
                    const savedView = normalizeSavedView({ id: matching?.id || createSavedViewId(), name, ...snapshot }, views.length, usedIds);
                    return matching ? views.map(view => view.id === matching.id ? savedView : view) : [savedView, ...views];
                });
                state.savedViews = committed;
                renderSavedViews();
                utils.notify(utils.translate(updated ? 'craft.viewUpdated' : 'savedViews.saved'));
                return true;
            } catch (error) {
                if (error?.name !== 'SavedViewsLimitError') throw error;
                state.savedViews = error.currentViews;
                renderSavedViews();
                utils.notify(utils.translate('savedViews.limitReached'), 'warning');
                return false;
            }
        }
        function createSavedViewId() {
            return `view-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        }
        function isSameSmartView(a, b) {
            return a.searchQuery === b.searchQuery &&
                a.filter === b.filter &&
                projectFilterKey(a.projectFilter) === projectFilterKey(b.projectFilter) &&
                a.sort === b.sort &&
                a.viewMode === b.viewMode;
        }
        function renderSavedViews() {
            if (!DOM.savedViewsBar || !DOM.savedViewsList) return;
            DOM.savedViewsBar.hidden = !state.storageAvailable || state.savedViews.length === 0;
            DOM.savedViewsList.textContent = '';
            if (state.savedViews.length === 0) {
                DOM.savedViewsList.removeAttribute('role');
                return;
            }
            DOM.savedViewsList.setAttribute('role', 'list');
            const fragment = document.createDocumentFragment();
            state.savedViews.forEach(view => fragment.appendChild(createSavedViewChip(view)));
            DOM.savedViewsList.appendChild(fragment);
        }
        function createSavedViewChip(view) {
            const item = document.createElement('div');
            item.className = 'saved-view-chip';
            item.setAttribute('role', 'listitem');
            const apply = document.createElement('button');
            apply.type = 'button';
            apply.className = 'saved-view-apply';
            apply.dataset.savedViewId = view.id;
            const name = document.createElement('span');
            name.className = 'saved-view-name';
            name.textContent = view.name;
            apply.appendChild(name);
            const metaText = getSavedViewMeta(view);
            if (metaText) {
                const meta = document.createElement('span');
                meta.className = 'saved-view-meta';
                meta.textContent = metaText;
                apply.appendChild(meta);
            }
            apply.title = utils.translate('savedViews.applyLabel').replace('{name}', view.name);
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'saved-view-delete';
            remove.dataset.savedViewDeleteId = view.id;
            remove.setAttribute('aria-label', utils.translate('savedViews.deleteLabel').replace('{name}', view.name));
            remove.innerHTML = '<svg class="icon icon-sm" aria-hidden="true"><use href="#icon-x"></use></svg>';
            item.append(apply, remove);
            return item;
        }
        function getSavedViewMeta(view) {
            const meta = [
                getProjectFilterLabel(view.projectFilter),
                utils.translate(`filters.${view.filter === 'no-deadline' ? 'noDeadline' : view.filter}`),
                utils.translate(`views.${view.viewMode}`)
            ].filter(Boolean).join(' · ');
            return normalizeSavedViewLabel(view.name) === normalizeSavedViewLabel(meta) ? '' : meta;
        }
        function normalizeSavedViewLabel(value) {
            return String(value || '').replace(/\s+/g, '').toLowerCase();
        }
        function getProjectFilterLabel(value) {
            const scope = normalizeProjectFilter(value);
            if (scope.kind === 'all') return utils.translate('projects.all');
            if (scope.kind === 'unassigned') return utils.translate('projects.none');
            return scope.name;
        }
        function handleSavedViewListClick(e) {
            const deleteButton = e.target.closest('[data-saved-view-delete-id]');
            if (deleteButton) {
                runAppAction('savedView.delete', { id: deleteButton.dataset.savedViewDeleteId });
                return;
            }
            const applyButton = e.target.closest('[data-saved-view-id]');
            if (applyButton) { runAppAction('savedView.apply', { id: applyButton.dataset.savedViewId }); setWorkspaceNavigationOpen(false); }
        }
        function applySavedView(id) {
            if (!ensureStorageAvailable()) return;
            const view = state.savedViews.find(item => item.id === id);
            if (!view) return;
            setWorkspaceScreen(view.viewMode === 'stats' ? 'review' : 'tasks', { render: false });
            state.focusMode = false;
            Object.assign(state, normalizeSmartViewSnapshot(view));
            DOM.inputs.search.value = state.searchQuery;
            syncSearchClearButton();
            if (state.viewMode === 'calendar') syncCalendarMonthToVisibleTasks();
            renderTaskList();
            syncDropdowns();
            utils.notify(utils.translate('savedViews.applied').replace('{name}', view.name));
            announceTaskViewSummary();
        }
        async function deleteSavedView(id) {
            if (!ensureStorageAvailable()) return;
            const view = state.savedViews.find(item => item.id === id);
            if (!view) return;
            const deleteButton = Array.from(DOM.savedViewsList.querySelectorAll('.saved-view-delete'))
                .find(button => button.dataset.savedViewDeleteId === id);
            const content = document.createElement('div');
            content.id = 'savedViewDeleteConfirm';
            const name = document.createElement('strong');
            name.id = 'savedViewDeleteName';
            name.textContent = view.name;
            const parts = utils.translate('savedViews.deleteConfirmMessage').split('{name}');
            content.append(document.createTextNode(parts[0]), name, document.createTextNode(parts.slice(1).join('{name}')));
            const isCurrent = utils.confirm(utils.translate('savedViews.deleteConfirmTitle'), content, async () => {
                try {
                    let focusViewId;
                    const committed = await dbActions.updateSavedViews(views => {
                        const index = views.findIndex(item => item.id === id);
                        const remaining = views.filter(item => item.id !== id);
                        focusViewId = remaining[Math.min(Math.max(index, 0), remaining.length - 1)]?.id;
                        return remaining;
                    });
                    state.savedViews = committed;
                    renderSavedViews();
                    if (isCurrent()) {
                        const next = Array.from(DOM.savedViewsList.querySelectorAll('.saved-view-apply'))
                            .find(button => button.dataset.savedViewId === focusViewId);
                        state.elementToFocusOnClose = captureFocusReturnTarget(next || DOM.saveSmartViewBtn);
                        utils.notify(utils.translate('savedViews.deleted').replace('{name}', view.name));
                    }
                } catch (error) {
                    if (isCurrent()) handleStorageOperationError(error, 'savedViews.updateError');
                    return false;
                }
            });
            DOM.submitBtn.textContent = utils.translate('savedViews.deleteConfirmAction');
            DOM.submitBtn.classList.add('btn-danger');
            state.elementToFocusOnClose = captureFocusReturnTarget(deleteButton || DOM.saveSmartViewBtn);
            DOM.cancelBtn.focus();
        }
        function enterFocusMode() {
            if (!ensureStorageAvailable()) return;
            closeMenu();
            closeAllDropdowns();
            state.focusMode = true;
            state.viewMode = 'list';
            state.filter = 'all';
            state.projectFilter = { kind: 'all' };
            state.sort = 'smart';
            state.searchQuery = '';
            DOM.inputs.search.value = '';
            syncSearchClearButton();
            syncViewSwitcher();
            renderTaskList();
            announceTaskViewSummary();
        }
        function toggleFocusMode() {
            if (state.focusMode) exitFocusMode();
            else enterFocusMode();
        }
        function exitFocusMode() {
            if (!ensureStorageAvailable()) return;
            state.focusMode = false;
            renderTaskList();
            announceTaskViewSummary();
        }
        function syncFocusModeUI() {
            syncFocusModeButton();
            if (!DOM.focusModeBar) return;
            DOM.focusModeBar.hidden = !state.focusMode;
            if (!state.focusMode) return;
            const tasks = getTodayPlanTasks();
            const completed = tasks.filter(task => task.completed).length;
            DOM.focusModeSummary.textContent = translateCount('focus.summary', tasks.length)
                .replace('{completed}', completed)
                .replace('{total}', tasks.length);
        }
        function syncFocusModeButton() {
            if (!DOM.focusModeToggleBtn) return;
            const active = state.focusMode;
            const label = utils.translate(active ? 'focus.activeTitle' : 'focus.openTitle');
            const shortLabel = utils.translate(active ? 'focus.activeShort' : 'focus.openShort');
            DOM.focusModeToggleBtn.classList.toggle('focus-active', active);
            DOM.focusModeToggleBtn.setAttribute('aria-pressed', String(active));
            DOM.focusModeToggleBtn.setAttribute('aria-label', label);
            DOM.focusModeToggleBtn.title = label;
            if (DOM.focusModeToggleText) DOM.focusModeToggleText.textContent = shortLabel;
        }
        function getTodayPlanTasks() {
            const todayKey = getTodayPlanDateKey();
            return state.tasks.filter(task => normalizeFocusDate(task.focusDate) === todayKey && !task.archived);
        }
        function getTodayPlanDateKey() {
            return utils.formatDateInputValue();
        }
        function isTaskInTodayPlan(task) {
            return normalizeFocusDate(task.focusDate) === getTodayPlanDateKey();
        }
        function normalizeFocusDate(value) {
            return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null;
        }
        function setBatchMode(enabled) {
            if (!ensureStorageAvailable()) return;
            closeMenu();
            state.batchMode = Boolean(enabled);
            if (state.batchMode) {
                state.viewMode = 'list';
                syncViewSwitcher();
            } else {
                state.selectedTaskIds.clear();
            }
            renderTaskList();
        }
        function syncBatchModeUI() {
            if (!DOM.batchToolbar) return;
            pruneBatchSelection();
            DOM.batchToolbar.hidden = !state.batchMode || state.viewMode === 'stats';
            syncBatchModeButton();
            if (!state.batchMode) return;
            const count = state.selectedTaskIds.size;
            DOM.batchToolbar.dataset.hasSelection = String(count > 0);
            if (count === 0) document.getElementById('batchMoreActions').open = false;
            DOM.batchSelectionSummary.textContent = translateCount('batch.selected', count).replace('{count}', count);
            [DOM.batchClearSelectionBtn, DOM.batchFocusBtn, DOM.batchCompleteBtn, DOM.batchArchiveBtn, DOM.batchDeleteBtn, DOM.batchMoveProjectBtn].forEach(button => {
                button.disabled = count === 0;
            });
        }
        function syncBatchModeButton() {
            if (!DOM.batchModeBtn) return;
            const active = Boolean(state.batchMode);
            const key = active ? 'batch.activeTitle' : 'batch.menuTitle';
            const label = utils.translate(key);
            DOM.batchModeBtn.setAttribute('aria-pressed', String(active));
            DOM.batchModeBtn.setAttribute('aria-label', label);
            DOM.batchModeBtn.title = label;
        }
        function pruneBatchSelection() {
            const ids = new Set((state.batchMode ? getVisibleTasks() : state.tasks).map(task => task.id));
            [...state.selectedTaskIds].forEach(id => {
                if (!ids.has(id)) state.selectedTaskIds.delete(id);
            });
        }
        function selectVisibleTasksForBatch() {
            if (!ensureStorageAvailable() || !state.batchMode) return;
            getVisibleTasks().forEach(task => state.selectedTaskIds.add(task.id));
            renderTaskList();
            utils.announce(translateCount('batch.selected', state.selectedTaskIds.size).replace('{count}', state.selectedTaskIds.size));
        }
        function clearBatchSelection() {
            if (!ensureStorageAvailable() || !state.batchMode) return;
            state.selectedTaskIds.clear();
            renderTaskList();
            utils.announce(translateCount('batch.selected', 0).replace('{count}', 0));
        }
        function toggleBatchTaskSelection(id, selected) {
            if (!state.storageAvailable || !state.batchMode) return;
            if (selected) state.selectedTaskIds.add(id);
            else state.selectedTaskIds.delete(id);
            syncBatchModeUI();
        }
        function getSelectedBatchTasks() {
            const selected = state.selectedTaskIds;
            return state.tasks.filter(task => selected.has(task.id));
        }
        async function runBatchTaskUpdate(action) {
            if (!ensureStorageAvailable()) return;
            const selectedTasks = getSelectedBatchTasks();
            if (selectedTasks.length === 0) {
                utils.notify(utils.translate('batch.noneSelected'), 'warning');
                return;
            }
            const more = document.getElementById('batchMoreActions');
            more.open = false;
            if (action === 'move-project') { promptBatchMoveProject(selectedTasks); return; }
            if (action === 'delete') {
                const message = translateCount('batch.confirmDelete', selectedTasks.length).replace('{count}', selectedTasks.length);
                confirmTaskChanges(utils.translate('batch.delete'), message, () => applyBatchTaskUpdate(action, selectedTasks));
                DOM.submitBtn.textContent = utils.translate('batch.delete');
                DOM.submitBtn.classList.add('btn-danger');
                state.elementToFocusOnClose = captureFocusReturnTarget(more.querySelector('summary'));
                return;
            }
            await applyBatchTaskUpdate(action, selectedTasks);
        }
        function promptBatchMoveProject(selectedTasks) {
            const content = document.createElement('div');
            content.className = 'confirm-details';
            const selection = document.createElement('p');
            selection.id = 'batchMoveSelectionCount';
            selection.className = 'batch-move-count';
            selection.textContent = translateCount('batch.selected', selectedTasks.length).replace('{count}', selectedTasks.length);
            const label = document.createElement('label');
            label.className = 'form-field';
            const text = document.createElement('span');
            text.textContent = utils.translate('craft.batchProjectLabel');
            const input = document.createElement('input');
            input.id = 'batchMoveProjectInput';
            input.type = 'text';
            input.required = true;
            input.autocomplete = 'off';
            input.setAttribute('list', 'batchProjectOptions');
            input.setAttribute('aria-describedby', selection.id);
            const options = document.createElement('datalist');
            options.id = 'batchProjectOptions';
            getProjectNames().forEach(project => {
                const option = document.createElement('option');
                option.value = project;
                options.appendChild(option);
            });
            label.append(text, input);
            content.append(selection, label, options);
            confirmTaskChanges(utils.translate('craft.batchMoveTitle'), content, async () => {
                if (hasActiveComposition(DOM.form)) return false;
                const project = normalizeTaskProject(input.value);
                if (!project) {
                    utils.notify(utils.translate('craft.batchProjectRequired'), 'warning');
                    input.focus();
                    return false;
                }
                try {
                    const before = captureUndoSnapshot();
                    await dbActions.updateTasks(selectedTasks.map(task => ({ ...task, project })));
                    state.selectedTaskIds.clear();
                    await refreshTasks();
                    registerUndoSnapshot(utils.translate('craft.batchProjectUndo'), before);
                    utils.notify(translateCount('craft.batchProjectMoved', selectedTasks.length).replace('{count}', selectedTasks.length).replace('{project}', project), 'success', { undo: true });
                    return true;
                } catch (error) {
                    handleStorageOperationError(error, 'batch.error');
                    return false;
                }
            });
            DOM.submitBtn.textContent = utils.translate('craft.batchProjectAction');
            state.elementToFocusOnClose = captureFocusReturnTarget(document.querySelector('#batchMoreActions > summary'));
            input.focus();
        }
        async function applyBatchTaskUpdate(action, selectedTasks) {
            const beforeTasks = captureUndoSnapshot();
            const now = new Date().toISOString();
            let affectedCount = selectedTasks.length;
            try {
                if (action === 'delete') {
                    await dbActions.deleteTasks(selectedTasks.map(task => task.id));
                } else if (action === 'archive') {
                    await dbActions.updateTasks(selectedTasks.map(task => ({ ...task, archived: true, archivedAt: now })));
                } else if (action === 'focus') {
                    const focusDate = getTodayPlanDateKey();
                    await dbActions.updateTasks(selectedTasks.map(task => ({ ...task, focusDate })));
                } else if (action === 'complete') {
                    const completeUpdates = buildBatchCompleteTasks(selectedTasks, now);
                    if (completeUpdates.length === 0) {
                        utils.notify(utils.translate('batch.nothingToComplete'), 'warning');
                        return;
                    }
                    affectedCount = selectedTasks.filter(task => !task.completed && !task.archived).length;
                    await dbActions.updateTasks(completeUpdates);
                }
                state.selectedTaskIds.clear();
                await refreshTasks();
                registerUndoSnapshot(utils.translate(`batch.undo.${action}`), beforeTasks);
                utils.notify(translateCount(`batch.success.${action}`, affectedCount).replace('{count}', affectedCount), 'success', { undo: true });
            } catch (error) {
                console.error('批量操作失败:', error);
                handleStorageOperationError(error, 'batch.error');
            }
        }
        function buildBatchCompleteTasks(tasks, completedAt) {
            const usedIds = new Set(state.tasks.map(task => Number(task.id)).filter(Number.isFinite));
            const result = [];
            let nextOrder = getNextTaskOrder();
            tasks.forEach(task => {
                if (task.completed || task.archived) return;
                const updatedTask = { ...task, completed: true, completedAt };
                if (shouldCreateNextRepeatTask(task)) {
                    const nextTask = createNextRepeatTaskWithUsedIds(task, usedIds, nextOrder);
                    nextOrder += CONFIG.DEFAULTS.ORDER_STEP;
                    updatedTask.nextRepeatTaskId = nextTask.id;
                    result.push(nextTask);
                }
                result.push(updatedTask);
            });
            return result;
        }
        function openCommandPalette() {
            beginDialogFeedbackContext();
            if (!ensureStorageAvailable()) return;
            closeMenu();
            closeAllDropdowns();
            closeAllCustomSelects();
            state.commandPaletteReturnFocus = document.activeElement;
            DOM.commandPalette.el.hidden = false;
            syncPageModalOpenState();
            DOM.commandPalette.input.value = '';
            state.commandPaletteActiveIndex = 0;
            renderCommandPalette();
            requestAnimationFrame(() => DOM.commandPalette.input.focus());
        }
        function closeCommandPalette({ restoreFocus = true } = {}) {
            DOM.commandPalette.el.hidden = true;
            syncPageModalOpenState();
            DOM.commandPalette.input.removeAttribute('aria-activedescendant');
            DOM.commandPalette.list.removeAttribute('role');
            DOM.commandPalette.list.textContent = '';
            state.commandPaletteItems = [];
            if (restoreFocus && state.commandPaletteReturnFocus) state.commandPaletteReturnFocus.focus();
            state.commandPaletteReturnFocus = null;
        }
        function renderCommandPalette() {
            const query = normalizeCommandPaletteQuery(DOM.commandPalette.input.value);
            const items = getCommandPaletteItems().filter(item => matchesCommandPaletteItem(item, query));
            state.commandPaletteItems = items;
            state.commandPaletteActiveIndex = Math.min(state.commandPaletteActiveIndex, Math.max(0, items.length - 1));
            DOM.commandPalette.list.textContent = '';
            if (items.length === 0) {
                DOM.commandPalette.list.removeAttribute('role');
                const empty = document.createElement('div');
                empty.className = 'command-empty';
                empty.textContent = utils.translate('commandPalette.empty');
                DOM.commandPalette.list.appendChild(empty);
                DOM.commandPalette.input.removeAttribute('aria-activedescendant');
                return;
            }
            DOM.commandPalette.list.setAttribute('role', 'listbox');
            const fragment = document.createDocumentFragment();
            items.forEach((item, index) => fragment.appendChild(createCommandPaletteItem(item, index)));
            DOM.commandPalette.list.appendChild(fragment);
            syncCommandPaletteActiveItem();
        }
        function getCommandPaletteItems() {
            const t = state.translations[state.currentLanguage];
            const viewItems = ['list', 'calendar', 'timeline', 'stats'].map(view => ({
                id: `view-${view}`,
                title: t[`commandPalette.commands.view.${view}`],
                subtitle: t['commandPalette.groups.views'],
                keywords: `${view} ${t[`views.${view}`]}`,
                icon: view === 'calendar' ? 'icon-calendar' : view === 'timeline' ? 'icon-timeline' : view === 'stats' ? 'icon-chart' : 'icon-list',
                run: () => runAppAction('view.set', { view })
            }));
            const projectItems = [
                { value: { kind: 'all' }, label: t['projects.all'] },
                { value: { kind: 'unassigned' }, label: t['projects.none'] },
                ...getProjectNames().map(project => ({ value: { kind: 'project', name: project }, label: project }))
            ].map(project => ({
                id: `project-${projectFilterKey(project.value)}`,
                title: t['commandPalette.commands.project'].replace('{project}', project.label),
                subtitle: t['commandPalette.groups.projects'],
                keywords: `project p ${project.label}`,
                icon: 'icon-filter',
                run: () => runAppAction('project.filter', { value: project.value })
            }));
            const savedViewItems = state.savedViews.map(view => ({
                id: `saved-view-${view.id}`,
                title: t['commandPalette.commands.savedView'].replace('{name}', view.name),
                subtitle: t['commandPalette.groups.savedViews'],
                keywords: `saved view smart ${view.name} ${view.searchQuery}`,
                icon: 'icon-bookmark',
                run: () => runAppAction('savedView.apply', { id: view.id })
            }));
            return [
                {
                    id: 'new-task',
                    title: t['commandPalette.commands.newTask'],
                    subtitle: t['commandPalette.groups.tasks'],
                    keywords: 'new add create task 添加任务 新建任务',
                    icon: 'icon-plus',
                    run: (returnFocus) => {
                        runAppAction('task.new');
                        state.elementToFocusOnClose = captureFocusReturnTarget(returnFocus || DOM.openModalBtn);
                    }
                },
                {
                    id: 'quick-add',
                    title: t['commandPalette.commands.quickAdd'],
                    subtitle: t['commandPalette.groups.tasks'],
                    keywords: 'quick add input 快速记录 快速添加 定位快速添加',
                    icon: 'icon-plus',
                    run: () => runAppAction('quickAdd.focus')
                },
                {
                    id: 'search',
                    title: t['commandPalette.commands.search'],
                    subtitle: t['commandPalette.groups.tasks'],
                    keywords: 'find filter search',
                    icon: 'icon-filter',
                    run: () => runAppAction('search.focus')
                },
                {
                    id: 'focus-mode',
                    title: t['commandPalette.commands.focusMode'],
                    subtitle: t['commandPalette.groups.tasks'],
                    keywords: 'today plan focus',
                    icon: 'icon-target',
                    run: () => runAppAction('focus.enter')
                },
                {
                    id: 'batch-mode',
                    title: t['commandPalette.commands.batchMode'],
                    subtitle: t['commandPalette.groups.tasks'],
                    keywords: 'batch multi select',
                    icon: 'icon-check-square',
                    run: () => runAppAction('batch.toggle', { enabled: true })
                },
                {
                    id: 'undo',
                    title: t['commandPalette.commands.undo'],
                    subtitle: t['commandPalette.groups.tasks'],
                    keywords: 'undo restore',
                    icon: 'icon-undo',
                    disabled: !state.undoAction,
                    run: () => runAppAction('undo.perform')
                },
                ...viewItems,
                ...savedViewItems,
                {
                    id: 'export-backup',
                    title: t['commandPalette.commands.exportBackup'],
                    subtitle: t['commandPalette.groups.data'],
                    keywords: 'download export backup json snapshot save',
                    icon: 'icon-backup',
                    run: () => runAppAction('data.backup')
                },
                {
                    id: 'transfer-saved-views',
                    title: t['viewsTransfer.menu'],
                    subtitle: t['commandPalette.groups.data'],
                    keywords: 'saved views transfer import export json search filter layouts',
                    icon: 'icon-backup',
                    run: returnFocus => {
                        runAppAction('savedView.transfer');
                        state.elementToFocusOnClose = captureFocusReturnTarget(returnFocus || DOM.openModalBtn);
                    }
                },
                ...projectItems
            ];
        }
        function createCommandPaletteItem(item, index) {
            const button = document.createElement('button');
            button.type = 'button';
            button.id = `command-option-${index}`;
            button.className = 'command-item';
            button.setAttribute('role', 'option');
            button.setAttribute('aria-selected', 'false');
            button.dataset.index = String(index);
            button.disabled = item.disabled === true;
            const icon = document.createElement('span');
            icon.className = 'command-item-icon';
            icon.appendChild(createIcon(item.icon, 'icon icon-sm'));
            const text = document.createElement('span');
            const title = document.createElement('span');
            title.className = 'command-item-title';
            title.textContent = item.title;
            text.append(title);
            button.append(icon, text);
            return button;
        }
        function normalizeCommandPaletteQuery(value) {
            return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
        }
        function matchesCommandPaletteItem(item, query) {
            if (!query) return true;
            const haystack = [item.title, item.subtitle, item.keywords].join(' ').toLowerCase();
            return query.split(' ').every(part => haystack.includes(part));
        }
        function handleCommandPaletteInputKeydown(e) {
            if (isCompositionKey(e)) return;
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                moveCommandPaletteActive(e.key === 'ArrowDown' ? 1 : -1);
                return;
            }
            if (e.key === 'Home' || e.key === 'End') {
                e.preventDefault();
                state.commandPaletteActiveIndex = e.key === 'Home' ? 0 : Math.max(0, state.commandPaletteItems.length - 1);
                syncCommandPaletteActiveItem();
                return;
            }
            if (e.key === 'Enter') {
                e.preventDefault();
                executeCommandPaletteItem(state.commandPaletteActiveIndex);
            }
        }
        function handleCommandPaletteSearchInput() {
            state.commandPaletteActiveIndex = 0;
            renderCommandPalette();
        }
        function handleCommandPaletteListClick(e) {
            const item = e.target.closest('.command-item');
            if (!item) return;
            executeCommandPaletteItem(Number(item.dataset.index));
        }
        function moveCommandPaletteActive(delta) {
            const total = state.commandPaletteItems.length;
            if (total === 0) return;
            state.commandPaletteActiveIndex = (state.commandPaletteActiveIndex + delta + total) % total;
            syncCommandPaletteActiveItem();
        }
        function syncCommandPaletteActiveItem() {
            const options = Array.from(DOM.commandPalette.list.querySelectorAll('.command-item'));
            options.forEach((option, index) => {
                const selected = index === state.commandPaletteActiveIndex;
                option.classList.toggle(CONFIG.UI.CLASSES.SELECTED, selected);
                option.setAttribute('aria-selected', String(selected));
                if (selected) {
                    DOM.commandPalette.input.setAttribute('aria-activedescendant', option.id);
                    option.scrollIntoView({ block: 'nearest' });
                }
            });
        }
        function executeCommandPaletteItem(index) {
            const item = state.commandPaletteItems[index];
            if (!item || item.disabled) return;
            const returnFocus = state.commandPaletteReturnFocus;
            closeCommandPalette({ restoreFocus: false });
            item.run(returnFocus);
            requestAnimationFrame(() => {
                if (isDialogOpen() || isFocusableReturnElement(document.activeElement)) return;
                const viewTarget = item.id.startsWith('view-') ? document.getElementById(`viewTab-${state.viewMode}`) : null;
                const target = [viewTarget, returnFocus, document.getElementById(`viewTab-${state.viewMode}`), DOM.openModalBtn]
                    .find(isFocusableReturnElement);
                target?.focus({ preventScroll: true });
            });
        }
        function applyProjectFilter(value, { exitFocus = false } = {}) {
            if (!ensureStorageAvailable()) return;
            if (exitFocus) state.focusMode = false;
            state.projectFilter = normalizeProjectFilter(value);
            renderTaskList();
            syncDropdowns({ focusTrigger: DOM.dropdowns.project.btn });
            announceTaskViewSummary();
        }
        function applyTaskFilter(value) {
            if (!ensureStorageAvailable()) return;
            state.filter = value;
            renderTaskList();
            syncDropdowns({ focusTrigger: DOM.dropdowns.filter.btn });
            announceTaskViewSummary();
        }
        function applyTaskSort(value) {
            if (!ensureStorageAvailable()) return;
            state.sort = value;
            renderTaskList();
            syncDropdowns({ focusTrigger: DOM.dropdowns.sort.btn });
            announceTaskViewSummary();
        }
        function beginDialogFeedbackContext() {
            if (!DOM.notification?.el) return;
            hideNotification();
        }
        function pauseNotificationTimer() {
            if (!state.notificationHideTimer) return;
            state.notificationRemaining = Math.max(0, state.notificationHideDeadline - Date.now());
            clearTimeout(state.notificationHideTimer);
            state.notificationHideTimer = null;
        }
        function resumeNotificationTimer() {
            if (!DOM.notification.el.classList.contains('show') || state.notificationHideTimer || state.notificationHovered || DOM.notification.el.contains(document.activeElement)) return;
            state.notificationHideDeadline = Date.now() + state.notificationRemaining;
            state.notificationHideTimer = setTimeout(() => hideNotification(), state.notificationRemaining);
        }
        function hideNotification({ restoreFocus = false } = {}) {
            const hadFocus = DOM.notification.el.contains(document.activeElement);
            if (state.notificationHideTimer) clearTimeout(state.notificationHideTimer);
            state.notificationHideTimer = null;
            state.notificationRemaining = 0;
            state.notificationHideDeadline = 0;
            state.notificationHovered = false;
            DOM.notification.el.classList.remove('show');
            DOM.notification.undoBtn.hidden = true;
            document.getElementById('notificationOpenTaskBtn').hidden = true;
            state.notificationTaskId = null;
            if (restoreFocus && hadFocus) {
                const target = resolveFocusReturnElement(state.notificationReturnFocus);
                (isFocusableReturnElement(target) ? target : DOM.openModalBtn).focus({ preventScroll: true });
            }
        }
        function openSavedTaskFromNotification() {
            if (isDialogOpen()) return;
            const taskId = state.notificationTaskId;
            if (taskId === null) return;
            const returnTarget = state.notificationReturnFocus;
            if (!getTaskById(taskId)) { utils.notify(utils.translate('storage.editConflict'), 'warning'); return; }
            if (runAppAction('task.edit', { taskId })) state.elementToFocusOnClose = returnTarget;
        }
        function notifyTaskSaved(taskId, messageKey) {
            const selectorId = CSS.escape(String(taskId));
            const outside = workspaceUI.screen === 'tasks' && state.viewMode !== 'stats'
                && !DOM.taskList.querySelector(`[data-task-id="${selectorId}"], [data-calendar-task-id="${selectorId}"]`);
            utils.notify(utils.translate(outside ? 'usability.savedOutsideView' : messageKey), 'success', { undo: true, openTaskId: outside ? taskId : null });
        }
        function syncDialogFeedbackPlacement() {
            if (!DOM.notification?.el) return;
            const dialog = isTaskDialogOpen() ? DOM.modal.querySelector('.modal-content')
                : isCommandPaletteOpen() ? DOM.commandPalette.el.querySelector('.command-palette-panel')
                : document.getElementById('workspaceScheduleDialog')?.open ? document.getElementById('workspaceScheduleDialog') : null;
            let host = document.querySelector('.workspace-feedback');
            if (dialog) {
                host = Array.from(dialog.children).find(element => element.classList.contains('dialog-feedback'));
                if (!host) {
                    host = document.createElement('div');
                    host.className = 'dialog-feedback';
                    const header = dialog.querySelector('.modal-header, .command-palette-header, .workspace-schedule-header');
                    if (header) header.after(host); else dialog.prepend(host);
                }
            }
            if (host && DOM.notification.el.parentElement !== host) host.appendChild(DOM.notification.el);
        }
        function syncPageModalOpenState() {
            const open = isDialogOpen();
            document.documentElement.classList.toggle('modal-open', open);
            document.body.classList.toggle('modal-open', open);
            syncDialogFeedbackPlacement();
        }
        function bindNotificationEvents() {
            if (DOM.notificationToggleBtn) {
                DOM.notificationToggleBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    runAppAction('notifications.toggle');
                });
            } else {
                console.error('Notification button not found in DOM');
            }
            if (DOM.notification.undoBtn) DOM.notification.undoBtn.addEventListener('click', () => runAppAction('undo.perform'));
        }
        function bindUpdatePromptEvents() {
            DOM.updatePrompt.reloadBtn.addEventListener('click', applyServiceWorkerUpdate);
            DOM.updatePrompt.dismissBtn.addEventListener('click', hideUpdatePrompt);
            document.getElementById('checkUpdateBtn').addEventListener('click', checkForAppUpdate);
            document.getElementById('settingsUpdateNowBtn').addEventListener('click', applyServiceWorkerUpdate);
            if ('ResizeObserver' in window) new ResizeObserver(syncUpdatePromptClearance).observe(DOM.updatePrompt.el);
            window.addEventListener('resize', syncUpdatePromptClearance);
            window.visualViewport?.addEventListener('resize', syncUpdatePromptClearance);
            syncUpdatePromptClearance();
            syncUpdateControls();
        }
        function syncUpdatePromptClearance() {
            const prompt = DOM.updatePrompt.el;
            const bounds = prompt.getBoundingClientRect();
            if (prompt.hidden || !bounds.height) {
                document.documentElement.style.removeProperty('--workspace-update-clearance');
                return;
            }
            const clearance = Math.max(0, Math.ceil(window.innerHeight - bounds.top) + 12);
            document.documentElement.style.setProperty('--workspace-update-clearance', `${clearance}px`);
        }
        function initInstallPrompt() {
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                state.deferredInstallPrompt = e;
                syncInstallEntry();
            });
            window.addEventListener('appinstalled', () => {
                state.deferredInstallPrompt = null;
                syncInstallEntry();
                utils.notify(utils.translate('pwa.install.installed'));
            });
            syncInstallEntry();
        }
        function syncInstallEntry() {
            const installed = isAppInstalled();
            DOM.menu.installBtn.hidden = installed;
            const status = document.getElementById('settingsInstallStatus');
            if (status) status.textContent = installed ? utils.translate('pwa.install.installed') : '';
            document.getElementById('settingsVersion').textContent = CONFIG.APP.VERSION;
            syncUpdateControls();
        }
        function isAppInstalled() {
            return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
        }
        async function handleInstallAppClick() {
            closeMenu();
            if (!state.deferredInstallPrompt) {
                showInstallHelp();
                return;
            }
            const promptEvent = state.deferredInstallPrompt;
            state.deferredInstallPrompt = null;
            promptEvent.prompt();
            const choice = await promptEvent.userChoice;
            syncInstallEntry();
            if (choice?.outcome === 'accepted') {
                utils.notify(utils.translate('pwa.install.accepted'));
            }
        }
        function showInstallHelp() {
            utils.confirm(utils.translate('pwa.install.title'), createInstallHelpContent(), () => {});
            DOM.cancelBtn.hidden = true;
            DOM.submitBtn.textContent = utils.translate('help.close');
        }
        function createInstallHelpContent() {
            const wrapper = document.createElement('div');
            wrapper.className = 'confirm-details';
            const userAgent = navigator.userAgent;
            const appleMobile = /iPhone|iPad|iPod/.test(userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
            const key = appleMobile ? 'pwa.install.ios'
                : /Android/.test(userAgent) ? 'pwa.install.android'
                : /Safari/.test(userAgent) && !/Chrome|Chromium|Edg/.test(userAgent) ? 'pwa.install.macSafari'
                : /Firefox/.test(userAgent) ? 'pwa.install.unavailable'
                : 'pwa.install.desktop';
            const list = document.createElement('ul');
            list.className = 'confirm-list';
            const item = document.createElement('li');
            item.textContent = utils.translate(key);
            list.appendChild(item);
            wrapper.appendChild(list);
            return wrapper;
        }
        function initServiceWorkerUpdates() {
            if (!('serviceWorker' in navigator)) { setUpdateCheckStatus('unsupported'); return; }
            let previousController = navigator.serviceWorker.controller;
            navigator.serviceWorker.addEventListener('message', event => {
                if (event.data?.type === 'REPORT_CLIENT_VERSION') reportServiceWorkerClientVersion(event.source);
            });
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                const controller = navigator.serviceWorker.controller;
                if (previousController && controller && controller !== previousController) markAppUpdateReady(controller);
                previousController = controller;
                reportServiceWorkerClientVersion();
                if (state.refreshingForUpdate) reloadForAppUpdate();
            });
            const register = async () => {
                try {
                    const registration = await getAppServiceWorkerRegistration();
                    reportServiceWorkerClientVersion();
                    if (registration.waiting && navigator.serviceWorker.controller) markAppUpdateReady(registration.waiting);
                } catch (error) {
                    console.warn('Service worker registration failed:', error);
                }
            };
            if (document.readyState === 'complete') register();
            else window.addEventListener('load', register, { once: true });
            navigator.serviceWorker.ready.then(() => reportServiceWorkerClientVersion()).catch(() => {});
        }
        function reportServiceWorkerClientVersion(worker = navigator.serviceWorker.controller) {
            worker?.postMessage({ type: 'CLIENT_VERSION', version: CONFIG.APP.VERSION });
        }
        async function getAppServiceWorkerRegistration() {
            if (state.serviceWorkerRegistration) return state.serviceWorkerRegistration;
            if (!state.serviceWorkerRegistrationPromise) {
                state.serviceWorkerRegistrationPromise = navigator.serviceWorker.register('./sw.js').then(registration => {
                    state.serviceWorkerRegistration = registration;
                    watchServiceWorkerUpdate(registration);
                    return registration;
                }).finally(() => { state.serviceWorkerRegistrationPromise = null; });
            }
            return state.serviceWorkerRegistrationPromise;
        }
        function watchServiceWorkerUpdate(registration) {
            if (state.watchedWorkerRegistrations.has(registration)) return;
            state.watchedWorkerRegistrations.add(registration);
            const observe = worker => {
                if (!worker || state.watchedUpdateWorkers.has(worker)) return;
                state.watchedUpdateWorkers.add(worker);
                const changed = () => {
                    if (worker.state === 'installed' && navigator.serviceWorker.controller) {
                        state.serviceWorkerRegistration = registration;
                        markAppUpdateReady(worker);
                    }
                };
                worker.addEventListener('statechange', changed);
                changed();
            };
            registration.addEventListener('updatefound', () => observe(registration.installing));
            observe(registration.installing || registration.waiting);
        }
        function syncUpdateControls() {
            const button = document.getElementById('checkUpdateBtn');
            const status = document.getElementById('updateCheckStatus');
            if (!button || !status) return;
            button.disabled = state.updateChecking;
            button.setAttribute('aria-busy', String(state.updateChecking));
            button.textContent = utils.translate(state.updateChecking ? 'pwa.update.checking' : 'pwa.update.check');
            status.dataset.state = state.updateCheckStatus;
            const key = state.updateCheckMessageKey || (state.updateCheckStatus === 'idle' ? '' : `pwa.update.${state.updateCheckStatus}`);
            status.textContent = key ? utils.translate(key).replace('{version}', CONFIG.APP.VERSION) : '';
            const reload = document.getElementById('settingsUpdateNowBtn');
            reload.hidden = !state.updateAvailable;
            reload.disabled = state.refreshingForUpdate;
        }
        function setUpdateCheckStatus(status, messageKey = '') {
            state.updateCheckStatus = status;
            state.updateCheckMessageKey = messageKey;
            syncUpdateControls();
        }
        function markAppUpdateReady(worker, reveal = false) {
            state.updateAvailable = true;
            if (worker) state.updateWorker = worker;
            if (reveal) state.updatePromptDismissed = false;
            setUpdateCheckStatus('ready');
            showUpdatePrompt();
        }
        function requestAppUpdateCheck() {
            return new Promise((resolve, reject) => {
                let settled = false;
                const listeners = [];
                const finish = (worker, error) => {
                    if (settled) return;
                    settled = true;
                    clearTimeout(timer);
                    listeners.forEach(remove => remove());
                    if (error) reject(error); else resolve(worker);
                };
                const timer = setTimeout(() => finish(null, new Error('Update check timed out')), 30000);
                getAppServiceWorkerRegistration().then(registration => {
                    if (settled) return;
                    const controller = navigator.serviceWorker.controller;
                    let candidate = null;
                    const observed = new Set();
                    const observe = worker => {
                        if (!worker || settled) return;
                        candidate = worker;
                        if (observed.has(worker)) return;
                        observed.add(worker);
                        const changed = () => {
                            if (worker.state === 'redundant') finish(null, new Error('Update installation failed'));
                            else if (['installed', 'activated'].includes(worker.state)) finish(controller ? worker : null);
                        };
                        worker.addEventListener('statechange', changed);
                        listeners.push(() => worker.removeEventListener('statechange', changed));
                        changed();
                    };
                    const found = () => observe(registration.installing || registration.waiting);
                    registration.addEventListener('updatefound', found);
                    listeners.push(() => registration.removeEventListener('updatefound', found));
                    found();
                    registration.update().then(() => {
                        if (settled) return;
                        found();
                        if (state.updateAvailable || (controller && navigator.serviceWorker.controller !== controller)) finish(state.updateWorker || navigator.serviceWorker.controller);
                        else if (!candidate) finish(null);
                    }).catch(error => finish(null, error));
                }).catch(error => finish(null, error));
            });
        }
        async function checkForAppUpdate() {
            if (state.updateChecking) return;
            if (!('serviceWorker' in navigator)) { setUpdateCheckStatus('unsupported'); return; }
            const waiting = state.serviceWorkerRegistration?.waiting;
            if (state.updateAvailable || waiting) { markAppUpdateReady(state.updateWorker || waiting, true); return; }
            if (navigator.onLine === false) { setUpdateCheckStatus('offline'); return; }
            state.updateChecking = true;
            setUpdateCheckStatus('checking');
            try {
                const worker = await requestAppUpdateCheck();
                if (worker || state.updateAvailable) markAppUpdateReady(worker || state.updateWorker, true);
                else setUpdateCheckStatus('latest');
            } catch (error) {
                setUpdateCheckStatus(navigator.onLine === false ? 'offline' : 'error');
            } finally {
                state.updateChecking = false;
                syncUpdateControls();
            }
        }
        function showUpdatePrompt() {
            if (state.updatePromptDismissed) return;
            DOM.updatePrompt.el.hidden = false;
            syncUpdatePromptClearance();
            utils.announce(utils.translate('pwa.update.message'));
        }
        function hideUpdatePrompt() {
            state.updatePromptDismissed = true;
            DOM.updatePrompt.el.hidden = true;
            syncUpdatePromptClearance();
        }
        function canReloadForAppUpdate() {
            const busy = state.quickAddSaving || state.taskFormSaving || state.pendingTaskActions.size;
            if (!busy && !hasUnsavedTaskWork()) return true;
            const key = busy ? 'pwa.update.busy' : 'pwa.update.saveFirst';
            setUpdateCheckStatus('blocked', key);
            utils.notify(utils.translate(key), 'warning');
            return false;
        }
        function reloadForAppUpdate() {
            state.refreshingForUpdate = false;
            syncUpdateControls();
            if (canReloadForAppUpdate()) window.location.reload();
        }
        function applyServiceWorkerUpdate() {
            if (state.refreshingForUpdate || !canReloadForAppUpdate()) return;
            const registration = state.serviceWorkerRegistration;
            const worker = registration?.waiting || state.updateWorker;
            if (worker && worker !== navigator.serviceWorker.controller && ['installed', 'activating'].includes(worker.state)) {
                state.refreshingForUpdate = true;
                syncUpdateControls();
                worker.postMessage({ type: 'SKIP_WAITING' });
                window.setTimeout(() => {
                    if (!state.refreshingForUpdate) return;
                    state.refreshingForUpdate = false;
                    setUpdateCheckStatus('error');
                }, 10000);
            } else reloadForAppUpdate();
        }
        function bindMenuEvents() {
            document.addEventListener('click', closeMainMenuOnOutsideClick);
            DOM.menu.container.addEventListener('keydown', handleMenuKeydown);
            DOM.menu.backupBtn.addEventListener('click', () => runAppAction('data.backup'));
            DOM.menu.exportCsvBtn.addEventListener('click', () => runAppAction('data.csv'));
            DOM.menu.importBtn.addEventListener('click', () => runAppAction('data.import.open'));
            DOM.menu.recoveryBtn.addEventListener('click', () => runAppAction('data.recovery'));
            DOM.menu.storageHealthBtn.addEventListener('click', () => runAppAction('data.health'));
            DOM.menu.archiveCompletedBtn.addEventListener('click', () => runAppAction('archive.completed'));
            DOM.menu.fileInput.addEventListener('change', (e) => runAppAction('data.import.file', { file: e.target.files[0] }));
        }
        function handleMainMenuClick(e) {
            e.stopPropagation();
            runAppAction('menu.toggle');
        }
        function toggleMainMenu() {
            return setWorkspaceScreen('settings', { focus: true });
        }
        function closeMainMenuOnOutsideClick(e) {
            if (!DOM.menu.container.classList.contains('menu')) return;
            if (isElementOpen(DOM.menu.container) && !DOM.menu.container.contains(e.target) && !DOM.menu.btn.contains(e.target)) {
                closeMenu();
            }
        }
        function handleMenuKeydown(e) {
            if (!DOM.menu.container.classList.contains('menu')) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                closeMenu();
                DOM.menu.btn.focus();
                return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return;
            e.preventDefault();
            moveMenuFocus(DOM.menu.container, e.key, e.target);
        }
        function moveMenuFocus(container, key, activeElement) {
            const items = getVisibleMenuItems(container);
            if (items.length === 0) return;
            const currentIndex = Math.max(0, items.indexOf(activeElement));
            let nextIndex = currentIndex;
            if (key === 'ArrowDown') nextIndex = currentIndex === items.length - 1 ? 0 : currentIndex + 1;
            if (key === 'ArrowUp') nextIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
            if (key === 'Home') nextIndex = 0;
            if (key === 'End') nextIndex = items.length - 1;
            items[nextIndex].focus();
        }
        function getVisibleMenuItems(container) {
            return Array.from(container.querySelectorAll('[role="menuitem"], [role="menuitemradio"]'))
                .filter(item => item.offsetParent !== null && !item.disabled);
        }
        function focusFirstMenuItem(container) {
            const item = getVisibleMenuItems(container)[0];
            if (item) item.focus();
        }
        function bindTaskListEvents() {
            DOM.taskList.addEventListener('click', handleTaskListClick);
            DOM.taskList.addEventListener('keydown', handleTaskActionMenuKeydown);
            DOM.taskList.addEventListener('focusin', event => {
                const control = event.target.closest('.task-item button, .task-item input');
                if (state.viewMode !== 'list' || !control || control.closest('.task-action-menu') || !control.matches(':focus-visible')) return;
                requestAnimationFrame(() => {
                    if (state.viewMode !== 'list' || isDialogOpen() || document.activeElement !== control || !control.isConnected) return;
                    const rect = control.getBoundingClientRect();
                    const header = document.querySelector('.workspace-topbar').getBoundingClientRect();
                    const dock = document.getElementById('workspaceMobileDock').getBoundingClientRect();
                    const top = header.bottom + 8;
                    const bottom = Math.min(innerHeight, dock.height && dock.top < innerHeight ? dock.top : innerHeight) - 8;
                    if (rect.top < top) window.scrollBy({ top: rect.top - top, behavior: 'instant' });
                    else if (rect.bottom > bottom) window.scrollBy({ top: rect.bottom - bottom, behavior: 'instant' });
                });
            });
        }
        function bindSubtaskInputEvents() {
            DOM.addSubtaskBtn.addEventListener('click', handleAddSubtaskInput);
            DOM.inputs.subtask.addEventListener('keypress', (e) => {
                if (isCompositionKey(e)) return;
                if (e.key === 'Enter') { e.preventDefault(); handleAddSubtaskInput(); }
            });
        }
        function bindSubtaskPreviewEvents() {
            DOM.subtaskListPreview.addEventListener('click', handleSubtaskPreviewClick);
            DOM.subtaskListPreview.addEventListener('focusout', handleSubtaskPreviewFocusOut);
            DOM.subtaskListPreview.addEventListener('keydown', handleSubtaskPreviewKeydown);
            DOM.subtaskListPreview.addEventListener('mousedown', preventSubtaskDeleteBlur);
        }
        function handleSubtaskPreviewClick(e) {
            const deleteBtn = e.target.closest('.subtask-delete-btn');
            if (deleteBtn) {
                removeTempSubtask(deleteBtn.dataset.subtaskId);
                return;
            }
            const textSpan = e.target.closest('.subtask-preview-text');
            if (textSpan) editTempSubtask(textSpan.dataset.subtaskId);
        }
        function handleSubtaskPreviewFocusOut(e) {
            if (e.target.classList.contains('subtask-edit-input')) {
                saveEditSubtask(e.target);
            }
        }
        function handleSubtaskPreviewKeydown(e) {
            if (isCompositionKey(e)) return;
            if (e.target.classList.contains('subtask-edit-input') && e.key === 'Enter') {
                e.preventDefault();
                e.target.blur();
                return;
            }
            if (e.target.classList.contains('subtask-preview-text') && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                editTempSubtask(e.target.dataset.subtaskId);
            }
        }
        function preventSubtaskDeleteBlur(e) {
            if (e.target.closest('.subtask-delete-btn')) {
                e.preventDefault();
            }
        }
        function getActiveSubtaskEditInput() {
            const input = DOM.subtaskListPreview.querySelector('.subtask-edit-input');
            return input?.dataset.editorActive === 'true' ? input : null;
        }
        function captureActiveSubtaskEdit() {
            const input = getActiveSubtaskEditInput();
            if (!input) return null;
            return {
                id: input.dataset.subtaskId,
                value: input.value,
                start: input.selectionStart,
                end: input.selectionEnd,
                direction: input.selectionDirection
            };
        }
        function retainSubtaskEdit(draft) {
            const subtask = draft && state.tempSubtasks.find(item => String(item.id) === draft.id);
            if (subtask && draft.value.trim()) subtask.text = draft.value.trim();
        }
        function removeTempSubtask(subtaskId) {
            const input = getActiveSubtaskEditInput();
            if (input && state.composingInputs.has(input)) return;
            const index = state.tempSubtasks.findIndex(item => String(item.id) === String(subtaskId));
            if (index < 0) return;
            const draft = captureActiveSubtaskEdit();
            const keepEditing = draft && draft.id !== String(subtaskId);
            if (keepEditing) retainSubtaskEdit(draft);
            state.tempSubtasks.splice(index, 1);
            state.editingSubtaskIndex = keepEditing
                ? state.tempSubtasks.findIndex(item => String(item.id) === draft.id) : -1;
            renderSubtaskPreview();
            const restored = getActiveSubtaskEditInput();
            if (restored && keepEditing) {
                restored.value = draft.value;
                restored.focus();
                restored.setSelectionRange(draft.start, draft.end, draft.direction);
            } else {
                const next = DOM.subtaskListPreview.children[Math.min(index, state.tempSubtasks.length - 1)];
                (next?.querySelector('.subtask-preview-text') || DOM.inputs.subtask).focus();
            }
        }
        function editTempSubtask(subtaskId) {
            const input = getActiveSubtaskEditInput();
            if (input && state.composingInputs.has(input)) return;
            const index = state.tempSubtasks.findIndex(item => String(item.id) === String(subtaskId));
            if (index < 0) return;
            retainSubtaskEdit(captureActiveSubtaskEdit());
            state.editingSubtaskIndex = index;
            renderSubtaskPreview();
        }
        function handleKeyboardShortcuts(e) {
            if (isCompositionKey(e)) return;
            if (DOM.mobileFiltersDialog?.open) return;
            if (document.getElementById('workspaceScheduleDialog').open) return;
            if (isCommandPaletteOpen()) {
                if (e.key === 'Tab') trapCommandPaletteFocus(e);
                else if (e.key === 'Escape') closeCommandPalette();
                return;
            }
            if (isTaskDialogOpen()) {
                if (e.key === 'Tab') trapDialogFocus(e);
                else if (e.key === 'Escape') {
                    e.preventDefault();
                    if (state.taskFormSession?.prompt) dismissTaskDraftDiscard();
                    else if (!closeOpenCustomSelect(DOM.modal)) requestCloseTaskDialog();
                }
                return;
            }
            if (e.key === 'Escape' && workspaceUI.captureOpen && document.getElementById('captureShelf').contains(document.activeElement)) { e.preventDefault(); setCaptureShelf(false, { restoreFocus: true }); return; }
            const meta = e.ctrlKey || e.metaKey;
            const key = e.key.toLowerCase();
            if (meta && key === 'p') { e.preventDefault(); runAppAction('command.open'); return; }
            if (meta && key === 'z' && !e.shiftKey && !isEditableElement(document.activeElement)) { e.preventDefault(); runAppAction('undo.perform'); return; }
            if (meta && key === 'k') { e.preventDefault(); runAppAction('search.focus'); return; }
            if (meta && key === 'i') { e.preventDefault(); if (DOM.modal.style.display !== 'flex') runAppAction('task.new'); return; }
            if (meta && key === 'm') { e.preventDefault(); runAppAction('menu.toggle'); return; }
            if (e.altKey && key === 't') { e.preventDefault(); runAppAction('scroll.top'); return; }
            if (e.key === 'Escape') {
                if (workspaceUI.screen === 'settings') {
                    if (closeOpenCustomSelect(document.getElementById('settingsWorkspace'))) return;
                    if (!isEditableElement(document.activeElement)) { e.preventDefault(); setWorkspaceScreen(workspaceUI.lastScreen, { restoreFocus: true }); }
                    return;
                }
                if (document.activeElement === DOM.inputs.search && DOM.inputs.search.value) clearSearchInput();
                else if (document.activeElement === DOM.inputs.search) DOM.inputs.search.blur();
                else {
                    closeAllDropdowns();
                    closeAllCustomSelects();
                    closeMenu();
                }
            }
        }
        function isEditableElement(element) {
            return element && (element.matches('input, textarea, select') || element.isContentEditable);
        }
        function isCompositionKey(e) {
            return e.isComposing || e.keyCode === 229 || state.composingInputs.has(e.target);
        }
        function hasActiveComposition(form) {
            const input = document.activeElement;
            return Boolean(input && form.contains(input) && state.composingInputs.has(input));
        }
        function isDialogOpen() {
            return DOM.mobileFiltersDialog?.open || document.getElementById('workspaceScheduleDialog')?.open || isTaskDialogOpen() || isCommandPaletteOpen();
        }
        function isTaskDialogOpen() {
            return DOM.modal && DOM.modal.style.display === 'flex';
        }
        function isCommandPaletteOpen() {
            return DOM.commandPalette && !DOM.commandPalette.el.hidden;
        }
        function trapDialogFocus(e) {
            if (state.taskFormSession?.saving && state.modalMode === 'form') {
                e.preventDefault();
                state.taskFormSession.status?.focus();
                return;
            }
            trapFocusInElement(state.taskFormSession?.prompt || DOM.modal, e);
        }
        function trapCommandPaletteFocus(e) {
            trapFocusInElement(DOM.commandPalette.el, e);
        }
        function captureFocusReturnTarget(element = document.activeElement) {
            if (!element || element === document.body) return { type: 'element', element: DOM.openModalBtn };
            const savedView = element.closest?.('[data-saved-view-id], [data-saved-view-delete-id]');
            if (savedView) {
                return { type: 'saved-view', id: savedView.dataset.savedViewDeleteId || savedView.dataset.savedViewId,
                    action: savedView.hasAttribute('data-saved-view-delete-id') ? 'delete' : 'apply' };
            }
            const statsAction = element.closest?.('[data-stats-action], [data-stats-filter]');
            if (statsAction) return { type: 'stats-action', action: statsAction.dataset.statsAction || '',
                filter: statsAction.dataset.statsFilter || '', project: statsAction.dataset.statsProject || '' };
            const menuTask = element.closest?.('.task-action-menu')?.closest('.task-item');
            if (menuTask?.dataset.taskId) {
                const tasks = Array.from(DOM.taskList.querySelectorAll('.task-item'));
                const index = tasks.indexOf(menuTask);
                return { type: 'task-menu', taskId: menuTask.dataset.taskId, nextTaskId: tasks[index + 1]?.dataset.taskId, previousTaskId: tasks[index - 1]?.dataset.taskId };
            }
            const planTask = element.closest?.('[data-task-plan]')?.closest('.task-item');
            if (planTask) return { type: 'task-plan', taskId: planTask.dataset.taskId };
            const calendarTask = element.closest?.('[data-calendar-task-id]');
            if (calendarTask) {
                return { type: 'calendar-task', taskId: calendarTask.dataset.calendarTaskId,
                    dateKey: getTaskDueDateKey(getTaskById(Number(calendarTask.dataset.calendarTaskId))),
                    source: calendarTask.classList.contains('calendar-detail-task') ? 'agenda' : 'month' };
            }
            const taskAction = element.closest?.('[data-action]');
            const taskEl = element.closest?.('.task-item');
            if (taskAction && taskEl?.dataset.taskId) {
                return {
                    type: 'task-action',
                    taskId: taskEl.dataset.taskId,
                    action: taskAction.dataset.action
                };
            }
            if (element.id) return { type: 'id', id: element.id };
            return { type: 'element', element };
        }
        function restoreFocusReturnTarget(target) {
            const element = resolveFocusReturnElement(target);
            if (isFocusableReturnElement(element)) {
                element.focus();
                return;
            }
            const fallback = workspaceUI.screen === 'settings' ? document.getElementById('settingsTitle') : DOM.openModalBtn;
            fallback.focus();
        }
        function resolveFocusReturnElement(target) {
            if (!target) return null;
            if (target instanceof Element) return target;
            if (target.type === 'stats-action') return Array.from(DOM.taskList.querySelectorAll('[data-stats-action], [data-stats-filter]')).find(button =>
                (button.dataset.statsAction || '') === target.action && (button.dataset.statsFilter || '') === target.filter
                && (button.dataset.statsProject || '') === target.project) || null;
            if (target.type === 'saved-view') {
                const attribute = target.action === 'delete' ? 'data-saved-view-delete-id' : 'data-saved-view-id';
                return DOM.savedViewsList.querySelector(`[${attribute}="${CSS.escape(String(target.id))}"]`) || DOM.saveSmartViewBtn;
            }
            if (target.type === 'task-menu') {
                for (const id of [target.taskId, target.nextTaskId, target.previousTaskId]) {
                    if (!id) continue;
                    const button = document.querySelector(`.task-item[data-task-id="${CSS.escape(String(id))}"] .task-more-toggle`);
                    if (isFocusableReturnElement(button)) return button;
                }
                return null;
            }
            if (target.type === 'task-action') {
                return document.querySelector(`.task-item[data-task-id="${CSS.escape(String(target.taskId))}"] [data-action="${CSS.escape(target.action)}"]`);
            }
            if (target.type === 'task-plan') {
                return document.querySelector(`.task-item[data-task-id="${CSS.escape(String(target.taskId))}"] [data-task-plan]`)
                    || document.getElementById('planningDoneBtn');
            }
            if (target.type === 'calendar-task') {
                const scope = target.source === 'agenda' ? '.calendar-day-detail ' : '.calendar-day ';
                const task = DOM.taskList.querySelector(`${scope}[data-calendar-task-id="${CSS.escape(String(target.taskId))}"]`);
                if (isFocusableReturnElement(task)) return task;
                if (target.source === 'agenda' && state.calendarDetailDateKey === target.dateKey) {
                    const title = DOM.taskList.querySelector('.calendar-detail-title');
                    if (isFocusableReturnElement(title)) return title;
                }
                return DOM.taskList.querySelector(`[data-calendar-detail-date="${CSS.escape(target.dateKey || '')}"]`)
                    || DOM.taskList.querySelector(`[data-calendar-add-date="${CSS.escape(target.dateKey || '')}"]`);
            }
            if (target.type === 'id') return document.getElementById(target.id);
            if (target.type === 'element') return target.element;
            return null;
        }
        function isFocusableReturnElement(element) {
            return Boolean(element && document.body.contains(element) && !element.disabled && !element.closest('[inert]') && element.offsetParent !== null && typeof element.focus === 'function');
        }
        function trapFocusInElement(root, e) {
            const focusable = getFocusableElements(root);
            if (focusable.length === 0) {
                e.preventDefault();
                return;
            }
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            const active = document.activeElement;
            if (!root.contains(active)) {
                e.preventDefault();
                first.focus();
                return;
            }
            if (e.shiftKey && active === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && active === last) {
                e.preventDefault();
                first.focus();
            }
        }
        function getFocusableDialogElements() {
            return getFocusableElements(DOM.modal);
        }
        function getFocusableElements(root) {
            return Array.from(root.querySelectorAll([
                'a[href]',
                'button:not([disabled])',
                'input:not([disabled])',
                'select:not([disabled])',
                'textarea:not([disabled])',
                '[tabindex]:not([tabindex="-1"])'
            ].join(','))).filter(el => Boolean(el.offsetParent) && el.getAttribute('aria-hidden') !== 'true' && !el.classList.contains('native-select-hidden'));
        }
        function prefersReducedMotion() {
            return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        }
        function getMotionAwareScrollBehavior() {
            return prefersReducedMotion() ? 'auto' : 'smooth';
        }
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: getMotionAwareScrollBehavior() });
        }
        function scrollIntoViewWithMotionPreference(el, options = {}) {
            el.scrollIntoView({ ...options, behavior: getMotionAwareScrollBehavior() });
        }
        async function handleTaskSave(e) {
            e.preventDefault();
            if (hasActiveComposition(DOM.form)) return;
            if (state.taskFormSaving) return;
            const session = state.taskFormSession;
            if (!session || state.modalMode !== 'form' || session.prompt) return;
            if (!canRunAppAction('task.save', { closeSurfaces: false })) return;
            const t = state.translations[state.currentLanguage];
            if (!DOM.inputs.noDeadline.checked && !normalizeDueDateValue(DOM.inputs.date.value)) {
                showEditorFieldError(DOM.inputs.date, 'dueDateError');
                return;
            }
            if (!DOM.inputs.noDeadline.checked && DOM.inputs.repeatType.value === 'custom' && !isValidFormRepeatInterval()) {
                showEditorFieldError(DOM.inputs.repeatInterval, 'repeatIntervalError');
                return;
            }
            if (!DOM.inputs.noDeadline.checked && DOM.inputs.repeatType.value === 'weekly-days' && !getSelectedRepeatWeekdays().length) {
                document.getElementById('repeatWeekdaysError').hidden = false;
                document.querySelector('#repeatWeekdaysRow .repeat-weekdays').setAttribute('aria-invalid', 'true');
                document.querySelector('#repeatWeekdaysRow .repeat-weekdays').setAttribute('aria-describedby', 'repeatWeekdaysError');
                revealEditorElement(document.getElementById('repeatWeekdaysRow'));
                DOM.inputs.repeatWeekdayInputs[0].focus({ preventScroll: true });
                return;
            }
            const taskPayload = buildTaskPayloadFromForm();
            if (!taskPayload.name) {
                utils.notify(t['messages.task.nameRequired'], 'warning');
                DOM.inputs.name.focus();
                return;
            }
            state.taskFormSaving = true;
            session.saving = true;
            lockTaskDraftForm(session);
            session.status = document.createElement('p');
            session.status.id = 'taskDraftSavingStatus';
            session.status.setAttribute('role', 'status');
            session.status.tabIndex = -1;
            session.status.textContent = utils.translate('drafts.saving');
            DOM.form.prepend(session.status);
            session.status.focus();
            try {
                const beforeTasks = captureUndoSnapshot();
                let savedTaskId = state.editingTaskId;
                const messageKey = isEditingTask() ? 'messages.task.updated' : 'messages.task.added';
                if (isEditingTask()) {
                    const original = getTaskById(state.editingTaskId);
                    if (!original || JSON.stringify(original) !== state.editingTaskSnapshot) {
                        utils.notify(utils.translate('storage.editConflict'), 'warning');
                        return;
                    }
                    const updatedTask = mergeTaskPayload(original, taskPayload);
                    const shouldClearNotificationDelivery = didReminderSettingsChange(original, updatedTask);
                    await dbActions.updateTask(updatedTask);
                    if (shouldClearNotificationDelivery) clearTaskNotificationDeliveryState(original.id);
                    registerUndoSnapshot(t['undo.labels.edit'], beforeTasks);
                } else {
                    const record = createTaskRecord(taskPayload);
                    savedTaskId = record.id;
                    await dbActions.addTask(record);
                    registerUndoSnapshot(t['undo.labels.add'], beforeTasks);
                }
                await refreshTasks();
                if (workspaceUI.captureFormText !== null && DOM.quickAddInput.value === workspaceUI.captureFormText) {
                    DOM.quickAddInput.value = '';
                    workspaceUI.captureDateKey = '';
                    clearQuickAddCaptureDraft();
                    syncCapturePreview();
                }
                workspaceUI.captureFormText = null;
                if (state.taskFormSession === session && state.modalMode === 'form') closeDialog();
                notifyTaskSaved(savedTaskId, messageKey);
            } catch (err) {
                console.error('保存任务失败:', err);
                handleStorageOperationError(err, 'messages.task.saveError');
            } finally {
                session.saving = false;
                if (state.taskFormSession === session && state.modalMode === 'form') {
                    state.taskFormSaving = false;
                    const restoreFocus = document.activeElement === session.status;
                    session.status?.remove();
                    session.status = null;
                    unlockTaskDraftForm(session);
                    if (restoreFocus) (session.lastFocus?.isConnected && !session.lastFocus.disabled ? session.lastFocus : DOM.inputs.name).focus();
                }
            }
        }
        async function handleQuickAddSubmit(e) {
            e.preventDefault();
            if (hasActiveComposition(DOM.quickAddForm)) return;
            await saveQuickAddText(DOM.quickAddInput.value.trim(), getQuickAddCaptureOptions());
        }
        function handleQuickAddInput() {
            syncCapturePreview();
            const draft = state.quickAddCaptureDraft;
            if (!draft) return;
            const currentText = DOM.quickAddInput.value.trim();
            if (!currentText || !isCaptureDraftTextRelated(draft.text, currentText)) clearQuickAddCaptureDraft();
        }
        async function saveQuickAddText(rawInput, options = {}) {
            if (state.quickAddSaving) return false;
            if (!canRunAppAction('task.quickAddSubmit', { closeSurfaces: false })) return false;
            const t = state.translations[state.currentLanguage];
            if (!rawInput) {
                utils.notify(t['messages.task.nameRequired'], 'warning');
                if (options.focusOnError !== false) DOM.quickAddInput.focus();
                clearQuickAddCaptureDraft();
                return false;
            }
            const taskPayload = buildTaskPayloadFromQuickAdd(rawInput, options);
            if (!taskPayload.name) {
                utils.notify(t['messages.task.nameRequired'], 'warning');
                if (options.focusOnError !== false) DOM.quickAddInput.focus();
                return false;
            }
            state.quickAddSaving = true;
            setQuickAddSaving(true);
            try {
                const beforeTasks = captureUndoSnapshot();
                const record = createTaskRecord(taskPayload);
                await dbActions.addTask(record);
                DOM.quickAddInput.value = '';
                workspaceUI.captureDateKey = '';
                clearQuickAddCaptureDraft();
                syncCapturePreview();
                registerUndoSnapshot(t['undo.labels.add'], beforeTasks);
                await refreshTasks();
                notifyTaskSaved(record.id, 'messages.task.added');
                return true;
            } catch (err) {
                console.error('快速添加任务失败:', err);
                handleStorageOperationError(err, 'messages.task.saveError');
                return false;
            } finally {
                state.quickAddSaving = false;
                setQuickAddSaving(false);
            }
        }
        function hasUnsavedQuickAddText() {
            return Boolean(DOM.quickAddInput?.value.trim());
        }
        function syncQuickAddDescriptions() {
            const descriptions = [];
            const preview = document.getElementById('capturePreview');
            if (preview && !preview.hidden && preview.textContent.trim()) descriptions.push(preview.id);
            if (!state.storageAvailable && hasUnsavedQuickAddText()) descriptions.push('quickAddRetainedMessage');
            if (descriptions.length) DOM.quickAddInput.setAttribute('aria-describedby', descriptions.join(' '));
            else DOM.quickAddInput.removeAttribute('aria-describedby');
        }
        function setQuickAddSaving(saving) {
            const retained = !state.storageAvailable && hasUnsavedQuickAddText();
            DOM.quickAddInput.readOnly = retained;
            DOM.quickAddInput.disabled = saving || (!state.storageAvailable && !retained);
            DOM.quickAddInput.setAttribute('aria-disabled', String(DOM.quickAddInput.disabled));
            syncQuickAddDescriptions();
            const button = DOM.quickAddForm.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = saving || !state.storageAvailable;
                button.setAttribute('aria-disabled', String(button.disabled));
            }
        }
        async function handleLaunchCapture() {
            const request = getLaunchCaptureRequest();
            if (!request) return;
            clearLaunchCaptureParams();
            setQuickAddCaptureDraft(request);
            if (request.text && request.save) {
                const saved = await saveQuickAddText(request.text, getQuickAddCaptureOptions({ focusOnError: false }));
                if (saved) return;
            }
            focusQuickAddForCapture(request.text);
        }
        function getLaunchCaptureRequest() {
            const params = new URLSearchParams(window.location.search);
            const captureRequested = params.get('capture') === '1';
            const addText = normalizeCaptureText(params.get('add'));
            const shared = getSharedCapturePayload(params);
            const text = addText || shared.text;
            if (!captureRequested && !text) return null;
            return {
                text,
                description: addText ? '' : shared.description,
                save: params.get('save') === '1' && Boolean(text)
            };
        }
        function getSharedCapturePayload(params) {
            const title = normalizeCaptureText(params.get('title'));
            const text = normalizeCaptureText(params.get('text'));
            const url = normalizeCaptureText(params.get('url'));
            const displayText = title || text || url;
            const description = [title && text !== title ? text : '', url]
                .map(value => String(value || '').trim())
                .filter(Boolean)
                .join('\n');
            return {
                text: displayText,
                description: normalizeCaptureDescription(description)
            };
        }
        function normalizeCaptureText(value) {
            return String(value || '').replace(/\s+/g, ' ').trim().slice(0, CONFIG.CAPTURE.MAX_TEXT_LENGTH);
        }
        function normalizeCaptureDescription(value) {
            return String(value || '').replace(/\r\n?/g, '\n').trim().slice(0, CONFIG.CAPTURE.MAX_TEXT_LENGTH * 2);
        }
        function clearLaunchCaptureParams() {
            const url = new URL(window.location.href);
            let changed = false;
            CONFIG.CAPTURE.PARAMS.forEach(param => {
                if (url.searchParams.has(param)) {
                    url.searchParams.delete(param);
                    changed = true;
                }
            });
            if (!changed) return;
            const nextUrl = `${url.pathname}${url.search}${url.hash}`;
            window.history.replaceState(window.history.state, document.title, nextUrl);
        }
        function focusQuickAddForCapture(hasText) {
            requestAnimationFrame(() => {
                if (!state.storageAvailable || DOM.quickAddInput.disabled) return;
                setCaptureShelf(true, { focus: false });
                DOM.quickAddInput.focus();
                if (hasText) {
                    DOM.quickAddInput.setSelectionRange(DOM.quickAddInput.value.length, DOM.quickAddInput.value.length);
                    utils.announce(utils.translate('quickAdd.captureReady'));
                }
            });
        }
        function setQuickAddCaptureDraft(request) {
            clearQuickAddCaptureDraft();
            if (!request.text) return;
            DOM.quickAddInput.value = request.text;
            state.quickAddCaptureDraft = {
                text: request.text,
                description: normalizeCaptureDescription(request.description)
            };
        }
        function getQuickAddCaptureOptions(options = {}) {
            const scope = normalizeProjectFilter(state.projectFilter);
            options = {
                project: workspaceUI.screen === 'tasks' && scope.kind === 'project' ? scope.name : '',
                focusDate: workspaceUI.screen === 'today' || (workspaceUI.screen === 'tasks' && (state.focusMode || workspaceUI.planning)) ? getTodayPlanDateKey() : null,
                ...options
            };
            const draft = state.quickAddCaptureDraft;
            const currentText = DOM.quickAddInput.value.trim();
            if (!draft || !draft.description || !currentText || !isCaptureDraftTextRelated(draft.text, currentText)) return options;
            return { ...options, description: draft.description };
        }
        function isCaptureDraftTextRelated(originalText, currentText) {
            const original = normalizeCaptureText(originalText).toLowerCase();
            const current = normalizeCaptureText(currentText).toLowerCase();
            if (!original || !current) return false;
            return original === current || original.includes(current) || current.includes(original);
        }
        function clearQuickAddCaptureDraft() {
            state.quickAddCaptureDraft = null;
        }
        function setCaptureShelf(open, { focus = false, restoreFocus = false, preserveContext = false } = {}) {
            if (open && isDialogOpen()) return false;
            const shelf = document.getElementById('captureShelf');
            if (!open && !preserveContext && !DOM.quickAddInput.value.trim()) workspaceUI.captureDateKey = '';
            workspaceUI.captureOpen = Boolean(open);
            shelf.hidden = !open;
            shelf.inert = !open;
            document.getElementById('quickCaptureBtn').setAttribute('aria-expanded', String(Boolean(open)));
            syncCapturePreview();
            if (open && focus) {
                const origin = document.activeElement;
                requestAnimationFrame(() => {
                    if (!workspaceUI.captureOpen || isDialogOpen()
                        || !isFocusableReturnElement(DOM.quickAddInput)) return;
                    const active = document.activeElement;
                    if (active !== origin
                        && !(active === document.body && !isFocusableReturnElement(origin))) return;
                    DOM.quickAddInput.focus({ preventScroll: true });
                });
            }
            if (!open && restoreFocus) document.getElementById('quickCaptureBtn').focus({ preventScroll: true });
            return true;
        }
        function syncCapturePreview() {
            const preview = document.getElementById('capturePreview');
            if (!preview || !DOM.quickAddInput) return;
            const raw = DOM.quickAddInput.value.trim();
            const payload = buildTaskPayloadFromQuickAdd(raw, getQuickAddCaptureOptions());
            const parts = [];
            if (payload.dueAt) {
                const due = new Date(payload.dueAt);
                parts.push(new Intl.DateTimeFormat(state.currentLanguage, { year: 'numeric', month: 'short', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' }).format(due));
                if (due.getTime() < Date.now()) parts.push(utils.translate('usability.captureOverdue'));
            } else parts.push(utils.translate('usability.captureNoDate'));
            if (payload.project) parts.push(`${utils.translate('usability.captureProject')}: ${payload.project}`);
            if (payload.focusDate === getTodayPlanDateKey()) parts.push(utils.translate('focus.title'));
            if (payload.tags.length) parts.push(payload.tags.map(tag => `#${tag}`).join(' '));
            preview.textContent = parts.join(' · ');
            preview.classList.toggle('is-overdue', Boolean(payload.dueAt && new Date(payload.dueAt).getTime() < Date.now()));
            preview.hidden = !raw && !workspaceUI.captureDateKey;
            preview.removeAttribute('title');
            syncQuickAddDescriptions();
        }
        function openCaptureDetails() {
            if (!ensureStorageAvailable() || state.quickAddSaving) return;
            const raw = DOM.quickAddInput.value;
            const payload = buildTaskPayloadFromQuickAdd(raw, getQuickAddCaptureOptions());
            setCaptureShelf(false, { preserveContext: true });
            openModal(undefined, { quickPayload: payload, captureText: raw, dueDateKey: workspaceUI.captureDateKey });
        }
        function openNewTaskEditor() {
            if (isDialogOpen() || !ensureStorageAvailable() || state.quickAddSaving) return;
            if (workspaceUI.captureOpen || hasUnsavedQuickAddText()) { openCaptureDetails(); return; }
            openModal(null, { quickPayload: buildTaskPayloadFromQuickAdd('', getQuickAddCaptureOptions()) });
        }
        function syncSettingsTabsOrientation() {
            const navigation = document.querySelector('.settings-section-navigation');
            navigation?.setAttribute('aria-orientation', window.matchMedia('(min-width: 1001px)').matches ? 'vertical' : 'horizontal');
        }
        function setSettingsSection(sectionId) {
            syncSettingsTabsOrientation();
            const buttons = Array.from(document.querySelectorAll('.settings-section-navigation [data-settings-section]'));
            const selected = buttons.some(button => button.dataset.settingsSection === sectionId) ? sectionId : 'settingsAppearance';
            workspaceUI.settingsSection = selected;
            const heading = document.getElementById('settingsTitle');
            const selectedButton = buttons.find(button => button.dataset.settingsSection === selected);
            if (heading && selectedButton) {
                heading.setAttribute('data-i18n', selectedButton.getAttribute('data-i18n'));
                heading.textContent = selectedButton.textContent;
            }
            buttons.forEach(button => {
                const active = button.dataset.settingsSection === selected;
                button.setAttribute('aria-selected', String(active));
                button.tabIndex = active ? 0 : -1;
                const pane = document.getElementById(button.dataset.settingsSection);
                if (pane) { pane.hidden = !active; pane.inert = !active; pane.setAttribute('aria-labelledby', button.id); }
            });
        }
        function handleSettingsTabsKeydown(event) {
            const vertical = window.matchMedia('(min-width: 1001px)').matches;
            const nextKey = vertical ? 'ArrowDown' : 'ArrowRight';
            const previousKey = vertical ? 'ArrowUp' : 'ArrowLeft';
            if (![previousKey, nextKey, 'Home', 'End'].includes(event.key)) return;
            const buttons = Array.from(document.querySelectorAll('.settings-section-navigation [data-settings-section]'));
            const index = buttons.indexOf(event.target.closest('[role="tab"]'));
            if (index < 0) return;
            event.preventDefault();
            const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === nextKey ? 1 : -1) + buttons.length) % buttons.length;
            setSettingsSection(buttons[nextIndex].dataset.settingsSection);
            buttons[nextIndex].focus({ preventScroll: true });
            buttons[nextIndex].scrollIntoView({ block: 'nearest', inline: 'nearest' });
        }
        function resetWorkspaceFilters({ preserveTodayPlan = false } = {}) {
            if (!state.storageAvailable) return;
            clearStatsDrilldown();
            DOM.inputs.search.value = '';
            state.searchQuery = '';
            state.filter = 'all';
            state.projectFilter = { kind: 'all' };
            state.focusMode = Boolean(preserveTodayPlan && state.focusMode);
            closeAllDropdowns();
            syncSearchClearButton();
            renderTaskList();
            syncDropdowns();
            announceTaskViewSummary();
            DOM.inputs.search.focus({ preventScroll: true });
        }
        function buildTaskPayloadFromQuickAdd(rawInput, options = {}) {
            const parsed = parseQuickAddInput(rawInput);
            if ((!parsed.date || parsed.implicitDate) && workspaceUI.captureDateKey) parsed.date = workspaceUI.captureDateKey;
            const dueFields = parsed.date ? createDueFields(parsed.date, parsed.time || CONFIG.DEFAULTS.TIME) : clearDueFields();
            const hasDueDate = Boolean(dueFields.dueAt);
            return {
                name: parsed.name,
                description: normalizeCaptureDescription(options.description),
                project: parsed.project || (Object.hasOwn(options, 'project') ? normalizeTaskProject(options.project) : CONFIG.CAPTURE.INBOX_PROJECT),
                focusDate: normalizeFocusDate(options.focusDate),
                tags: parsed.tags,
                subtasks: [],
                ...dueFields,
                reminderOffset: hasDueDate ? CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES : -1,
                reminderRepeat: -1,
                repeatType: 'none',
                repeatInterval: 1,
                order: getNextTaskOrder()
            };
        }
        const taskInputNameIndex = { tasks: null, revision: -1, projects: [], tags: [] };
        function getTaskInputNames() {
            if (taskInputNameIndex.tasks !== state.tasks || taskInputNameIndex.revision !== state.taskRevision) {
                taskInputNameIndex.tasks = state.tasks;
                taskInputNameIndex.revision = state.taskRevision;
                taskInputNameIndex.projects = getProjectNames().sort((a, b) => b.length - a.length);
                taskInputNameIndex.tags = [...new Set(state.tasks.flatMap(task => normalizeTaskTags(task.tags)))]
                    .sort((a, b) => b.length - a.length);
            }
            return taskInputNameIndex;
        }
        function parseQuickAddInput(rawInput) {
            return TaskInput.parseQuickAddInput(rawInput, {
                names: getTaskInputNames(), now: new Date(),
                dates: { formatDateInputValue: utils.formatDateInputValue, normalizeDueDateValue }
            });
        }
        function buildTaskPayloadFromForm() {
            const dueFields = getFormDueFieldsForSave();
            const hasDueDate = Boolean(dueFields.dueAt);
            const reminderFields = getTaskReminderFieldsForFormSave(hasDueDate);
            const repeatType = hasDueDate ? normalizeTaskRepeatType(DOM.inputs.repeatType.value) : 'none';
            return {
                ...getTaskTextFieldsForFormSave(),
                ...(!isEditingTask() ? { focusDate: state.taskFormSession?.creationFocusDate || null } : {}),
                subtasks: getSubtasksForFormSave(),
                ...dueFields,
                ...reminderFields,
                repeatType,
                repeatInterval: normalizeTaskRepeatInterval(repeatType, DOM.inputs.repeatInterval.value),
                repeatWeekdays: repeatType === 'weekly-days' ? getRepeatWeekdaysForForm() : [],
                repeatPaused: repeatType !== 'none' && DOM.inputs.repeatPaused.checked,
                order: isEditingTask() ? undefined : getNextTaskOrder()
            };
        }
        function getTaskReminderFieldsForFormSave(hasDueDate) {
            const readValue = (select, fallback) => select.value !== '' && Number.isFinite(Number(select.value)) ? Number(select.value) : fallback;
            const reminderOffset = hasDueDate ? readValue(DOM.inputs.reminderOffset, CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES) : -1;
            const fields = {
                reminderOffset,
                reminderRepeat: hasDueDate && reminderOffset !== -1 ? readValue(DOM.inputs.reminderRepeat, -1) : -1
            };
            if (!isEditingTask() || !state.taskFormSession?.baseline || !state.editingTaskSnapshot) return fields;
            const original = JSON.parse(state.editingTaskSnapshot);
            const baseline = JSON.parse(state.taskFormSession.baseline).values;
            if (hasTaskDueDate(original) !== hasDueDate || DOM.inputs.noDeadline.checked !== baseline.noDeadline || DOM.inputs.reminderOffset.value !== baseline.reminderOffset) return fields;
            if (Number.isFinite(original.reminderOffset)) fields.reminderOffset = original.reminderOffset;
            if (DOM.inputs.reminderRepeat.value === baseline.reminderRepeat && Number.isFinite(original.reminderRepeat)) fields.reminderRepeat = original.reminderRepeat;
            return fields;
        }
        function getSubtasksForFormSave() {
            const subtasks = cloneSubtasksWithUniqueIds(state.tempSubtasks);
            const editing = getActiveSubtaskEditInput();
            const edited = editing && subtasks.find(subtask => String(subtask.id) === editing.dataset.subtaskId);
            if (edited && editing.value.trim()) edited.text = editing.value.trim();
            const pending = DOM.inputs.subtask.value.trim();
            if (pending) subtasks.push({ id: createUniqueSubtaskId(subtasks), text: pending, completed: false });
            return subtasks;
        }
        function getTaskTextFieldsForFormSave() {
            const fields = {
                name: DOM.inputs.name.value.trim(),
                description: DOM.inputs.desc.value.trim(),
                project: normalizeTaskProject(DOM.inputs.project.value),
                tags: parseTagsInput(DOM.inputs.tags.value)
            };
            if (!isEditingTask() || !state.taskFormSession?.baseline || !state.editingTaskSnapshot) return fields;
            const original = JSON.parse(state.editingTaskSnapshot);
            const baseline = JSON.parse(state.taskFormSession.baseline).values;
            [['name', 'name'], ['description', 'desc'], ['project', 'project'], ['tags', 'tags']].forEach(([field, input]) => {
                if (DOM.inputs[input].value === baseline[input]) fields[field] = original[field];
            });
            return fields;
        }
        function createTaskRecord(taskPayload) {
            return {
                id: createTaskId(),
                createdAt: new Date().toISOString(),
                completed: false,
                completedAt: null,
                archived: false,
                archivedAt: null,
                focusDate: null,
                snoozedUntil: null,
                lastReminderAt: null,
                repeatSourceId: null,
                repeatCreatedFrom: null,
                nextRepeatTaskId: null,
                repeatWeekdays: [],
                repeatPaused: false,
                ...taskPayload
            };
        }
        function mergeTaskPayload(original, taskPayload) {
            const updatedTask = { ...original, ...taskPayload };
            if (taskPayload.order === undefined) updatedTask.order = original.order || 0;
            if (didReminderSettingsChange(original, updatedTask)) {
                updatedTask.snoozedUntil = null;
                updatedTask.lastReminderAt = null;
            }
            return updatedTask;
        }
        function isEditingTask() {
            return state.editingTaskId !== null;
        }
        function didReminderSettingsChange(original, updatedTask) {
            return getTaskDueInstant(original) !== getTaskDueInstant(updatedTask) ||
                normalizeDueDateValue(original.dueLocalDate) !== normalizeDueDateValue(updatedTask.dueLocalDate) ||
                normalizeDueTimeValue(original.dueLocalTime) !== normalizeDueTimeValue(updatedTask.dueLocalTime) ||
                getTaskReminderOffset(original) !== getTaskReminderOffset(updatedTask) ||
                getTaskReminderRepeat(original) !== getTaskReminderRepeat(updatedTask);
        }
        function getTaskById(id) {
            return state.tasks.find(task => task.id === id);
        }
        function getNextTaskOrder() {
            const maxOrder = state.tasks.length > 0 ? Math.max(...state.tasks.map(task => task.order || 0)) : 0;
            return maxOrder + CONFIG.DEFAULTS.ORDER_STEP;
        }
        async function refreshTasks() {
            state.tasks = await loadNormalizedTasks();
            renderTaskList();
            if (workspaceUI.screen === 'settings') updateBackupHealthStatus().catch(handleBackgroundStorageFailure);
        }
        function cloneSubtasks(subtasks) {
            return Array.isArray(subtasks) ? subtasks.map(subtask => ({ ...subtask })) : [];
        }
        function cloneSubtasksWithUniqueIds(subtasks) {
            const usedIds = new Set();
            return cloneSubtasks(subtasks).map(subtask => ({
                ...subtask,
                id: normalizeUniqueNumericId(subtask.id, usedIds)
            }));
        }
        function createUniqueNumericId(usedIds) {
            let id;
            do {
                id = Date.now() + Math.floor(Math.random() * 1000000);
            } while (usedIds.has(id));
            usedIds.add(id);
            return id;
        }
        function normalizeUniqueNumericId(value, usedIds) {
            const id = normalizeTaskReferenceId(value);
            if (id !== null && !usedIds.has(id)) {
                usedIds.add(id);
                return id;
            }
            return createUniqueNumericId(usedIds);
        }
        function createUniqueSubtaskId(subtasks) {
            const usedIds = new Set(cloneSubtasks(subtasks)
                .map(subtask => Number(subtask.id))
                .filter(Number.isFinite));
            return createUniqueNumericId(usedIds);
        }
        function createTaskId(usedIds = new Set(state.tasks.map(task => Number(task.id)).filter(Number.isFinite))) {
            return createUniqueNumericId(usedIds);
        }
        function getFormDueFieldsForSave() {
            if (DOM.inputs.noDeadline.checked || !DOM.inputs.date.value) return clearDueFields();
            const original = isEditingTask() ? getTaskById(state.editingTaskId) : null;
            const originalInstant = original ? getTaskDueInstant(original) : null;
            if (originalInstant && DOM.inputs.date.value === getTaskDueDateKey(original) && DOM.inputs.time.value === getTaskDueTimeValue(original)) {
                return createDueFieldsFromInstant(originalInstant, getTaskDueTimeZone(original));
            }
            return createDueFields(DOM.inputs.date.value, DOM.inputs.time.value, getFormDueTimeZoneForSave());
        }
        function getFormDueTimeZoneForSave() {
            if (!isEditingTask()) return getCurrentTimeZone();
            const original = getTaskById(state.editingTaskId);
            if (!original || !hasTaskDueDate(original)) return getCurrentTimeZone();
            const formDate = normalizeDueDateValue(DOM.inputs.date.value);
            const formTime = normalizeDueTimeValue(DOM.inputs.time.value) || CONFIG.DEFAULTS.TIME;
            if (formDate === getTaskDueDateKey(original) && formTime === getTaskDueTimeValue(original)) {
                return getTaskDueTimeZone(original);
            }
            return getCurrentTimeZone();
        }
        function formatTaskDueDate(task) {
            const dueAt = getTaskDueInstant(task);
            if (dueAt) return utils.formatDate(dueAt, getTaskDueTimeZone(task));
            const localDate = getTaskDueLocalDate(task);
            return localDate ? utils.formatDateObject(localDate) : '';
        }
        async function loadNormalizedTasks() {
            const loadedTasks = await dbActions.getAllTasks();
            const { tasks, changed } = normalizeTaskRecords(loadedTasks);
            if (changed) await dbActions.updateTasks(tasks);
            return tasks;
        }
        function normalizeTaskRecords(tasks) {
            let changed = false;
            const normalizedTasks = tasks.map(task => {
                const result = normalizeSubtasksForTask(task.subtasks);
                const normalizedTask = { ...task, subtasks: result.subtasks };
                if (result.changed) changed = true;
                const dueFields = normalizeTaskDueFields(normalizedTask);
                ['dueDate', 'dueAt', 'dueLocalDate', 'dueLocalTime', 'dueTimeZone'].forEach(key => {
                    if (normalizedTask[key] !== dueFields[key]) {
                        normalizedTask[key] = dueFields[key];
                        changed = true;
                    }
                });
                const completed = normalizeBoolean(normalizedTask.completed);
                if (normalizedTask.completed !== completed) {
                    normalizedTask.completed = completed;
                    changed = true;
                }
                const archived = normalizeBoolean(normalizedTask.archived);
                if (normalizedTask.archived !== archived) {
                    normalizedTask.archived = archived;
                    changed = true;
                }
                if (normalizedTask.archivedAt && !normalizeStoredDate(normalizedTask.archivedAt)) {
                    normalizedTask.archivedAt = null;
                    changed = true;
                }
                if (!('archivedAt' in normalizedTask)) {
                    normalizedTask.archivedAt = null;
                    changed = true;
                }
                if (normalizedTask.completedAt && !normalizeStoredDate(normalizedTask.completedAt)) {
                    normalizedTask.completedAt = null;
                    changed = true;
                }
                if (!('completedAt' in normalizedTask)) {
                    normalizedTask.completedAt = null;
                    changed = true;
                }
                const project = normalizeTaskProject(normalizedTask.project);
                if (normalizedTask.project !== project) {
                    normalizedTask.project = project;
                    changed = true;
                }
                const tags = normalizeTaskTags(normalizedTask.tags);
                if (!Array.isArray(normalizedTask.tags) || JSON.stringify(normalizedTask.tags) !== JSON.stringify(tags)) {
                    normalizedTask.tags = tags;
                    changed = true;
                }
                if (!Number.isFinite(Number(normalizedTask.reminderRepeat))) {
                    normalizedTask.reminderRepeat = -1;
                    changed = true;
                } else {
                    const reminderRepeat = Number(normalizedTask.reminderRepeat);
                    if (normalizedTask.reminderRepeat !== reminderRepeat) changed = true;
                    normalizedTask.reminderRepeat = reminderRepeat;
                }
                const repeatType = normalizeTaskRepeatType(normalizedTask.repeatType);
                if (normalizedTask.repeatType !== repeatType) {
                    normalizedTask.repeatType = repeatType;
                    changed = true;
                }
                const repeatInterval = normalizeTaskRepeatInterval(repeatType, normalizedTask.repeatInterval);
                if (normalizedTask.repeatInterval !== repeatInterval) {
                    normalizedTask.repeatInterval = repeatInterval;
                    changed = true;
                }
                const repeatWeekdays = repeatType === 'weekly-days' ? getTaskRepeatWeekdays(normalizedTask) : [];
                if (!Array.isArray(normalizedTask.repeatWeekdays) || JSON.stringify(normalizedTask.repeatWeekdays) !== JSON.stringify(repeatWeekdays)) {
                    normalizedTask.repeatWeekdays = repeatWeekdays;
                    changed = true;
                }
                const repeatPaused = normalizedTask.repeatPaused === true;
                if (normalizedTask.repeatPaused !== repeatPaused) {
                    normalizedTask.repeatPaused = repeatPaused;
                    changed = true;
                }
                const focusDate = normalizeFocusDate(normalizedTask.focusDate);
                if (normalizedTask.focusDate !== focusDate) {
                    normalizedTask.focusDate = focusDate;
                    changed = true;
                }
                ['repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId'].forEach(key => {
                    const value = normalizeTaskReferenceId(normalizedTask[key]);
                    if (normalizedTask[key] !== value) changed = true;
                    normalizedTask[key] = value;
                });
                if (normalizedTask.snoozedUntil && !normalizeStoredDate(normalizedTask.snoozedUntil)) {
                    normalizedTask.snoozedUntil = null;
                    changed = true;
                }
                if (normalizedTask.lastReminderAt && !normalizeStoredDate(normalizedTask.lastReminderAt)) {
                    normalizedTask.lastReminderAt = null;
                    changed = true;
                }
                if (!('snoozedUntil' in normalizedTask)) {
                    normalizedTask.snoozedUntil = null;
                    changed = true;
                }
                if (!('lastReminderAt' in normalizedTask)) {
                    normalizedTask.lastReminderAt = null;
                    changed = true;
                }
                return normalizedTask;
            });
            return { tasks: normalizedTasks, changed };
        }
        function normalizeSubtasksForTask(subtasks) {
            if (!Array.isArray(subtasks)) return { subtasks: [], changed: Boolean(subtasks) };
            const usedIds = new Set();
            let changed = false;
            const normalizedSubtasks = subtasks.map(subtask => {
                const sourceSubtask = subtask && typeof subtask === 'object' ? subtask : {};
                const normalizedId = normalizeUniqueNumericId(sourceSubtask.id, usedIds);
                const completed = normalizeBoolean(sourceSubtask.completed);
                if (sourceSubtask.id !== normalizedId) changed = true;
                if (sourceSubtask.completed !== completed) changed = true;
                return { ...sourceSubtask, id: normalizedId, completed };
            });
            return { subtasks: normalizedSubtasks, changed };
        }
        function normalizeBoolean(value, defaultValue = false) {
            if (typeof value === 'boolean') return value;
            if (typeof value === 'string') {
                const normalized = value.trim().toLowerCase();
                if (normalized === 'true') return true;
                if (normalized === 'false') return false;
            }
            if (typeof value === 'number') {
                if (value === 1) return true;
                if (value === 0) return false;
            }
            return defaultValue;
        }
        function editTask(id) {
            const task = getTaskById(id);
            if (!task) return;
            openModal(task);
        }
        async function deleteTask(id) {
            if (!ensureStorageAvailable()) return;
            const t = state.translations[state.currentLanguage];
            const task = getTaskById(id);
            if (!task) return;
            const message = document.createElement('p');
            message.textContent = utils.translate('craft.deleteTaskMessage').replace('{task}', task.name);
            confirmTaskChanges(utils.translate('craft.deleteTaskTitle'), message, async () => {
                try {
                    const beforeTasks = captureUndoSnapshot();
                    await dbActions.deleteTask(id);
                    await refreshTasks();
                    registerUndoSnapshot(t['undo.labels.delete'], beforeTasks);
                    utils.notify(t['messages.task.deleted'], 'success', { undo: true });
                } catch (e) {
                    console.error('删除任务失败:', e);
                    handleStorageOperationError(e, 'messages.task.deleteError');
                    return false;
                }
            });
            DOM.submitBtn.textContent = t['task.actions.delete'];
            DOM.submitBtn.classList.add('btn-danger');
            DOM.cancelBtn.focus();
        }
        async function toggleTaskComplete(id) {
            if (!ensureStorageAvailable()) return;
            const task = getTaskById(id);
            if (!task) return;
            const t = state.translations[state.currentLanguage];
            const beforeTasks = captureUndoSnapshot();
            const previousCompleted = task.completed;
            const previousCompletedAt = task.completedAt || null;
            const previousNextRepeatTaskId = task.nextRepeatTaskId ?? null;
            const nextRepeatTask = !previousCompleted && shouldCreateNextRepeatTask(task) ? createNextRepeatTask(task) : null;
            task.completed = !previousCompleted;
            task.completedAt = task.completed ? new Date().toISOString() : null;
            if (nextRepeatTask) task.nextRepeatTaskId = nextRepeatTask.id;
            try {
                if (nextRepeatTask) {
                    await dbActions.updateTasks([task, nextRepeatTask]);
                } else {
                    await dbActions.updateTask(task);
                }
                const el = document.querySelector(`.task-item[data-task-id="${id}"]`);
                if (el && task.completed) {
                    el.classList.add(CONFIG.UI.CLASSES.ANIMATE);
                    setTimeout(() => el.classList.remove(CONFIG.UI.CLASSES.ANIMATE), 500);
                }
                registerUndoSnapshot(t['undo.labels.complete'], beforeTasks);
                utils.notify(nextRepeatTask ? t['messages.task.repeatCreated'] : (task.completed ? t['messages.task.markedComplete'] : t['messages.task.markedIncomplete']), 'success', { undo: true });
                await refreshTasks();
            } catch (err) {
                console.error('更新任务状态失败:', err);
                task.completed = previousCompleted;
                task.completedAt = previousCompletedAt;
                task.nextRepeatTaskId = previousNextRepeatTaskId;
                renderTaskList();
                handleStorageOperationError(err);
            }
        }
        async function skipRepeatOccurrence(id) {
            if (!ensureStorageAvailable()) return;
            const task = getTaskById(id);
            if (!task || !shouldShowSkipRepeatAction(task)) return;
            if (findExistingRepeatSuccessor(task)) {
                utils.notify(utils.translate('messages.task.repeatAlreadyScheduled'), 'warning');
                return;
            }
            const t = state.translations[state.currentLanguage];
            const beforeTasks = captureUndoSnapshot();
            const updatedTask = {
                ...task,
                ...calculateNextRepeatDueFields(task, getTaskRepeatRule(task)),
                snoozedUntil: null,
                lastReminderAt: null
            };
            try {
                await dbActions.updateTask(updatedTask);
                clearTaskNotificationDeliveryState(task.id);
                registerUndoSnapshot(t['undo.labels.skipRepeat'], beforeTasks);
                utils.notify(t['messages.task.repeatSkipped'], 'success', { undo: true });
                await refreshTasks();
            } catch (err) {
                console.error('跳过重复任务失败:', err);
                handleStorageOperationError(err);
            }
        }
        function getRepeatLineageIndex() {
            if (getRepeatLineageIndex.cached?.tasks === state.tasks) return getRepeatLineageIndex.cached;
            const byId = new Map();
            const children = new Map();
            const byRoot = new Map();
            state.tasks.forEach(task => {
                const id = normalizeTaskReferenceId(task.id);
                if (id === null) return;
                byId.set(id, task);
                const parent = normalizeTaskReferenceId(task.repeatCreatedFrom);
                if (parent !== null) {
                    if (!children.has(parent)) children.set(parent, []);
                    children.get(parent).push(id);
                }
                const root = normalizeTaskReferenceId(task.repeatSourceId);
                if (root !== null) {
                    if (!byRoot.has(root)) byRoot.set(root, []);
                    byRoot.get(root).push(id);
                }
            });
            const index = { tasks: state.tasks, byId, children, byRoot };
            getRepeatLineageIndex.cached = index;
            return index;
        }
        function getRepeatDeletionUpdates(tasks, ids) {
            const deleted = new Set(ids.map(normalizeTaskReferenceId).filter(id => id !== null));
            const byId = new Map(tasks.map(task => [normalizeTaskReferenceId(task.id), task]).filter(([id]) => id !== null));
            const next = new Map([...byId.keys()].map(id => [id, new Set()]));
            const previous = new Map([...byId.keys()].map(id => [id, new Set()]));
            const addLink = (from, to) => {
                if (!byId.has(from) || !byId.has(to)) return;
                next.get(from).add(to);
                previous.get(to).add(from);
            };
            byId.forEach((task, id) => {
                addLink(id, normalizeTaskReferenceId(task.nextRepeatTaskId));
                addLink(normalizeTaskReferenceId(task.repeatCreatedFrom), id);
            });
            const degree = new Map([...previous].map(([id, links]) => [id, links.size]));
            const order = [...degree].filter(([, count]) => count === 0).map(([id]) => id);
            for (let offset = 0; offset < order.length; offset++) {
                next.get(order[offset]).forEach(id => {
                    degree.set(id, degree.get(id) - 1);
                    if (degree.get(id) === 0) order.push(id);
                });
            }
            const blocked = new Set([...degree].filter(([, count]) => count > 0).map(([id]) => id));
            const pending = [...blocked];
            while (pending.length) {
                const id = pending.pop();
                [...next.get(id), ...previous.get(id)].forEach(neighbor => {
                    if (blocked.has(neighbor)) return;
                    blocked.add(neighbor);
                    pending.push(neighbor);
                });
            }
            const resolve = (links, sequence) => {
                const resolved = new Map();
                sequence.forEach(id => {
                    if (!deleted.has(id) || blocked.has(id)) return;
                    const candidates = new Set();
                    let ambiguous = false;
                    links.get(id).forEach(neighbor => {
                        const candidate = deleted.has(neighbor) ? resolved.get(neighbor) : neighbor;
                        if (candidate === undefined) ambiguous = true;
                        else if (candidate !== null) candidates.add(candidate);
                    });
                    resolved.set(id, ambiguous || candidates.size > 1 ? undefined : (candidates.values().next().value ?? null));
                });
                return resolved;
            };
            const successors = resolve(next, [...order].reverse());
            const predecessors = resolve(previous, order);
            const updates = [];
            byId.forEach((task, id) => {
                if (deleted.has(id) || blocked.has(id)) return;
                const updated = { ...task };
                [['nextRepeatTaskId', successors], ['repeatCreatedFrom', predecessors]].forEach(([field, resolved]) => {
                    const reference = normalizeTaskReferenceId(task[field]);
                    if (deleted.has(reference) && resolved.has(reference) && resolved.get(reference) !== undefined) updated[field] = resolved.get(reference);
                });
                if (updated.nextRepeatTaskId !== task.nextRepeatTaskId || updated.repeatCreatedFrom !== task.repeatCreatedFrom) updates.push(updated);
            });
            return updates;
        }
        function findExistingRepeatSuccessor(task) {
            const id = normalizeTaskReferenceId(task.id);
            if (id === null) return null;
            const index = getRepeatLineageIndex();
            const pending = [normalizeTaskReferenceId(task.nextRepeatTaskId), ...(index.children.get(id) || [])];
            const visited = new Set([id]);
            while (pending.length) {
                const candidateId = pending.pop();
                if (candidateId === null || visited.has(candidateId)) continue;
                visited.add(candidateId);
                const candidate = index.byId.get(candidateId);
                if (candidate) return candidate;
                pending.push(...(index.children.get(candidateId) || []));
            }
            const root = normalizeTaskReferenceId(task.repeatSourceId);
            if (root === null || root === id) {
                const descendantId = (index.byRoot.get(id) || []).find(candidateId => candidateId !== id);
                if (descendantId !== undefined) return index.byId.get(descendantId) || null;
            }
            return null;
        }
        function shouldCreateNextRepeatTask(task) {
            const rule = getTaskRepeatRule(task);
            if (!hasTaskDueDate(task) || task.completed || task.archived || rule.type === 'none' || rule.paused) return false;
            return !findExistingRepeatSuccessor(task);
        }
        function createNextRepeatTask(task) {
            const usedIds = new Set(state.tasks.map(item => Number(item.id)).filter(Number.isFinite));
            return createNextRepeatTaskWithUsedIds(task, usedIds);
        }
        function createNextRepeatTaskWithUsedIds(task, usedIds, order = getNextTaskOrder()) {
            const nextId = createUniqueNumericId(usedIds);
            const now = new Date().toISOString();
            return {
                ...task,
                id: nextId,
                ...calculateNextRepeatDueFields(task, getTaskRepeatRule(task)),
                focusDate: null,
                completed: false,
                completedAt: null,
                archived: false,
                archivedAt: null,
                snoozedUntil: null,
                lastReminderAt: null,
                subtasks: resetRepeatedSubtasks(task.subtasks),
                createdAt: now,
                repeatSourceId: normalizeTaskReferenceId(task.repeatSourceId) ?? task.id,
                repeatCreatedFrom: task.id,
                nextRepeatTaskId: null,
                order
            };
        }
        function resetRepeatedSubtasks(subtasks) {
            return cloneSubtasksWithUniqueIds(subtasks).map(subtask => ({ ...subtask, completed: false }));
        }
        async function handleClearCompleted() {
            if (!ensureStorageAvailable()) return;
            const t = state.translations[state.currentLanguage];
            const completed = state.tasks.filter(x => x.completed && !x.archived);
            if (completed.length === 0) return utils.notify(t['messages.clearCompleted.none'], 'warning');
            confirmTaskChanges(t['actions.clearCompleted'], translateCount('messages.clearCompleted.confirm', completed.length).replace('{count}', completed.length), async () => {
                try {
                    const beforeTasks = captureUndoSnapshot();
                    const completedIds = new Set(completed.map(task => task.id));
                    await dbActions.deleteTasks([...completedIds]);
                    await refreshTasks();
                    registerUndoSnapshot(t['undo.labels.clearCompleted'], beforeTasks);
                    utils.notify(translateCount('messages.clearCompleted.success', completed.length).replace('{count}', completed.length), 'success', { undo: true });
                } catch (e) {
                    console.error('清除已完成任务失败:', e);
                    if (!handleStorageOperationError(e, 'messages.clearCompleted.error')) throw e;
                }
            });
            DOM.submitBtn.textContent = translateCount('dataReview.deleteAction', completed.length).replace('{count}', completed.length);
            DOM.submitBtn.classList.add('btn-danger');
        }
        async function handleArchiveCompleted() {
            if (!ensureStorageAvailable()) return;
            const t = state.translations[state.currentLanguage];
            const completed = state.tasks.filter(task => task.completed && !task.archived);
            closeMenu();
            if (completed.length === 0) return utils.notify(t['messages.archive.none'], 'warning');
            confirmTaskChanges(t['actions.archiveCompleted'], translateCount('messages.archive.confirm', completed.length).replace('{count}', completed.length), async () => {
                const beforeTasks = captureUndoSnapshot();
                const archivedAt = new Date().toISOString();
                const archivedTasks = completed.map(task => ({ ...task, archived: true, archivedAt }));
                try {
                    await dbActions.updateTasks(archivedTasks);
                    await refreshTasks();
                    registerUndoSnapshot(t['undo.labels.archiveCompleted'], beforeTasks);
                    utils.notify(translateCount('messages.archive.success', completed.length).replace('{count}', completed.length), 'success', { undo: true });
                } catch (error) {
                    console.error('归档已完成任务失败:', error);
                    if (!handleStorageOperationError(error, 'messages.archive.error')) throw error;
                }
            });
            DOM.submitBtn.textContent = translateCount('dataReview.archiveAction', completed.length).replace('{count}', completed.length);
        }
        async function toggleTaskArchive(id) {
            if (!ensureStorageAvailable()) return;
            const task = getTaskById(id);
            if (!task) return;
            const t = state.translations[state.currentLanguage];
            const beforeTasks = captureUndoSnapshot();
            const wasArchived = !!task.archived;
            const updatedTask = {
                ...task,
                archived: !wasArchived,
                archivedAt: !wasArchived ? new Date().toISOString() : null
            };
            try {
                await dbActions.updateTask(updatedTask);
                Object.assign(task, { archived: updatedTask.archived, archivedAt: updatedTask.archivedAt });
                renderTaskList();
                registerUndoSnapshot(t['undo.labels.archive'], beforeTasks);
                utils.notify(updatedTask.archived ? t['messages.archive.taskArchived'] : t['messages.archive.taskRestored'], 'success', { undo: true });
            } catch (error) {
                console.error('更新归档状态失败:', error);
                handleStorageOperationError(error, 'messages.archive.error');
            }
        }
        async function toggleTaskFocus(id) {
            if (!ensureStorageAvailable()) return;
            const task = getTaskById(id);
            if (!task || task.archived) return;
            const t = state.translations[state.currentLanguage];
            const beforeTasks = captureUndoSnapshot();
            const wasInFocus = isTaskInTodayPlan(task);
            const updatedTask = { ...task, focusDate: wasInFocus ? null : getTodayPlanDateKey() };
            try {
                await dbActions.updateTask(updatedTask);
                Object.assign(task, { focusDate: updatedTask.focusDate });
                renderTaskList();
                registerUndoSnapshot(t['undo.labels.focus'], beforeTasks);
                utils.notify(wasInFocus ? t['focus.removed'] : t['focus.added'], 'success', { undo: true });
            } catch (error) {
                console.error('更新今日计划失败:', error);
                handleStorageOperationError(error, 'messages.task.updateError');
            }
        }
        async function snoozeTaskReminder(id) {
            if (!ensureStorageAvailable()) return;
            const task = getTaskById(id);
            if (!task || !shouldShowReminderIcon(task)) return;
            const t = state.translations[state.currentLanguage];
            const beforeTasks = captureUndoSnapshot();
            const snoozedUntilAt = new Date(Date.now() + CONFIG.NOTIFICATIONS.SNOOZE_MINUTES * 60000).toISOString();
            const updatedTask = { ...task, snoozedUntil: snoozedUntilAt };
            try {
                await dbActions.updateTask(updatedTask);
                task.snoozedUntil = snoozedUntilAt;
                clearTaskNotificationDeliveryState(task.id);
                renderTaskList();
                registerUndoSnapshot(t['undo.labels.snooze'], beforeTasks);
                utils.notify(translateCount('messages.task.snoozed', CONFIG.NOTIFICATIONS.SNOOZE_MINUTES).replace('{minutes}', CONFIG.NOTIFICATIONS.SNOOZE_MINUTES), 'success', { undo: true });
            } catch (error) {
                console.error('稍后提醒失败:', error);
                handleStorageOperationError(error);
            }
        }
        async function restoreNotificationSetting(savedNotify) {
            if (savedNotify !== true) {
                state.notificationsEnabled = false;
                return;
            }
            if (!supportsNotifications() || !hasNotificationPermission()) {
                await dbActions.setConfig(CONFIG.STORAGE.NOTIFICATIONS, false);
                state.notificationsEnabled = false;
                return;
            }
            state.notificationsEnabled = true;
        }
        function handleNotificationToggleError(error) {
            console.error('切换通知设置失败:', error);
            updateNotificationBtnUI();
            handleStorageOperationError(error);
        }
        async function toggleNotifications() {
            if (!ensureStorageAvailable()) return;
            if (state.notificationsEnabled) {
                await setNotificationsEnabled(false);
                utils.notify(utils.translate('notifications.disable'));
                updateNotificationBtnUI();
                return;
            }
            const granted = await requestNotificationPermission();
            if (granted) {
                await setNotificationsEnabled(true);
                utils.notify(utils.translate('settings.notificationEnabled'));
                checkNotifications();
            }
            updateNotificationBtnUI();
        }
        async function requestNotificationPermission() {
            if (!supportsNotifications()) {
                utils.notify(utils.translate('notifications.notSupported'), 'error');
                return false;
            }
            if (typeof Notification.requestPermission !== 'function') {
                utils.notify(utils.translate('notifications.notSupported'), 'error');
                return false;
            }
            if (Notification.permission === 'denied') {
                utils.notify(utils.translate('settings.notificationBlockedHelp'), 'warning');
                return false;
            }
            try {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') return true;
                utils.notify(utils.translate('notifications.permissionDenied'), 'warning');
            } catch (error) {
                console.error('Error requesting permission:', error);
                utils.notify(utils.translate('notifications.error'), 'error');
            }
            return false;
        }
        async function setNotificationsEnabled(enabled) {
            await dbActions.setConfig(CONFIG.STORAGE.NOTIFICATIONS, enabled);
            state.notificationsEnabled = enabled;
            document.querySelectorAll('.task-item[data-task-id]').forEach(element => {
                const task = getTaskById(Number(element.dataset.taskId));
                if (task) renderTaskMeta(element, task);
            });
        }
        function supportsNotifications() {
            return 'Notification' in window;
        }
        function hasNotificationPermission() {
            return supportsNotifications() && Notification.permission === 'granted';
        }
        function updateNotificationBtnUI() {
            const btn = DOM.notificationToggleBtn;
            if (!btn) return;
            const blocked = supportsNotifications() && Notification.permission === 'denied';
            const unsupported = !supportsNotifications();
            const label = blocked ? utils.translate('usability.notificationHelp')
                : unsupported ? utils.translate('usability.notificationHelp')
                : utils.translate(state.notificationsEnabled ? 'notifications.disable' : 'notifications.enable');
            const statusKey = unsupported ? 'notificationUnsupported' : blocked ? 'notificationBlocked'
                : state.notificationsEnabled && hasNotificationPermission() ? 'notificationEnabled' : 'notificationDisabled';
            btn.dataset.notificationState = statusKey;
            const notificationStatus = document.getElementById('settingsNotificationStatus');
            if (notificationStatus) notificationStatus.textContent = utils.translate(`settings.${statusKey}`);
            if (blocked || unsupported) btn.removeAttribute('aria-pressed');
            else btn.setAttribute('aria-pressed', String(state.notificationsEnabled && hasNotificationPermission()));
            if (notificationStatus?.textContent.trim()) btn.setAttribute('aria-describedby', notificationStatus.id);
            else btn.removeAttribute('aria-describedby');
            const iconUse = btn.querySelector('use');
            const textSpan = btn.querySelector('span');
            btn.classList.toggle('notifications-enabled', state.notificationsEnabled);
            if (state.notificationsEnabled) {
                iconUse.setAttribute('href', '#icon-bell');
            } else {
                iconUse.setAttribute('href', '#icon-bell-off');
            }
            if (textSpan) textSpan.textContent = label;
            btn.title = label;
            btn.setAttribute('aria-label', label);
        }
        function openNotificationHelp() {
            const target = captureFocusReturnTarget();
            utils.confirm(utils.translate('usability.notificationHelpTitle'), utils.translate('usability.notificationHelpBody'), () => {});
            DOM.cancelBtn.hidden = true;
            DOM.submitBtn.textContent = utils.translate('help.close');
            state.elementToFocusOnClose = target;
        }
        function checkNotifications() {
            if (!state.notificationsEnabled) return;
            state.tasks.forEach(task => {
                if (task.completed || task.archived || !hasTaskDueDate(task)) return;
                const timeLeft = calculateTaskTimeLeft(task);
                if (timeLeft === null) return;
                const offset = getTaskReminderOffset(task);
                if (offset === -1) return;
                const notificationKey = getTaskNotificationKey(task, offset);
                const dueState = getTaskReminderDueState(task, timeLeft, offset);
                if ((!dueState.due && !dueState.missed) || !shouldDeliverTaskReminder(task, notificationKey, dueState) || state.pendingNotificationKeys.has(notificationKey)) return;
                state.pendingNotificationKeys.add(notificationKey);
                deliverTaskReminder(task, notificationKey, dueState)
                    .catch(error => {
                        console.warn('提醒投递失败:', error);
                        handleStorageOperationError(error);
                    })
                    .finally(() => {
                        state.pendingNotificationKeys.delete(notificationKey);
                    });
            });
        }
        function shouldSendReminder(timeLeft, offset) {
            return timeLeft <= offset && timeLeft > -CONFIG.NOTIFICATIONS.DELIVERY_WINDOW_MINUTES;
        }
        function getTaskReminderDueState(task, timeLeft, offset) {
            const now = new Date();
            const snoozedUntil = normalizeStoredDate(task.snoozedUntil);
            if (snoozedUntil) {
                if (new Date(snoozedUntil) > now) return { due: false, missed: false, snoozed: true };
                return { due: true, missed: false, snoozed: true };
            }
            return {
                due: shouldSendReminder(timeLeft, offset),
                missed: isMissedReminder(timeLeft, offset),
                snoozed: false
            };
        }
        function isMissedReminder(timeLeft, offset) {
            return timeLeft <= offset - CONFIG.NOTIFICATIONS.DELIVERY_WINDOW_MINUTES;
        }
        function shouldDeliverTaskReminder(task, notificationKey, dueState) {
            if (dueState.snoozed) return true;
            const repeat = getTaskReminderRepeat(task);
            const deliveredInSession = state.notifiedTasks.has(notificationKey);
            if (!task.lastReminderAt) return !deliveredInSession;
            const last = new Date(task.lastReminderAt);
            if (Number.isNaN(last.getTime())) return !deliveredInSession;
            if (repeat === -1) return false;
            return (Date.now() - last.getTime()) / 60000 >= repeat;
        }
        async function deliverTaskReminder(task, notificationKey, dueState) {
            const expected = { id: task.id, key: notificationKey, snoozedUntil: task.snoozedUntil || null, lastReminderAt: task.lastReminderAt || null };
            const messageKey = dueState.missed ? 'notifications.missedReminder' : 'notifications.taskDue';
            const body = utils.translate(messageKey).replace('{taskName}', task.name);
            const sent = await sendNotification(body);
            if (!sent) return;
            const lastReminderAt = new Date().toISOString();
            const recorded = await dbActions.recordReminderDelivery(expected, lastReminderAt);
            await refreshTasks();
            if (!recorded) return;
            state.notifiedTasks.add(notificationKey);
            safeSetStorageItem('sessionStorage', CONFIG.STORAGE.NOTIFIED_TASKS, JSON.stringify([...state.notifiedTasks]));
            markReminderIconNotified(task.id);
            if (dueState.missed) utils.notify(body, 'warning');
        }
        function getTaskReminderOffset(task) {
            const offset = Number(task.reminderOffset);
            return Number.isFinite(offset) ? offset : CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES;
        }
        function getTaskReminderRepeat(task) {
            const repeat = Number(task.reminderRepeat);
            return Number.isFinite(repeat) && repeat > 0 ? repeat : -1;
        }
        function getTaskNotificationKey(task, offset = getTaskReminderOffset(task)) {
            const dueKey = getTaskDueInstant(task) || normalizeDueDateValue(task.dueLocalDate) || 'no-date';
            return `${task.id}|${dueKey}|${offset}`;
        }
        function markReminderIconNotified(taskId) {
            const el = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
            const icon = el ? el.querySelector('.task-reminder-icon') : null;
            if (icon) icon.style.color = 'var(--text-tertiary)';
        }
        async function sendNotification(body) {
            if (!hasNotificationPermission()) return false;
            const title = utils.translate('app.title');
            const options = {
                body: body,
                icon: CONFIG.NOTIFICATIONS.ICON,
                vibrate: CONFIG.NOTIFICATIONS.VIBRATE_PATTERN,
                requireInteraction: true
            };
            let sent = false;
            if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                sent = await showServiceWorkerNotification(title, options);
            } else {
                sent = showWindowNotification(title, options);
            }
            if (sent) {
                playNotificationFeedback();
                vibrateNotification();
            }
            return sent;
        }
        async function showServiceWorkerNotification(title, options) {
            try {
                const registration = await navigator.serviceWorker.ready;
                await registration.showNotification(title, options);
                return true;
            } catch (error) {
                console.warn('Service worker notification failed:', error);
                return showWindowNotification(title, options);
            }
        }
        function showWindowNotification(title, options) {
            try {
                const notification = new Notification(title, options);
                notification.onclick = () => {
                    window.focus();
                    notification.close();
                };
                return true;
            } catch (error) {
                console.warn('Window notification failed:', error);
                return false;
            }
        }
        function playNotificationFeedback() {
            try {
                const audio = new Audio(CONFIG.NOTIFICATIONS.SOUND_SRC);
                audio.volume = 0.6;
                const playPromise = audio.play();
                if (playPromise) playPromise.catch(e => console.warn('Audio play blocked/failed:', e));
            } catch (e) {
                console.error('Audio setup error:', e);
            }
        }
        function vibrateNotification() {
            if ('vibrate' in navigator && typeof navigator.vibrate === 'function') {
                if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return;
                try {
                    navigator.vibrate(CONFIG.NOTIFICATIONS.VIBRATE_PATTERN);
                } catch (error) {
                    console.warn('Vibration failed:', error);
                }
            }
        }
        function handleAddSubtaskInput() {
            const editing = getActiveSubtaskEditInput();
            if (editing && state.composingInputs.has(editing)) return;
            const val = DOM.inputs.subtask.value.trim();
            if (!val) return;
            state.tempSubtasks.push({ id: createUniqueSubtaskId(state.tempSubtasks), text: val, completed: false });
            DOM.inputs.subtask.value = '';
            renderSubtaskPreview();
            DOM.inputs.subtask.focus();
        }
        async function toggleSubtaskComplete(taskId, subtaskId) {
            if (!ensureStorageAvailable()) return;
            const task = getTaskById(taskId);
            if (!task || !task.subtasks) return;
            const sub = task.subtasks.find(s => s.id === subtaskId);
            if (sub) {
                const nextCompleted = !sub.completed;
                const updatedSubtasks = task.subtasks.map(item => item.id === subtaskId ? { ...item, completed: nextCompleted } : { ...item });
                const updatedTask = { ...task, subtasks: updatedSubtasks };
                try {
                    await dbActions.updateTask(updatedTask);
                    task.subtasks = updatedSubtasks;
                    updateSubtaskCompletionDisplay(taskId, subtaskId, nextCompleted);
                } catch (error) {
                    console.error('更新子任务状态失败:', error);
                    renderTaskList();
                    handleStorageOperationError(error);
                }
            }
        }
        function updateSubtaskCompletionDisplay(taskId, subtaskId, completed) {
            const task = getTaskById(taskId);
            const taskEl = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
            if (!task || !taskEl) return;
            const checkbox = taskEl.querySelector(`.subtask-checkbox[data-subtask-id="${subtaskId}"]`);
            if (checkbox) {
                checkbox.checked = completed;
                const row = checkbox.closest('.subtask-display-item');
                if (row) row.classList.toggle(CONFIG.UI.CLASSES.COMPLETED, completed);
            }
            const total = task.subtasks.length;
            const completedCount = task.subtasks.filter(s => s.completed).length;
            const progressText = taskEl.querySelector('.subtask-summary-bar .progress-text');
            if (progressText) progressText.textContent = `${completedCount}/${total} ${state.translations[state.currentLanguage]['task.subtasks']}`;
        }
        function updateFilterCounts() {
            const counts = getFilterCounts();
            setFilterCountText('count-all', counts.all);
            setFilterCountText('count-active', counts.active);
            setFilterCountText('count-completed', counts.completed);
            setFilterCountText('count-archived', counts.archived);
            setFilterCountText('count-overdue', counts.overdue);
            setFilterCountText('count-no-deadline', counts['no-deadline']);
        }
        function getFilterCounts() {
            const scopedTasks = state.tasks.filter(matchesTaskProject);
            const includeCompletionHistory = hasSearchCompletionFilter();
            const counts = {
                all: 0,
                active: 0,
                completed: 0,
                archived: 0,
                overdue: 0,
                'no-deadline': 0
            };
            scopedTasks.forEach(task => {
                if (task.archived) {
                    counts.archived++;
                    if (includeCompletionHistory && task.completed) counts.all++;
                    return;
                }
                counts.all++;
                if (!hasTaskDueDate(task)) counts['no-deadline']++;
                if (task.completed) counts.completed++;
                else {
                    counts.active++;
                    if (hasTaskDueDate(task)) {
                        if (calculateTaskTimeLeft(task) < 0) counts.overdue++;
                    }
                }
            });
            return counts;
        }
        function setFilterCountText(id, count) {
            const el = document.getElementById(id);
            if (el) el.textContent = `(${count})`;
        }
        function renderTaskList() {
            workspaceUI.cancelSearchRender?.();
            const t = state.translations[state.currentLanguage];
            if (!t) return;
            state.searchTexts = new WeakMap();
            DOM.taskPagination.hidden = true;
            if (!state.storageAvailable) {
                syncWorkspace();
                renderStorageUnavailableState();
                return;
            }
            planTaskTimeRefresh();
            syncWorkspace();
            syncViewSwitcher();
            renderSavedViews();
            syncFocusModeUI();
            syncBatchModeUI();
            if (workspaceUI.screen === 'settings') syncMaintenanceStatus();
            renderProjectFilterOptions();
            updateFilterCounts();
            if (state.tasks.length === 0) {
                const constrained = Boolean(state.searchQuery || normalizeProjectFilter(state.projectFilter).kind !== 'all'
                    || (state.viewMode !== 'stats' && (state.focusMode || !['all', 'active'].includes(state.filter))));
                if (constrained) renderEmptyTaskList(state.focusMode ? getEmptyFocusHTML(t) : getEmptyMatchHTML(t));
                else if (state.viewMode === 'calendar') { removeInitialLoader(); renderCalendarView([]); }
                else if (state.viewMode === 'stats') { removeInitialLoader(); renderStatsView([]); }
                else renderEmptyTaskList(getEmptyStateHTML(t));
                return;
            }
            const pageKey = JSON.stringify([state.searchQuery, state.filter, state.sort, state.projectFilter, state.focusMode, state.batchMode, state.viewMode]);
            if (state.listPageKey !== pageKey) {
                state.listPageKey = pageKey;
                state.listRenderLimit = 100;
                state.calendarDetailRenderLimit = 100;
                state.calendarSearchNeedsSync = state.calendarSearchQuery !== state.searchQuery;
                state.calendarSearchQuery = state.searchQuery;
            }
            let visibleTasks = getVisibleTasks();
            removeInitialLoader();
            if (state.viewMode === 'stats') {
                renderStatsView(getStatsScopeTasks());
                return;
            }
            if (visibleTasks.length === 0) {
                renderEmptyTaskList(state.focusMode ? getEmptyFocusHTML(t) : getEmptyMatchHTML(t));
                return;
            }
            clearEmptyTaskList();
            if (state.viewMode === 'calendar') {
                renderCalendarView(visibleTasks);
                return;
            }
            if (state.viewMode === 'timeline') {
                renderTimelineView(visibleTasks);
                return;
            }
            if (shouldPaginateTaskCards() && visibleTasks.length > 100) {
                const total = visibleTasks.length;
                visibleTasks = visibleTasks.slice(0, state.listRenderLimit);
                DOM.taskPagination.hidden = false;
                DOM.taskPaginationSummary.textContent = translateCount('pagination.summary', total)
                    .replace('{shown}', visibleTasks.length).replace('{total}', total);
                DOM.loadMoreTasksBtn.hidden = visibleTasks.length === total;
            }
            if (shouldGroupVisibleTasks(visibleTasks)) {
                renderGroupedTaskList(visibleTasks);
                return;
            }
            removeProjectGroupHeaders();
            patchTaskList(visibleTasks);
        }
        function shouldPaginateTaskCards() {
            return state.batchMode || state.sort !== 'manual';
        }
        function getVisibleTasks() {
            return utils.sortTasks(state.tasks.filter(isTaskVisible));
        }
        function isTaskVisible(task) {
            if (state.focusMode && !isTaskInTodayPlan(task)) return false;
            if (!matchesTaskProject(task)) return false;
            if (!matchesTaskSearch(task)) return false;
            if (hasSearchStatusFilter()) return shouldShowTaskForStatusSearch(task);
            if (hasSearchCompletionFilter() && state.filter === 'all') return true;
            if (state.filter === 'archived') return !!task.archived;
            if (task.archived) return false;
            switch (state.filter) {
                case 'active': return !task.completed;
                case 'completed': return task.completed;
                case 'overdue': return !task.completed && hasTaskDueDate(task) && calculateTaskTimeLeft(task) < 0;
                case 'no-deadline': return !hasTaskDueDate(task);
                default: return true;
            }
        }
        function matchesTaskProject(task) {
            const scope = normalizeProjectFilter(state.projectFilter);
            if (scope.kind === 'all') return true;
            const project = normalizeTaskProject(task.project);
            if (scope.kind === 'unassigned') return !project;
            return project === scope.name;
        }
        function matchesTaskSearch(task) {
            if (!state.searchQuery) return true;
            const query = parseSearchQuery(state.searchQuery);
            return query.terms.every(token => getTaskSearchText(task).includes(token))
                && query.projects.every(value => matchesTaskProjectSearch(task, value))
                && query.tags.every(value => matchesTaskTagSearch(task, value))
                && query.exactProjects.every(value => normalizeTaskProject(task.project).toLowerCase() === value)
                && query.exactTags.every(value => normalizeTaskTags(task.tags).some(tag => tag.toLowerCase() === value))
                && query.statuses.every(value => matchesTaskStatusSearch(task, value))
                && query.completed.every(value => matchesTaskCompletionSearch(task, value))
                && query.due.every(value => matchesTaskDueSearch(task, value));
        }
        function clearSearchInput({ keepFocus = true } = {}) {
            if (!ensureStorageAvailable()) return;
            clearStatsDrilldown();
            DOM.inputs.search.value = '';
            state.searchQuery = '';
            syncSearchClearButton();
            renderTaskList();
            announceTaskViewSummary();
            if (keepFocus) DOM.inputs.search.focus();
        }
        function announceTaskViewSummary() {
            if (!state.storageAvailable) return;
            const view = utils.translate(`views.${state.viewMode}`);
            const count = state.viewMode === 'stats' ? getStatsScopeTasks().length : getVisibleTasks().length;
            utils.announce(translateCount('messages.view.summary', count).replace('{view}', view).replace('{count}', count));
        }
        function syncSearchClearButton() {
            DOM.clearSearchBtn.hidden = DOM.inputs.search.value.length === 0;
        }
        function hasSearchStatusFilter() {
            return getSearchStatusFilters().length > 0;
        }
        function hasSearchCompletionFilter() {
            return Boolean(state.searchQuery && parseSearchQuery(state.searchQuery).completed.length);
        }
        function getSearchStatusFilters() {
            return state.searchQuery ? parseSearchQuery(state.searchQuery).statuses : [];
        }
        function shouldShowTaskForStatusSearch(task) {
            return !task.archived || searchStatusIncludesArchived();
        }
        function searchStatusIncludesArchived() {
            return getSearchStatusFilters().some(isArchivedStatusSearch);
        }
        function parseSearchQuery(query) {
            const key = String(query || '');
            if (state.searchParseKey === key && state.searchParseTasks === state.tasks
                && state.searchParseRevision === state.taskRevision) return state.searchParseValue;
            const parsed = TaskInput.parseSearchQuery(query, getTaskInputNames());
            state.searchParseKey = key;
            state.searchParseValue = parsed;
            state.searchParseTasks = state.tasks;
            state.searchParseRevision = state.taskRevision;
            return parsed;
        }
        function matchesTaskProjectSearch(task, value) {
            const project = normalizeTaskProject(task.project).toLowerCase();
            if (matchesSearchAlias(value, ['none', 'unassigned', '未分组'])) return !project;
            return project.includes(value);
        }
        function matchesTaskTagSearch(task, value) {
            return normalizeTaskTags(task.tags)
                .map(tag => tag.toLowerCase())
                .some(tag => tag.includes(value));
        }
        function matchesTaskStatusSearch(task, value) {
            if (isArchivedStatusSearch(value)) return !!task.archived;
            if (matchesSearchAlias(value, ['completed', 'complete', 'done', '已完成'])) return !!task.completed && !task.archived;
            if (matchesSearchAlias(value, ['active', 'open', 'todo', '进行中'])) return !task.completed && !task.archived;
            if (matchesSearchAlias(value, ['overdue', 'expired', '已过期'])) return !task.completed && hasTaskDueDate(task) && calculateTaskTimeLeft(task) < 0;
            if (matchesSearchAlias(value, ['no-deadline', 'none', 'undated', '无截止日期'])) return !hasTaskDueDate(task);
            if (matchesSearchAlias(value, ['repeat', 'recurring', '重复'])) return task.repeatType && task.repeatType !== 'none';
            const timeLeft = calculateTaskTimeLeft(task);
            if (timeLeft === null) return false;
            const status = utils.getStatus(timeLeft).cls;
            if (matchesSearchAlias(value, ['safe', '安全'])) return status === CONFIG.UI.STATUS.SAFE;
            if (matchesSearchAlias(value, ['warning', 'warn', '警告'])) return status === CONFIG.UI.STATUS.WARNING;
            if (matchesSearchAlias(value, ['urgent', 'danger', '紧急'])) return status === CONFIG.UI.STATUS.DANGER;
            return false;
        }
        function isArchivedStatusSearch(value) {
            return matchesSearchAlias(value, ['archived', 'archive', '已归档']);
        }
        function matchesTaskDueSearch(task, value) {
            const dueKey = getTaskDueDateKey(task);
            if (matchesSearchAlias(value, ['no-deadline', 'none', 'undated', '无截止日期'])) return !dueKey;
            if (!dueKey) return false;
            if (matchesSearchAlias(value, ['overdue', 'expired', '已过期'])) return calculateTaskTimeLeft(task) < 0;
            if (matchesSearchAlias(value, ['today', '今天'])) return dueKey === getRelativeDateKey(0);
            if (matchesSearchAlias(value, ['tomorrow', '明天'])) return dueKey === getRelativeDateKey(1);
            if (matchesSearchAlias(value, ['week', '7d', '本周'])) return dueKey >= getRelativeDateKey(0) && dueKey <= getRelativeDateKey(7);
            if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return dueKey === value;
            return false;
        }
        function getRelativeDateKey(offsetDays) {
            const date = new Date();
            date.setDate(date.getDate() + offsetDays);
            return utils.formatDateInputValue(date);
        }
        function matchesTaskCompletionSearch(task, value) {
            if (!task.completed) return false;
            const completedKey = getCompletionDateKey(task);
            if (!completedKey) return false;
            if (value === 'week') return completedKey >= getRelativeDateKey(-6) && completedKey <= getRelativeDateKey(0);
            return /^\d{4}-\d{2}-\d{2}$/.test(value) && completedKey === value;
        }
        function getTaskSearchText(task) {
            if (state.searchTexts.has(task)) return state.searchTexts.get(task);
            const text = [
                task.name,
                task.description,
                task.project,
                ...normalizeTaskTags(task.tags),
                ...normalizeSubtaskSearchTexts(task.subtasks)
            ].filter(Boolean).join(' ').toLowerCase();
            state.searchTexts.set(task, text);
            return text;
        }
        function normalizeSubtaskSearchTexts(subtasks) {
            if (!Array.isArray(subtasks)) return [];
            return subtasks.map(subtask => String(subtask?.text || '').trim()).filter(Boolean);
        }
        function renderProjectFilterOptions() {
            const projects = getProjectNames();
            state.projectFilter = normalizeProjectFilter(state.projectFilter);
            if (state.projectFilter.kind === 'project' && !projects.includes(state.projectFilter.name)) projects.push(state.projectFilter.name);
            const t = state.translations[state.currentLanguage];
            const options = [
                { value: { kind: 'all' }, text: t['projects.all'] },
                { value: { kind: 'unassigned' }, text: t['projects.none'] },
                ...projects.map(project => ({ value: { kind: 'project', name: project }, text: project }))
            ];
            const signature = JSON.stringify(options);
            const menu = getDropdownMenu(DOM.dropdowns.project);
            const optionsChanged = menu.dataset.signature !== signature;
            if (optionsChanged) {
                menu.textContent = '';
                options.forEach(option => {
                    const el = document.createElement('button');
                    el.type = 'button';
                    el.className = 'dropdown-option';
                    el.setAttribute('role', 'option');
                    el.setAttribute('aria-selected', 'false');
                    el.dataset.project = projectFilterKey(option.value);
                    const label = document.createElement('span');
                    label.textContent = option.text;
                    el.appendChild(label);
                    menu.appendChild(el);
                });
                menu.dataset.signature = signature;
            }
            const selected = getAllDropdownOptions(DOM.dropdowns.project)
                .find(option => option.dataset.project === projectFilterKey(state.projectFilter));
            const preserveOpen = !optionsChanged && isElementOpen(DOM.dropdowns.project.container);
            if (selected) updateDropdownUI(DOM.dropdowns.project.container, selected, DOM.dropdowns.project.btn, { preserveOpen });
            if (preserveOpen) requestAnimationFrame(() => {
                if (isElementOpen(DOM.dropdowns.project.container)) positionDropdownMenu(DOM.dropdowns.project);
            });
        }
        function getProjectNames() {
            return [...new Set(state.tasks.map(task => normalizeTaskProject(task.project)).filter(Boolean))]
                .sort((a, b) => a.localeCompare(b, state.currentLanguage));
        }
        function shouldGroupVisibleTasks(tasks) {
            return normalizeProjectFilter(state.projectFilter).kind === 'all' && state.sort === 'smart' && !state.searchQuery && tasks.length > 0;
        }
        function renderGroupedTaskList(tasks) {
            DOM.taskList.textContent = '';
            const fragment = document.createDocumentFragment();
            groupTasksByProject(tasks).forEach(group => {
                fragment.appendChild(createProjectGroupHeader(group.name, group.tasks.length));
                group.tasks.forEach(task => fragment.appendChild(createTaskNode(task)));
            });
            DOM.taskList.appendChild(fragment);
        }
        function groupTasksByProject(tasks) {
            const groups = new Map();
            tasks.forEach(task => {
                const name = normalizeTaskProject(task.project);
                if (!groups.has(name)) groups.set(name, []);
                groups.get(name).push(task);
            });
            return [...groups.entries()].map(([name, groupTasks]) => ({ name: name || utils.translate('projects.none'), tasks: groupTasks }));
        }
        function createProjectGroupHeader(name, count) {
            const header = document.createElement('div');
            header.className = 'task-group-header';
            header.setAttribute('role', 'heading');
            header.setAttribute('aria-level', '2');
            const label = document.createElement('span');
            label.textContent = translateCount('projects.groupTitle', count)
                .replace('{project}', name)
                .replace('{count}', count);
            header.appendChild(label);
            return header;
        }
        function removeProjectGroupHeaders() {
            DOM.taskList.querySelectorAll('.task-group-header').forEach(header => header.remove());
        }
        function syncCalendarMonthToVisibleTasks() {
            const datedTask = getVisibleTasks().find(hasTaskDueDate);
            state.calendarMonthDate = !window.matchMedia('(min-width: 780px)').matches && !state.searchQuery ? getCalendarTodayDate() : datedTask ? parseDateKey(getTaskDueDateKey(datedTask)) : getCalendarTodayDate();
            state.calendarDetailDateKey = '';
            state.calendarDetailRenderLimit = 100;
        }
        function getCalendarDefaultDetailDateKey() {
            const today = getCalendarTodayDate();
            const anchor = state.calendarMonthDate;
            if (today.getUTCFullYear() === anchor.getUTCFullYear() && today.getUTCMonth() === anchor.getUTCMonth()) return getCalendarDateKey(today);
            const firstDay = new Date(anchor);
            firstDay.setUTCDate(1);
            return getCalendarDateKey(firstDay);
        }
        function renderCalendarView(tasks) {
            DOM.taskList.textContent = '';
            const datedTasks = sortTasksForDateView(tasks.filter(hasTaskDueDate));
            const undatedTasks = tasks.filter(task => !hasTaskDueDate(task));
            const byDate = groupTasksByDateKey(datedTasks);
            if (state.calendarSearchNeedsSync) {
                state.calendarSearchNeedsSync = false;
                if (state.searchQuery && datedTasks.length) {
                    const displayedDates = new Set(getCalendarDays(state.calendarMonthDate).map(getCalendarDateKey));
                    if (![...byDate.keys()].some(key => displayedDates.has(key))) {
                        state.calendarMonthDate = parseDateKey(getTaskDueDateKey(datedTasks[0]));
                        state.calendarDetailDateKey = '';
                    }
                }
            }
            const mobile = !window.matchMedia('(min-width: 780px)').matches;
            if (mobile && !state.calendarDetailDateKey) state.calendarDetailDateKey = getCalendarDefaultDetailDateKey();
            const calendar = document.createElement('div');
            calendar.className = 'calendar-view';
            calendar.appendChild(createCalendarShell(datedTasks));
            const detailTasks = byDate.get(state.calendarDetailDateKey) || [];
            if (state.calendarDetailDateKey && (detailTasks.length || mobile)) calendar.appendChild(createCalendarDayDetail(state.calendarDetailDateKey, detailTasks));
            else state.calendarDetailDateKey = '';
            if (undatedTasks.length > 0) calendar.appendChild(createUndatedSection(undatedTasks));
            DOM.taskList.appendChild(calendar);
        }
        function createCalendarShell(tasks) {
            const shell = document.createElement('section');
            shell.className = 'calendar-shell';
            shell.append(createCalendarHeader(), createCalendarGrid(tasks));
            return shell;
        }
        function createCalendarHeader() {
            const header = document.createElement('div');
            header.className = 'calendar-header';
            const title = document.createElement('h2');
            title.className = 'calendar-title';
            title.textContent = formatCalendarMonthTitle(state.calendarMonthDate);
            const actions = document.createElement('div');
            actions.className = 'calendar-actions';
            actions.append(
                createCalendarNavButton('prev-year', 'icon-chevrons-right', utils.translate('calendar.previousYear'), true),
                createCalendarNavButton('prev', 'icon-chevron-right', utils.translate('calendar.previous'), true),
                createCalendarTodayButton(),
                createCalendarNavButton('next', 'icon-chevron-right', utils.translate('calendar.next')),
                createCalendarNavButton('next-year', 'icon-chevrons-right', utils.translate('calendar.nextYear'))
            );
            header.append(title, actions);
            return header;
        }
        function createCalendarTodayButton() {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-nav-btn';
            button.dataset.calendarAction = 'today';
            button.textContent = utils.translate('calendar.today');
            return button;
        }
        function createCalendarNavButton(action, iconId, label, flip = false) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-nav-btn';
            button.dataset.calendarAction = action;
            button.setAttribute('aria-label', label);
            const icon = createIcon(iconId, 'icon icon-sm');
            if (flip) icon.style.transform = 'rotate(180deg)';
            button.appendChild(icon);
            return button;
        }
        function createCalendarGrid(tasks) {
            const grid = document.createElement('div');
            grid.className = 'calendar-grid';
            getWeekdayLabels().forEach(label => {
                const weekday = document.createElement('div');
                weekday.className = 'calendar-weekday';
                weekday.textContent = label;
                grid.appendChild(weekday);
            });
            const byDate = groupTasksByDateKey(tasks);
            getCalendarDays(state.calendarMonthDate).forEach(day => grid.appendChild(createCalendarDay(day, byDate.get(getCalendarDateKey(day)) || [])));
            return grid;
        }
        function createCalendarDay(day, tasks) {
            const cell = document.createElement('div');
            const todayKey = utils.formatDateInputValue();
            const dayKey = getCalendarDateKey(day);
            cell.className = `calendar-day ${day.getUTCMonth() === state.calendarMonthDate.getUTCMonth() ? '' : 'outside-month'} ${dayKey === todayKey ? 'today' : ''}`.trim();
            cell.setAttribute('role', 'group');
            cell.setAttribute('aria-label', formatCalendarDayLabel(day, tasks.length));
            const header = document.createElement('div');
            header.className = 'calendar-day-header';
            header.appendChild(createCalendarDateButton(dayKey, day, tasks.length));
            const list = document.createElement('div');
            list.className = 'calendar-task-list';
            tasks.slice(0, 3).forEach(task => list.appendChild(createCalendarTaskButton(task)));
            if (tasks.length > 3) {
                list.appendChild(createCalendarMoreButton(dayKey, day, tasks.length));
            }
            const dots = document.createElement('span');
            dots.className = 'calendar-day-count';
            dots.setAttribute('aria-hidden', 'true');
            dots.textContent = tasks.length ? (tasks.length > 9 ? '9+' : String(tasks.length)) : '';
            cell.classList.toggle('selected-day', state.calendarDetailDateKey === dayKey);
            cell.classList.toggle('has-tasks', tasks.length > 0);
            cell.classList.toggle('has-overdue', tasks.some(task => !task.completed && !task.archived && matchesTaskDueSearch(task, 'overdue')));
            cell.append(header, list, dots);
            return cell;
        }
        function createCalendarMoreButton(dayKey, day, count) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-more calendar-more-btn';
            button.dataset.calendarDetailDate = dayKey;
            const label = translateCount('calendar.showDayTasks', count)
                .replace('{date}', formatCalendarAddDate(day))
                .replace('{count}', count);
            button.title = label;
            button.textContent = utils.translate('calendar.more').replace('{count}', count - 3);
            button.setAttribute('aria-label', `${button.textContent} · ${label}`);
            return button;
        }
        function createCalendarDateButton(dayKey, day, count = 0) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-date-number';
            const mobile = !window.matchMedia('(min-width: 780px)').matches;
            if (mobile) {
                button.dataset.calendarDetailDate = dayKey;
                button.setAttribute('aria-pressed', String(state.calendarDetailDateKey === dayKey));
            } else button.dataset.calendarAddDate = dayKey;
            const label = mobile ? formatCalendarDayLabel(day, count)
                : utils.translate('calendar.addTaskOnDate').replace('{date}', formatCalendarAddDate(day));
            button.title = label;
            button.setAttribute('aria-label', label);
            button.textContent = String(day.getUTCDate());
            return button;
        }
        function createCalendarTaskButton(task) {
            const status = getTaskRenderStatus(task, state.translations[state.currentLanguage]).statusObj;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-task';
            button.dataset.calendarTaskId = String(task.id);
            button.style.setProperty('--task-color', getStatusColorFromClass(status.cls));
            button.textContent = task.name;
            button.title = task.name;
            button.setAttribute('aria-label', `${task.name}, ${status.text}`);
            return button;
        }
        function createCalendarDayDetail(dayKey, tasks) {
            const section = document.createElement('section');
            section.className = 'calendar-day-detail';
            section.setAttribute('aria-label', formatCalendarDayLabel(parseDateKey(dayKey), tasks.length));
            const header = document.createElement('div');
            header.className = 'calendar-detail-header';
            const title = document.createElement('h3');
            title.className = 'calendar-detail-title';
            title.tabIndex = -1;
            title.textContent = `${formatTimelineDate(dayKey)} · ${translateCount('calendar.taskCount', tasks.length).replace('{count}', tasks.length)}`;
            const close = document.createElement('button');
            close.type = 'button';
            close.className = 'calendar-detail-close';
            close.dataset.calendarDetailClose = 'true';
            close.hidden = !window.matchMedia('(min-width: 780px)').matches;
            close.title = utils.translate('calendar.closeDayTasks');
            close.setAttribute('aria-label', utils.translate('calendar.closeDayTasks'));
            close.appendChild(createIcon('icon-x', 'icon icon-sm'));
            const add = document.createElement('button');
            add.type = 'button'; add.className = 'calendar-agenda-add btn btn-secondary';
            add.dataset.calendarAddDate = dayKey;
            add.textContent = utils.translate('actions.addTask');
            header.append(title, add, close);
            const list = document.createElement('div');
            list.className = 'calendar-detail-list';
            list.id = 'calendarDayTasks';
            const visible = shouldPaginateTaskCards() ? tasks.slice(0, state.calendarDetailRenderLimit) : tasks;
            visible.forEach(task => list.appendChild(createCalendarDetailTaskButton(task)));
            if (!visible.length) { const empty = document.createElement('p'); empty.className = 'calendar-agenda-empty'; empty.textContent = utils.translate('usability.noDayTasks'); list.appendChild(empty); }
            section.append(header, list);
            if (tasks.length > 100 && shouldPaginateTaskCards()) {
                section.appendChild(createCalendarPagination('detail-more', list.id, visible.length, tasks.length));
            }
            return section;
        }
        function createCalendarDetailTaskButton(task) {
            const status = getTaskRenderStatus(task, state.translations[state.currentLanguage]).statusObj;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-detail-task';
            button.dataset.calendarTaskId = String(task.id);
            button.style.setProperty('--task-color', getStatusColorFromClass(status.cls));
            const name = document.createElement('span');
            name.className = 'calendar-detail-task-name';
            name.textContent = task.name;
            const statusText = document.createElement('span');
            statusText.className = 'calendar-detail-task-status';
            statusText.textContent = status.text;
            const time = document.createElement('span');
            time.className = 'calendar-detail-task-time';
            time.textContent = getTaskDueTimeValue(task);
            button.append(time, name, statusText);
            return button;
        }
        function getStatusColorFromClass(statusClass) {
            const map = {
                [CONFIG.UI.STATUS.SAFE]: 'var(--color-success)',
                [CONFIG.UI.STATUS.WARNING]: 'var(--color-warning)',
                [CONFIG.UI.STATUS.DANGER]: 'var(--color-warning)',
                [CONFIG.UI.STATUS.OVERDUE]: 'var(--color-danger)',
                [CONFIG.UI.STATUS.NO_DEADLINE]: 'var(--text-tertiary)',
                [CONFIG.UI.STATUS.ARCHIVED]: 'var(--text-tertiary)',
                [CONFIG.UI.CLASSES.COMPLETED]: 'var(--color-success)'
            };
            return map[statusClass] || 'var(--color-primary)';
        }
        function getCalendarDays(anchorDate) {
            const first = new Date(anchorDate);
            first.setUTCDate(1);
            first.setUTCHours(12, 0, 0, 0);
            const offset = (first.getUTCDay() + 6) % 7;
            const start = new Date(first);
            start.setUTCDate(first.getUTCDate() - offset);
            return Array.from({ length: 42 }, (_, index) => {
                const day = new Date(start);
                day.setUTCDate(start.getUTCDate() + index);
                return day;
            });
        }
        function getCalendarTodayDate() {
            const localNow = new Date();
            const civilDate = new Date(0);
            civilDate.setUTCFullYear(localNow.getFullYear(), localNow.getMonth(), localNow.getDate());
            civilDate.setUTCHours(12, 0, 0, 0);
            return civilDate;
        }
        function getCalendarDateKey(date) {
            return `${String(date.getUTCFullYear()).padStart(4, '0')}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
        }
        function getWeekdayLabels() {
            const base = new Date('2025-01-06T12:00:00.000Z');
            return Array.from({ length: 7 }, (_, index) => {
                const day = new Date(base);
                day.setUTCDate(base.getUTCDate() + index);
                return new Intl.DateTimeFormat(state.currentLanguage, { weekday: 'short', timeZone: 'UTC' }).format(day);
            });
        }
        function formatCalendarMonthTitle(date) {
            return new Intl.DateTimeFormat(state.currentLanguage, { year: 'numeric', month: 'long', timeZone: 'UTC' }).format(date);
        }
        function formatCalendarDayLabel(day, count) {
            return `${new Intl.DateTimeFormat(state.currentLanguage, { dateStyle: 'full', timeZone: 'UTC' }).format(day)}, ${translateCount('calendar.taskCount', count).replace('{count}', count)}`;
        }
        function formatCalendarAddDate(day) {
            return new Intl.DateTimeFormat(state.currentLanguage, { dateStyle: 'medium', timeZone: 'UTC' }).format(day);
        }
        function renderTimelineView(tasks) {
            DOM.taskList.textContent = '';
            const timeline = document.createElement('div');
            timeline.className = 'timeline-view';
            timeline.setAttribute('role', 'list');
            const bounded = shouldPaginateTaskCards();
            const limit = bounded ? state.listRenderLimit : tasks.length;
            const groups = [...groupTasksByDateKey(sortTasksForDateView(tasks))].sort(([a], [b]) => {
                if (a === '__none__') return 1;
                if (b === '__none__') return -1;
                return a.localeCompare(b);
            });
            let shown = 0;
            groups.forEach(([key, groupTasks]) => {
                const visible = groupTasks.slice(0, Math.max(0, limit - shown));
                if (!visible.length) return;
                timeline.appendChild(createTimelineGroup(key, visible, groupTasks.length));
                shown += visible.length;
            });
            DOM.taskList.appendChild(timeline);
            if (bounded && tasks.length > 100) {
                DOM.taskPagination.hidden = false;
                DOM.taskPaginationSummary.textContent = translateCount('pagination.summary', tasks.length)
                    .replace('{shown}', shown).replace('{total}', tasks.length);
                DOM.loadMoreTasksBtn.hidden = shown === tasks.length;
            }
        }
        function createTimelineGroup(key, tasks, totalCount = tasks.length) {
            const group = document.createElement('section');
            group.className = 'timeline-group';
            group.classList.toggle('is-today', key === utils.formatDateInputValue());
            group.classList.toggle('is-undated', key === '__none__');
            group.classList.toggle('has-overdue', tasks.some(task => !task.completed && !task.archived && matchesTaskDueSearch(task, 'overdue')));
            group.setAttribute('role', 'listitem');
            const marker = document.createElement('div');
            marker.className = 'timeline-marker';
            const dot = document.createElement('div');
            dot.className = 'timeline-dot';
            marker.appendChild(dot);
            const content = document.createElement('div');
            content.className = 'timeline-content';
            const title = document.createElement('h2');
            title.className = 'timeline-date-title';
            title.append(createTimelineTitleText(key), createTimelineCount(totalCount));
            content.appendChild(title);
            tasks.forEach(task => content.appendChild(createTaskNode(task)));
            group.append(marker, content);
            return group;
        }
        function createTimelineTitleText(key) {
            const span = document.createElement('span');
            span.textContent = key === '__none__' ? utils.translate('calendar.noDeadline') : formatTimelineDate(key);
            return span;
        }
        function createTimelineCount(count) {
            const span = document.createElement('span');
            span.className = 'timeline-count';
            span.textContent = translateCount('calendar.taskCount', count).replace('{count}', count);
            return span;
        }
        function createUndatedSection(tasks) {
            const section = document.createElement('section');
            section.className = 'date-view-undated';
            section.id = 'calendarUndatedTasks';
            const title = document.createElement('h3');
            title.textContent = `${utils.translate('calendar.noDeadline')} · ${translateCount('calendar.taskCount', tasks.length).replace('{count}', tasks.length)}`;
            section.appendChild(title);
            const visible = shouldPaginateTaskCards() ? tasks.slice(0, state.listRenderLimit) : tasks;
            visible.forEach(task => section.appendChild(createTaskNode(task)));
            if (tasks.length > 100 && shouldPaginateTaskCards()) {
                section.appendChild(createCalendarPagination('undated-more', section.id, visible.length, tasks.length));
            }
            return section;
        }
        function createCalendarPagination(action, targetId, shown, total) {
            const pagination = document.createElement('div');
            pagination.className = 'task-pagination';
            const summary = document.createElement('p');
            summary.setAttribute('role', 'status');
            summary.setAttribute('aria-live', 'polite');
            summary.textContent = translateCount('pagination.summary', total).replace('{shown}', shown).replace('{total}', total);
            pagination.appendChild(summary);
            if (shown < total) {
                const more = document.createElement('button');
                more.type = 'button';
                more.className = 'btn btn-secondary';
                more.dataset.calendarAction = action;
                more.setAttribute('aria-controls', targetId);
                more.textContent = utils.translate('pagination.more');
                pagination.appendChild(more);
            }
            return pagination;
        }
        function groupTasksByDateKey(tasks) {
            const groups = new Map();
            tasks.forEach(task => {
                const key = getTaskDueDateKey(task) || '__none__';
                if (!groups.has(key)) groups.set(key, []);
                groups.get(key).push(task);
            });
            return groups;
        }
        function sortTasksForDateView(tasks) {
            return [...tasks].sort((a, b) => {
                const dueA = getTaskDueSortValue(a);
                const dueB = getTaskDueSortValue(b);
                if (dueA !== null && dueB !== null) return dueA - dueB;
                if (dueA !== null) return -1;
                if (dueB !== null) return 1;
                return new Date(a.createdAt) - new Date(b.createdAt);
            });
        }
        function formatTimelineDate(key) {
            const date = new Date(`${key}T12:00:00Z`);
            return new Intl.DateTimeFormat(state.currentLanguage, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(date);
        }
        function shiftCalendarMonth(delta) {
            const date = new Date(state.calendarMonthDate);
            date.setUTCDate(1);
            date.setUTCMonth(date.getUTCMonth() + delta);
            state.calendarMonthDate = date;
            state.calendarDetailDateKey = '';
            state.listRenderLimit = 100;
            state.calendarDetailRenderLimit = 100;
            renderTaskList();
        }
        function getStatsScopeTasks() {
            return state.tasks
                .filter(matchesTaskProject)
                .filter(matchesTaskSearch)
                .filter(task => !hasSearchStatusFilter() || shouldShowTaskForStatusSearch(task));
        }
        function renderStatsView(tasks) {
            const previousInventory = DOM.taskList.querySelector('.stats-inventory');
            const inventoryOpen = previousInventory ? previousInventory.open : true;
            DOM.taskList.textContent = '';
            const stats = calculateTaskStats(tasks);
            const scope = normalizeProjectFilter(state.projectFilter);
            const scopeText = scope.kind === 'project' ? scope.name
                : utils.translate(scope.kind === 'unassigned' ? 'projects.none' : 'projects.all');
            const todayText = translateCount('statsInsights.todayReview', stats.completedToday).replace('{count}', stats.completedToday);
            document.getElementById('workspaceTitle').textContent = utils.translate('v5.nav.review');
            document.getElementById('workspaceSummary').textContent = `${scopeText} · ${todayText}${state.searchQuery ? ` · ${utils.translate('statsInsights.searchApplied')}` : ''}`;
            DOM.taskList.appendChild(reviewView.render(stats, { inventoryOpen }));
        }


        function calculateTaskStats(tasks) {
            const archived = tasks.filter(task => task.archived).length;
            const activeScopeTasks = tasks.filter(task => !task.archived);
            const pendingTasks = activeScopeTasks.filter(task => !task.completed);
            const completionHistoryTasks = tasks.filter(task => task.completed && getCompletionDateKey(task));
            const total = activeScopeTasks.length;
            const completed = activeScopeTasks.filter(task => task.completed).length;
            const deadlineTasks = pendingTasks.filter(hasTaskDueDate).length;
            const overdue = pendingTasks.filter(task => matchesTaskDueSearch(task, 'overdue')).length;
            const dueToday = pendingTasks.filter(task => matchesTaskDueSearch(task, 'today')).length;
            const undated = pendingTasks.filter(task => matchesTaskDueSearch(task, 'none')).length;
            const completedToday = completionHistoryTasks.filter(task => getCompletionDateKey(task) === utils.formatDateInputValue()).length;
            const completionRate = total > 0 ? completed / total : 0;
            const overdueRate = deadlineTasks > 0 ? overdue / deadlineTasks : 0;
            const streakDays = calculateCompletionStreak(completionHistoryTasks);
            const completionTrend = calculateCompletionTrend(completionHistoryTasks);
            const projects = new Map();
            pendingTasks.forEach(task => {
                const name = normalizeTaskProject(task.project);
                const key = name || '';
                if (!projects.has(key)) projects.set(key, { scope: name ? { kind: 'project', name } : { kind: 'unassigned' }, pending: 0, overdue: 0 });
                const project = projects.get(key);
                project.pending++;
                if (matchesTaskDueSearch(task, 'overdue')) project.overdue++;
            });
            const projectRows = Array.from(projects.values()).sort((a, b) => b.overdue - a.overdue || b.pending - a.pending || getProjectFilterLabel(a.scope).localeCompare(getProjectFilterLabel(b.scope), state.currentLanguage));
            return {
                total,
                completed,
                overdue,
                archived,
                recordCount: tasks.length,
                pending: pendingTasks.length,
                pendingTasks,
                dueToday,
                undated,
                deadlineTasks,
                completedToday,
                completedWeek: completionTrend.reduce((sum, day) => sum + day.count, 0),
                completionRate,
                overdueRate,
                streakDays,
                completionTrend,
                projectRows,
                completedDetail: total ? translateCount('stats.completedDetail', total).replace('{completed}', completed).replace('{total}', total) : utils.translate('statsInsights.noInventory'),
                overdueDetail: deadlineTasks ? translateCount('stats.overdueDetail', deadlineTasks).replace('{overdue}', overdue).replace('{total}', deadlineTasks) : utils.translate('statsInsights.noScheduled'),
                streakDetail: translateCount('stats.streakDetail', streakDays).replace('{count}', streakDays)
            };
        }
        function calculateCompletionTrend(tasks) {
            const counts = new Map();
            tasks.forEach(task => {
                const key = getCompletionDateKey(task);
                if (key) counts.set(key, (counts.get(key) || 0) + 1);
            });
            const today = new Date();
            return Array.from({ length: 7 }, (_, index) => {
                const date = new Date(today);
                date.setDate(today.getDate() - (6 - index));
                const key = utils.formatDateInputValue(date);
                return {
                    key,
                    label: new Intl.DateTimeFormat(state.currentLanguage, { weekday: 'short' }).format(date),
                    fullLabel: new Intl.DateTimeFormat(state.currentLanguage, { year: 'numeric', month: 'short', day: 'numeric' }).format(date),
                    count: counts.get(key) || 0
                };
            });
        }
        function calculateCompletionStreak(tasks) {
            const completedDays = new Set(tasks.map(getCompletionDateKey).filter(Boolean));
            let cursor = new Date();
            if (!completedDays.has(utils.formatDateInputValue(cursor))) cursor.setDate(cursor.getDate() - 1);
            let streak = 0;
            while (completedDays.has(utils.formatDateInputValue(cursor))) {
                streak++;
                cursor.setDate(cursor.getDate() - 1);
            }
            return streak;
        }
        function getCompletionDateKey(task) {
            const completedAt = normalizeStoredDate(task.completedAt);
            return completedAt ? utils.formatDateInputValue(new Date(completedAt)) : '';
        }
        function removeInitialLoader() {
            const loader = document.getElementById('initial-loader');
            if (loader) loader.remove();
        }
        function renderEmptyTaskList(html) {
            DOM.taskList.innerHTML = html;
        }
        function clearEmptyTaskList() {
            if (DOM.taskList.querySelector('.empty-state')) DOM.taskList.innerHTML = '';
        }
        function patchTaskList(tasks) {
            if (Array.from(DOM.taskList.children).some(el => !el.classList.contains('task-item'))) {
                DOM.taskList.textContent = '';
            }
            if (DOM.taskList.children.length === 0) {
                appendTaskNodes(tasks);
            } else {
                reconcileTaskNodes(tasks);
            }
        }
        function appendTaskNodes(tasks) {
            const fragment = document.createDocumentFragment();
            tasks.forEach(task => fragment.appendChild(createTaskNode(task)));
            DOM.taskList.appendChild(fragment);
        }
        function reconcileTaskNodes(tasks) {
            const existingMap = getTaskElementMap();
            let refNode = DOM.taskList.firstChild;
            tasks.forEach(task => {
                const existingEl = existingMap.get(task.id);
                if (existingEl) {
                    renderTaskItem(existingEl, task);
                    if (existingEl !== refNode) {
                        DOM.taskList.insertBefore(existingEl, refNode);
                    }
                    existingMap.delete(task.id);
                    refNode = existingEl.nextSibling;
                } else {
                    DOM.taskList.insertBefore(createTaskNode(task), refNode);
                }
            });
            existingMap.forEach(el => el.remove());
        }
        function getTaskElementMap() {
            const existingMap = new Map();
            Array.from(DOM.taskList.children).forEach(el => {
                if (el.classList.contains('task-item')) existingMap.set(Number(el.dataset.taskId), el);
            });
            return existingMap;
        }
        function createTaskNode(task) {
            const el = DOM.taskTemplate.content.cloneNode(true).firstElementChild;
            el.dataset.taskId = task.id;
            renderTaskItem(el, task);
            return el;
        }
        function renderTaskItem(el, task) {
            const t = state.translations[state.currentLanguage];
            const { statusObj, timeLeft } = getTaskRenderStatus(task, t);
            renderTaskHeader(el, task, statusObj, t);
            const menu = el.querySelector('.task-action-menu');
            const menuButton = el.querySelector('.task-more-toggle');
            if (menu && menuButton) { menu.id = `task-actions-${task.id}`; menuButton.setAttribute('aria-controls', menu.id); menuButton.setAttribute('aria-label', `${utils.translate('workspace.taskActions')}: ${task.name}`); }
            renderTaskDescription(el, task);
            renderTaskMeta(el, task);
            renderSubtaskList(el, task);
            renderTaskProgress(el, task, statusObj);
            renderTaskStatus(el, task, statusObj, timeLeft);
            renderTaskActionTitles(el, task, t);
            renderTaskDragHandle(el);
            renderTaskSelectionControl(el, task);
            syncTaskAccessibility(el, task);
            markDecorativeIcons(el);
        }
        function getTaskRenderStatus(task, t) {
            if (task.archived) {
                return {
                    statusObj: { cls: CONFIG.UI.STATUS.ARCHIVED, text: t['status.archived'], percent: 100 },
                    timeLeft: null
                };
            }
            if (task.completed) {
                return {
                    statusObj: { cls: CONFIG.UI.CLASSES.COMPLETED, text: t['status.completed'], percent: 100 },
                    timeLeft: null
                };
            }
            if (hasTaskDueDate(task)) {
                const timeLeft = calculateTaskTimeLeft(task);
                return { statusObj: utils.getStatus(timeLeft), timeLeft };
            }
            return {
                statusObj: { cls: CONFIG.UI.STATUS.NO_DEADLINE, text: t['status.noDeadline'], percent: 0 },
                timeLeft: null
            };
        }
        function renderTaskHeader(el, task, statusObj, t) {
            el.className = `task-item ${statusObj.cls} ${task.completed ? 'completed-task' : ''} ${task.archived ? 'archived-task' : ''}`;
            const nameEl = el.querySelector('.task-name');
            nameEl.id = `task-name-${task.id}`;
            nameEl.textContent = task.name;
            nameEl.disabled = Boolean(task.archived);
            renderTaskPlanningControls(el, task, t);
            renderReminderIcon(el, task);
            const dateEl = el.querySelector('.task-date');
            dateEl.id = `task-date-${task.id}`;
            const hasDueDate = hasTaskDueDate(task);
            dateEl.hidden = !hasDueDate;
            dateEl.textContent = hasDueDate ? `${t['task.deadline']}: ${formatTaskDueDate(task)}` : '';
            if (hasDueDate) {
                const fullDate = dateEl.textContent;
                dateEl.title = fullDate;
                groupTaskDeadlineClock(dateEl, task);
                const clock = dateEl.querySelector('.task-clock');
                if (state.viewMode === 'timeline' && clock) {
                    const full = document.createElement('span');
                    full.className = 'sr-only';
                    full.textContent = fullDate;
                    clock.setAttribute('aria-hidden', 'true');
                    dateEl.replaceChildren(full, clock);
                }
            } else dateEl.removeAttribute('title');
        }
        function groupTaskDeadlineClock(element, task) {
            const instant = getTaskDueInstant(task);
            const date = instant ? new Date(instant) : getTaskDueLocalDate(task);
            const timeZone = instant ? getTaskDueTimeZone(task) : null;
            const formatter = state.dateTimeFormatters[`${state.currentLanguage}|${timeZone || 'local'}`];
            if (!date || !formatter) return;
            const parts = formatter.formatToParts(date);
            const clockTypes = new Set(['hour', 'minute', 'second', 'dayPeriod']);
            const first = parts.findIndex(part => clockTypes.has(part.type));
            let last = parts.length - 1;
            while (last >= first && !clockTypes.has(parts[last].type)) last -= 1;
            if (first < 0 || last < first) return;
            const clock = parts.slice(first, last + 1).map(part => part.value).join('');
            const text = element.textContent;
            const start = text.replace(/\s/g, ' ').lastIndexOf(clock.replace(/\s/g, ' '));
            if (start < 0) return;
            const span = document.createElement('span');
            span.className = 'task-clock';
            span.textContent = text.slice(start, start + clock.length);
            element.replaceChildren(document.createTextNode(text.slice(0, start)), span, document.createTextNode(text.slice(start + clock.length)));
        }
        function renderTaskDescription(el, task) {
            let descEl = el.querySelector('.task-desc');
            if (task.description) {
                if (!descEl) {
                    descEl = document.createElement('div');
                    descEl.className = 'task-desc';
                    el.querySelector('.task-header').after(descEl);
                }
                descEl.textContent = task.description;
            } else if (descEl) descEl.remove();
        }
        function renderTaskMeta(el, task) {
            const project = normalizeTaskProject(task.project);
            const tags = normalizeTaskTags(task.tags);
            const repeatLabel = getTaskRepeatLabel(task);
            const snoozedUntil = !task.completed && !task.archived && task.snoozedUntil && Number.isFinite(Date.parse(task.snoozedUntil)) ? task.snoozedUntil : '';
            const scope = normalizeProjectFilter(state.projectFilter);
            const implicitProject = state.viewMode === 'list' && ((scope.kind === 'all' && state.sort === 'smart' && !state.searchQuery)
                || (scope.kind === 'project' && !state.focusMode));
            const showProject = Boolean(project) && !implicitProject;
            let metaEl = el.querySelector('.task-meta');
            if (!showProject && tags.length === 0 && !repeatLabel && !snoozedUntil) {
                if (metaEl) metaEl.remove();
                return;
            }
            if (!metaEl) {
                metaEl = document.createElement('div');
                metaEl.className = 'task-meta';
                const row = el.querySelector('.task-meta-line');
                if (row) row.prepend(metaEl);
                else el.querySelector('.task-header').after(metaEl);
            }
            metaEl.textContent = '';
            if (showProject) { const chip = createTaskChip(project, 'project-chip'); chip.dataset.projectTone = String(workspaceProjectTone(project)); metaEl.appendChild(chip); }
            tags.forEach(tag => metaEl.appendChild(createTaskChip(`#${tag}`, 'tag-chip')));
            if (repeatLabel) metaEl.appendChild(createTaskChip(repeatLabel, 'repeat-chip'));
            if (snoozedUntil) {
                const chip = createTaskChip(utils.translate('craft.snoozedUntil').replace('{date}', utils.formatDate(snoozedUntil)), 'snooze-chip');
                chip.title = utils.translate('craft.snoozeDeliveryHint');
                metaEl.appendChild(chip);
                if (!state.notificationsEnabled || !hasNotificationPermission()) {
                    const off = createTaskChip(utils.translate('craft.snoozeNotificationsOff'), 'notification-off-chip');
                    off.title = utils.translate('craft.snoozeDeliveryHint');
                    metaEl.appendChild(off);
                }
            }
        }
        function getTaskRepeatLabel(task) {
            const rule = getTaskRepeatRule(task);
            if (rule.type === 'none') return '';
            let label = '';
            if (rule.type === 'custom') label = translateCount('task.repeat.custom', rule.interval).replace('{days}', rule.interval);
            else if (rule.type === 'weekly-days') label = utils.translate('task.repeat.weeklyDays').replace('{days}', formatRepeatWeekdays(rule.weekdays));
            else label = utils.translate(`task.repeat.${rule.type}`);
            return rule.paused ? `${label} · ${utils.translate('task.repeat.paused')}` : label;
        }
        function formatRepeatWeekdays(weekdays) {
            return normalizeTaskRepeatWeekdays(weekdays)
                .map(day => utils.translate(`form.repeat.weekdays.${getWeekdayKey(day)}`))
                .join(utils.translate('task.repeat.weekdaySeparator'));
        }
        function getWeekdayKey(day) {
            return ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'][day] || 'mon';
        }
        function createTaskChip(text, extraClass) {
            const chip = document.createElement('span');
            chip.className = `task-chip ${extraClass}`;
            chip.textContent = text;
            return chip;
        }
        function renderTaskProgress(el, task, statusObj) {
            let bar = el.querySelector('.progress-bar');
            if (shouldShowTaskTiming(task)) {
                if (!bar) {
                    bar = createTaskProgressBar();
                    getTaskProgressAnchor(el).after(bar);
                }
                bar.querySelector('.progress-fill').style.width = `${statusObj.percent}%`;
            } else if (bar) bar.remove();
        }
        function createTaskProgressBar() {
            const bar = document.createElement('div');
            bar.className = 'progress-bar';
            bar.setAttribute('aria-hidden', 'true');
            bar.innerHTML = '<div class="progress-fill"></div>';
            return bar;
        }
        function getTaskProgressAnchor(el) {
            return el.querySelector('.subtasks-wrapper') || el.querySelector('.task-meta') || el.querySelector('.task-desc') || el.querySelector('.task-header');
        }
        function renderTaskStatus(el, task, statusObj, timeLeft) {
            const statusInd = el.querySelector('.status-indicator');
            statusInd.id = `task-status-${task.id}`;
            const statusText = statusInd.querySelector('.status-text');
            statusText.textContent = statusObj.text;
            statusText.classList.toggle('sr-only', state.viewMode === 'timeline' && !hasTaskDueDate(task) && !task.completed && !task.archived);
            statusInd.classList.toggle('compact-timing', state.viewMode === 'timeline' && shouldShowTaskTiming(task));
            let timeEl = statusInd.querySelector('.status-time-left');
            if (shouldShowTaskTiming(task)) {
                if (!timeEl) {
                    timeEl = document.createElement('span');
                    timeEl.className = 'status-time-left';
                    statusText.after(timeEl);
                }
                timeEl.textContent = `(${utils.formatTime(timeLeft)})`;
                timeEl.classList.toggle('sr-only', state.viewMode === 'timeline');
            } else if (timeEl) timeEl.remove();
        }
        function shouldShowTaskTiming(task) {
            return hasTaskDueDate(task) && !task.completed && !task.archived;
        }
        function renderReminderIcon(el, task) {
            const reminderIcon = el.querySelector('.task-reminder-icon');
            if (!reminderIcon) return;
            if (!shouldShowReminderIcon(task)) {
                reminderIcon.style.display = 'none';
                return;
            }
            reminderIcon.style.display = 'inline-block';
            reminderIcon.setAttribute('aria-label', utils.translate('notifications.reminderSet'));
            reminderIcon.setAttribute('role', 'img');
            reminderIcon.style.color = hasTaskReminderBeenDelivered(task) ? 'var(--text-tertiary)' : 'var(--color-warning)';
        }
        function shouldShowReminderIcon(task) {
            return hasTaskDueDate(task) && !task.completed && !task.archived && getTaskReminderOffset(task) !== -1;
        }
        function hasTaskReminderBeenDelivered(task) {
            if (state.notifiedTasks.has(getTaskNotificationKey(task))) return true;
            if (!task.lastReminderAt) return false;
            const last = new Date(task.lastReminderAt);
            if (Number.isNaN(last.getTime())) return false;
            const repeat = getTaskReminderRepeat(task);
            if (repeat === -1) return true;
            return (Date.now() - last.getTime()) / 60000 < repeat;
        }
        function renderTaskActionTitles(el, task, t) {
            renderTaskFocusButton(el.querySelector('[data-action="focus"]'), task, t);
            const toggleButton = el.querySelector('[data-action="toggle"]');
            renderTaskToggleButton(toggleButton, task.completed);
            if (toggleButton) toggleButton.hidden = !!task.archived;
            setButtonLabel(toggleButton, task.completed ? t['task.actions.markIncomplete'] : t['task.actions.markComplete']);
            renderTaskSnoozeButton(el.querySelector('[data-action="snooze"]'), task, t);
            renderTaskSkipRepeatButton(el.querySelector('[data-action="skip-repeat"]'), task, t);
            renderTaskArchiveButton(el.querySelector('[data-action="archive"]'), task, t);
            const editButton = el.querySelector('[data-action="edit"]');
            if (editButton) editButton.hidden = !!task.archived;
            setButtonLabel(editButton, t['task.actions.edit']);
            setButtonLabel(el.querySelector('[data-action="delete"]'), t['task.actions.delete']);
            syncTaskActionPendingState(el, task.id);
        }
        function renderTaskPlanningControls(el, task, t) {
            const planning = workspaceUI.planning && workspaceUI.screen === 'tasks' && state.viewMode === 'list';
            const planned = isTaskInTodayPlan(task);
            el.querySelector('.task-plan-badge').hidden = !planned || planning || Boolean(task.archived);
            const button = el.querySelector('[data-task-plan]');
            button.id = `task-plan-${task.id}`;
            button.hidden = !planning || Boolean(task.archived);
            button.setAttribute('aria-pressed', String(planned));
            const label = utils.translate(planned ? 'v5.planning.remove' : 'v5.planning.add');
            button.querySelector('[data-task-plan-label]').textContent = label;
            button.setAttribute('aria-label', `${label}: ${task.name}`);
            button.title = planned ? t['task.actions.removeFocus'] : t['task.actions.addFocus'];
        }
        function renderTaskFocusButton(button, task, t) {
            if (!button) return;
            button.hidden = !!task.archived;
            if (task.archived) return;
            const inFocus = isTaskInTodayPlan(task);
            button.classList.toggle(CONFIG.UI.CLASSES.ACTIVE, inFocus);
            const iconUse = button.querySelector('use');
            if (iconUse) iconUse.setAttribute('href', '#icon-target');
            setButtonLabel(button, inFocus ? t['task.actions.removeFocus'] : t['task.actions.addFocus']);
        }
        function syncTaskAccessibility(el, task) {
            el.setAttribute('role', 'article');
            el.setAttribute('aria-labelledby', `task-name-${task.id}`);
            el.setAttribute('aria-describedby', hasTaskDueDate(task) ? `task-date-${task.id} task-status-${task.id}` : `task-status-${task.id}`);
        }
        function renderTaskSnoozeButton(button, task, t) {
            if (!button) return;
            const visible = shouldShowReminderIcon(task);
            button.hidden = !visible;
            if (visible) setButtonLabel(button, translateCount('craft.snoozeAction', CONFIG.NOTIFICATIONS.SNOOZE_MINUTES).replace('{minutes}', CONFIG.NOTIFICATIONS.SNOOZE_MINUTES));
        }
        function renderTaskSkipRepeatButton(button, task, t) {
            if (!button) return;
            const visible = shouldShowSkipRepeatAction(task);
            button.hidden = !visible;
            if (visible) setButtonLabel(button, t['task.actions.skipRepeat']);
        }
        function shouldShowSkipRepeatAction(task) {
            const rule = getTaskRepeatRule(task);
            return hasTaskDueDate(task) && rule.type !== 'none' && !rule.paused && !task.completed && !task.archived;
        }
        function renderTaskArchiveButton(button, task, t) {
            if (!button) return;
            button.hidden = false;
            const iconUse = button.querySelector('use');
            if (iconUse) iconUse.setAttribute('href', task.archived ? '#icon-archive-restore' : '#icon-archive');
            setButtonLabel(button, task.archived ? t['task.actions.restoreArchive'] : t['task.actions.archive']);
        }
        function renderTaskToggleButton(button, completed) {
            if (!button) return;
            button.classList.toggle('complete-btn', !completed);
            button.classList.toggle('restore-btn', completed);
            button.dataset.toggleState = completed ? 'restore' : 'complete';
            button.setAttribute('aria-pressed', String(completed));
            const iconUse = button.querySelector('use');
            if (iconUse) iconUse.setAttribute('href', '#icon-check');
        }
        function setButtonLabel(button, label) {
            if (!button) return;
            button.title = label;
            button.setAttribute('aria-label', label);
            const text = button.querySelector('[data-action-label]');
            if (text) text.textContent = label;
        }
        function syncTaskActionPendingState(el, taskId) {
            const pending = isAnyTaskActionPending(taskId);
            const opener = el.querySelector('[data-task-open]');
            if (opener) {
                opener.disabled = pending || Boolean(getTaskById(taskId)?.archived);
                opener.setAttribute('aria-busy', String(pending));
            }
            const plan = el.querySelector('[data-task-plan]');
            if (plan) {
                plan.disabled = pending || Boolean(getTaskById(taskId)?.archived);
                plan.setAttribute('aria-busy', String(pending));
            }
            el.querySelectorAll('[data-action="focus"], [data-action="toggle"], [data-action="snooze"], [data-action="skip-repeat"], [data-action="archive"]').forEach(button => {
                button.disabled = pending;
                button.setAttribute('aria-busy', String(pending));
            });
        }
        function renderTaskDragHandle(el) {
            const existingHandle = el.querySelector('.drag-handle');
            if (existingHandle) existingHandle.remove();
            el.removeAttribute('draggable');
            el.classList.remove('draggable-item');
            if (!canReorderTasks()) return;
            el.setAttribute('draggable', 'true');
            el.classList.add('draggable-item');
            el.prepend(createDragHandle(el.querySelector('.task-name')?.textContent || ''));
        }
        function renderTaskSelectionControl(el, task) {
            const existing = el.querySelector('.task-selection');
            if (!state.batchMode) {
                if (existing) existing.remove();
                return;
            }
            const selected = state.selectedTaskIds.has(task.id);
            let label = existing;
            if (!label) {
                label = document.createElement('label');
                label.className = 'task-selection';
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'task-select-checkbox';
                label.appendChild(checkbox);
                const dragHandle = el.querySelector('.drag-handle');
                if (dragHandle) dragHandle.after(label);
                else el.prepend(label);
            }
            const checkbox = label.querySelector('.task-select-checkbox');
            checkbox.checked = selected;
            checkbox.dataset.taskId = String(task.id);
            checkbox.setAttribute('aria-label', utils.translate('batch.selectTask').replace('{taskName}', task.name));
        }
        function createDragHandle(taskName) {
            const handle = document.createElement('button');
            handle.type = 'button';
            handle.className = 'drag-handle';
            handle.draggable = true;
            handle.setAttribute('aria-label', utils.translate('task.actions.reorder').replace('{taskName}', taskName));
            handle.innerHTML = `<svg class="icon"><use href="#icon-drag"></use></svg>`;
            return handle;
        }
        function renderSubtaskList(el, task) {
            let wrapper = el.querySelector('.subtasks-wrapper');
            if (!task.subtasks || task.subtasks.length === 0) {
                if (wrapper) wrapper.remove();
                return;
            }
            if (!wrapper) {
                wrapper = document.createElement('div');
                wrapper.className = 'subtasks-wrapper';
                const prev = el.querySelector('.task-meta-line') || el.querySelector('.task-desc') || el.querySelector('.task-header');
                prev.after(wrapper);
            }
            const total = task.subtasks.length;
            const completed = task.subtasks.filter(s => s.completed).length;
            const wasExpanded = wrapper.classList.contains(CONFIG.UI.CLASSES.EXPANDED);
            wrapper.textContent = '';
            const summaryBar = document.createElement('button');
            summaryBar.type = 'button';
            summaryBar.className = 'subtask-summary-bar';
            summaryBar.setAttribute('aria-expanded', String(wasExpanded));
            summaryBar.setAttribute('aria-controls', `subtasks-${task.id}`);
            const countText = document.createElement('div');
            countText.className = 'subtask-count-text';
            countText.appendChild(createIcon('icon-subtask-arrow', 'icon', { width: '14', height: '14', style: 'margin-right:6px' }));
            const progressText = document.createElement('span');
            progressText.className = 'progress-text';
            progressText.textContent = `${completed}/${total} ${state.translations[state.currentLanguage]['task.subtasks']}`;
            countText.appendChild(progressText);
            summaryBar.append(
                countText,
                createIcon('icon-subtask-toggle', 'icon icon-sm subtask-toggle-icon')
            );
            const subtaskList = document.createElement('div');
            subtaskList.className = 'subtasks-list';
            subtaskList.id = `subtasks-${task.id}`;
            subtaskList.setAttribute('role', 'list');
            task.subtasks.forEach(sub => {
                const item = document.createElement('div');
                item.className = `subtask-display-item ${sub.completed ? CONFIG.UI.CLASSES.COMPLETED : ''}`;
                item.setAttribute('role', 'listitem');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'subtask-checkbox';
                checkbox.dataset.subtaskId = String(sub.id);
                checkbox.checked = !!sub.completed;
                checkbox.setAttribute('aria-label', sub.text);
                const text = document.createElement('span');
                text.className = 'subtask-text';
                text.textContent = sub.text;
                item.append(checkbox, text);
                subtaskList.appendChild(item);
            });
            wrapper.append(summaryBar, subtaskList);
            if (wasExpanded) wrapper.classList.add(CONFIG.UI.CLASSES.EXPANDED);
        }
        function renderSubtaskPreview() {
            const listEl = DOM.subtaskListPreview;
            const count = document.getElementById('taskSubtaskCount');
            count.textContent = String(state.tempSubtasks.length);
            count.hidden = state.tempSubtasks.length === 0;
            listEl.querySelectorAll('.subtask-edit-input').forEach(input => { input.dataset.editorActive = 'false'; });
            listEl.replaceChildren();
            state.tempSubtasks.forEach((sub, index) => {
                listEl.appendChild(createSubtaskPreviewItem(sub, index));
            });
            if (state.editingSubtaskIndex >= 0) document.getElementById('taskSubtasksDetails').open = true;
            focusSubtaskEditInput(listEl.children[state.editingSubtaskIndex]);
        }
        function createSubtaskPreviewItem(subtask, index) {
            const li = document.createElement('li');
            li.className = 'subtask-preview-item';
            if (index === state.editingSubtaskIndex) {
                li.append(createSubtaskEditInput(subtask), createSubtaskDeleteButton(index, subtask.text, subtask.id));
            } else {
                li.append(createSubtaskPreviewText(subtask.text, index, subtask.id), createSubtaskDeleteButton(index, subtask.text, subtask.id));
            }
            return li;
        }
        function createSubtaskEditInput(subtask) {
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'subtask-edit-input';
            input.value = subtask.text;
            input.dataset.subtaskId = String(subtask.id);
            input.dataset.editorActive = 'true';
            input.setAttribute('aria-label', utils.translate('form.subtasks.editInput'));
            return input;
        }
        function createSubtaskPreviewText(text, index, subtaskId) {
            const span = document.createElement('span');
            span.className = 'subtask-preview-text';
            span.dataset.index = index;
            span.dataset.subtaskId = String(subtaskId);
            span.tabIndex = 0;
            span.setAttribute('role', 'button');
            span.setAttribute('aria-label', utils.translate('form.subtasks.edit').replace('{text}', text));
            span.textContent = text;
            return span;
        }
        function focusSubtaskEditInput(item) {
            const input = item?.querySelector('.subtask-edit-input');
            if (!input?.isConnected || document.activeElement === input) return;
            input.focus();
            input.setSelectionRange(input.value.length, input.value.length);
        }
        function setTranslatedText(el, key) {
            el.setAttribute('data-i18n', key);
            el.textContent = utils.translate(key);
        }
        function createIcon(symbolId, className = 'icon', attrs = {}) {
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('class', className);
            svg.setAttribute('aria-hidden', 'true');
            svg.setAttribute('focusable', 'false');
            Object.entries(attrs).forEach(([key, value]) => svg.setAttribute(key, value));
            const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
            use.setAttribute('href', `#${symbolId}`);
            svg.appendChild(use);
            return svg;
        }
        function markDecorativeIcons(root = document) {
            root.querySelectorAll('svg.icon').forEach(svg => {
                if (svg.getAttribute('role') === 'img') return;
                svg.setAttribute('aria-hidden', 'true');
                svg.setAttribute('focusable', 'false');
            });
        }
        function enhanceSelectControls(root = document) {
            root.querySelectorAll('select:not([data-custom-select-ready]):not([data-native-select])').forEach(enhanceSelectControl);
            syncAllCustomSelects(root);
        }
        function enhanceSelectControl(select) {
            select.dataset.customSelectReady = 'true';
            const wrapper = document.createElement('div');
            wrapper.className = 'custom-select';
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'custom-select-btn';
            button.id = `${select.id || `select-${Date.now()}`}-custom-button`;
            button.setAttribute('aria-haspopup', 'listbox');
            button.setAttribute('aria-expanded', 'false');
            const value = document.createElement('span');
            value.className = 'custom-select-value';
            const chevron = createIcon('icon-chevron-down', 'icon icon-sm chevron');
            button.append(value, chevron);
            const menu = document.createElement('div');
            menu.className = 'custom-select-menu';
            menu.id = `${button.id}-list`;
            menu.setAttribute('role', 'listbox');
            menu.setAttribute('aria-labelledby', button.id);
            button.setAttribute('aria-controls', menu.id);
            select.before(wrapper);
            wrapper.append(select, button, menu);
            select.classList.add('native-select-hidden');
            select.setAttribute('aria-hidden', 'true');
            select.tabIndex = -1;
            button.setAttribute('aria-label', getSelectAccessibleName(select));
            const label = select.id ? document.querySelector(`label[for="${CSS.escape(select.id)}"]`) : null;
            if (label && !label.dataset.customSelectLabelReady) {
                label.dataset.customSelectLabelReady = 'true';
                label.addEventListener('click', (e) => {
                    const control = document.getElementById(label.getAttribute('for'));
                    const customButton = control?.closest('.custom-select')?.querySelector('.custom-select-btn');
                    if (!customButton) return;
                    e.preventDefault();
                    customButton.focus();
                });
            }
            button.addEventListener('click', handleCustomSelectButtonClick);
            button.addEventListener('keydown', handleCustomSelectButtonKeydown);
            menu.addEventListener('click', handleCustomSelectMenuClick);
            menu.addEventListener('keydown', handleCustomSelectMenuKeydown);
            select.addEventListener('change', () => syncCustomSelect(select));
            syncCustomSelect(select);
        }
        function syncAllCustomSelects(root = document) {
            root.querySelectorAll('select[data-custom-select-ready]').forEach(syncCustomSelect);
        }
        function syncCustomSelect(select) {
            const wrapper = select.closest('.custom-select');
            if (!wrapper) return;
            const button = wrapper.querySelector('.custom-select-btn');
            const value = wrapper.querySelector('.custom-select-value');
            const selectedOption = select.options[select.selectedIndex] || select.options[0];
            button.disabled = select.disabled;
            button.setAttribute('aria-label', formatControlAccessibleValue(getSelectAccessibleName(select), selectedOption?.textContent || ''));
            if (value) value.textContent = selectedOption ? selectedOption.textContent : '';
            renderCustomSelectOptions(select);
        }
        function renderCustomSelectOptions(select) {
            const wrapper = select.closest('.custom-select');
            const menu = wrapper?.querySelector('.custom-select-menu');
            if (!menu) return;
            const signature = Array.from(select.options).map(option => `${option.value}:${option.textContent}:${option.disabled}`).join('|');
            if (menu.dataset.signature !== signature) {
                menu.textContent = '';
                Array.from(select.options).forEach((option, index) => {
                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'custom-select-option';
                    item.id = `${menu.id}-option-${index}`;
                    item.dataset.value = option.value;
                    item.setAttribute('role', 'option');
                    item.disabled = option.disabled;
                    const label = document.createElement('span');
                    label.textContent = option.textContent;
                    item.append(label, createIcon('icon-check', 'icon icon-sm'));
                    menu.appendChild(item);
                });
                menu.dataset.signature = signature;
            }
            menu.querySelectorAll('.custom-select-option').forEach(item => {
                const selected = item.dataset.value === select.value;
                item.classList.toggle(CONFIG.UI.CLASSES.SELECTED, selected);
                item.setAttribute('aria-selected', String(selected));
            });
        }
        function getSelectAccessibleName(select) {
            const label = select.id ? document.querySelector(`label[for="${CSS.escape(select.id)}"]`) : null;
            return select.getAttribute('aria-label') || label?.textContent?.trim() || select.name || 'Select';
        }
        function formatControlAccessibleValue(label, value) {
            const cleanLabel = String(label || '').trim();
            const cleanValue = String(value || '').trim();
            if (!cleanValue) return cleanLabel;
            if (!cleanLabel) return cleanValue;
            return `${cleanLabel}: ${cleanValue}`;
        }
        function handleCustomSelectButtonClick(e) {
            e.preventDefault();
            e.stopPropagation();
            const select = e.currentTarget.closest('.custom-select')?.querySelector('select');
            if (select) toggleCustomSelect(select);
        }
        function handleCustomSelectButtonKeydown(e) {
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(e.key)) return;
            e.preventDefault();
            const select = e.currentTarget.closest('.custom-select')?.querySelector('select');
            if (!select) return;
            openCustomSelect(select, (e.key === 'Enter' || e.key === ' ') ? 'selected' : e.key);
        }
        function handleCustomSelectMenuClick(e) {
            e.stopPropagation();
            const option = e.target.closest('.custom-select-option');
            if (option) chooseCustomSelectOption(option);
        }
        function handleCustomSelectMenuKeydown(e) {
            const option = e.target.closest('.custom-select-option');
            if (!option) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                closeCustomSelect(option.closest('.custom-select'), true);
                return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(e.key)) return;
            e.preventDefault();
            e.stopPropagation();
            if (e.key === 'Enter' || e.key === ' ') {
                chooseCustomSelectOption(option);
                return;
            }
            moveCustomSelectFocus(option.closest('.custom-select'), e.key, option);
        }
        function toggleCustomSelect(select) {
            const wrapper = select.closest('.custom-select');
            if (!wrapper || select.disabled) return;
            if (wrapper.classList.contains(CONFIG.UI.CLASSES.OPEN)) {
                closeCustomSelect(wrapper, false);
            } else openCustomSelect(select, 'selected');
        }
        function openCustomSelect(select, key = 'selected') {
            const wrapper = select.closest('.custom-select');
            if (!wrapper || select.disabled) return;
            closeAllCustomSelects(wrapper);
            syncCustomSelect(select);
            const menu = wrapper.querySelector('.custom-select-menu');
            const button = wrapper.querySelector('.custom-select-btn');
            wrapper.classList.add(CONFIG.UI.CLASSES.OPEN);
            button.setAttribute('aria-expanded', 'true');
            const rect = wrapper.getBoundingClientRect();
            const below = window.innerHeight - rect.bottom;
            const above = rect.top;
            wrapper.classList.toggle('open-up', below < 230 && above > below);
            const options = getCustomSelectOptions(wrapper);
            let target = options.find(option => option.classList.contains(CONFIG.UI.CLASSES.SELECTED)) || options[0];
            if (key === 'ArrowUp' || key === 'End') target = options[options.length - 1] || target;
            if (key === 'Home') target = options[0] || target;
            if (target) requestAnimationFrame(() => target.focus());
            if (menu && target) menu.setAttribute('aria-activedescendant', target.id);
        }
        function chooseCustomSelectOption(option) {
            if (option.disabled) return;
            const wrapper = option.closest('.custom-select');
            const select = wrapper?.querySelector('select');
            if (!select) return;
            select.value = option.dataset.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            closeCustomSelect(wrapper, true);
        }
        function moveCustomSelectFocus(wrapper, key, activeOption) {
            const options = getCustomSelectOptions(wrapper);
            if (options.length === 0) return;
            const currentIndex = Math.max(0, options.indexOf(activeOption));
            let nextIndex = currentIndex;
            if (key === 'ArrowDown') nextIndex = currentIndex === options.length - 1 ? 0 : currentIndex + 1;
            if (key === 'ArrowUp') nextIndex = currentIndex === 0 ? options.length - 1 : currentIndex - 1;
            if (key === 'Home') nextIndex = 0;
            if (key === 'End') nextIndex = options.length - 1;
            options[nextIndex].focus();
            wrapper.querySelector('.custom-select-menu')?.setAttribute('aria-activedescendant', options[nextIndex].id);
        }
        function getCustomSelectOptions(wrapper) {
            return Array.from(wrapper.querySelectorAll('.custom-select-option')).filter(option => !option.disabled);
        }
        function closeCustomSelect(wrapper, focusButton = false) {
            if (!wrapper) return;
            wrapper.classList.remove(CONFIG.UI.CLASSES.OPEN, 'open-up');
            const button = wrapper.querySelector('.custom-select-btn');
            const menu = wrapper.querySelector('.custom-select-menu');
            if (button) button.setAttribute('aria-expanded', 'false');
            if (menu) menu.removeAttribute('aria-activedescendant');
            if (focusButton && button) button.focus();
        }
        function closeAllCustomSelects(except = null) {
            document.querySelectorAll('.custom-select.open').forEach(wrapper => {
                if (wrapper !== except) closeCustomSelect(wrapper, false);
            });
        }
        function closeOpenCustomSelect(root = document) {
            const wrapper = root.querySelector('.custom-select.open');
            if (!wrapper) return false;
            closeCustomSelect(wrapper, true);
            return true;
        }
        function closeCustomSelectsOnOutsideClick(e) {
            if (!e.target.closest('.custom-select')) closeAllCustomSelects();
        }
        function createSubtaskDeleteButton(index, text, subtaskId) {
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'subtask-delete-btn';
            deleteBtn.dataset.index = index;
            deleteBtn.dataset.subtaskId = String(subtaskId);
            const label = utils.translate('form.subtasks.delete').replace('{text}', text);
            deleteBtn.title = label;
            deleteBtn.setAttribute('aria-label', label);
            deleteBtn.appendChild(createIcon('icon-x', 'icon icon-sm'));
            return deleteBtn;
        }
        function clearConfirmHandler() {
            if (DOM.submitBtn.dataset.recoveryConfirmGuard === 'true') {
                delete DOM.submitBtn.dataset.recoveryConfirmGuard;
                DOM.submitBtn.removeAttribute('aria-disabled');
            }
            if (DOM.submitBtn._confirmHandler) {
                DOM.submitBtn.removeEventListener('click', DOM.submitBtn._confirmHandler);
                delete DOM.submitBtn._confirmHandler;
            }
        }
        function resetDialogToFormMode() {
            retireTaskFormSession();
            state.modalMode = 'form';
            DOM.modal.dataset.dialogMode = 'editor';
            DOM.modal.removeAttribute('aria-describedby');
            const msg = document.getElementById('confirm-message-text');
            if (msg) msg.style.display = 'none';
            DOM.formGroups.forEach(g => { g.style.display = ''; });
            DOM.submitBtn.type = 'submit';
            DOM.cancelBtn.hidden = false;
            DOM.submitBtn.disabled = false;
            DOM.form.classList.remove('is-confirm');
            DOM.submitBtn.classList.remove('btn-danger');
            clearConfirmHandler();
        }
        function openModal(editingTask = null, options = {}) {
            closeMobileFilters({ restoreFocus: false });
            if (!ensureStorageAvailable()) return;
            beginDialogFeedbackContext();
            state.elementToFocusOnClose = captureFocusReturnTarget();
            workspaceUI.captureFormText = options.captureText ?? null;
            resetDialogToFormMode();
            DOM.form.reset();
            document.getElementById('taskAdvancedDetails').open = Boolean((editingTask && ((editingTask.repeatType || 'none') !== 'none' || Number(editingTask.reminderRepeat ?? -1) !== -1 || (hasTaskDueDate(editingTask) && Number(editingTask.reminderOffset ?? CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES) !== CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES))));
            state.editingSubtaskIndex = -1;
            if (editingTask) {
                prepareEditTaskForm(editingTask);
            } else {
                prepareNewTaskForm(options);
            }
            syncTaskProjectOptions();
            renderSubtaskPreview();
            document.getElementById('taskSubtasksDetails').open = Boolean(state.tempSubtasks.length || state.editingSubtaskIndex >= 0);
            utils.applyTranslations();
            enhanceSelectControls(DOM.modal);
            state.taskFormSession = { baseline: captureTaskFormDraft(), creationFocusDate: editingTask ? null : options.quickPayload?.focusDate || null, lastFocus: DOM.inputs.name, saving: false, prompt: null, lock: null, status: null };
            DOM.modal.style.display = 'flex';
            syncPageModalOpenState();
            syncTaskDraftRecoveryUI();
            DOM.inputs.name.focus();
        }
        function prepareEditTaskForm(editingTask) {
            state.editingTaskId = editingTask.id;
            state.editingTaskSnapshot = JSON.stringify(editingTask);
            setDialogFormLabels('modal.editTitle', 'actions.updateTask');
            DOM.inputs.name.value = editingTask.name;
            DOM.inputs.desc.value = editingTask.description || '';
            DOM.inputs.project.value = editingTask.project || '';
            DOM.inputs.tags.value = formatTagsInput(editingTask.tags);
            state.tempSubtasks = cloneSubtasksWithUniqueIds(editingTask.subtasks);
            const dueDateKey = getTaskDueDateKey(editingTask);
            setDeadlineControls({
                enabled: Boolean(dueDateKey),
                dateKey: dueDateKey,
                time: getTaskDueTimeValue(editingTask),
                reminderOffset: editingTask.reminderOffset ?? CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES,
                reminderRepeat: editingTask.reminderRepeat ?? -1,
                repeatType: editingTask.repeatType ?? 'none',
                repeatInterval: editingTask.repeatInterval ?? 1,
                repeatWeekdays: editingTask.repeatWeekdays ?? [],
                repeatPaused: editingTask.repeatPaused === true
            });
        }
        function prepareNewTaskForm(options = {}) {
            const dueDate = isValidDate(options.dueDate) ? options.dueDate : new Date();
            const captured = options.quickPayload;
            state.editingTaskId = null;
            state.editingTaskSnapshot = null;
            setDialogFormLabels('modal.addTitle', 'actions.addTask');
            DOM.inputs.name.value = captured?.name || '';
            DOM.inputs.desc.value = captured?.description || '';
            DOM.inputs.project.value = captured?.project || '';
            DOM.inputs.tags.value = captured ? formatTagsInput(captured.tags) : '';
            state.tempSubtasks = [];
            setDeadlineControls({
                enabled: captured ? Boolean(captured.dueAt) : Boolean(normalizeDueDateValue(options.dueDateKey)),
                date: dueDate,
                dateKey: captured ? getTaskDueDateKey(captured) : normalizeDueDateValue(options.dueDateKey),
                time: captured ? getTaskDueTimeValue(captured) : options.dueTime || CONFIG.DEFAULTS.TIME,
                reminderOffset: CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES,
                reminderRepeat: -1,
                repeatType: 'none',
                repeatInterval: 1,
                repeatWeekdays: [],
                repeatPaused: false
            });
        }
        function setDialogFormLabels(titleKey, submitKey) {
            setTranslatedText(DOM.modalTitle, titleKey);
            setTranslatedText(DOM.submitBtn, submitKey);
        }
        function setDeadlineControls({ enabled, date, dateKey, time, reminderOffset, reminderRepeat, repeatType, repeatInterval, repeatWeekdays, repeatPaused }) {
            delete DOM.inputs.repeatType.dataset.weekdaysInitialized;
            clearRepeatWeekdayError();
            clearEditorFieldError(DOM.inputs.date, 'dueDateError');
            clearEditorFieldError(DOM.inputs.repeatInterval, 'repeatIntervalError');
            DOM.inputs.noDeadline.checked = !enabled;
            DOM.inputs.date.disabled = !enabled;
            DOM.inputs.time.disabled = !enabled;
            DOM.inputs.reminderOffset.disabled = !enabled;
            DOM.inputs.reminderRepeat.disabled = !enabled || String(reminderOffset) === '-1';
            DOM.inputs.repeatType.disabled = !enabled;
            DOM.inputs.repeatInterval.disabled = !enabled;
            DOM.inputs.repeatPaused.disabled = !enabled;
            DOM.inputs.repeatWeekdayInputs.forEach(input => { input.disabled = !enabled; });
            DOM.inputs.date.value = dateKey || utils.formatDateInputValue(date || new Date());
            DOM.inputs.time.value = enabled ? (time || utils.formatTimeInputValue(date || new Date())) : CONFIG.DEFAULTS.TIME;
            setReminderSelectValue(DOM.inputs.reminderOffset, reminderOffset, CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES);
            setReminderSelectValue(DOM.inputs.reminderRepeat, reminderRepeat ?? -1, -1);
            syncReminderSelectLabels();
            DOM.inputs.repeatType.value = enabled ? normalizeTaskRepeatType(repeatType) : 'none';
            DOM.inputs.repeatInterval.value = String(normalizeTaskRepeatInterval(DOM.inputs.repeatType.value, repeatInterval));
            setSelectedRepeatWeekdays(normalizeTaskRepeatWeekdays(repeatWeekdays));
            DOM.inputs.repeatPaused.checked = Boolean(repeatPaused);
            syncDeadlineDependentSections();
            syncReminderRepeatControl();
            syncRepeatControls();
        }
        function setReminderSelectValue(select, value, fallback) {
            select.querySelectorAll('option[data-reminder-custom]').forEach(option => option.remove());
            const numeric = Number(value);
            const normalized = Number.isFinite(numeric) ? numeric : fallback;
            const selected = String(normalized);
            if (!Array.from(select.options).some(option => option.value === selected)) {
                const option = document.createElement('option');
                option.value = selected;
                option.dataset.reminderCustom = select === DOM.inputs.reminderOffset
                    ? `form.reminder.options.${normalized < 0 ? 'customAfter' : 'customBefore'}`
                    : 'form.reminderRepeat.options.custom';
                select.appendChild(option);
            }
            select.value = selected;
        }
        function syncReminderSelectLabels() {
            document.querySelectorAll('option[data-reminder-custom]').forEach(option => {
                const minutes = option.parentElement === DOM.inputs.reminderOffset ? String(Math.abs(Number(option.value))) : option.value;
                option.textContent = translateCount(option.dataset.reminderCustom, minutes).replace('{minutes}', minutes);
            });
        }
        function syncDeadlineDependentSections() {
            const noDeadline = DOM.inputs.noDeadline.checked;
            DOM.inputs.date.disabled = noDeadline;
            DOM.inputs.date.required = !noDeadline;
            if (noDeadline || normalizeDueDateValue(DOM.inputs.date.value)) clearEditorFieldError(DOM.inputs.date, 'dueDateError');
            DOM.inputs.time.disabled = noDeadline;
            DOM.inputs.reminderOffset.disabled = noDeadline;
            if (DOM.deadlineFields) DOM.deadlineFields.hidden = noDeadline;
            if (DOM.reminderGroup) DOM.reminderGroup.hidden = noDeadline;
            if (DOM.repeatGroup) DOM.repeatGroup.hidden = noDeadline;
            document.getElementById('taskScheduleUnavailable').hidden = !noDeadline;
            syncEditorDatePresets();
            if (noDeadline) closeAllCustomSelects();
        }
        function syncReminderRepeatControl() {
            DOM.inputs.reminderRepeat.disabled = DOM.inputs.noDeadline.checked || DOM.inputs.reminderOffset.value === '-1';
            syncAllCustomSelects(DOM.modal);
        }
        function syncRepeatControls() {
            const disabled = DOM.inputs.noDeadline.checked;
            DOM.inputs.repeatType.disabled = disabled;
            const repeatType = normalizeTaskRepeatType(DOM.inputs.repeatType.value);
            const custom = !disabled && repeatType === 'custom';
            const weeklyDays = !disabled && repeatType === 'weekly-days';
            const repeatEnabled = !disabled && repeatType !== 'none';
            DOM.inputs.repeatCustomRow.hidden = !custom;
            DOM.inputs.repeatWeekdaysRow.hidden = !weeklyDays;
            DOM.inputs.repeatPauseRow.hidden = !repeatEnabled;
            DOM.inputs.repeatInterval.disabled = !custom;
            DOM.inputs.repeatInterval.required = custom;
            if (!custom) clearEditorFieldError(DOM.inputs.repeatInterval, 'repeatIntervalError');
            DOM.inputs.repeatWeekdayInputs.forEach(input => { input.disabled = !weeklyDays; });
            DOM.inputs.repeatPaused.disabled = !repeatEnabled;
            if (weeklyDays && getSelectedRepeatWeekdays().length === 0 && !DOM.inputs.repeatType.dataset.weekdaysInitialized) setSelectedRepeatWeekdays([1, 3, 5]);
            if (weeklyDays) DOM.inputs.repeatType.dataset.weekdaysInitialized = 'true';
            if (!weeklyDays || getSelectedRepeatWeekdays().length) clearRepeatWeekdayError();
            syncAllCustomSelects(DOM.modal);
        }
        function revealEditorElement(element) {
            if (!element?.isConnected || state.modalMode !== 'form' || !isTaskDialogOpen()) return;
            let disclosure = element.closest('details');
            while (disclosure) { disclosure.open = true; disclosure = disclosure.parentElement?.closest('details'); }
            const form = DOM.form.getBoundingClientRect();
            const footer = DOM.form.querySelector('.form-actions').getBoundingClientRect();
            const header = DOM.modal.querySelector('.modal-header').getBoundingClientRect();
            const top = Math.max(form.top, header.bottom) + 12;
            const bottom = Math.min(form.bottom, footer.top, window.innerHeight) - 12;
            const rect = element.getBoundingClientRect();
            if (rect.height > bottom - top || rect.top < top) DOM.form.scrollTop += rect.top - top;
            else if (rect.bottom > bottom) DOM.form.scrollTop += rect.bottom - bottom;
        }
        function clearRepeatWeekdayError() {
            const error = document.getElementById('repeatWeekdaysError');
            if (error) error.hidden = true;
            const group = document.querySelector('#repeatWeekdaysRow .repeat-weekdays');
            group?.removeAttribute('aria-invalid');
            group?.removeAttribute('aria-describedby');
        }
        function isValidFormRepeatInterval() {
            const value = DOM.inputs.repeatInterval.value.trim();
            const number = Number(value);
            return value !== '' && Number.isInteger(number) && number >= 1 && number <= 365;
        }
        function clearEditorFieldError(input, errorId) {
            const error = document.getElementById(errorId);
            if (error) error.hidden = true;
            input?.removeAttribute('aria-invalid');
            if (!input) return;
            const descriptions = (input.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== errorId);
            if (descriptions.length) input.setAttribute('aria-describedby', descriptions.join(' '));
            else input.removeAttribute('aria-describedby');
        }
        function showEditorFieldError(input, errorId) {
            const error = document.getElementById(errorId);
            error.hidden = false;
            input.setAttribute('aria-invalid', 'true');
            const descriptions = new Set((input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
            descriptions.add(errorId);
            input.setAttribute('aria-describedby', [...descriptions].join(' '));
            const details = input.closest('details');
            if (details) details.open = true;
            const group = input.closest('.repeat-custom-row, .form-group');
            revealEditorElement(group || input);
            input.focus({ preventScroll: true });
        }
        function syncEditorDatePresets() {
            document.querySelectorAll('.editor-date-presets [data-task-date-preset]').forEach(button => {
                const preset = button.dataset.taskDatePreset;
                if (preset !== 'pick') button.setAttribute('aria-pressed', String(!DOM.inputs.noDeadline.checked && DOM.inputs.date.value === getRelativeDateKey(Number(preset))));
            });
        }
        function syncTaskProjectOptions() {
            const list = document.getElementById('taskProjectOptions');
            list.replaceChildren();
            const names = Array.from(new Set(state.tasks.map(task => normalizeTaskProject(task.project)).filter(Boolean)));
            names.sort((a, b) => a.localeCompare(b, state.currentLanguage));
            names.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                list.appendChild(option);
            });
        }
        function getSelectedRepeatWeekdays() {
            return normalizeTaskRepeatWeekdays(DOM.inputs.repeatWeekdayInputs
                .filter(input => input.checked)
                .map(input => input.value));
        }
        function getRepeatWeekdaysForForm() {
            const selected = getSelectedRepeatWeekdays();
            return selected;
        }
        function setSelectedRepeatWeekdays(weekdays) {
            const selected = new Set(normalizeTaskRepeatWeekdays(weekdays));
            DOM.inputs.repeatWeekdayInputs.forEach(input => { input.checked = selected.has(Number(input.value)); });
        }
        function captureTaskFormDraft() {
            const values = {};
            Object.entries(DOM.inputs).forEach(([key, input]) => {
                if (key === 'search') return;
                if (input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement || input instanceof HTMLSelectElement) values[key] = input.type === 'checkbox' ? input.checked : input.value;
            });
            values.weekdays = DOM.inputs.repeatWeekdayInputs.map(input => input.checked);
            const subtasks = state.tempSubtasks.map(subtask => ({ ...subtask }));
            const editing = getActiveSubtaskEditInput();
            const edited = editing && subtasks.find(subtask => String(subtask.id) === editing.dataset.subtaskId);
            if (edited) edited.text = editing.value;
            return JSON.stringify({ values, subtasks });
        }
        function isTaskFormDirty() {
            return Boolean(state.taskFormSession && state.modalMode === 'form' && isTaskDialogOpen() && captureTaskFormDraft() !== state.taskFormSession.baseline);
        }
        function hasUnsavedTaskWork() {
            return isTaskFormDirty() || state.recoverableTaskDrafts.length > 0 || hasUnsavedQuickAddText();
        }
        function handleTaskDraftBeforeUnload(event) {
            if (!hasUnsavedTaskWork()) return;
            event.preventDefault();
            event.returnValue = '';
        }
        function preserveTaskDraftForRecovery() {
            if (!isTaskFormDirty()) return;
            const session = state.taskFormSession;
            const id = session.recoveryId || `draft-${Date.now()}-${++state.taskDraftRecoverySequence}`;
            const draft = {
                id,
                capturedAt: new Date().toISOString(),
                form: JSON.parse(captureTaskFormDraft()),
                editingTaskId: state.editingTaskId,
                editingTaskSnapshot: state.editingTaskSnapshot,
                editingSubtaskIndex: state.editingSubtaskIndex,
                baseline: session.baseline,
                creationFocusDate: session.creationFocusDate,
                captureText: workspaceUI.captureFormText,
                advancedOpen: document.getElementById('taskAdvancedDetails').open,
                subtasksOpen: document.getElementById('taskSubtasksDetails').open
            };
            const existing = state.recoverableTaskDrafts.findIndex(item => item.id === id);
            if (existing === -1) state.recoverableTaskDrafts.push(draft);
            else state.recoverableTaskDrafts[existing] = draft;
            session.recoveryId = id;
        }
        function syncTaskDraftRecoveryUI() {
            if (!DOM.taskDraftRecoveryBanner) return;
            const count = state.recoverableTaskDrafts.length;
            DOM.taskDraftRecoveryBanner.hidden = count === 0;
            if (!count) return;
            const blocked = Boolean(state.taskFormSession && state.modalMode === 'form' && isTaskDialogOpen());
            document.getElementById('taskDraftRecoveryDescription').textContent = translateCount('drafts.recoveryDescription', count).replace('{count}', count);
            const statusKey = !state.storageAvailable ? 'drafts.recoveryWaiting' : blocked ? 'drafts.recoveryBlocked' : '';
            const status = document.getElementById('taskDraftRecoveryStatus');
            status.textContent = statusKey ? utils.translate(statusKey) : '';
            status.hidden = !statusKey;
            DOM.taskDraftRecoveryRestoreBtn.disabled = !state.storageAvailable || blocked;
            DOM.taskDraftRecoveryDiscardBtn.disabled = blocked;
        }
        function downloadRecoverableTaskDrafts() {
            if (!state.recoverableTaskDrafts.length) return;
            const date = new Date().toISOString();
            downloadJsonPayload({
                app: 'Task Tracer',
                type: 'task-draft',
                version: '1.0',
                date,
                notice: translateCount('drafts.recoveryDescription', state.recoverableTaskDrafts.length).replace('{count}', state.recoverableTaskDrafts.length),
                drafts: state.recoverableTaskDrafts
            }, `Task-Tracer-unsaved-drafts-${date.replace(/[:.]/g, '-')}.json`);
        }
        function restoreRecoverableTaskDraft() {
            if (!state.storageAvailable || !state.recoverableTaskDrafts.length || (state.taskFormSession && state.modalMode === 'form' && isTaskDialogOpen())) return;
            const draft = state.recoverableTaskDrafts[0];
            openModal(undefined, { captureText: draft.captureText ?? null });
            state.taskFormSession.creationFocusDate = normalizeFocusDate(draft.creationFocusDate);
            document.getElementById('taskAdvancedDetails').open = Boolean(draft.advancedOpen);
            document.getElementById('taskSubtasksDetails').open = Boolean(draft.subtasksOpen || draft.form.subtasks.length || draft.form.values.subtask?.trim() || draft.editingSubtaskIndex >= 0);
            Object.entries(draft.form.values).forEach(([key, value]) => {
                const input = DOM.inputs[key];
                if (key === 'search') return;
                if (input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement || input instanceof HTMLSelectElement) {
                    if (input.type === 'checkbox') input.checked = value; else input.value = value;
                }
            });
            setReminderSelectValue(DOM.inputs.reminderOffset, draft.form.values.reminderOffset, CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES);
            setReminderSelectValue(DOM.inputs.reminderRepeat, draft.form.values.reminderRepeat, -1);
            syncReminderSelectLabels();
            DOM.inputs.repeatWeekdayInputs.forEach((input, index) => { input.checked = draft.form.values.weekdays[index]; });
            state.editingTaskId = draft.editingTaskId;
            state.editingTaskSnapshot = draft.editingTaskSnapshot;
            state.tempSubtasks = draft.form.subtasks.map(subtask => ({ ...subtask }));
            state.editingSubtaskIndex = draft.editingSubtaskIndex;
            setDialogFormLabels(draft.editingTaskId === null ? 'modal.addTitle' : 'modal.editTitle', draft.editingTaskId === null ? 'actions.addTask' : 'actions.updateTask');
            syncDeadlineDependentSections();
            syncReminderRepeatControl();
            syncRepeatControls();
            DOM.inputs.repeatWeekdayInputs.forEach((input, index) => { input.checked = draft.form.values.weekdays[index]; });
            state.taskFormSession.baseline = draft.baseline;
            state.taskFormSession.recoveryId = draft.id;
            state.recoverableTaskDrafts.shift();
            syncAllCustomSelects(DOM.modal);
            syncTaskDraftRecoveryUI();
            renderSubtaskPreview();
            if (!DOM.subtaskListPreview.querySelector('.subtask-edit-input')) DOM.inputs.name.focus();
        }
        function discardRecoverableTaskDraft() {
            if (!state.recoverableTaskDrafts.length || (state.taskFormSession && state.modalMode === 'form' && isTaskDialogOpen())) return;
            const draft = state.recoverableTaskDrafts[0];
            utils.confirm(utils.translate('drafts.recoveryDiscardTitle'), utils.translate('drafts.recoveryDiscardDescription'), () => {
                state.recoverableTaskDrafts = state.recoverableTaskDrafts.filter(item => item.id !== draft.id);
                syncTaskDraftRecoveryUI();
            });
        }
        function lockTaskDraftForm(session, hideFields = false) {
            closeTaskTagSuggestions();
            if (session.lock) return;
            session.lock = {
                groups: Array.from(DOM.formGroups, group => ({ group, inert: group.inert, hidden: group.getAttribute('aria-hidden') })),
                controls: [DOM.closeModalBtn, DOM.cancelBtn, DOM.submitBtn].map(control => ({ control, disabled: control.disabled })),
                labelledBy: DOM.modal.getAttribute('aria-labelledby'),
                describedBy: DOM.modal.getAttribute('aria-describedby')
            };
            session.lock.groups.forEach(({ group }) => { group.inert = true; if (hideFields) group.setAttribute('aria-hidden', 'true'); });
            session.lock.controls.forEach(({ control }) => { control.disabled = true; });
        }
        function unlockTaskDraftForm(session) {
            if (!session.lock) return;
            session.lock.groups.forEach(({ group, inert, hidden }) => {
                group.inert = inert;
                if (hidden === null) group.removeAttribute('aria-hidden'); else group.setAttribute('aria-hidden', hidden);
            });
            session.lock.controls.forEach(({ control, disabled }) => { control.disabled = disabled; });
            for (const [attribute, value] of [['aria-labelledby', session.lock.labelledBy], ['aria-describedby', session.lock.describedBy]]) {
                if (value === null) DOM.modal.removeAttribute(attribute); else DOM.modal.setAttribute(attribute, value);
            }
            session.lock = null;
        }
        function dismissTaskDraftDiscard() {
            const session = state.taskFormSession;
            if (!session?.prompt) return;
            session.prompt.remove();
            session.prompt = null;
            unlockTaskDraftForm(session);
            const focus = session.lastFocus?.isConnected && !session.lastFocus.disabled ? session.lastFocus : DOM.inputs.name;
            focus.focus();
        }
        function requestCloseTaskDialog() {
            const session = state.taskFormSession;
            if (session?.saving && state.modalMode === 'form') return;
            if (!isTaskFormDirty()) { closeDialog(); return; }
            if (session.prompt) { document.getElementById('draftKeepEditingBtn').focus(); return; }
            closeAllCustomSelects();
            lockTaskDraftForm(session, true);
            const prompt = document.createElement('div');
            prompt.id = 'draftDiscardPrompt';
            prompt.className = 'confirm-details';
            prompt.setAttribute('role', 'alert');
            const title = document.createElement('h3');
            title.id = 'draftDiscardTitle';
            title.textContent = utils.translate('drafts.title');
            const description = document.createElement('p');
            description.id = 'draftDiscardDescription';
            description.textContent = utils.translate('drafts.description');
            const keep = document.createElement('button');
            keep.type = 'button';
            keep.id = 'draftKeepEditingBtn';
            keep.className = 'btn btn-primary';
            keep.textContent = utils.translate('drafts.keepEditing');
            keep.addEventListener('click', dismissTaskDraftDiscard);
            const discard = document.createElement('button');
            discard.type = 'button';
            discard.id = 'draftDiscardBtn';
            discard.className = 'btn btn-secondary';
            discard.textContent = utils.translate('drafts.discard');
            discard.addEventListener('click', closeDialog);
            prompt.append(title, description, keep, discard);
            session.prompt = prompt;
            DOM.form.prepend(prompt);
            DOM.modal.setAttribute('aria-labelledby', title.id);
            DOM.modal.setAttribute('aria-describedby', description.id);
            keep.focus();
        }
        function retireTaskFormSession() {
            const session = state.taskFormSession;
            if (!session) return;
            session.prompt?.remove();
            session.status?.remove();
            unlockTaskDraftForm(session);
            state.taskFormSession = null;
            state.taskFormSaving = false;
        }
        function closeDialog() {
            const returnToCapture = workspaceUI.captureFormText !== null;
            retireTaskFormSession();
            if (state.pendingTaskImportReader) {
                const reader = state.pendingTaskImportReader;
                state.pendingTaskImportReader = null;
                reader.abort();
            }
            closeAllCustomSelects();
            DOM.modal.style.display = 'none';
            syncPageModalOpenState();
            syncTaskDraftRecoveryUI();
            state.editingTaskId = null;
            workspaceUI.captureFormText = null;
            DOM.form.reset();
            DOM.inputs.reminderOffset.disabled = false;
            DOM.inputs.reminderOffset.value = String(CONFIG.NOTIFICATIONS.DEFAULT_OFFSET_MINUTES);
            DOM.inputs.reminderRepeat.disabled = false;
            DOM.inputs.reminderRepeat.value = '-1';
            DOM.inputs.repeatType.disabled = false;
            DOM.inputs.repeatType.value = 'none';
            DOM.inputs.repeatInterval.value = '1';
            DOM.inputs.repeatPaused.checked = false;
            setSelectedRepeatWeekdays([]);
            syncRepeatControls();
            state.tempSubtasks = [];
            state.editingSubtaskIndex = -1;
            resetDialogToFormMode();
            restoreFocusReturnTarget(state.elementToFocusOnClose);
            state.elementToFocusOnClose = null;
            if (returnToCapture) setCaptureShelf(true, { focus: true });
        }
        const repository = ports.createTaskRepository({
            name: CONFIG.DB.NAME, version: CONFIG.DB.VERSION,
            stores: { tasks: CONFIG.DB.STORES.TASKS, config: CONFIG.DB.STORES.CONFIG },
            keys: { revision: 'taskRevision', recoveryHistory: 'recoveryHistory', savedViews: CONFIG.STORAGE.SAVED_VIEWS,
                lastBackupAt: CONFIG.STORAGE.LAST_BACKUP_AT, lastTaskBackup: CONFIG.STORAGE.LAST_TASK_BACKUP },
            recovery: { limit: CONFIG.BACKUP.RECOVERY_LIMIT, intervalMs: CONFIG.BACKUP.RECOVERY_INTERVAL_MS },
            now: () => Date.now(), createId: () => crypto.randomUUID()
        });
        const observeTaskWrite = promise => promise.then(result => { state.taskRevision = result.taskRevision; });
        const taskWriteOptions = () => ({ expectedRevision: state.taskRevision });
        const deletionWriteOptions = () => ({ ...taskWriteOptions(), getDeletionUpdates: getRepeatDeletionUpdates });
        const dbActions = {
            init: async () => {
                state.db = await repository.open({ onVersionChange: (database, error) => {
                    if (state.db !== database) return;
                    state.db = null;
                    handleStorageUnavailable(error);
                } });
                return state.db;
            },
            readTaskSnapshot: () => repository.readTaskSnapshot(state.db),
            getAllTasks: async () => {
                const snapshot = await repository.readTaskSnapshot(state.db);
                state.taskRevision = snapshot.taskRevision;
                return snapshot.tasks;
            },
            getTaskBackupStatus: () => repository.getTaskBackupStatus(state.db),
            recordTaskBackup: (date, taskRevision) => repository.recordTaskBackup(state.db, date, taskRevision).then(() => {}),
            addTask: task => observeTaskWrite(repository.addTask(state.db, task, taskWriteOptions())),
            addTasksIfEmpty: tasks => observeTaskWrite(repository.addTasksIfEmpty(state.db, tasks, taskWriteOptions())),
            updateTask: task => observeTaskWrite(repository.updateTask(state.db, task, taskWriteOptions())),
            updateTasks: tasks => observeTaskWrite(repository.updateTasks(state.db, tasks, taskWriteOptions())),
            deleteTask: id => observeTaskWrite(repository.deleteTask(state.db, id, deletionWriteOptions())),
            deleteTasks: ids => observeTaskWrite(repository.deleteTasks(state.db, ids, deletionWriteOptions())),
            mergeImportedTasks: (tasks, ids) => observeTaskWrite(repository.mergeImportedTasks(state.db, tasks, ids, deletionWriteOptions())),
            replaceAllTasks: tasks => observeTaskWrite(repository.replaceAllTasks(state.db, tasks, taskWriteOptions())),
            undoTaskChanges: (before, after) => observeTaskWrite(repository.undoTaskChanges(state.db, before, after, taskWriteOptions())),
            recordReminderDelivery: (expected, time) => repository.recordReminderDelivery(state.db, expected, time,
                { getNotificationKey: getTaskNotificationKey }).then(result => result.recorded),
            getConfig: key => repository.getConfig(state.db, key),
            setConfig: (key, value) => repository.setConfig(state.db, key, value),
            deleteConfig: key => repository.deleteConfig(state.db, key),
            updateSavedViews: change => repository.updateSavedViews(state.db, raw => change(normalizeSavedViews(raw))),
            clearReviewedRecoveryHistory: keys => repository.clearReviewedRecoveryHistory(state.db, keys),
            renameProject: (previous, next, undo) => repository.renameProject(
                state.db, previous, next, { ...taskWriteOptions(), undo,
                    normalizeProject: normalizeTaskProject, renameReferences: renameProjectReferences }
            ).then(result => { state.taskRevision = result.taskRevision; return result; })
        };
        const initDB = dbActions.init;
        const utils = {
            debounce: (func, delay = 300) => {
                let id;
                const debounced = (...args) => {
                    clearTimeout(id);
                    id = setTimeout(() => { id = undefined; func(...args); }, delay);
                };
                debounced.cancel = () => { clearTimeout(id); id = undefined; };
                return debounced;
            },
            notify: (msg, type = 'success', options = {}) => {
                syncDialogFeedbackPlacement();
                const hadFocus = DOM.notification.el.contains(document.activeElement);
                if (!hadFocus) state.notificationReturnFocus = captureFocusReturnTarget();
                if (state.notificationHideTimer) {
                    clearTimeout(state.notificationHideTimer);
                    state.notificationHideTimer = null;
                }
                DOM.notification.text.setAttribute('aria-live', (type === 'error' || type === 'warning') ? 'assertive' : 'polite');
                const icon = { success: 'icon-check', warning: 'icon-alert-triangle', error: 'icon-circle-error', info: 'icon-circle-info' }[type] || 'icon-circle-info';
                DOM.notification.el.querySelector('svg use')?.setAttribute('href', `#${icon}`);
                DOM.notification.el.className = `notification ${type} show`;
                const showUndo = options.undo === true && Boolean(state.undoAction);
                if (DOM.notification.undoBtn) {
                    DOM.notification.undoBtn.hidden = !showUndo;
                    DOM.notification.undoBtn.textContent = utils.translate('undo.action');
                }
                state.notificationTaskId = options.openTaskId ?? null;
                const openTask = document.getElementById('notificationOpenTaskBtn');
                openTask.hidden = state.notificationTaskId === null;
                openTask.textContent = utils.translate('usability.openSavedTask');
                DOM.notification.text.textContent = msg;
                if (hadFocus && (document.activeElement === document.body || !isFocusableReturnElement(document.activeElement))) document.getElementById('workspaceNotificationClose').focus({ preventScroll: true });
                state.notificationRemaining = showUndo || state.notificationTaskId !== null ? 6500 : 3000;
                resumeNotificationTimer();
            },
            announce: (msg) => {
                if (!DOM.srStatus) return;
                DOM.srStatus.textContent = '';
                requestAnimationFrame(() => {
                    DOM.srStatus.textContent = msg;
                });
            },
            confirm: (title, msg, onConfirm) => {
                beginDialogFeedbackContext();
                DOM.submitBtn.classList.remove('btn-danger');
                retireTaskFormSession();
                state.modalMode = 'confirm';
                DOM.modal.dataset.dialogMode = 'confirm';
                DOM.form.classList.add('is-confirm');
                DOM.cancelBtn.hidden = false;
                clearConfirmHandler();
                DOM.modalTitle.textContent = title;
                DOM.modalTitle.removeAttribute('data-i18n');
                let p = document.getElementById('confirm-message-text');
                if (!p || p.tagName !== 'DIV') {
                    if (p) p.remove();
                    p = document.createElement('div');
                    p.id = 'confirm-message-text';
                    p.className = 'confirm-message';
                    DOM.form.prepend(p);
                }
                setConfirmMessageContent(p, msg);
                enhanceSelectControls(p);
                p.style.display = 'block';
                DOM.modal.setAttribute('aria-describedby', 'confirm-message-text');
                DOM.formGroups.forEach(g => g.style.display = 'none');
                const t = state.translations[state.currentLanguage];
                DOM.submitBtn.textContent = t['actions.confirm'];
                DOM.submitBtn.removeAttribute('data-i18n');
                DOM.submitBtn.type = 'button';
                DOM.submitBtn.disabled = false;
                updateImportSafetyGate(getImportPreviewRoot(p));
                const isCurrent = () => isTaskDialogOpen() && state.modalMode === 'confirm' && DOM.submitBtn._confirmHandler === handler;
                const handler = async event => {
                    event.preventDefault();
                    if (!isCurrent()) return;
                    DOM.submitBtn.disabled = true;
                    try {
                        const result = await onConfirm();
                        if (!isCurrent()) return;
                        if (result === false) {
                            DOM.submitBtn.disabled = false;
                            return;
                        }
                        closeDialog();
                    } catch (error) {
                        console.error('确认操作失败:', error);
                        if (isCurrent()) DOM.submitBtn.disabled = false;
                    }
                };
                DOM.submitBtn._confirmHandler = handler;
                DOM.submitBtn.addEventListener('click', handler);
                state.elementToFocusOnClose = captureFocusReturnTarget();
                DOM.modal.style.display = 'flex';
                syncPageModalOpenState();
                DOM.submitBtn.focus();
                return isCurrent;
            },
            applyTheme: (theme) => {
                document.documentElement.setAttribute('data-theme', theme);
                if (window.__TASK_TRACER_SET_THEME_CHROME__) window.__TASK_TRACER_SET_THEME_CHROME__(theme);
                else document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? CONFIG.UI.THEME.DARK_COLOR : CONFIG.UI.THEME.LIGHT_COLOR);
            },
            toggleTheme: () => setThemePreference(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'),
            formatDateInputValue: (date = new Date()) => TaskDates.formatDateInputValue(date),
            formatTimeInputValue: (date = new Date()) => TaskDates.formatTimeInputValue(date),
            localDateTimeToInstantISO: (date, time, zone = getCurrentTimeZone()) => TaskDates.localDateTimeToInstantISO(date, time, zone),
            formatDateObject: (date, timeZone = null) => {
                const d = date instanceof Date ? date : new Date(date);
                const cacheKey = `${state.currentLanguage}|${timeZone || 'local'}`;
                if (!state.dateTimeFormatters[cacheKey]) {
                    const options = {
                        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    };
                    if (timeZone) options.timeZone = normalizeTimeZoneName(timeZone);
                    state.dateTimeFormatters[cacheKey] = new Intl.DateTimeFormat(
                        state.currentLanguage,
                        options
                    );
                }
                return state.dateTimeFormatters[cacheKey].format(d);
            },
            formatDate: (iso, timeZone = null) => utils.formatDateObject(new Date(iso), timeZone),
            formatTime: (min) => {
                const t = state.translations[state.currentLanguage];
                if (min < 0) {
                    const m = Math.abs(Math.floor(min));
                    if (m < 60) return translateCount('time.minutesAgo', m).replace('{minutes}', m);
                    if (m < 1440) return translateCount('time.hoursAgo', Math.floor(m/60)).replace('{hours}', Math.floor(m/60));
                    return translateCount('time.daysAgo', Math.floor(m/1440)).replace('{days}', Math.floor(m/1440));
                }
                const m = Math.floor(min);
                if (m < 60) return translateCount('time.minutesLeft', m).replace('{minutes}', m);
                if (m < 1440) {
                    const h = Math.floor(m/60), rest = m%60;
                    return `${translateCount('time.hoursLeft', h).replace('{hours}',h)} ${rest>0 ? translateCount('time.minutesLeft', rest).replace('{minutes}',rest) : ''}`;
                }
                const d = Math.floor(m/1440), h = Math.floor((m%1440)/60), rest = m%60;
                return `${translateCount('time.daysLeft', d).replace('{days}', d)} ${h>0 ? translateCount('time.hoursLeft', h).replace('{hours}', h) : ''} ${rest>0 ? translateCount('time.minutesLeft', rest).replace('{minutes}', rest) : ''}`;
            },
            getStatus: (min) => {
                const t = state.translations[state.currentLanguage];
                const S = CONFIG.UI.STATUS;
                if (min < 0) return { cls: S.OVERDUE, text: t['status.overdue'], percent: 100 };
                if (min <= 4320) return { cls: S.DANGER, text: t['status.danger'], percent: Math.min(100, ((4320 - min)/4320)*100) };
                if (min <= 10080) return { cls: S.WARNING, text: t['status.warning'], percent: Math.min(100, ((10080 - min)/5760)*100) };
                return { cls: S.SAFE, text: t['status.safe'], percent: Math.min(100, Math.max(0, ((53280 - min)/43200)*100)) };
            },
            sortTasks: (list) => {
                const l = [...list];
                switch (state.sort) {
                    case 'manual':
                        return l.sort((a, b) => {
                            const oA = (a.order !== undefined) ? a.order : 0;
                            const oB = (b.order !== undefined) ? b.order : 0;
                            if (oA !== oB) return oA - oB;
                            return a.id - b.id;
                        });
                    case 'created-desc': return l.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
                    case 'due-asc': return l.sort((a, b) => {
                        const dueA = getTaskDueSortValue(a);
                        const dueB = getTaskDueSortValue(b);
                        if (dueA === null && dueB !== null) return 1;
                        if (dueA !== null && dueB === null) return -1;
                        if (dueA === null && dueB === null) return 0;
                        return dueA - dueB;
                    });
                    case 'alpha-asc': return l.sort((a, b) => a.name.localeCompare(b.name, state.currentLanguage));
                    case 'smart':
                    default: return l.sort((a, b) => {
                        if (a.completed !== b.completed) return a.completed ? 1 : -1;
                        const dueA = getTaskDueSortValue(a);
                        const dueB = getTaskDueSortValue(b);
                        if (dueA === null && dueB !== null) return 1;
                        if (dueA !== null && dueB === null) return -1;
                        if (dueA !== null && dueB !== null) return dueA - dueB;
                        return new Date(a.createdAt) - new Date(b.createdAt);
                    });
                }
            },
            applyTranslations: () => {
                let t = state.translations[state.currentLanguage];
                if (!t) {
                    console.warn(`没有 ${state.currentLanguage} 可用的翻译。将要使用默认语言。`);
                    const fallbackLang = Object.keys(state.translations)[0];
                    if (!fallbackLang) {
                        console.error("完全没有翻译文件。");
                        return;
                    }
                    state.currentLanguage = fallbackLang;
                    t = state.translations[state.currentLanguage];
                }
                document.querySelectorAll('[data-i18n], [data-i18n-placeholder], [data-i18n-title], [data-i18n-aria-label]').forEach(el => {
                    if (el.dataset.i18n) el.textContent = utils.translate(el.dataset.i18n);
                    if (el.dataset.i18nPlaceholder) el.placeholder = utils.translate(el.dataset.i18nPlaceholder);
                    if (el.dataset.i18nTitle) el.title = utils.translate(el.dataset.i18nTitle);
                    if (el.dataset.i18nAriaLabel) el.setAttribute('aria-label', utils.translate(el.dataset.i18nAriaLabel));
                });
                syncDropdowns();
                syncReminderSelectLabels();
                syncAllCustomSelects();
                syncUndoControls();
                syncToolsDrawer();
                renderTaskList();
            },
            translate: (key) => {
                const current = state.translations[state.currentLanguage] || {};
                const fallback = state.translations[CONFIG.DEFAULTS.LANG] || {};
                return current[key] ?? fallback[key] ?? key;
            },
        };
        function setConfirmMessageContent(el, msg) {
            el.textContent = '';
            if (msg instanceof Node) {
                el.appendChild(msg);
            } else {
                el.textContent = msg;
            }
        }
        function setupDropdowns() {
            bindDropdownToggle(DOM.dropdowns.project);
            bindDropdownToggle(DOM.dropdowns.filter);
            bindDropdownToggle(DOM.dropdowns.sort);
            DOM.dropdowns.project.container.addEventListener('click', handleProjectDropdownClick);
            DOM.dropdowns.filter.container.addEventListener('click', handleFilterDropdownClick);
            DOM.dropdowns.sort.container.addEventListener('click', handleSortDropdownClick);
            document.addEventListener('click', closeDropdownsOnOutsideClick);
            let resizeFrame = 0;
            window.addEventListener('resize', () => {
                cancelAnimationFrame(resizeFrame);
                resizeFrame = requestAnimationFrame(() => {
                    Object.values(DOM.dropdowns).forEach(dropdown => {
                        if (isElementOpen(dropdown.container)) positionDropdownMenu(dropdown);
                    });
                });
            });
        }
        function bindDropdownToggle(dropdown) {
            dropdown.btn.addEventListener('click', (e) => {
                e.stopPropagation();
                runAppAction('dropdown.toggle', { dropdown });
            });
            dropdown.btn.addEventListener('keydown', (e) => handleDropdownButtonKeydown(e, dropdown));
            getDropdownMenu(dropdown).addEventListener('keydown', (e) => handleDropdownMenuKeydown(e, dropdown));
        }
        function handleDropdownButtonKeydown(e, dropdown) {
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return;
            e.preventDefault();
            runAppAction('dropdown.open', { dropdown, key: e.key });
        }
        function handleDropdownMenuKeydown(e, dropdown) {
            if (e.key === 'Escape') {
                e.preventDefault();
                closeDropdown(dropdown);
                dropdown.btn.focus();
                return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(e.key)) return;
            const option = e.target.closest('.dropdown-option');
            if (!option) return;
            e.preventDefault();
            if (e.key === 'Enter' || e.key === ' ') {
                option.click();
                return;
            }
            moveDropdownFocus(dropdown, e.key, option);
        }
        function toggleDropdown(dropdown) {
            const opening = !isElementOpen(dropdown.container);
            closeAllDropdowns();
            if (opening) openDropdownAndFocusOption(dropdown, 'selected');
        }
        function openDropdownAndFocusOption(dropdown, key) {
            openPopover(dropdown.container, dropdown.btn);
            positionDropdownMenu(dropdown);
            const options = getDropdownOptions(dropdown);
            if (options.length === 0) return;
            let target = options.find(option => option.classList.contains(CONFIG.UI.CLASSES.SELECTED)) || options[0];
            if (key === 'ArrowUp' || key === 'End') target = options[options.length - 1];
            if (key === 'Home') target = options[0];
            requestAnimationFrame(() => {
                if (isElementOpen(dropdown.container) && target.isConnected) target.focus();
            });
        }
        function positionDropdownMenu(dropdown) {
            const menu = getDropdownMenu(dropdown);
            menu.style.left = '';
            menu.style.right = '';
            menu.style.top = '';
            menu.style.bottom = '';
            menu.style.maxHeight = '';
            const button = dropdown.btn.getBoundingClientRect();
            if (DOM.mobileFiltersDialog?.open && DOM.mobileFiltersDialog.contains(dropdown.container)) {
                const below = Math.max(0, innerHeight - button.bottom - 16);
                const above = Math.max(0, button.top - 16);
                const opensUp = below < Math.min(menu.scrollHeight, 300) && above > below;
                const height = Math.min(menu.scrollHeight, Math.max(72, Math.min(300, opensUp ? above : below)));
                menu.style.maxHeight = `${height}px`;
                menu.style.overflowY = 'auto';
                menu.style.top = `${opensUp ? button.top - height - 6 : button.bottom + 6}px`;
                menu.style.bottom = 'auto';
                menu.style.left = `${Math.max(16, Math.min(button.left, innerWidth - menu.getBoundingClientRect().width - 16))}px`;
                return;
            }
            const header = document.querySelector('.workspace-topbar')?.getBoundingClientRect();
            const dock = document.querySelector('.workspace-mobile-dock')?.getBoundingClientRect();
            const viewportBottom = dock && dock.width > 0 && dock.height > 0 ? Math.min(innerHeight, dock.top) : innerHeight;
            const below = Math.max(0, viewportBottom - button.bottom - 12);
            const above = Math.max(0, button.top - Math.max(12, header?.bottom || 0) - 12);
            const opensUp = below < Math.min(menu.scrollHeight, 410) && above > below;
            menu.style.top = opensUp ? 'auto' : '100%';
            menu.style.bottom = opensUp ? 'calc(100% + 6px)' : 'auto';
            menu.style.maxHeight = `${Math.max(72, Math.min(410, opensUp ? above : below))}px`;
            menu.style.overflowY = 'auto';
            const rect = menu.getBoundingClientRect();
            const parent = dropdown.container.getBoundingClientRect();
            const left = Math.max(12, Math.min(rect.left, innerWidth - rect.width - 12));
            menu.style.left = `${left - parent.left}px`;
            menu.style.right = 'auto';
        }
        function handleProjectDropdownClick(e) {
            const option = e.target.closest('.dropdown-option');
            if (!option) return;
            try {
                const value = JSON.parse(option.dataset.project);
                if (isValidProjectFilter(value)) runAppAction('project.filter', { value });
            } catch {}
        }
        function handleFilterDropdownClick(e) {
            const option = e.target.closest('.dropdown-option');
            if (!option) return;
            runAppAction('filter.set', { value: option.dataset.filter });
        }
        function handleSortDropdownClick(e) {
            const option = e.target.closest('.dropdown-option');
            if (!option) return;
            runAppAction('sort.set', { value: option.dataset.sort });
        }
        function closeDropdownsOnOutsideClick(e) {
            if (!e.target.closest('.dropdown-container')) {
                closeAllDropdowns();
            }
        }
        function closeAllDropdowns() {
            Object.values(DOM.dropdowns).forEach(closeDropdown);
        }
        function closeDropdown(dropdown) {
            closePopover(dropdown.container, dropdown.btn);
        }
        function getDropdownMenu(dropdown) {
            return dropdown.container.querySelector('.dropdown-menu-content');
        }
        function getDropdownOptions(dropdown) {
            return getAllDropdownOptions(dropdown)
                .filter(option => option.offsetParent !== null);
        }
        function getAllDropdownOptions(dropdown) {
            return Array.from(dropdown.container.querySelectorAll('.dropdown-option'))
                .filter(option => !option.disabled);
        }
        function moveDropdownFocus(dropdown, key, activeOption) {
            const options = getDropdownOptions(dropdown);
            if (options.length === 0) return;
            const currentIndex = Math.max(0, options.indexOf(activeOption));
            let nextIndex = currentIndex;
            if (key === 'ArrowDown') nextIndex = currentIndex === options.length - 1 ? 0 : currentIndex + 1;
            if (key === 'ArrowUp') nextIndex = currentIndex === 0 ? options.length - 1 : currentIndex - 1;
            if (key === 'Home') nextIndex = 0;
            if (key === 'End') nextIndex = options.length - 1;
            options[nextIndex].focus();
        }
        function syncDropdowns({ focusTrigger = null } = {}) {
            syncFilterToggleSummary();
            const projectOpt = getAllDropdownOptions(DOM.dropdowns.project)
                .find(option => option.dataset.project === projectFilterKey(state.projectFilter));
            if (projectOpt) updateDropdownUI(DOM.dropdowns.project.container, projectOpt, DOM.dropdowns.project.btn);
            const filterOpt = DOM.dropdowns.filter.container.querySelector(`.dropdown-option[data-filter="${state.filter}"]`);
            if (filterOpt) updateDropdownUI(DOM.dropdowns.filter.container, filterOpt, DOM.dropdowns.filter.btn);
            const sortOpt = DOM.dropdowns.sort.container.querySelector(`.dropdown-option[data-sort="${state.sort}"]`);
            if (sortOpt) updateDropdownUI(DOM.dropdowns.sort.container, sortOpt, DOM.dropdowns.sort.btn);
            if (focusTrigger) focusTrigger.focus();
        }
        function updateDropdownUI(container, selected, btn, { preserveOpen = false } = {}) {
            container.querySelectorAll('.dropdown-option').forEach(option => {
                const isSelected = option === selected;
                option.classList.toggle(CONFIG.UI.CLASSES.SELECTED, isSelected);
                option.setAttribute('aria-selected', String(isSelected));
            });
            if (!preserveOpen) closePopover(container, btn);
            const span = selected.querySelector('span');
            if (span) {
                const targetSpan = btn.querySelector('[id^="current"]');
                if (targetSpan) targetSpan.textContent = span.textContent;
                const baseLabel = getDropdownAccessibleName(btn);
                if (baseLabel) btn.setAttribute('aria-label', formatControlAccessibleValue(baseLabel, span.textContent));
            }
        }
        function getDropdownAccessibleName(btn) {
            return btn.dataset.i18nAriaLabel ? utils.translate(btn.dataset.i18nAriaLabel) : '';
        }
        function toggleMenu(menu, btn) {
            const opening = !isElementOpen(menu);
            if (opening) {
                openPopover(menu, btn);
            } else closeMenu();
        }
        function closeMenu() {
            if (!DOM.menu.container.classList.contains('menu')) return;
            closePopover(DOM.menu.container, DOM.menu.btn);
        }
        function openPopover(container, btn) {
            container.classList.add(CONFIG.UI.CLASSES.SHOW);
            setExpanded(btn, true);
            if (container === DOM.menu.container) requestAnimationFrame(() => focusFirstMenuItem(container));
        }
        function closePopover(container, btn) {
            container.classList.remove(CONFIG.UI.CLASSES.SHOW);
            setExpanded(btn, false);
        }
        function setExpanded(btn, expanded) {
            btn.setAttribute('aria-expanded', String(expanded));
        }
        function isElementOpen(el) {
            return el.classList.contains(CONFIG.UI.CLASSES.SHOW);
        }
        function handleTaskListClick(e) {
            const more = e.target.closest('.task-more-toggle');
            if (more) { toggleTaskActionMenu(more); return; }
            const plan = e.target.closest('[data-task-plan]');
            if (plan) {
                const taskId = getTaskIdFromElement(plan);
                if (!plan.disabled && workspaceUI.planning && !getTaskById(taskId)?.archived && !isAnyTaskActionPending(taskId)) {
                    runAppAction('task.action', { taskAction: 'focus', taskId, returnTarget: captureFocusReturnTarget(plan) });
                }
                return;
            }
            const opener = e.target.closest('[data-task-open]');
            if (opener) {
                const taskId = getTaskIdFromElement(opener);
                const task = getTaskById(taskId);
                if (opener.disabled || !task || task.archived || isAnyTaskActionPending(taskId)) return;
                const returnTarget = captureFocusReturnTarget(opener);
                closeTaskActionMenus(false);
                if (runAppAction('task.edit', { taskId }) && isTaskDialogOpen()) state.elementToFocusOnClose = returnTarget;
                return;
            }
            if (e.target.closest('.task-action-menu .action-btn')) closeTaskActionMenus(false);

            if (e.target.closest('#addExampleTasksBtn')) {
                addSampleTasks();
                return;
            }
            if (handleStatsShortcutClick(e)) return;
            if (handleCalendarActionClick(e)) return;
            if (handleCalendarDetailClick(e)) return;
            if (handleCalendarAddClick(e)) return;
            if (handleCalendarTaskClick(e)) return;
            if (handleTaskSelectionClick(e)) return;
            if (handleSubtaskCheckboxClick(e)) return;
            if (handleSubtaskRowClick(e)) return;
            if (handleSubtaskSummaryClick(e)) return;
            handleTaskActionClick(e);
        }
        function handleTaskSelectionClick(e) {
            if (!e.target.classList.contains('task-select-checkbox')) return false;
            e.stopPropagation();
            if (!canRunAppAction('batch.selectVisible', { closeSurfaces: false })) return true;
            toggleBatchTaskSelection(Number(e.target.dataset.taskId), e.target.checked);
            return true;
        }
        function handleStatsShortcutClick(e) {
            const button = e.target.closest('[data-stats-action], [data-stats-filter]');
            if (!button) return false;
            if (button.disabled || !canRunAppAction('filter.set')) return true;
            const action = button.dataset.statsAction || `inventory-${button.dataset.statsFilter}`;
            const stats = calculateTaskStats(getStatsScopeTasks());
            const reviewDate = button.dataset.statsDate || '';
            let project = null;
            if (action === 'project') {
                try { project = normalizeProjectFilter(JSON.parse(button.dataset.statsProject)); } catch { return true; }
            }
            const counts = {
                overdue: stats.overdue,
                today: stats.dueToday,
                undated: stats.undated,
                pending: stats.pending,
                'inventory-all': stats.total,
                'inventory-completed': stats.completed,
                'inventory-overdue': stats.overdue,
                'inventory-archived': stats.archived,
                'review-week': stats.completedWeek,
                'review-day': stats.completionTrend.find(day => day.key === reviewDate)?.count
            };
            const count = action === 'project'
                ? stats.pendingTasks.filter(task => project.kind === 'unassigned' ? !normalizeTaskProject(task.project) : normalizeTaskProject(task.project) === project.name).length
                : counts[action];
            if (!Number.isFinite(count) || count <= 0) return true;
            const terms = {
                overdue: ['status:active', 'due:overdue'],
                today: ['status:active', 'due:today'],
                undated: ['status:active', 'due:none'],
                pending: ['status:active'],
                project: ['status:active'],
                'inventory-all': [],
                'inventory-completed': ['status:completed'],
                'inventory-overdue': ['status:active', 'due:overdue'],
                'inventory-archived': ['status:archived'],
                'review-week': ['completed:week'],
                'review-day': [`completed:${reviewDate}`]
            }[action];
            const origin = { rawQuery: DOM.inputs.search.value, query: state.searchQuery, projectFilter: normalizeProjectFilter(state.projectFilter), filter: state.filter,
                scrollY: window.scrollY, control: { action: button.dataset.statsAction || '', filter: button.dataset.statsFilter || '', project: button.dataset.statsProject || '', date: reviewDate } };
            const original = DOM.inputs.search.value.trim();
            setWorkspaceScreen('tasks', { render: false });
            state.projectFilter = normalizeProjectFilter(origin.projectFilter);
            const existing = new Set(normalizeSearchQuery(original).split(' ').filter(Boolean));
            const query = [original, ...terms.filter(term => !existing.has(term))].filter(Boolean).join(' ');
            state.focusMode = false;
            state.filter = action === 'inventory-archived' ? 'archived' : action === 'inventory-completed' ? 'completed'
                : ['inventory-all', 'review-week', 'review-day'].includes(action) ? 'all' : 'active';
            if (project) state.projectFilter = project;
            DOM.inputs.search.value = query;
            state.searchQuery = normalizeSearchQuery(query);
            workspaceUI.statsDrilldown = { origin, target: { query: state.searchQuery, projectFilter: normalizeProjectFilter(state.projectFilter), filter: state.filter } };
            state.viewMode = 'list';
            closeAllDropdowns();
            syncSearchClearButton();
            syncViewSwitcher();
            renderTaskList();
            syncDropdowns();
            announceTaskViewSummary();
            window.scrollTo({ top: 0, behavior: 'instant' });
            document.getElementById('workspaceTitle').focus({ preventScroll: true });
            return true;
        }
        function handleCalendarActionClick(e) {
            const button = e.target.closest('[data-calendar-action]');
            if (!button) return false;
            const action = button.dataset.calendarAction;
            if (action === 'undated-more' || action === 'detail-more') {
                if (!ensureStorageAvailable()) return true;
                const undated = action === 'undated-more';
                const selector = undated ? '.date-view-undated .task-item' : '.calendar-detail-task';
                const attribute = undated ? 'data-task-id' : 'data-calendar-task-id';
                const previousIds = new Set(Array.from(DOM.taskList.querySelectorAll(selector), node => node.getAttribute(attribute)));
                if (undated) state.listRenderLimit += 100;
                else state.calendarDetailRenderLimit += 100;
                renderTaskList();
                const firstNew = Array.from(DOM.taskList.querySelectorAll(selector)).find(node => !previousIds.has(node.getAttribute(attribute)));
                const target = undated ? ((state.batchMode ? firstNew?.querySelector('.task-select-checkbox') : null) || firstNew?.querySelector('button:not([disabled])')) : firstNew;
                if (target) target.focus();
                return true;
            }
            if (action === 'prev-year') shiftCalendarMonth(-12);
            if (action === 'prev') shiftCalendarMonth(-1);
            if (action === 'next') shiftCalendarMonth(1);
            if (action === 'next-year') shiftCalendarMonth(12);
            if (action === 'today') {
                state.calendarMonthDate = getCalendarTodayDate();
                state.calendarDetailDateKey = '';
                state.listRenderLimit = 100;
                state.calendarDetailRenderLimit = 100;
                renderTaskList();
            }
            const replacement = DOM.taskList.querySelector(`[data-calendar-action="${CSS.escape(action)}"]`);
            if (isFocusableReturnElement(replacement)) replacement.focus({ preventScroll: true });
            return true;
        }
        function handleCalendarDetailClick(e) {
            const close = e.target.closest('[data-calendar-detail-close]');
            if (close) {
                const closedDateKey = state.calendarDetailDateKey;
                state.calendarDetailDateKey = '';
                renderTaskList();
                requestAnimationFrame(() => focusCalendarMoreButton(closedDateKey));
                return true;
            }
            const button = e.target.closest('[data-calendar-detail-date]');
            if (!button) return false;
            state.calendarDetailDateKey = button.dataset.calendarDetailDate;
            state.calendarDetailRenderLimit = 100;
            renderTaskList();
            requestAnimationFrame(() => {
                const detail = DOM.taskList.querySelector('.calendar-day-detail');
                if (detail) scrollIntoViewWithMotionPreference(detail, { block: 'nearest' });
                const closeButton = detail ? detail.querySelector('.calendar-detail-close') : null;
                const target = closeButton && !closeButton.hidden ? closeButton : detail?.querySelector('.calendar-detail-title');
                target?.focus({ preventScroll: true });
            });
            return true;
        }
        function focusCalendarMoreButton(dateKey) {
            const escapedKey = CSS.escape(dateKey);
            const button = DOM.taskList.querySelector(`[data-calendar-detail-date="${escapedKey}"]`)
                || DOM.taskList.querySelector(`[data-calendar-add-date="${escapedKey}"]`);
            if (button && isFocusableReturnElement(button)) { button.focus(); return true; }
            return false;
        }
        function handleCalendarAddClick(e) {
            const button = e.target.closest('[data-calendar-add-date]');
            if (!button) return false;
            workspaceUI.captureDateKey = button.dataset.calendarAddDate;
            setCaptureShelf(true, { focus: true });
            return true;
        }
        function parseDateKey(dateKey) {
            const normalized = normalizeDueDateValue(dateKey);
            return normalized ? new Date(`${normalized}T12:00:00.000Z`) : getCalendarTodayDate();
        }
        function handleCalendarTaskClick(e) {
            const button = e.target.closest('[data-calendar-task-id]');
            if (!button) return false;
            runAppAction('task.edit', { taskId: Number(button.dataset.calendarTaskId) });
            return true;
        }
        function handleSubtaskCheckboxClick(e) {
            if (!e.target.classList.contains('subtask-checkbox')) return false;
            e.stopPropagation();
            runAppAction('subtask.toggle', { taskId: getTaskIdFromElement(e.target), subtaskId: Number(e.target.dataset.subtaskId) });
            return true;
        }
        function handleSubtaskRowClick(e) {
            const row = e.target.closest('.subtask-display-item');
            if (!row) return false;
            const checkbox = row.querySelector('.subtask-checkbox');
            if (checkbox && e.target !== checkbox) {
                checkbox.click();
                return true;
            }
            return false;
        }
        function handleSubtaskSummaryClick(e) {
            const summary = e.target.closest('.subtask-summary-bar');
            if (!summary) return false;
            const wrapper = summary.closest('.subtasks-wrapper');
            const expanded = wrapper.classList.toggle(CONFIG.UI.CLASSES.EXPANDED);
            summary.setAttribute('aria-expanded', String(expanded));
            return true;
        }
        function handleTaskActionClick(e) {
            const btn = e.target.closest('.action-btn');
            if (!btn) return false;
            if (btn.disabled) return true;
            const returnTarget = captureFocusReturnTarget(btn);
            const accepted = runAppAction('task.action', { taskAction: btn.dataset.action, taskId: getTaskIdFromElement(btn), returnTarget });
            if (!accepted && returnTarget.type === 'task-menu' && !isDialogOpen()) restoreFocusReturnTarget(returnTarget);
            return true;
        }
        async function runTaskAction(action, taskId, returnTarget = null) {
            if (!canRunAppAction('task.action', { closeSurfaces: false })) return;
            if (!isGuardedTaskAction(action)) {
                runUnguardedTaskAction(action, taskId);
                if (returnTarget?.type === 'task-menu' && isTaskDialogOpen()) state.elementToFocusOnClose = returnTarget;
                return;
            }
            const key = getTaskActionKey(taskId, action);
            if (state.pendingTaskActions.has(key)) return;
            state.pendingTaskActions.add(key);
            setTaskActionPending(taskId, true);
            try {
                await runGuardedTaskAction(action, taskId);
            } catch (error) {
                console.error('任务操作失败:', error);
                handleStorageOperationError(error);
            } finally {
                state.pendingTaskActions.delete(key);
                setTaskActionPending(taskId, false);
                const active = document.activeElement;
                if (['task-menu', 'task-plan'].includes(returnTarget?.type) && !isDialogOpen() && (active === document.body || !isFocusableReturnElement(active) || active.closest?.('.task-action-menu'))) restoreFocusReturnTarget(returnTarget);
            }
        }
        function runUnguardedTaskAction(action, taskId) {
            switch (action) {
                case 'edit': editTask(taskId); break;
                case 'delete': deleteTask(taskId); break;
            }
        }
        function runGuardedTaskAction(action, taskId) {
            switch (action) {
                case 'toggle': return toggleTaskComplete(taskId);
                case 'snooze': return snoozeTaskReminder(taskId);
                case 'skip-repeat': return skipRepeatOccurrence(taskId);
                case 'archive': return toggleTaskArchive(taskId);
                case 'focus': return toggleTaskFocus(taskId);
                default: return Promise.resolve();
            }
        }
        function isGuardedTaskAction(action) {
            return ['toggle', 'snooze', 'skip-repeat', 'archive', 'focus'].includes(action);
        }
        function getTaskActionKey(taskId, action) {
            return `${taskId}:${action}`;
        }
        function isAnyTaskActionPending(taskId) {
            return ['toggle', 'snooze', 'skip-repeat', 'archive', 'focus'].some(action => state.pendingTaskActions.has(getTaskActionKey(taskId, action)));
        }
        function setTaskActionPending(taskId, pending) {
            const el = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
            if (el) syncTaskActionPendingState(el, taskId);
        }
        function getTaskIdFromElement(el) {
            return Number(el.closest('.task-item').dataset.taskId);
        }
        function saveEditSubtask(inputEl) {
            if (!inputEl?.isConnected || inputEl !== getActiveSubtaskEditInput()) return;
            if (state.composingInputs.has(inputEl)) return;
            const subtask = state.tempSubtasks.find(item => String(item.id) === inputEl.dataset.subtaskId);
            if (!subtask) return;
            if (inputEl.value.trim()) subtask.text = inputEl.value.trim();
            state.editingSubtaskIndex = -1;
            renderSubtaskPreview();
        }
        function setupDragAndDrop() {
            const dragState = {
                item: null,
                scrollSpeed: 0,
                scrollFrameId: null
            };
            DOM.taskList.addEventListener('dragstart', (e) => handleTaskDragStart(e, dragState));
            DOM.taskList.addEventListener('dragend', () => finishTaskDrag(dragState, 'dragging'));
            DOM.taskList.addEventListener('dragover', (e) => handleTaskDragOver(e, dragState));
            DOM.taskList.addEventListener('keydown', handleTaskReorderKeydown);
            DOM.taskList.addEventListener('touchstart', (e) => handleTaskTouchStart(e, dragState), { passive: false });
            DOM.taskList.addEventListener('touchmove', (e) => handleTaskTouchMove(e, dragState), { passive: false });
            DOM.taskList.addEventListener('touchend', () => finishTaskDrag(dragState, 'touch-dragging'));
        }
        function handleTaskReorderKeydown(e) {
            const handle = e.target.closest('.drag-handle');
            if (!handle || !canReorderTasks()) return;
            if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) return;
            const item = handle.closest('.task-item');
            if (!item) return;
            e.preventDefault();
            const moved = moveTaskElementByKeyboard(item, e.key);
            if (!moved) {
                announceTaskReorderBoundary(item, e.key);
                return;
            }
            saveNewOrder();
            handle.focus();
            announceTaskReorderMove(item);
        }
        function moveTaskElementByKeyboard(item, key) {
            if (key === 'ArrowUp') {
                const previous = item.previousElementSibling;
                if (!previous) return false;
                DOM.taskList.insertBefore(item, previous);
                return true;
            }
            if (key === 'ArrowDown') {
                const next = item.nextElementSibling;
                if (!next) return false;
                DOM.taskList.insertBefore(item, next.nextElementSibling);
                return true;
            }
            if (key === 'Home') {
                const first = DOM.taskList.querySelector('.task-item');
                if (!first || first === item) return false;
                DOM.taskList.insertBefore(item, first);
                return true;
            }
            const items = Array.from(DOM.taskList.querySelectorAll('.task-item'));
            const last = items[items.length - 1];
            if (!last || last === item) return false;
            DOM.taskList.appendChild(item);
            return true;
        }
        function announceTaskReorderMove(item) {
            const taskName = item.querySelector('.task-name')?.textContent || '';
            const items = Array.from(DOM.taskList.querySelectorAll('.task-item'));
            const position = items.indexOf(item) + 1;
            utils.announce(utils.translate('messages.reorder.moved')
                .replace('{taskName}', taskName)
                .replace('{position}', position)
                .replace('{total}', items.length));
        }
        function announceTaskReorderBoundary(item, key) {
            const taskName = item.querySelector('.task-name')?.textContent || '';
            const messageKey = key === 'ArrowUp' || key === 'Home' ? 'messages.reorder.first' : 'messages.reorder.last';
            utils.announce(utils.translate(messageKey).replace('{taskName}', taskName));
        }
        function handleTaskDragStart(e, dragState) {
            if (!canReorderTasks()) return;
            const item = e.target.closest('.task-item');
            if (!item) return;
            dragState.item = item;
            e.dataTransfer.effectAllowed = 'move';
            requestAnimationFrame(() => item.classList.add('dragging'));
        }
        function handleTaskDragOver(e, dragState) {
            if (!canReorderTasks() || !dragState.item) return;
            e.preventDefault();
            updateDragPosition(dragState, e.clientY);
        }
        function handleTaskTouchStart(e, dragState) {
            if (!canReorderTasks()) return;
            const handle = e.target.closest('.drag-handle');
            if (!handle) return;
            const item = handle.closest('.task-item');
            if (!item) return;
            dragState.item = item;
            item.classList.add('touch-dragging');
            preventCancelableEvent(e);
        }
        function handleTaskTouchMove(e, dragState) {
            if (!canReorderTasks() || !dragState.item) return;
            preventCancelableEvent(e);
            updateDragPosition(dragState, e.touches[0].clientY);
        }
        function finishTaskDrag(dragState, activeClass) {
            if (!dragState.item) return;
            dragState.item.classList.remove(activeClass);
            stopAutoScroll(dragState);
            saveNewOrder();
            dragState.item = null;
        }
        function updateDragPosition(dragState, y) {
            handleEdgeScroll(dragState, y);
            moveDraggedTask(dragState, y);
        }
        function moveDraggedTask(dragState, y) {
            const afterElement = getDragAfterElement(DOM.taskList, y);
            const currentNextSibling = dragState.item.nextElementSibling;
            if (afterElement === currentNextSibling) return;
            if (afterElement == null) {
                DOM.taskList.appendChild(dragState.item);
            } else {
                DOM.taskList.insertBefore(dragState.item, afterElement);
            }
        }
        function handleEdgeScroll(dragState, y) {
            const threshold = CONFIG.DRAG.EDGE_SCROLL_THRESHOLD;
            const maxSpeed = CONFIG.DRAG.MAX_SCROLL_SPEED;
            const minSpeed = CONFIG.DRAG.MIN_SCROLL_SPEED;
            const viewportHeight = window.innerHeight;
            if (y < threshold) {
                setAutoScrollSpeed(dragState, -Math.max(minSpeed, maxSpeed * ((threshold - y) / threshold)));
            } else if (y > viewportHeight - threshold) {
                const distance = y - (viewportHeight - threshold);
                setAutoScrollSpeed(dragState, Math.max(minSpeed, maxSpeed * (distance / threshold)));
            } else {
                stopAutoScroll(dragState);
            }
        }
        function setAutoScrollSpeed(dragState, speed) {
            dragState.scrollSpeed = speed;
            if (!dragState.scrollFrameId) performAutoScroll(dragState);
        }
        function performAutoScroll(dragState) {
            if (dragState.scrollSpeed !== 0) {
                window.scrollBy(0, dragState.scrollSpeed);
                dragState.scrollFrameId = requestAnimationFrame(() => performAutoScroll(dragState));
            } else {
                dragState.scrollFrameId = null;
            }
        }
        function stopAutoScroll(dragState) {
            dragState.scrollSpeed = 0;
            if (dragState.scrollFrameId) {
                cancelAnimationFrame(dragState.scrollFrameId);
                dragState.scrollFrameId = null;
            }
        }
        function canReorderTasks() {
            return state.storageAvailable && state.viewMode === 'list' && state.sort === 'manual' && !state.searchQuery && !state.batchMode && !state.focusMode;
        }
        function preventCancelableEvent(e) {
            if (e.cancelable) e.preventDefault();
        }
        function getDragAfterElement(container, y) {
            const draggableElements = [...container.querySelectorAll('.task-item:not(.dragging):not(.touch-dragging)')];
            return draggableElements.reduce((closest, child) => {
                const box = child.getBoundingClientRect();
                const offset = y - box.top - box.height / 2;
                if (offset < 0 && offset > closest.offset) {
                    return { offset: offset, element: child };
                } else {
                    return closest;
                }
            }, { offset: Number.NEGATIVE_INFINITY }).element;
        }
        async function saveNewOrder() {
            if (!canRunAppAction('order.save', { closeSurfaces: false })) return;
            const newOrderIds = Array.from(DOM.taskList.children)
                .map(el => Number(el.dataset.taskId))
                .filter(id => !isNaN(id));
            if (newOrderIds.length === 0) return;
            const orderedTasks = mergeVisibleManualOrder(newOrderIds);
            if (orderedTasks.length === 0) return;
            try {
                await dbActions.updateTasks(orderedTasks);
                applyTaskOrderUpdates(orderedTasks);
            } catch (err) {
                console.error('排序保存失败:', err);
                renderTaskList();
                handleStorageOperationError(err, 'messages.task.saveError');
            }
        }
        function mergeVisibleManualOrder(visibleOrderIds) {
            const visibleIds = new Set(visibleOrderIds);
            const visibleTasks = visibleOrderIds.map(getTaskById).filter(Boolean);
            let visibleIndex = 0;
            const mergedTasks = sortTasksByManualOrder(state.tasks).map(task => {
                if (!visibleIds.has(task.id)) return task;
                return visibleTasks[visibleIndex++] || task;
            });
            return mergedTasks.map((task, index) => ({ ...task, order: index * CONFIG.DEFAULTS.MANUAL_ORDER_STEP }));
        }
        function applyTaskOrderUpdates(orderedTasks) {
            const orderById = new Map(orderedTasks.map(task => [task.id, task.order]));
            state.tasks.forEach(task => {
                if (orderById.has(task.id)) task.order = orderById.get(task.id);
            });
        }
        function sortTasksByManualOrder(tasks) {
            return [...tasks].sort((a, b) => {
                const oA = (a.order !== undefined) ? a.order : 0;
                const oB = (b.order !== undefined) ? b.order : 0;
                if (oA !== oB) return oA - oB;
                return a.id - b.id;
            });
        }
        async function loadTranslations() {
            let bundled = {};
            try {
                const data = JSON.parse(document.getElementById('bundledTranslations')?.textContent || 'null');
                if (data?.resourceVersion === CONFIG.I18N.RESOURCE_VERSION) bundled = data.languages || {};
            } catch (error) {}
            const entries = await Promise.all(CONFIG.LANGUAGES.map(async (l) => {
                try {
                    const url = `${CONFIG.I18N.RESOURCE_PATH}/${l.code}.json?v=${CONFIG.I18N.RESOURCE_VERSION}`;
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`Failed to load ${l.code} translations: ${response.status}`);
                    const translations = await response.json();
                    if (!translations || typeof translations !== 'object' || Array.isArray(translations)) throw new Error(`Invalid ${l.code} translations`);
                    return [l.code, flattenTranslations(translations)];
                } catch (error) {
                    const translations = bundled[l.code];
                    if (!translations || typeof translations !== 'object' || Array.isArray(translations)) throw error;
                    return [l.code, flattenTranslations(translations)];
                }
            }));
            state.translations = Object.fromEntries(entries);
            validateTranslations();
        }
        function flattenTranslations(source, prefix = '', target = {}) {
            Object.entries(source).forEach(([key, value]) => {
                const path = prefix ? `${prefix}.${key}` : key;
                if (value && typeof value === 'object' && !Array.isArray(value)) {
                    flattenTranslations(value, path, target);
                } else {
                    target[path] = value;
                }
            });
            return target;
        }
        function validateTranslations() {
            const base = state.translations[CONFIG.DEFAULTS.LANG];
            if (!base) throw new Error(`Missing default language: ${CONFIG.DEFAULTS.LANG}`);
            const baseKeys = Object.keys(base).sort();
            CONFIG.LANGUAGES.forEach(({ code }) => {
                const current = state.translations[code];
                if (!current) throw new Error(`Missing language: ${code}`);
                const missing = baseKeys.filter(key => !(key in current));
                const extra = Object.keys(current).filter(key => !(key in base));
                if (missing.length || extra.length) {
                    console.warn(`[i18n] ${code} key mismatch`, { missing, extra });
                }
            });
        }
        function createLangButtons() {
            for (const select of [DOM.languageSelect]) {
                select.textContent = '';
                CONFIG.LANGUAGES.forEach(language => {
                    const option = document.createElement('option');
                    option.value = language.code;
                    option.textContent = language.name;
                    select.appendChild(option);
                });
            }
        }
        function syncLanguageSelect() {
            for (const select of [DOM.languageSelect]) if (select) select.value = state.currentLanguage;
        }
        function initLanguage() {
            syncLanguageSelect();
            document.documentElement.lang = state.currentLanguage;
            document.documentElement.dir = getLanguageDirection(state.currentLanguage);
            utils.applyTranslations();
            syncFocusModeButton();
            syncThemePreferenceSelect();
            syncTaskDraftRecoveryUI();
            syncWorkspaceScreen();
            updateNotificationBtnUI();
            syncInstallEntry();
            setSettingsSection(workspaceUI.settingsSection);
            syncCapturePreview();
            if (state.storageAvailable && workspaceUI.screen === 'settings') updateBackupHealthStatus().catch(handleBackgroundStorageFailure);
        }
        function getLanguageDirection(code) {
            return ['ar', 'fa', 'he', 'ur'].includes(normalizeLanguageCode(code).split('-')[0]) ? 'rtl' : 'ltr';
        }
        function switchLanguage(code) {
            if (!state.translations[code] || code === state.currentLanguage) return;
            if (!ensureStorageAvailable()) return;
            const previousLanguage = state.currentLanguage;
            state.currentLanguage = code;
            initLanguage();
            dbActions.setConfig(CONFIG.STORAGE.LANG, code).catch(error => {
                console.error('保存语言设置失败:', error);
                if (state.currentLanguage !== code) return;
                state.currentLanguage = previousLanguage;
                initLanguage();
                handleStorageOperationError(error);
            });
        }
        function startProgressTimer() {
            if (state.progressInterval) clearInterval(state.progressInterval);
            if (!state.timeViewEventsBound) {
                for (const type of ['focusin', 'focusout', 'selectionchange', 'click', 'pointerup', 'dragend', 'touchend']) {
                    document.addEventListener(type, scheduleTaskTimeRefresh);
                }
                state.timeViewEventsBound = true;
            }
            state.progressInterval = setInterval(refreshTaskTimers, 60000);
            refreshTaskTimers();
        }
        function planTaskTimeRefresh() {
            const now = Date.now();
            const localNow = new Date(now);
            let next = new Date(localNow.getFullYear(), localNow.getMonth(), localNow.getDate() + 1).getTime();
            for (const task of state.tasks) {
                const due = getTaskDueSortValue(task);
                if (due === null) continue;
                for (const offset of [0, 4320, 10080]) {
                    const boundary = due - offset * 60000 + (offset === 0 ? 1 : 0);
                    if (boundary > now && boundary < next) next = boundary;
                }
            }
            state.timeViewBoundary = next;
            state.timeViewDay = utils.formatDateInputValue(localNow);
            state.timeViewOffset = localNow.getTimezoneOffset();
            state.timeViewCheckedAt = now;
            state.timeViewRefreshPending = false;
        }
        function scheduleTaskTimeRefresh() {
            if (!state.timeViewRefreshPending || state.timeViewRefreshFrame !== null) return;
            state.timeViewRefreshFrame = requestAnimationFrame(() => {
                state.timeViewRefreshFrame = null;
                refreshTimeDependentView();
            });
        }
        function canRefreshTimeDependentView() {
            if (workspaceUI.navigationOpen || DOM.taskList.querySelector('.task-action-menu:not([hidden])')) return false;
            if (document.hidden || !state.storageAvailable || isDialogOpen()
                || state.quickAddSaving || state.taskFormSaving || state.pendingTaskActions.size
                || (state.batchMode && state.selectedTaskIds.size)) return false;
            const active = document.activeElement;
            if (DOM.taskList.contains(active) && ((isEditableElement(active) && !active.matches('input[type="checkbox"], input[type="radio"]'))
                || active.closest('.drag-handle'))) return false;
            if (DOM.taskList.querySelector('.dragging, .touch-dragging')) return false;
            return !hasTaskTimeTextSelection();
        }
        function hasTaskTimeTextSelection() {
            const selection = window.getSelection();
            if (!selection || selection.isCollapsed) return false;
            for (let index = 0; index < selection.rangeCount; index++) {
                if (selection.getRangeAt(index).intersectsNode(DOM.taskList)) return true;
            }
            return false;
        }
        function getTimeRefreshFocusSelector(element) {
            if (!element || element === document.body) return '';
            if (element.id) return `#${CSS.escape(element.id)}`;
            const task = element.closest('.task-item[data-task-id]');
            if (task) {
                const prefix = `.task-item[data-task-id="${CSS.escape(task.dataset.taskId)}"]`;
                if (element.dataset.action) return `${prefix} [data-action="${CSS.escape(element.dataset.action)}"]`;
                if (element.dataset.subtaskId) return `${prefix} [data-subtask-id="${CSS.escape(element.dataset.subtaskId)}"]`;
                if (element.classList.contains('subtask-summary-bar')) return `${prefix} .subtask-summary-bar`;
                if (element.classList.contains('task-select-checkbox')) return `${prefix} .task-select-checkbox`;
            }
            for (const attribute of ['data-calendar-task-id', 'data-calendar-action', 'data-calendar-detail-date',
                'data-calendar-detail-close', 'data-calendar-add-date', 'data-stats-filter', 'data-saved-view-id', 'data-saved-view-delete-id']) {
                if (element.hasAttribute(attribute)) {
                    const scope = element.classList.contains('calendar-detail-task') ? '.calendar-day-detail ' : '';
                    return `${scope}[${attribute}="${CSS.escape(element.getAttribute(attribute))}"]`;
                }
            }
            return '';
        }
        function refreshTimeDependentView() {
            if (!state.timeViewRefreshPending || !canRefreshTimeDependentView()) return;
            const active = document.activeElement;
            const selector = getTimeRefreshFocusSelector(active);
            renderTaskList();
            announceTaskViewSummary();
            if (active && active !== document.body && (!active.isConnected || document.activeElement !== active)) {
                const replacement = selector ? document.querySelector(selector) : null;
                const target = isFocusableReturnElement(replacement) ? replacement : DOM.viewSwitcher.querySelector('[aria-current="page"]');
                target?.focus({ preventScroll: true });
            }
        }
        function refreshTaskTimers() {
            if (state.storageAvailable && state.translations[state.currentLanguage]) {
                const now = Date.now();
                const localNow = new Date(now);
                if (state.timeViewBoundary === null) planTaskTimeRefresh();
                if (now >= state.timeViewBoundary || now < state.timeViewCheckedAt
                    || utils.formatDateInputValue(localNow) !== state.timeViewDay
                    || localNow.getTimezoneOffset() !== state.timeViewOffset) {
                    state.timeViewRefreshPending = true;
                }
                state.timeViewCheckedAt = now;
                refreshTimeDependentView();
            }
            if (!hasTaskTimeTextSelection()) document.querySelectorAll('.task-item:not(.completed-task):not(.archived-task)').forEach(el => {
                const id = Number(el.dataset.taskId);
                const task = state.tasks.find(t => t.id === id);
                if (!task || task.completed || task.archived || !hasTaskDueDate(task)) return;
                const timeLeft = calculateTaskTimeLeft(task);
                if (timeLeft === null) return;
                const statusObj = utils.getStatus(timeLeft);
                const statusText = el.querySelector('.status-text');
                const timeEl = el.querySelector('.status-time-left');
                if (statusText) statusText.textContent = statusObj.text;
                if (timeEl) timeEl.textContent = `(${utils.formatTime(timeLeft)})`;
                const progressFill = el.querySelector('.progress-fill');
                if (progressFill) progressFill.style.width = `${statusObj.percent}%`;
                const allStatusClasses = Object.values(CONFIG.UI.STATUS);
                if (!el.classList.contains(statusObj.cls)) {
                    el.classList.remove(...allStatusClasses);
                    el.classList.add(statusObj.cls);
                }
            });
            if (state.notificationsEnabled) {
                checkNotifications();
            }
        }
        function getEmptyStateHTML(t) {
            return `<div class="empty-state"><svg class="icon icon-lg" aria-hidden="true"><use href="#icon-empty-tasks"></use></svg><h2>${t['empty.noTasks.title']}</h2><button type="button" class="empty-examples-link" id="addExampleTasksBtn">${t['usability.examplesAction']}</button></div>`;
        }
        function getEmptyMatchHTML(t, preserveTodayPlan = false) {
            return `<div class="empty-state"><svg class="icon icon-lg" aria-hidden="true"><use href="#icon-empty-search"></use></svg><h2>${t['empty.noMatches.title']}</h2><button type="button" class="btn btn-secondary" data-reset-filters="${preserveTodayPlan ? 'today' : ''}">${t['usability.resetFilters']}</button></div>`;
        }
        function getEmptyFocusHTML(t) {
            if (state.tasks.some(task => !task.archived && isTaskInTodayPlan(task))) return getEmptyMatchHTML(t, true);
            return `<div class="empty-state"><svg class="icon icon-lg" aria-hidden="true" focusable="false"><use href="#icon-target"></use></svg><h2>${t['focus.emptyTitle']}</h2><p>${t['focus.emptyDescription']}</p></div>`;
        }
        function handleVisibilityChange() {
            if (!document.hidden && workspaceUI.screen === 'settings') syncSettingsStatus();
            refreshTaskTimers();
            if (!state.progressInterval) startProgressTimer();
        }
        async function backupTasks() {
            await downloadTaskData('backup');
        }
        function openHelp() {
            const returnTarget = captureFocusReturnTarget();
            closeMenu();
            const content = document.createElement('div');
            content.className = 'help-guide';
            const heading = document.createElement('h3');
            heading.textContent = utils.translate('help.shortcuts');
            const shortcuts = document.createElement('dl');
            for (const [key, label] of [['Ctrl / ⌘ + I', 'newTask'], ['Ctrl / ⌘ + K', 'search'], ['Ctrl / ⌘ + P', 'commands'], ['Ctrl / ⌘ + M', 'settings'], ['Ctrl / ⌘ + Z', 'undo']]) {
                const term = document.createElement('dt');
                term.textContent = key;
                const description = document.createElement('dd');
                description.textContent = utils.translate(`help.${label}`);
                shortcuts.append(term, description);
            }
            const actions = document.createElement('div');
            actions.className = 'help-actions';
            const commands = document.createElement('button');
            commands.id = 'helpCommandsBtn';
            commands.type = 'button';
            commands.className = 'btn btn-secondary';
            commands.textContent = utils.translate('help.commands');
            commands.disabled = !state.storageAvailable;
            commands.addEventListener('click', () => { closeDialog(); runAppAction('command.open'); });
            const diagnostics = document.createElement('button');
            diagnostics.id = 'helpDiagnosticsBtn';
            diagnostics.type = 'button';
            diagnostics.className = 'btn btn-secondary';
            diagnostics.textContent = utils.translate('help.diagnostics');
            diagnostics.addEventListener('click', async () => {
                diagnostics.disabled = true;
                try { await openDiagnostics(diagnostics); }
                catch (error) { diagnostics.disabled = false; utils.notify(utils.translate('help.diagnosticError'), 'error'); }
            });
            const support = document.createElement('a');
            support.href = 'https://github.com/muquew/Task-Tracer/issues/new/choose';
            support.target = '_blank';
            support.rel = 'noopener noreferrer';
            support.className = 'btn btn-secondary';
            support.textContent = utils.translate('help.support');
            const guide = document.createElement('a');
            guide.href = `https://github.com/muquew/Task-Tracer/blob/main/${state.currentLanguage === 'zh-CN' ? 'README_zh_cn.md' : 'README.md'}`;
            guide.target = '_blank';
            guide.rel = 'noopener noreferrer';
            guide.className = 'btn btn-secondary';
            guide.textContent = utils.translate('help.userGuide');
            actions.append(commands, diagnostics, guide, support);
            content.append(actions, heading, shortcuts);
            utils.confirm(utils.translate('help.menu'), content, () => {});
            DOM.cancelBtn.hidden = true;
            DOM.submitBtn.textContent = utils.translate('help.close');
            state.elementToFocusOnClose = returnTarget;
        }
        async function openDiagnostics(source) {
            const returnTarget = isTaskDialogOpen() ? state.elementToFocusOnClose : captureFocusReturnTarget(source);
            const pending = openLocalReadDialog(utils.translate('help.diagnostics'), 'diagnosticsReadStatus');
            state.elementToFocusOnClose = returnTarget;
            const storage = navigator.storage;
            let persistent = null;
            let estimate = null;
            try { persistent = storage?.persisted ? await storage.persisted() : null; } catch (error) {}
            try { estimate = storage?.estimate ? await storage.estimate() : null; } catch (error) {}
            if (!pending.isCurrent()) return;
            const safeStorageErrors = new Set(['QuotaExceededError', 'StorageUpgradeBlockedError', 'StorageVersionChangedError', 'SecurityError', 'InvalidStateError', 'UnknownError', 'NotAllowedError']);
            const report = {
                type: 'task-tracer-diagnostics', schemaVersion: 1,
                generatedAt: new Date().toISOString(), appVersion: CONFIG.APP.VERSION,
                resourceVersion: CONFIG.I18N.RESOURCE_VERSION, databaseVersion: CONFIG.DB.VERSION,
                browser: { userAgent: navigator.userAgent, language: navigator.language, online: navigator.onLine,
                    standalone: window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true },
                capabilities: { indexedDB: 'indexedDB' in window, serviceWorker: 'serviceWorker' in navigator,
                    notifications: 'Notification' in window, notificationPermission: 'Notification' in window ? Notification.permission : 'unsupported',
                    persistenceRequest: Boolean(storage?.persist) },
                storage: { available: state.storageAvailable, error: state.storageError ? (safeStorageErrors.has(state.storageError.name) ? state.storageError.name : 'StorageError') : null,
                    persistent, usageBytes: Number.isFinite(estimate?.usage) ? estimate.usage : null,
                    quotaBytes: Number.isFinite(estimate?.quota) ? estimate.quota : null },
                serviceWorker: { controlled: Boolean(navigator.serviceWorker?.controller) }
            };
            const content = document.createElement('div');
            const preview = document.createElement('dl');
            preview.id = 'diagnosticPreview';
            preview.className = 'diagnostic-summary';
            preview.tabIndex = 0;
            preview.setAttribute('aria-label', utils.translate('help.diagnostics'));
            const browserIdentity = [
                ['Edge', /\bEdg(?:A|iOS)?\/([\d.]+)/],
                ['Opera', /\bOPR\/([\d.]+)/],
                ['Firefox', /\b(?:Firefox|FxiOS)\/([\d.]+)/],
                ['Chrome', /\b(?:HeadlessChrome|Chrome|CriOS)\/([\d.]+)/],
                ['Safari', /\bVersion\/([\d.]+)/]
            ].map(([name, pattern]) => [name, navigator.userAgent.match(pattern)?.[1]]).find(([, version]) => version);
            const browserLabel = browserIdentity ? browserIdentity.join(' ') : '—';
            for (const [key, value] of [
                ['diagnosticVersion', CONFIG.APP.VERSION],
                ['diagnosticBrowser', browserLabel],
                ['diagnosticConnection', utils.translate(navigator.onLine ? 'help.diagnosticOnline' : 'help.diagnosticOffline')],
                ['diagnosticStorage', utils.translate(state.storageAvailable ? 'help.diagnosticAvailable' : 'help.diagnosticUnavailable')]
            ]) {
                const label = document.createElement('dt');
                label.textContent = utils.translate(`help.${key}`);
                const valueElement = document.createElement('dd');
                valueElement.textContent = value;
                preview.append(label, valueElement);
            }
            content.append(preview);
            utils.confirm(utils.translate('help.diagnostics'), content, () => {
                downloadJsonPayload(report, `task-tracer-diagnostics-${CONFIG.APP.VERSION}.json`);
            });
            DOM.submitBtn.textContent = utils.translate('help.downloadDiagnostics');
            state.elementToFocusOnClose = returnTarget;
        }
        function quoteCsvCell(value) {
            let text = String(value ?? '');
            if (/^[\s\uFEFF\u200B\u2060]*[=+@-]/u.test(text) || /^[\t\r\n]/.test(text)) text = `'${text}`;
            return `"${text.replace(/"/g, '""')}"`;
        }
        async function exportTasksCsv() {
            if (!ensureStorageAvailable()) return;
            closeMenu();
            try {
                const snapshot = await dbActions.readTaskSnapshot();
                const tasks = normalizeTaskRecords(snapshot.tasks).tasks;
                const columns = ['id', 'name', 'description', 'project', 'tags', 'status', 'due_at', 'due_local_date', 'due_local_time', 'due_time_zone', 'completed_at', 'created_at', 'repeat_type', 'repeat_interval', 'repeat_weekdays', 'repeat_paused', 'subtasks'];
                const rows = tasks.map(task => [
                    task.id, task.name, task.description, task.project, JSON.stringify(task.tags || []),
                    task.archived ? 'archived' : task.completed ? 'completed' : 'active',
                    task.dueAt || '', task.dueLocalDate || '', task.dueLocalTime || '', task.dueTimeZone || '',
                    task.completedAt || '', task.createdAt || '', task.repeatType || 'none', task.repeatInterval || 1,
                    JSON.stringify(task.repeatWeekdays || []), Boolean(task.repeatPaused), JSON.stringify(task.subtasks || [])
                ]);
                const csv = [columns, ...rows].map(row => row.map(quoteCsvCell).join(',')).join('\r\n') + '\r\n';
                const blob = new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' });
                const date = new Date().toISOString().replace(/[:.]/g, '-');
                downloadBlob(blob, `task-tracer-tasks-${date}.csv`);
                utils.notify(translateCount('csv.success', tasks.length).replace('{count}', tasks.length));
            } catch (error) {
                handleStorageOperationError(error, 'csv.error');
            }
        }
        function openLocalReadDialog(title, statusId) {
            const focusTarget = captureFocusReturnTarget();
            const returnTarget = focusTarget;
            const message = document.createElement('p');
            message.id = statusId;
            message.setAttribute('role', 'status');
            message.textContent = utils.translate('dialogs.loading');
            const isCurrent = utils.confirm(title, message, () => {});
            DOM.submitBtn.disabled = true;
            DOM.submitBtn.textContent = utils.translate('dialogs.loading');
            state.elementToFocusOnClose = returnTarget;
            DOM.cancelBtn.focus();
            return { isCurrent, returnTarget };
        }
        async function openStorageHealth() {
            if (!ensureStorageAvailable()) return;
            closeMenu();
            const pending = openLocalReadDialog(utils.translate('settingsRefinement.storageTitle'), 'storageHealthReadStatus');
            const storage = navigator.storage;
            let persistent = false;
            let estimate;
            try { persistent = storage?.persisted ? await storage.persisted() : false; } catch (error) {}
            if (!pending.isCurrent()) return;
            try { estimate = storage?.estimate ? await storage.estimate() : null; } catch (error) {}
            if (!pending.isCurrent()) return;
            const content = document.createElement('div');
            const status = document.createElement('p');
            status.id = 'storagePersistenceStatus';
            status.setAttribute('role', 'status');
            status.textContent = utils.translate(persistent ? 'storage.health.persistent' : storage?.persist ? 'storage.health.bestEffort' : 'storage.health.unsupported');
            const usage = document.createElement('p');
            usage.id = 'storageUsage';
            const formatBytes = value => new Intl.NumberFormat(state.currentLanguage, { maximumFractionDigits: 1 }).format(value / (1024 * 1024));
            usage.textContent = Number.isFinite(estimate?.usage) && Number.isFinite(estimate?.quota)
                ? utils.translate('storage.health.usage').replace('{used}', formatBytes(estimate.usage)).replace('{quota}', formatBytes(estimate.quota))
                : utils.translate('storage.health.estimateUnavailable');
            const exportButton = document.createElement('button');
            exportButton.type = 'button';
            exportButton.className = 'btn btn-secondary';
            exportButton.id = 'storageHealthExportBtn';
            exportButton.textContent = utils.translate('actions.exportBackup');
            exportButton.addEventListener('click', () => { closeDialog(); backupTasks(); });
            content.append(status, usage, exportButton);
            const isCurrent = utils.confirm(utils.translate('settingsRefinement.storageTitle'), content, async () => {
                if (persistent || !storage?.persist) return;
                try {
                    const granted = await storage.persist();
                    if (!isCurrent()) return false;
                    persistent = granted;
                    status.textContent = utils.translate(granted ? 'storage.health.persistent' : 'storage.health.bestEffort');
                    utils.notify(utils.translate(granted ? 'storage.health.granted' : 'storage.health.notGranted'), granted ? 'success' : 'warning');
                    if (granted) return;
                } catch (error) {
                    if (isCurrent()) utils.notify(utils.translate('storage.health.requestError'), 'warning');
                }
                return false;
            });
            const readOnly = persistent || !storage?.persist;
            DOM.submitBtn.textContent = utils.translate(readOnly ? 'viewsTransfer.close' : 'storage.health.request');
            DOM.submitBtn.disabled = false;
            DOM.cancelBtn.hidden = readOnly;
            state.elementToFocusOnClose = pending.returnTarget;
            if (DOM.submitBtn.disabled) DOM.cancelBtn.focus();
        }
        function getRecoveryHistoryKeys(history) {
            return (Array.isArray(history) ? history : []).map(entry => entry && typeof entry.id === 'string' ? entry.id : null);
        }
        function confirmClearRecoveryHistory(history, returnTarget) {
            const message = document.createElement('p');
            message.id = 'recoveryClearConfirm';
            message.textContent = utils.translate('recovery.clearConfirm');
            const isCurrent = utils.confirm(utils.translate('recovery.clearTitle'), message, async () => {
                try {
                    await dbActions.clearReviewedRecoveryHistory(getRecoveryHistoryKeys(history));
                    if (!isCurrent()) return false;
                    utils.notify(utils.translate('recovery.cleared'));
                } catch (error) {
                    if (!isCurrent()) return false;
                    if (error?.name === 'RecoveryHistoryConflictError') {
                        await openRecoveryHistory(returnTarget, 'recovery.historyChanged');
                    } else {
                        utils.notify(utils.translate('recovery.clearError'), 'error');
                    }
                    return false;
                }
            });
            DOM.submitBtn.textContent = utils.translate('recovery.clearHistory');
            DOM.submitBtn.classList.add('btn-danger');
            state.elementToFocusOnClose = returnTarget;
            DOM.cancelBtn.focus();
        }
        async function openRecoveryHistory(returnTarget, noticeKey) {
            if (!ensureStorageAvailable()) return;
            closeMenu();
            const pending = openLocalReadDialog(utils.translate('recovery.title'), 'recoveryReadStatus');
            if (returnTarget) pending.returnTarget = returnTarget;
            try {
                const history = await dbActions.getConfig('recoveryHistory');
                if (!pending.isCurrent()) return;
                const entries = (Array.isArray(history) ? history : []).filter(entry => entry && typeof entry.id === 'string' && Array.isArray(entry.tasks));
                if (!entries.length) {
                    closeDialog();
                    utils.notify(utils.translate('recovery.empty'), 'warning');
                    return;
                }
                const content = document.createElement('div');
                const label = document.createElement('label');
                label.htmlFor = 'recoverySelect';
                label.textContent = utils.translate('recovery.choose');
                const select = document.createElement('select');
                select.id = 'recoverySelect';
                entries.forEach(entry => {
                    const option = document.createElement('option');
                    option.value = entry.id;
                    option.textContent = translateCount('recovery.point', entry.tasks.length)
                        .replace('{date}', new Date(entry.createdAt).toLocaleString(state.currentLanguage))
                        .replace('{count}', entry.tasks.length);
                    select.appendChild(option);
                });
                const impact = document.createElement('p');
                impact.id = 'recoveryImpact';
                impact.className = 'recovery-impact';
                impact.setAttribute('role', 'status');
                let restoreInProgress = false;
                const syncRestoreAction = () => {
                    const selected = entries.find(entry => entry.id === select.value);
                    const targetCount = selected?.tasks.length || 0;
                    impact.textContent = utils.translate('dataReview.recoveryImpact')
                        .replace('{current}', state.tasks.length).replace('{target}', targetCount);
                    if (isTaskDialogOpen() && state.modalMode === 'confirm'
                        && content.isConnected && document.getElementById('confirm-message-text')?.contains(content)) {
                        DOM.submitBtn.textContent = translateCount('dataReview.restoreAction', targetCount).replace('{count}', targetCount);
                        DOM.submitBtn.classList.toggle('btn-danger', state.tasks.length > 0);
                        DOM.submitBtn.disabled = restoreInProgress || !selected || !checkbox.checked;
                        DOM.submitBtn.setAttribute('aria-disabled', String(DOM.submitBtn.disabled));
                        DOM.submitBtn.dataset.recoveryConfirmGuard = 'true';
                    }
                };
                const preview = document.createElement('section');
                preview.setAttribute('aria-label', utils.translate('recovery.previewTitle'));
                const summary = document.createElement('p');
                summary.id = 'recoveryPreviewSummary';
                summary.setAttribute('role', 'status');
                const taskList = document.createElement('ol');
                taskList.id = 'recoveryTaskPreview';
                taskList.className = 'restore-check-items recovery-task-preview';
                const empty = document.createElement('p');
                empty.id = 'recoveryPreviewEmpty';
                empty.textContent = utils.translate('recovery.previewEmpty');
                const more = document.createElement('button');
                more.id = 'recoveryPreviewMore';
                more.type = 'button';
                more.className = 'btn btn-secondary';
                more.textContent = utils.translate('pagination.more');
                more.setAttribute('aria-controls', taskList.id);
                const previewPageSize = 100;
                let previewLimit = previewPageSize;
                const renderPreview = (focusNew = false) => {
                    const selected = entries.find(entry => entry.id === select.value);
                    const tasks = selected?.tasks || [];
                    syncRestoreAction();
                    const previousCount = taskList.children.length;
                    const visible = tasks.slice(0, previewLimit);
                    taskList.replaceChildren();
                    visible.forEach((task, index) => {
                        const item = document.createElement('li');
                        item.tabIndex = -1;
                        const name = String(task?.name || utils.translate('task.importedFallback').replace('{index}', index + 1));
                        const status = utils.translate(normalizeBoolean(task?.archived) ? 'filters.archived' : normalizeBoolean(task?.completed) ? 'filters.completed' : 'filters.active');
                        item.textContent = `${name} · ${status}`;
                        taskList.appendChild(item);
                    });
                    summary.textContent = translateCount('recovery.previewSummary', tasks.length)
                        .replace('{shown}', visible.length).replace('{count}', tasks.length)
                        .replace('{completed}', tasks.filter(task => normalizeBoolean(task?.completed)).length)
                        .replace('{archived}', tasks.filter(task => normalizeBoolean(task?.archived)).length);
                    summary.hidden = tasks.length === 0;
                    empty.hidden = tasks.length !== 0;
                    more.hidden = visible.length >= tasks.length;
                    if (focusNew && visible.length > previousCount) taskList.children[previousCount]?.focus();
                };
                more.addEventListener('click', () => { previewLimit += previewPageSize; renderPreview(true); });
                preview.append(summary, taskList, empty, more);
                const previewDetails = document.createElement('details');
                previewDetails.id = 'recoveryPreviewDetails';
                previewDetails.className = 'import-reference';
                const previewToggle = document.createElement('summary');
                previewToggle.id = 'recoveryPreviewToggle';
                previewToggle.textContent = utils.translate('settingsRefinement.recoveryPreviewToggle');
                previewDetails.append(previewToggle, preview);
                const actions = document.createElement('div');
                actions.className = 'help-actions';
                const exportButton = document.createElement('button');
                exportButton.id = 'recoveryExportBtn';
                exportButton.type = 'button';
                exportButton.className = 'btn btn-secondary';
                exportButton.textContent = utils.translate('recovery.exportPoint');
                exportButton.addEventListener('click', () => {
                    const selected = entries.find(entry => entry.id === select.value);
                    if (!selected) return;
                    try {
                        const tasks = normalizeTaskRecords(cloneTaskSnapshot(selected.tasks)).tasks;
                        const date = new Date().toISOString();
                        downloadJsonPayload(createTaskDataPayload('backup', date, tasks), createTaskDataFilename('recovery-backup', date));
                        utils.notify(translateCount('recovery.exported', tasks.length).replace('{count}', tasks.length));
                    } catch (error) { utils.notify(utils.translate('recovery.exportError'), 'error'); }
                });
                const clearButton = document.createElement('button');
                clearButton.id = 'recoveryClearBtn';
                clearButton.type = 'button';
                clearButton.className = 'btn btn-secondary';
                clearButton.textContent = utils.translate('recovery.clearHistory');
                clearButton.addEventListener('click', () => confirmClearRecoveryHistory(history, pending.returnTarget));
                actions.append(exportButton, clearButton);
                const confirmation = document.createElement('label');
                confirmation.className = 'recovery-confirm';
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = 'recoveryConfirm';
                checkbox.setAttribute('aria-describedby', 'recoveryImpact');
                confirmation.append(checkbox, document.createTextNode(utils.translate('recovery.confirm')));
                checkbox.addEventListener('change', syncRestoreAction);
                content.append(label, select, impact, previewDetails, confirmation, actions);
                select.addEventListener('change', () => { checkbox.checked = false; previewLimit = previewPageSize; renderPreview(); });
                renderPreview();
                confirmTaskChanges(utils.translate('recovery.title'), content, async () => {
                    if (!checkbox.checked) {
                        utils.notify(utils.translate('recovery.confirmRequired'), 'warning');
                        checkbox.focus();
                        return false;
                    }
                    const selected = entries.find(entry => entry.id === select.value);
                    if (!selected) return false;
                    restoreInProgress = true;
                    checkbox.disabled = true;
                    select.disabled = true;
                    syncAllCustomSelects(content);
                    syncRestoreAction();
                    try {
                        await dbActions.replaceAllTasks(cloneTaskSnapshot(selected.tasks));
                        state.undoAction = null;
                        syncUndoControls();
                        clearNotificationDeliveryState();
                        await refreshTasks();
                        utils.notify(utils.translate('recovery.restored'));
                    } catch (error) {
                        handleStorageOperationError(error, 'recovery.error');
                        return false;
                    } finally {
                        restoreInProgress = false;
                        checkbox.disabled = false;
                        select.disabled = false;
                        syncAllCustomSelects(content);
                        syncRestoreAction();
                    }
                });
                syncRestoreAction();
                state.elementToFocusOnClose = pending.returnTarget;
                checkbox.focus();
                if (noticeKey) utils.notify(utils.translate(noticeKey), 'warning');
            } catch (error) {
                if (!pending.isCurrent()) return;
                handleStorageOperationError(error, 'recovery.error');
            }
        }
        async function downloadTaskData(mode) {
            if (!ensureStorageAvailable()) return;
            const t = state.translations[state.currentLanguage];
            try {
                const snapshot = await dbActions.readTaskSnapshot();
                const tasks = normalizeTaskRecords(snapshot.tasks).tasks;
                const date = new Date().toISOString();
                const payload = createTaskDataPayload(mode, date, tasks);
                downloadJsonPayload(payload, createTaskDataFilename(mode, date));
                if (mode === 'backup') {
                    await dbActions.recordTaskBackup(date, snapshot.taskRevision);
                    await updateBackupHealthStatus();
                }
                closeMenu();
                utils.notify(t['messages.backup.success']);
            } catch (err) {
                console.error('导出/备份任务失败:', err);
                handleStorageOperationError(err, 'messages.backup.error');
            }
        }
        function downloadEmergencyBackup() {
            const tasks = cloneTaskSnapshot(state.storageFallbackTasks);
            if (tasks.length === 0) {
                syncStorageAvailabilityUI();
                utils.notify(utils.translate('storage.unavailable.noSnapshot'), 'warning');
                return;
            }
            const date = new Date().toISOString();
            const payload = createTaskDataPayload('emergency-backup', date, tasks, 'memory-fallback');
            downloadJsonPayload(payload, createTaskDataFilename('emergency-backup', date));
            utils.notify(translateCount('storage.unavailable.emergencyBackupSuccess', tasks.length).replace('{count}', tasks.length));
        }
        function downloadPreImportSnapshot(tasks) {
            const date = new Date().toISOString();
            const payload = createTaskDataPayload('pre-import-backup', date, cloneTaskSnapshot(tasks));
            downloadJsonPayload(payload, createTaskDataFilename('pre-import-backup', date));
        }
        function downloadJsonPayload(payload, filename) {
            const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
            downloadBlob(blob, filename);
        }
        function downloadBlob(blob, filename) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        function createTaskDataPayload(mode, date, tasks, storage = 'indexeddb') {
            const versionNotes = [
                utils.translate('backup.versionNotes.schema'),
                utils.translate('backup.versionNotes.compatibility')
            ];
            if (mode === 'emergency-backup') versionNotes.push(utils.translate('backup.versionNotes.emergency'));
            const payload = {
                version: CONFIG.BACKUP.FILE_VERSION,
                type: mode,
                exportId: createTaskDataExportId(mode, date),
                date,
                app: 'Task Tracer',
                schema: {
                    version: CONFIG.BACKUP.FILE_VERSION,
                    storage,
                    includes: ['tasks', 'subtasks', 'projects', 'tags', 'localDueDates', 'exactDueInstants', 'reminders', 'repeatRules', 'completionDates', 'archiveState', 'todayPlan']
                },
                versionNotes,
                tasks
            };
            payload.checksum = createTaskDataChecksum(payload);
            return payload;
        }
        function createTaskDataExportId(mode, date) {
            return `${mode}-${date.replace(/[^0-9]/g, '').slice(0, 14)}-${Math.random().toString(36).slice(2, 10)}`;
        }
        function createTaskDataChecksum(payload) {
            const copy = { ...payload };
            delete copy.checksum;
            return `fnv1a32:${createStableHash(copy)}`;
        }
        function createStableHash(value) {
            const text = stableStringify(value);
            let hash = 2166136261;
            for (let index = 0; index < text.length; index += 1) {
                hash ^= text.charCodeAt(index);
                hash = Math.imul(hash, 16777619);
            }
            return (hash >>> 0).toString(16).padStart(8, '0');
        }
        function stableStringify(value) {
            if (value === null) return 'null';
            if (typeof value !== 'object') return JSON.stringify(value) ?? undefined;
            if (Array.isArray(value)) return `[${value.map(item => stableStringify(item) ?? 'null').join(',')}]`;
            const entries = Object.keys(value).sort().map(key => {
                const serialized = stableStringify(value[key]);
                return serialized === undefined ? null : `${JSON.stringify(key)}:${serialized}`;
            }).filter(Boolean);
            return `{${entries.join(',')}}`;
        }
        function createTaskDataFilename(mode, date) {
            const stamp = date.replace(/[:.]/g, '-').replace('T', '_').replace('Z', '');
            return `task-tracer_${mode}_${stamp}.json`;
        }
        async function scheduleBackupReminder() {
            const status = await updateBackupHealthStatus();
            if (!status.due || status.taskCount === 0) return;
            const canRemind = () => state.storageAvailable && !isDialogOpen() && !DOM.notification.el.classList.contains(CONFIG.UI.CLASSES.SHOW);
            setTimeout(() => {
                if (!canRemind()) return;
                updateBackupHealthStatus().then(latest => {
                    if (latest.due && latest.taskCount > 0 && canRemind()) {
                        utils.notify(utils.translate('messages.backup.reminder'), 'warning');
                    }
                }).catch(handleBackgroundStorageFailure);
            }, 900);
        }
        async function updateBackupHealthStatus(knownStatus) {
            const snapshot = arguments.length > 0 ? knownStatus : await dbActions.getTaskBackupStatus();
            const status = { ...getBackupHealthStatus(snapshot), taskCount: snapshot.taskCount };
            if (!DOM.menu.backupHealthText) return status;
            DOM.menu.backupHealth.classList.toggle('backup-due', status.due);
            DOM.menu.backupHealthText.textContent = status.text;
            return status;
        }
        function getBackupHealthStatus({ lastBackupAt, lastTaskBackup, taskRevision, taskCount }) {
            if (!lastBackupAt) {
                return { due: taskCount > 0, text: utils.translate(taskCount > 0 ? 'backup.health.never' : 'backup.health.empty') };
            }
            const ageDays = Math.max(0, Math.floor((Date.now() - new Date(lastBackupAt).getTime()) / 86400000));
            const ageText = formatBackupAge(ageDays);
            const recorded = lastTaskBackup && lastTaskBackup.date === lastBackupAt
                && Number.isSafeInteger(lastTaskBackup.taskRevision) && lastTaskBackup.taskRevision >= 0;
            if (!recorded || lastTaskBackup.taskRevision !== taskRevision) {
                return { due: true, text: utils.translate(recorded ? 'backup.health.changed' : 'backup.health.coverageUnknown').replace('{age}', ageText) };
            }
            const due = ageDays >= CONFIG.BACKUP.REMINDER_DAYS;
            return {
                due,
                text: utils.translate(due ? 'backup.health.due' : 'backup.health.ok').replace('{age}', ageText)
            };
        }
        function formatBackupAge(ageDays) {
            if (ageDays === 0) return utils.translate('backup.health.today');
            if (ageDays === 1) return utils.translate('backup.health.yesterday');
            return translateCount('backup.health.daysAgo', ageDays).replace('{days}', ageDays);
        }
        function importTasks(file) {
            if (!file) return;
            if (!ensureStorageAvailable()) {
                DOM.menu.fileInput.value = '';
                return;
            }
            if (state.pendingTaskImportReader) state.pendingTaskImportReader.abort();
            closeMenu();
            const reader = new FileReader();
            const t = state.translations[state.currentLanguage];
            const status = document.createElement('p');
            status.id = 'taskImportReadStatus';
            status.setAttribute('role', 'status');
            status.textContent = utils.translate('dialogs.loading');
            utils.confirm(t['actions.import'], status, () => {});
            DOM.submitBtn.disabled = true;
            DOM.submitBtn.textContent = t['actions.confirm'];
            state.elementToFocusOnClose = { type: 'id', id: 'importBtn' };
            state.pendingTaskImportReader = reader;
            reader.onload = e => {
                if (state.pendingTaskImportReader !== reader || !isTaskDialogOpen() || !status.isConnected) return;
                state.pendingTaskImportReader = null;
                try {
                    const data = JSON.parse(e.target.result.toString());
                    const importPayload = prepareImportPayload(data);
                    if (!importPayload.rawTasks) {
                        closeDialog();
                        utils.notify(t['messages.import.formatError'], 'error');
                        return;
                    }
                    const importedTasks = normalizeImportedTasks(importPayload.rawTasks);
                    openTaskImportPreview(importPayload, importedTasks);
                } catch (error) {
                    closeDialog();
                    utils.notify(t['messages.import.readError'], 'error');
                    console.error('导入错误:', error);
                }
            };
            reader.onerror = () => {
                if (state.pendingTaskImportReader !== reader) return;
                state.pendingTaskImportReader = null;
                closeDialog();
                utils.notify(t['messages.import.readError'], 'error');
            };
            reader.onabort = () => { if (state.pendingTaskImportReader === reader) state.pendingTaskImportReader = null; };
            reader.readAsText(file);
            DOM.menu.fileInput.value = '';
        }
        function openTaskImportPreview(importPayload, importedTasks, returnTarget = state.elementToFocusOnClose) {
            const t = state.translations[state.currentLanguage];
            const preview = buildImportPreview(importedTasks, importPayload.rawTasks, importPayload.sourceData, importPayload.compatibilitySteps);
            utils.confirm(t['messages.import.previewTitle'], createImportPreviewContent(preview), async () => {
                try {
                    if (preview.taskRevision !== state.taskRevision) {
                        openTaskImportPreview(importPayload, importedTasks);
                        utils.notify(utils.translate('messages.import.stalePreview'), 'warning');
                        return false;
                    }
                    const beforeTasks = captureUndoSnapshot();
                    const importOptions = getImportOptions();
                    if (!importOptions.merge && preview.sourceInfo.checksumStatus === 'invalid' && !isImportChecksumRiskConfirmed()) {
                        markImportChecksumRiskConfirmed();
                        return false;
                    }
                    if (!importOptions.merge && beforeTasks.length > 0 && !isPreImportSnapshotConfirmed()) {
                        downloadPreImportSnapshot(beforeTasks);
                        markPreImportSnapshotConfirmed();
                        return false;
                    }
                    const preparedImport = importOptions.merge
                        ? prepareImportedTasksForMerge(importedTasks, importOptions.conflictActions, importOptions.conflictDefault)
                        : { tasks: importedTasks, idsToDelete: [] };
                    if (importOptions.merge) await dbActions.mergeImportedTasks(preparedImport.tasks, preparedImport.idsToDelete);
                    else await dbActions.replaceAllTasks(preparedImport.tasks);
                    clearNotificationDeliveryState();
                    await refreshTasks();
                    registerUndoSnapshot(t['undo.labels.import'], beforeTasks);
                    utils.notify(translateCount(importOptions.merge ? 'messages.import.successMerged' : 'messages.import.success', preparedImport.tasks.length).replace('{count}', preparedImport.tasks.length), 'success', { undo: true });
                } catch (err) {
                    console.error('导入任务失败:', err);
                    if (!handleStorageOperationError(err, 'messages.import.readError')) throw err;
                }
            });
            state.elementToFocusOnClose = returnTarget;
        }
        function getImportTaskArray(data) {
            if (Array.isArray(data)) return data;
            if (data && typeof data === 'object' && Array.isArray(data.tasks)) return data.tasks;
            return null;
        }
        function prepareImportPayload(data) {
            const rawTasks = getImportTaskArray(data);
            if (!rawTasks) return { sourceData: data, rawTasks: null, compatibilitySteps: [] };
            if (Array.isArray(data)) return { sourceData: data, rawTasks, compatibilitySteps: [{ from: 'legacy-array', to: CONFIG.BACKUP.FILE_VERSION }] };
            const sourceData = { ...data, tasks: rawTasks };
            const sourceVersion = getImportPayloadVersion(sourceData);
            const compatibilitySteps = sourceVersion && sourceVersion !== CONFIG.BACKUP.FILE_VERSION
                ? [{ from: sourceVersion, to: CONFIG.BACKUP.FILE_VERSION }]
                : [];
            if (!sourceVersion) compatibilitySteps.push({ from: 'unversioned', to: CONFIG.BACKUP.FILE_VERSION });
            return { sourceData, rawTasks, compatibilitySteps };
        }
        function getImportPayloadVersion(data) {
            if (!data || typeof data !== 'object' || Array.isArray(data)) return '';
            const schema = data.schema && typeof data.schema === 'object' ? data.schema : null;
            const value = schema?.version ?? data.version ?? '';
            return value === undefined || value === null ? '' : String(value);
        }
        function buildImportPreview(importedTasks, rawTasks = [], sourceData = null, compatibilitySteps = []) {
            const importNameOccurrences = getImportNameOccurrences(importedTasks);
            const fileDuplicateNames = getImportFileDuplicateNames(importNameOccurrences);
            const existingByName = getExistingTasksByName();
            const existingDuplicateNames = getImportExistingDuplicateNames(importNameOccurrences, existingByName);
            const conflicts = getImportConflicts(importedTasks, existingByName);
            const duplicateIds = getDuplicateImportIds(rawTasks);
            const completedCount = state.tasks.filter(task => task.completed).length;
            const archivedCount = state.tasks.filter(task => task.archived).length;
            const importDiff = getImportDiff(importedTasks, existingByName);
            return {
                taskRevision: state.taskRevision,
                importCount: importedTasks.length,
                currentCount: state.tasks.length,
                completedCount,
                archivedCount,
                fileDuplicateNames,
                duplicateIds,
                existingDuplicateNames,
                conflicts,
                sourceInfo: getImportSourceInfo(sourceData, compatibilitySteps),
                newTaskNames: importDiff.newTaskNames,
                conflictTaskNames: importDiff.conflictTaskNames,
                currentTaskNames: state.tasks.map(task => task.name)
            };
        }
        function getImportSourceInfo(sourceData, compatibilitySteps = []) {
            const objectSource = sourceData && typeof sourceData === 'object' && !Array.isArray(sourceData) ? sourceData : null;
            const schema = objectSource && objectSource.schema && typeof objectSource.schema === 'object' ? objectSource.schema : null;
            const type = objectSource && objectSource.type !== undefined ? String(objectSource.type) : (Array.isArray(sourceData) ? 'legacy-array' : '');
            const version = objectSource && objectSource.version !== undefined && objectSource.version !== null ? String(objectSource.version) : '';
            const schemaVersion = schema && schema.version !== undefined && schema.version !== null ? String(schema.version) : '';
            const storage = schema && schema.storage !== undefined && schema.storage !== null ? String(schema.storage) : '';
            const app = objectSource && objectSource.app !== undefined && objectSource.app !== null ? String(objectSource.app) : '';
            const includes = Array.isArray(schema?.includes) ? schema.includes.map(item => String(item)) : [];
            const hasTasksEnvelope = Boolean(objectSource && Array.isArray(objectSource.tasks));
            const hasTemplate = Boolean(hasTasksEnvelope && app === 'Task Tracer' && schema && (version || schemaVersion));
            const checksum = objectSource && objectSource.checksum !== undefined && objectSource.checksum !== null ? String(objectSource.checksum) : '';
            const checksumStatus = checksum ? (checksum === createTaskDataChecksum(objectSource) ? 'valid' : 'invalid') : (objectSource ? 'missing' : 'unavailable');
            return { type, version, schemaVersion, storage, app, includes, hasTemplate, hasTasksEnvelope, checksum, checksumStatus, compatibilitySteps };
        }
        function getImportDiff(importedTasks, existingByName) {
            const newTaskNames = [];
            const conflictTaskNames = [];
            importedTasks.forEach(task => {
                const key = normalizeTaskNameForCompare(task.name);
                if (key && existingByName.has(key)) conflictTaskNames.push(task.name);
                else newTaskNames.push(task.name);
            });
            return { newTaskNames, conflictTaskNames };
        }
        function getImportNameOccurrences(importedTasks) {
            const names = new Map();
            importedTasks.forEach(task => {
                const key = normalizeTaskNameForCompare(task.name);
                if (!key) return;
                names.set(key, { key, label: task.name, count: (names.get(key)?.count || 0) + 1 });
            });
            return names;
        }
        function getImportFileDuplicateNames(names) {
            return [...names.values()]
                .filter(item => item.count > 1)
                .map(item => item.label);
        }
        function getImportExistingDuplicateNames(names, existingByName = getExistingTasksByName()) {
            return [...names.values()]
                .filter(item => existingByName.has(item.key))
                .map(item => item.label);
        }
        function getExistingTasksByName() {
            const existing = new Map();
            state.tasks.forEach(task => {
                const key = normalizeTaskNameForCompare(task.name);
                if (!key) return;
                if (!existing.has(key)) existing.set(key, []);
                existing.get(key).push(task);
            });
            return existing;
        }
        function getImportConflicts(importedTasks, existingByName) {
            return importedTasks.map((task, index) => {
                const key = normalizeTaskNameForCompare(task.name);
                const existing = key ? existingByName.get(key) || [] : [];
                return {
                    index,
                    key,
                    name: task.name,
                    existingCount: existing.length,
                    existingIds: existing.map(item => item.id)
                };
            }).filter(conflict => conflict.key && conflict.existingCount > 0);
        }
        function normalizeTaskNameForCompare(name) {
            return String(name || '').trim().toLowerCase();
        }
        function createImportPreviewContent(preview) {
            const t = state.translations[state.currentLanguage];
            const wrapper = document.createElement('div');
            wrapper.className = 'confirm-details';
            wrapper.dataset.importPreview = 'true';
            wrapper.dataset.preImportSnapshotConfirmed = 'false';
            wrapper.dataset.checksumRiskConfirmed = 'false';
            wrapper.dataset.checksumStatus = preview.sourceInfo.checksumStatus || '';
            wrapper.dataset.currentCount = String(preview.currentCount);
            wrapper.importPreviewData = preview;
            const outcome = document.createElement('section');
            outcome.className = 'import-outcome';
            outcome.setAttribute('aria-labelledby', 'importOutcomeTitle');
            const outcomeTitle = document.createElement('h3');
            outcomeTitle.id = 'importOutcomeTitle';
            outcomeTitle.textContent = t['dataReview.importOutcomeTitle'];
            const summary = document.createElement('p');
            summary.id = 'importOutcomeSummary';
            summary.setAttribute('role', 'status');
            outcome.append(outcomeTitle, summary);
            wrapper.append(createImportModeOption(t), outcome,
                createImportSafetyGate(preview, t), createImportConflictControls(preview, t));
            const details = document.createElement('details');
            details.className = 'import-reference';
            const detailsTitle = document.createElement('summary');
            detailsTitle.textContent = t['dataReview.importDetails'];
            details.append(detailsTitle, createImportDiffPreview(preview, t));
            if (preview.fileDuplicateNames.length) {
                appendImportNameList(details, `${t['messages.import.previewFileDuplicates']} (${preview.fileDuplicateNames.length})`, preview.fileDuplicateNames);
            }
            wrapper.appendChild(details);
            wrapper.addEventListener('change', event => {
                if (event.target.matches('#importConflictDefaultAction, [data-import-conflict-index]')) updateImportSafetyGate(wrapper);
            });
            syncImportConflictControls(wrapper);
            return wrapper;
        }
        function getImportOutcome(preview, root) {
            const merge = Boolean(root?.querySelector('#mergeImportMode')?.checked);
            if (!merge) return { merge, imported: preview.importCount, added: preview.importCount, skipped: 0,
                replaced: preview.currentCount, kept: 0, after: preview.importCount,
                snapshotConfirmed: root?.dataset.preImportSnapshotConfirmed === 'true' };
            const actions = new Map();
            root?.querySelectorAll('[data-import-conflict-index]').forEach(select => actions.set(Number(select.dataset.importConflictIndex), select.value));
            const defaultAction = root?.querySelector('#importConflictDefaultAction')?.value || 'keep';
            const replacedIds = new Set();
            let skipped = 0;
            let replacementInputs = 0;
            preview.conflicts.forEach(conflict => {
                const action = actions.get(conflict.index) || defaultAction;
                if (action === 'skip') skipped++;
                if (action === 'replace') {
                    replacementInputs++;
                    conflict.existingIds.forEach(id => replacedIds.add(id));
                }
            });
            const imported = preview.importCount - skipped;
            const replaced = replacedIds.size;
            const kept = preview.currentCount - replaced;
            return { merge, imported, added: imported - replacementInputs, skipped, replaced, kept, after: kept + imported,
                snapshotConfirmed: root?.dataset.preImportSnapshotConfirmed === 'true' };
        }
        function formatImportOutcome(preview, outcome, t) {
            return t[outcome.merge ? 'dataReview.mergeSummary' : 'dataReview.replaceSummary']
                .replace('{current}', preview.currentCount).replace('{incoming}', preview.importCount)
                .replace('{added}', outcome.added).replace('{replaced}', outcome.replaced)
                .replace('{skipped}', outcome.skipped).replace('{kept}', outcome.kept).replace('{after}', outcome.after);
        }
        function syncImportOutcome(root, outcome) {
            const preview = root?.importPreviewData;
            if (!preview) return;
            const t = state.translations[state.currentLanguage];
            const summary = root.querySelector('#importOutcomeSummary');
            if (summary) summary.textContent = formatImportOutcome(preview, outcome, t);
            const section = root.querySelector('.import-outcome');
            section?.classList.toggle('is-risk', outcome.replaced > 0);
        }
        function createImportSafetyGate(preview, t) {
            const gate = document.createElement('div');
            gate.className = 'import-safety-gate';
            gate.dataset.importSafetyGate = 'true';
            gate.hidden = preview.sourceInfo.checksumStatus !== 'invalid';
            gate.setAttribute('role', 'status');
            const detail = document.createElement('span');
            detail.dataset.importSafetyDetail = 'true';
            detail.textContent = getImportSafetyText(preview.currentCount, preview.sourceInfo.checksumStatus, false, false, t);
            gate.append(detail);
            return gate;
        }
        function getImportSafetyText(currentCount, checksumStatus, snapshotConfirmed, checksumConfirmed, t) {
            if (checksumStatus === 'invalid' && !checksumConfirmed) return t['messages.import.importSafetyChecksumRisk'];
            if (snapshotConfirmed) return t['messages.import.importSafetySnapshotReady'];
            if (checksumStatus === 'invalid' && checksumConfirmed && currentCount > 0) return translateCount('messages.import.importSafetyChecksumSnapshot', currentCount).replace('{count}', currentCount);
            if (checksumStatus === 'invalid' && checksumConfirmed) return t['messages.import.importSafetyChecksumConfirmed'];
            if (currentCount > 0) return translateCount('messages.import.importSafetyReplace', currentCount).replace('{count}', currentCount);
            return t['messages.import.importSafetyClean'];
        }
        function getImportSubmitLabelKey(currentCount, checksumStatus, snapshotConfirmed, checksumConfirmed, mergeEnabled) {
            if (mergeEnabled) return 'dataReview.importMergeAction';
            if (checksumStatus === 'invalid' && !checksumConfirmed) return 'messages.import.confirmChecksumRisk';
            if (currentCount > 0 && !snapshotConfirmed) return 'messages.import.downloadSnapshot';
            return 'dataReview.importReplaceAction';
        }
        function getImportPreviewRoot(root = document) {
            if (root?.matches?.('[data-import-preview]')) return root;
            return root?.querySelector ? root.querySelector('[data-import-preview]') : null;
        }
        function isPreImportSnapshotConfirmed() {
            return getImportPreviewRoot()?.dataset.preImportSnapshotConfirmed === 'true';
        }
        function isImportChecksumRiskConfirmed() {
            return getImportPreviewRoot()?.dataset.checksumRiskConfirmed === 'true';
        }
        function markPreImportSnapshotConfirmed() {
            const root = getImportPreviewRoot();
            if (!root) return;
            root.dataset.preImportSnapshotConfirmed = 'true';
            updateImportSafetyGate(root);
        }
        function markImportChecksumRiskConfirmed() {
            const root = getImportPreviewRoot();
            if (!root) return;
            root.dataset.checksumRiskConfirmed = 'true';
            updateImportSafetyGate(root);
        }
        function updateImportSafetyGate(root = getImportPreviewRoot()) {
            if (!root) return;
            const preview = root.importPreviewData;
            const outcome = preview ? getImportOutcome(preview, root) : null;
            if (outcome) syncImportOutcome(root, outcome);
            const gate = root.querySelector('[data-import-safety-gate]');
            const detail = root.querySelector('[data-import-safety-detail]');
            const mergeEnabled = Boolean(root.querySelector('#mergeImportMode')?.checked);
            const currentCount = Number(root.dataset.currentCount || 0);
            const checksumStatus = root.dataset.checksumStatus || '';
            const snapshotConfirmed = root.dataset.preImportSnapshotConfirmed === 'true';
            const checksumConfirmed = root.dataset.checksumRiskConfirmed === 'true';
            if (gate) {
                gate.hidden = checksumStatus !== 'invalid' && (mergeEnabled || !snapshotConfirmed);
                gate.classList.toggle('risk', checksumStatus === 'invalid' && !checksumConfirmed);
                gate.classList.toggle('warn', snapshotConfirmed || checksumConfirmed);
            }
            if (detail) detail.textContent = mergeEnabled && checksumStatus === 'invalid'
                ? utils.translate('messages.import.restoreIntegrityInvalid')
                : getImportSafetyText(currentCount, checksumStatus, snapshotConfirmed, checksumConfirmed, state.translations[state.currentLanguage]);
            if (DOM.submitBtn && root.closest('#confirm-message-text')) {
                const labelKey = getImportSubmitLabelKey(currentCount, checksumStatus, snapshotConfirmed, checksumConfirmed, mergeEnabled);
                const noChanges = Boolean(outcome?.merge && outcome.imported === 0 && outcome.replaced === 0);
                const key = noChanges ? 'dataReview.importNoChanges' : labelKey;
                const count = outcome?.imported ?? currentCount;
                DOM.submitBtn.textContent = translateCount(key, count).replace('{count}', count);
                DOM.submitBtn.classList.toggle('btn-danger', mergeEnabled ? Boolean(outcome && outcome.replaced > 0) : snapshotConfirmed);
                if (noChanges) {
                    DOM.submitBtn.dataset.noImportChanges = 'true';
                    DOM.submitBtn.disabled = true;
                } else if (DOM.submitBtn.dataset.noImportChanges === 'true') {
                    delete DOM.submitBtn.dataset.noImportChanges;
                    DOM.submitBtn.disabled = false;
                }
            }
        }
        function createImportDiffPreview(preview, t) {
            const section = document.createElement('section');
            section.className = 'import-diff-preview';
            section.setAttribute('aria-label', t['messages.import.diffTitle']);
            const title = document.createElement('strong');
            title.className = 'import-diff-title';
            title.textContent = t['messages.import.diffTitle'];
            const grid = document.createElement('div');
            grid.className = 'import-diff-grid';
            grid.append(
                createImportDiffItem(t['messages.import.diffNew'], preview.newTaskNames.length, formatImportNamePreview(preview.newTaskNames, t)),
                createImportDiffItem(t['messages.import.diffConflicts'], preview.conflictTaskNames.length, formatImportNamePreview(preview.conflictTaskNames, t)),
                createImportDiffItem(t['messages.import.diffReplace'], preview.currentCount, formatImportNamePreview(preview.currentTaskNames, t))
            );
            section.append(title, grid);
            return section;
        }
        function createImportDiffItem(label, count, detailText) {
            const item = document.createElement('div');
            item.className = 'import-diff-item';
            const labelEl = document.createElement('strong');
            labelEl.textContent = label;
            const countEl = document.createElement('span');
            countEl.className = 'import-diff-count';
            countEl.textContent = String(count);
            const detail = document.createElement('span');
            detail.className = 'import-diff-detail';
            detail.title = detailText;
            detail.textContent = detailText;
            item.append(labelEl, countEl, detail);
            return item;
        }
        function formatImportNamePreview(names, t) {
            if (!Array.isArray(names) || names.length === 0) return t['messages.import.diffNone'];
            const visible = names.slice(0, 4).join(t['messages.import.diffSeparator']);
            return names.length > 4 ? t['messages.import.diffMore'].replace('{names}', visible).replace('{count}', names.length - 4) : visible;
        }
        function createImportConflictControls(preview, t) {
            const section = document.createElement('div');
            section.className = 'import-conflict-list';
            section.dataset.importConflictSection = 'true';
            section.dataset.importConflictCount = String(preview.conflicts.length);
            if (preview.conflicts.length === 0) return section;
            section.initializeConflictControls = () => {
                if (section.dataset.initialized === 'true') return;
                section.dataset.initialized = 'true';
                const title = document.createElement('strong');
                title.className = 'confirm-list-title';
                title.textContent = t['messages.import.conflictTitle'];
                const label = document.createElement('label');
                label.htmlFor = 'importConflictDefaultAction';
                label.textContent = t['messages.import.conflictDefaultLabel'];
                const defaultAction = document.createElement('select');
                defaultAction.id = 'importConflictDefaultAction';
                defaultAction.setAttribute('aria-label', t['messages.import.conflictDefaultLabel']);
                [
                    ['keep', 'messages.import.conflictKeep'],
                    ['skip', 'messages.import.conflictSkip'],
                    ['replace', 'messages.import.conflictReplace']
                ].forEach(([value, key]) => {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = t[key];
                    defaultAction.appendChild(option);
                });
                const rows = document.createElement('div');
                const summary = document.createElement('p');
                summary.id = 'importConflictSummary';
                summary.setAttribute('role', 'status');
                const more = document.createElement('button');
                more.type = 'button';
                more.className = 'btn btn-secondary';
                more.id = 'importConflictMoreBtn';
                let shown = 0;
                const showMore = (moveFocus = false) => {
                    const start = shown;
                    const fragment = document.createDocumentFragment();
                    preview.conflicts.slice(start, start + 100).forEach(conflict => {
                        fragment.appendChild(createImportConflictRow(conflict, t, defaultAction.value));
                    });
                    rows.appendChild(fragment);
                    shown = Math.min(start + 100, preview.conflicts.length);
                    summary.textContent = translateCount('messages.import.conflictShowing', preview.conflicts.length).replace('{shown}', shown).replace('{total}', preview.conflicts.length);
                    more.hidden = shown === preview.conflicts.length;
                    more.textContent = translateCount('messages.import.conflictMore', Math.min(100, preview.conflicts.length - shown)).replace('{count}', Math.min(100, preview.conflicts.length - shown));
                    enhanceSelectControls(section);
                    if (moveFocus) rows.children[start]?.querySelector('.custom-select-btn')?.focus();
                };
                defaultAction.addEventListener('change', () => {
                    rows.querySelectorAll('[data-import-conflict-index]').forEach(select => { select.value = defaultAction.value; });
                    syncAllCustomSelects(section);
                });
                more.addEventListener('click', () => showMore(true));
                section.append(title, label, defaultAction, summary, rows, more);
                showMore();
            };
            return section;
        }
        function createImportConflictRow(conflict, t, defaultAction = 'keep') {
            const row = document.createElement('div');
            row.className = 'import-conflict-row';
            const label = document.createElement('label');
            label.className = 'import-conflict-name';
            const selectId = `import-conflict-${conflict.index}`;
            label.htmlFor = selectId;
            label.textContent = conflict.name;
            const meta = document.createElement('span');
            meta.className = 'import-conflict-meta';
            meta.textContent = translateCount('messages.import.conflictExistingCount', conflict.existingCount).replace('{count}', conflict.existingCount);
            label.appendChild(meta);
            const select = document.createElement('select');
            select.id = selectId;
            select.className = 'import-conflict-select';
            select.dataset.importConflictIndex = String(conflict.index);
            select.setAttribute('aria-label', t['messages.import.conflictActionLabel'].replace('{name}', conflict.name));
            [
                ['keep', 'messages.import.conflictKeep'],
                ['skip', 'messages.import.conflictSkip'],
                ['replace', 'messages.import.conflictReplace']
            ].forEach(([value, key]) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = t[key];
                select.appendChild(option);
            });
            select.value = ['keep', 'skip', 'replace'].includes(defaultAction) ? defaultAction : 'keep';
            row.append(label, select);
            return row;
        }
        function createImportModeOption(t) {
            const group = document.createElement('fieldset');
            group.className = 'import-mode-options';
            const legend = document.createElement('legend');
            legend.className = 'import-mode-title';
            legend.textContent = t['dataReview.importModeTitle'];
            group.appendChild(legend);
            [
                ['mergeImportMode', 'messages.import.mergeMode', 'messages.import.mergeModeHint'],
                ['replaceImportMode', 'settingsRefinement.importReplaceTitle', 'dataReview.importReplaceHint']
            ].forEach(([id, titleKey, hintKey]) => {
                const row = document.createElement('div');
                row.className = 'confirm-option';
                const input = document.createElement('input');
                input.type = 'radio';
                input.name = 'taskImportMode';
                input.id = id;
                input.value = id === 'mergeImportMode' ? 'merge' : 'replace';
                input.defaultChecked = id === 'replaceImportMode';
                input.checked = input.defaultChecked;
                input.addEventListener('change', () => syncImportConflictControls());
                const label = document.createElement('label');
                label.htmlFor = id;
                label.textContent = t[titleKey];
                row.append(input, label);
                group.appendChild(row);
            });
            return group;
        }
        function syncImportConflictControls(root = document) {
            const mergeEnabled = Boolean((root.querySelector('#mergeImportMode') || document.getElementById('mergeImportMode'))?.checked);
            root.querySelectorAll('[data-import-conflict-section]').forEach(section => {
                const hasConflicts = Number(section.dataset.importConflictCount) > 0;
                section.hidden = !mergeEnabled || !hasConflicts;
                if (mergeEnabled && hasConflicts) section.initializeConflictControls?.();
                section.querySelectorAll('select').forEach(select => {
                    select.disabled = !mergeEnabled;
                });
            });
            updateImportSafetyGate(getImportPreviewRoot(root));
            syncAllCustomSelects(root);
        }
        function getImportOptions() {
            return {
                merge: Boolean(document.getElementById('mergeImportMode')?.checked),
                conflictActions: getImportConflictActions(),
                conflictDefault: document.getElementById('importConflictDefaultAction')?.value || 'keep'
            };
        }
        function getImportConflictActions() {
            const actions = new Map();
            document.querySelectorAll('[data-import-conflict-index]').forEach(select => {
                actions.set(Number(select.dataset.importConflictIndex), select.value);
            });
            return actions;
        }
        function prepareImportedTasksForMerge(importedTasks, conflictActions = new Map(), conflictDefault = 'keep') {
            const usedIds = new Set(state.tasks.map(task => Number(task.id)).filter(Number.isFinite));
            const idMap = new Map();
            const existingByName = getExistingTasksByName();
            const idsToDelete = new Set();
            const tasksToImport = importedTasks.filter((task, index) => {
                const key = normalizeTaskNameForCompare(task.name);
                const existing = key ? existingByName.get(key) || [] : [];
                if (existing.length === 0) return true;
                const action = conflictActions.get(index) || (['keep', 'skip', 'replace'].includes(conflictDefault) ? conflictDefault : 'keep');
                if (action === 'skip') return false;
                if (action === 'replace') existing.forEach(item => idsToDelete.add(item.id));
                return true;
            });
            const remapped = tasksToImport.map(task => {
                const originalId = Number(task.id);
                const id = normalizeUniqueNumericId(task.id, usedIds);
                if (Number.isFinite(originalId)) idMap.set(originalId, id);
                return { ...task, id };
            });
            let order = getNextTaskOrder();
            const tasks = sanitizeDanglingTaskReferences(remapped.map(task => {
                const mergedTask = { ...task, order };
                order += CONFIG.DEFAULTS.ORDER_STEP;
                ['repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId'].forEach(key => {
                    if (idMap.has(mergedTask[key])) mergedTask[key] = idMap.get(mergedTask[key]);
                });
                return mergedTask;
            }));
            return { tasks, idsToDelete: [...idsToDelete] };
        }
        function appendImportNameList(wrapper, label, names) {
            if (names.length === 0) return;
            const title = document.createElement('strong');
            title.className = 'confirm-list-title';
            title.textContent = label;
            const list = document.createElement('ul');
            list.className = 'confirm-list';
            names.slice(0, 6).forEach(name => {
                const item = document.createElement('li');
                item.textContent = name;
                list.appendChild(item);
            });
            wrapper.append(title, list);
        }
        function createConfirmRow(label, value) {
            const row = document.createElement('div');
            row.className = 'confirm-row';
            const labelEl = document.createElement('span');
            labelEl.textContent = label;
            const valueEl = document.createElement('strong');
            valueEl.textContent = value;
            row.append(labelEl, valueEl);
            return row;
        }
        function normalizeImportedTasks(rawTasks) {
            const duplicateIds = new Set(getDuplicateImportIds(rawTasks));
            const usedIds = new Set(rawTasks.map(task => normalizeTaskReferenceId(task?.id)).filter(id => id !== null));
            const assignedOriginalIds = new Set();
            const normalizeId = value => {
                const originalId = normalizeTaskReferenceId(value);
                if (originalId !== null && !assignedOriginalIds.has(originalId)) {
                    assignedOriginalIds.add(originalId);
                    return originalId;
                }
                return createUniqueNumericId(usedIds);
            };
            const tasks = rawTasks.map((rawTask, index) => normalizeImportedTask(rawTask, index, normalizeId));
            return sanitizeDanglingTaskReferences(sanitizeAmbiguousImportedReferences(tasks, duplicateIds));
        }
        function getDuplicateImportIds(rawTasks) {
            const counts = new Map();
            rawTasks.forEach(rawTask => {
                if (!rawTask || typeof rawTask !== 'object') return;
                const id = normalizeTaskReferenceId(rawTask.id);
                if (id === null) return;
                counts.set(id, (counts.get(id) || 0) + 1);
            });
            return [...counts.entries()].filter(([, count]) => count > 1).map(([id]) => id);
        }
        function remapImportedTaskReferences(tasks, idMap = new Map()) {
            if (idMap.size === 0) return tasks;
            return tasks.map(task => {
                const remappedTask = { ...task };
                ['repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId'].forEach(key => {
                    if (idMap.has(remappedTask[key])) remappedTask[key] = idMap.get(remappedTask[key]);
                });
                return remappedTask;
            });
        }
        function sanitizeAmbiguousImportedReferences(tasks, duplicateIds = new Set()) {
            if (duplicateIds.size === 0) return tasks;
            return tasks.map(task => {
                const sanitizedTask = { ...task };
                ['repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId'].forEach(key => {
                    if (duplicateIds.has(normalizeTaskReferenceId(sanitizedTask[key]))) sanitizedTask[key] = null;
                });
                return sanitizedTask;
            });
        }
        function sanitizeDanglingTaskReferences(tasks) {
            const ids = new Set(tasks.map(task => Number(task.id)).filter(Number.isFinite));
            return tasks.map(task => {
                const sanitizedTask = { ...task };
                ['repeatSourceId', 'repeatCreatedFrom', 'nextRepeatTaskId'].forEach(key => {
                    if (sanitizedTask[key] === null || sanitizedTask[key] === undefined) {
                        sanitizedTask[key] = null;
                        return;
                    }
                    const value = normalizeTaskReferenceId(sanitizedTask[key]);
                    sanitizedTask[key] = value !== null && ids.has(value) ? value : null;
                });
                return sanitizedTask;
            });
        }
        function normalizeTaskReferenceId(value) {
            if (typeof value !== 'number' && typeof value !== 'string') return null;
            if (typeof value === 'string' && value.trim() === '') return null;
            const numeric = Number(value);
            return Number.isFinite(numeric) ? numeric : null;
        }
        function normalizeImportedTask(rawTask, index, normalizeId) {
            const task = rawTask && typeof rawTask === 'object' ? rawTask : {};
            const repeatType = normalizeTaskRepeatType(task.repeatType);
            const dueFields = normalizeTaskDueFields(task);
            return {
                id: normalizeId(task.id),
                name: String(task.name || '').trim() || utils.translate('task.importedFallback').replace('{index}', index + 1),
                description: task.description ? String(task.description) : '',
                project: normalizeTaskProject(task.project),
                tags: normalizeTaskTags(task.tags),
                ...dueFields,
                reminderOffset: Number.isFinite(Number(task.reminderOffset)) ? Number(task.reminderOffset) : 15,
                reminderRepeat: Number.isFinite(Number(task.reminderRepeat)) ? Number(task.reminderRepeat) : -1,
                repeatType,
                repeatInterval: normalizeTaskRepeatInterval(repeatType, task.repeatInterval),
                repeatWeekdays: repeatType === 'weekly-days' ? (normalizeTaskRepeatWeekdays(task.repeatWeekdays).length ? normalizeTaskRepeatWeekdays(task.repeatWeekdays) : [1]) : [],
                repeatPaused: normalizeBoolean(task.repeatPaused),
                repeatSourceId: normalizeTaskReferenceId(task.repeatSourceId),
                repeatCreatedFrom: normalizeTaskReferenceId(task.repeatCreatedFrom),
                nextRepeatTaskId: normalizeTaskReferenceId(task.nextRepeatTaskId),
                snoozedUntil: normalizeStoredDate(task.snoozedUntil),
                lastReminderAt: normalizeStoredDate(task.lastReminderAt),
                subtasks: normalizeImportedSubtasks(task.subtasks),
                completed: normalizeBoolean(task.completed),
                completedAt: normalizeStoredDate(task.completedAt),
                archived: normalizeBoolean(task.archived),
                archivedAt: normalizeStoredDate(task.archivedAt),
                focusDate: normalizeFocusDate(task.focusDate),
                createdAt: normalizeStoredDate(task.createdAt) || new Date().toISOString(),
                order: Number.isFinite(Number(task.order)) ? Number(task.order) : (index + 1) * CONFIG.DEFAULTS.ORDER_STEP
            };
        }
        function normalizeImportedSubtasks(rawSubtasks) {
            if (!Array.isArray(rawSubtasks)) return [];
            const usedIds = new Set();
            return rawSubtasks.map(rawSubtask => {
                const subtask = rawSubtask && typeof rawSubtask === 'object' ? rawSubtask : {};
                return {
                    id: normalizeUniqueNumericId(subtask.id, usedIds),
                    text: String(subtask.text || '').trim(),
                    completed: normalizeBoolean(subtask.completed)
                };
            }).filter(subtask => subtask.text);
        }
        let sampleTasksSaving = false;
        async function addSampleTasks() {
            if (!ensureStorageAvailable() || sampleTasksSaving || state.tasks.length > 0) return;
            sampleTasksSaving = true;
            const button = document.getElementById('addExampleTasksBtn');
            if (button) button.disabled = true;
            try {
            const t = state.translations[state.currentLanguage];
            const beforeTasks = captureUndoSnapshot();
            const usedIds = new Set(state.tasks.map(task => Number(task.id)).filter(Number.isFinite));
            let order = getNextTaskOrder();
            const createSampleTask = (payload) => {
                const task = createTaskRecord({ reminderOffset: -1, ...payload, name: t['onboarding.examplePrefix'].replace('{name}', payload.name), order });
                task.id = createTaskId(usedIds);
                order += CONFIG.DEFAULTS.ORDER_STEP;
                return task;
            };
            const samples = normalizeTaskRecords([
                createSampleTask({ name: t['samples.task1.name'] || "完成项目报告", description: t['samples.task1.description'] || "编写并提交季度项目总结报告", project: t['samples.task1.project'] || "工作", tags: [t['samples.task1.tag'] || "报告"], ...createDueFieldsFromDate(new Date(Date.now() + 432000000)) }),
                createSampleTask({ name: t['samples.task2.name'] || "团队会议准备", description: t['samples.task2.description'] || "准备下周团队会议的演示材料", project: t['samples.task2.project'] || "工作", tags: [t['samples.task2.tag'] || "会议"], ...createDueFieldsFromDate(new Date(Date.now() + 864000000)) }),
                createSampleTask({ name: t['samples.task3.name'] || "学习计划制定", description: t['samples.task3.description'] || "制定下个月的个人学习计划", project: t['samples.task3.project'] || "个人", tags: [t['samples.task3.tag'] || "学习"], ...clearDueFields() })
            ]).tasks;
            await dbActions.addTasksIfEmpty(samples);
            registerUndoSnapshot(t['onboarding.examplesUndo'], beforeTasks);
            await refreshTasks();
            utils.notify(t['onboarding.examplesAdded'], 'success', { undo: true });
            } catch (error) {
                handleStorageOperationError(error, 'onboarding.examplesError');
            } finally {
                sampleTasksSaving = false;
                if (button?.isConnected) button.disabled = false;
            }
        }
    };
})(window.TaskTracer = window.TaskTracer || {});
