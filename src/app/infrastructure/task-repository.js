(() => {
    'use strict';

    const namespace = window.TaskTracer || (window.TaskTracer = {});

    namespace.createTaskRepository = function createTaskRepository(options = {}) {
        const name = options.name;
        const version = options.version;
        const stores = Object.freeze({ tasks: 'tasks', config: 'config', ...options.stores });
        const keys = Object.freeze({ revision: 'taskRevision', recoveryHistory: 'recoveryHistory',
            savedViews: 'savedViews', lastBackupAt: 'lastBackupAt', lastTaskBackup: 'lastTaskBackup', ...options.keys });
        const recovery = Object.freeze({ limit: 10, intervalMs: 300000, ...options.recovery });
        const databaseFactory = options.indexedDB;
        const now = options.now || (() => Date.now());
        const createId = options.createId || (() => window.crypto.randomUUID());

        if (typeof name !== 'string' || !name || !Number.isSafeInteger(version) || version < 1) {
            throw new TypeError('A database name and positive integer version are required');
        }
        if (!Number.isSafeInteger(recovery.limit) || recovery.limit < 1 || !Number.isFinite(recovery.intervalMs)
            || recovery.intervalMs < 0) throw new TypeError('Invalid recovery checkpoint configuration');

        const storedDate = value => typeof value === 'string' && !Number.isNaN(Date.parse(value)) ? value : null;
        const conflict = message => new DOMException(message, 'TaskConflictError');
        const synchronous = value => {
            if (value && typeof value.then === 'function') throw new TypeError('IndexedDB changes must be synchronous');
            return value;
        };

        function transaction(database, names, mode, abortMessage, execute) {
            return new Promise((resolve, reject) => {
                if (!database || typeof database.transaction !== 'function') {
                    reject(new DOMException('Database connection is unavailable', 'InvalidStateError'));
                    return;
                }
                const tx = database.transaction(names, mode);
                let result;
                let failure;
                const abort = error => {
                    failure = failure || error;
                    try { tx.abort(); }
                    catch (abortError) { reject(failure || abortError); }
                };
                tx.oncomplete = () => resolve(result);
                tx.onerror = event => {
                    const error = event.target?.error;
                    if (error?.name !== 'AbortError') failure = failure || tx.taskConflictError || error || tx.error;
                };
                tx.onabort = () => reject(failure || tx.taskConflictError || tx.error || new Error(abortMessage));
                try { execute(tx, value => { result = value; }, abort); }
                catch (error) { abort(error); }
            });
        }

        function open({ onVersionChange } = {}) {
            return new Promise((resolve, reject) => {
                let abandoned = false;
                const request = (databaseFactory || window.indexedDB).open(name, version);
                request.onerror = () => reject(request.error);
                request.onblocked = () => {
                    abandoned = true;
                    reject(new DOMException('Close older app windows before retrying the database upgrade', 'StorageUpgradeBlockedError'));
                };
                request.onsuccess = () => {
                    const database = request.result;
                    if (abandoned) { database.close(); return; }
                    database.onversionchange = () => {
                        database.close();
                        if (onVersionChange) onVersionChange(database,
                            new DOMException('The database changed in another window', 'StorageVersionChangedError'));
                    };
                    resolve(database);
                };
                request.onupgradeneeded = () => {
                    if (abandoned) { request.transaction.abort(); return; }
                    const database = request.result;
                    if (!database.objectStoreNames.contains(stores.tasks)) {
                        const tasks = database.createObjectStore(stores.tasks, { keyPath: 'id' });
                        tasks.createIndex('dueDate', 'dueDate', { unique: false });
                    }
                    if (!database.objectStoreNames.contains(stores.config)) {
                        database.createObjectStore(stores.config, { keyPath: 'key' });
                    }
                };
            });
        }

        function dbOp(database, storeName, mode, change) {
            return transaction(database, [storeName], mode, `${storeName} transaction aborted`, (tx, setResult) => {
                const request = synchronous(change(tx.objectStore(storeName)));
                request.addEventListener('success', () => setResult(request.result));
            });
        }

        function readTaskSnapshot(database) {
            return transaction(database, [stores.tasks, stores.config], 'readonly', 'Read tasks transaction aborted', (tx, setResult) => {
                const tasks = tx.objectStore(stores.tasks).getAll();
                const revision = tx.objectStore(stores.config).get(keys.revision);
                revision.onsuccess = () => setResult({ tasks: tasks.result, taskRevision: revision.result?.value || 0 });
            });
        }

        function getTaskBackupStatus(database) {
            return transaction(database, [stores.tasks, stores.config], 'readonly', 'Read backup status transaction aborted', (tx, setResult) => {
                const config = tx.objectStore(stores.config);
                const count = tx.objectStore(stores.tasks).count();
                const revision = config.get(keys.revision);
                const date = config.get(keys.lastBackupAt);
                const backup = config.get(keys.lastTaskBackup);
                backup.onsuccess = () => setResult({ taskCount: count.result, taskRevision: revision.result?.value || 0,
                    lastBackupAt: storedDate(date.result?.value), lastTaskBackup: backup.result?.value || null });
            });
        }

        function recordTaskBackup(database, date, taskRevision) {
            return transaction(database, [stores.config], 'readwrite', 'Record backup transaction aborted', (tx, setResult, abort) => {
                const config = tx.objectStore(stores.config);
                const previous = config.get(keys.lastBackupAt);
                previous.onsuccess = () => {
                    try {
                        const previousDate = storedDate(previous.result?.value);
                        if (previousDate && previousDate > date) { setResult({ recorded: false }); return; }
                        config.put({ key: keys.lastBackupAt, value: date });
                        config.put({ key: keys.lastTaskBackup, value: { date, taskRevision } });
                        setResult({ recorded: true });
                    } catch (error) { abort(error); }
                };
            });
        }

        function writeTaskTransaction(database, write, { expectedRevision, abortMessage = 'Task transaction aborted', forceCheckpoint = false } = {}) {
            if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0) {
                return Promise.reject(new TypeError('An observed task revision is required'));
            }
            return transaction(database, [stores.tasks, stores.config], 'readwrite', abortMessage, (tx, setResult, abort) => {
                const tasks = tx.objectStore(stores.tasks);
                const config = tx.objectStore(stores.config);
                const revision = config.get(keys.revision);
                revision.onsuccess = () => {
                    const currentRevision = revision.result?.value || 0;
                    if (currentRevision !== expectedRevision) { abort(conflict('Tasks changed in another window')); return; }
                    const history = config.get(keys.recoveryHistory);
                    history.onsuccess = () => {
                        const entries = Array.isArray(history.result?.value) ? history.result.value : [];
                        const timestamp = now();
                        const checkpointDue = forceCheckpoint || !entries.length
                            || timestamp - Date.parse(entries[0].createdAt) >= recovery.intervalMs;
                        const apply = beforeTasks => {
                            try {
                                synchronous(write(tasks, beforeTasks));
                                const nextRevision = currentRevision + 1;
                                config.put({ key: keys.revision, value: nextRevision });
                                setResult({ taskRevision: nextRevision });
                            } catch (error) { abort(error); }
                        };
                        if (!checkpointDue) { apply(); return; }
                        const before = tasks.getAll();
                        before.onsuccess = () => {
                            try {
                                const entry = { id: createId(), createdAt: new Date(timestamp).toISOString(), tasks: before.result };
                                config.put({ key: keys.recoveryHistory, value: [entry, ...entries].slice(0, recovery.limit) });
                                apply(before.result);
                            } catch (error) { abort(error); }
                        };
                    };
                };
            });
        }

        function recordReminderDelivery(database, expected, lastReminderAt, { getNotificationKey } = {}) {
            if (typeof getNotificationKey !== 'function') return Promise.reject(new TypeError('A notification identity function is required'));
            return transaction(database, [stores.tasks, stores.config], 'readwrite', 'Record reminder delivery transaction aborted', (tx, setResult, abort) => {
                const tasks = tx.objectStore(stores.tasks);
                const config = tx.objectStore(stores.config);
                const revision = config.get(keys.revision);
                revision.onsuccess = () => {
                    const currentRevision = revision.result?.value || 0;
                    setResult({ recorded: false, taskRevision: currentRevision });
                    const request = tasks.get(expected.id);
                    request.onsuccess = () => {
                        try {
                            const current = request.result;
                            if (!current || current.completed || current.archived) return;
                            if (synchronous(getNotificationKey(current)) !== expected.key) return;
                            if ((current.snoozedUntil || null) !== expected.snoozedUntil) return;
                            if ((current.lastReminderAt || null) !== expected.lastReminderAt) return;
                            tasks.put({ ...current, lastReminderAt, snoozedUntil: null });
                            config.put({ key: keys.revision, value: currentRevision + 1 });
                            setResult({ recorded: true, taskRevision: currentRevision + 1 });
                        } catch (error) { abort(error); }
                    };
                };
            });
        }

        function updateSavedViews(database, change) {
            return transaction(database, [stores.config], 'readwrite', 'Saved views transaction aborted', (tx, setResult, abort) => {
                const config = tx.objectStore(stores.config);
                const request = config.get(keys.savedViews);
                request.onsuccess = () => {
                    try {
                        const committed = synchronous(change(request.result?.value));
                        config.put({ key: keys.savedViews, value: committed });
                        setResult(committed);
                    } catch (error) { abort(error); }
                };
            });
        }

        function clearReviewedRecoveryHistory(database, expectedKeys) {
            const reviewed = JSON.stringify(expectedKeys);
            return transaction(database, [stores.config], 'readwrite', 'Clear recovery history transaction aborted', (tx, setResult, abort) => {
                const config = tx.objectStore(stores.config);
                const request = config.get(keys.recoveryHistory);
                request.onsuccess = () => {
                    try {
                        const current = (Array.isArray(request.result?.value) ? request.result.value : [])
                            .map(entry => entry && typeof entry.id === 'string' ? entry.id : null);
                        if (JSON.stringify(current) !== reviewed) {
                            abort(new DOMException('Recovery history changed after review', 'RecoveryHistoryConflictError'));
                            return;
                        }
                        config.delete(keys.recoveryHistory);
                    } catch (error) { abort(error); }
                };
            });
        }

        function deletion(database, tasks, ids, writeOptions, abortMessage) {
            if (ids.length && typeof writeOptions?.getDeletionUpdates !== 'function') {
                return Promise.reject(new TypeError('A deletion reconciliation function is required'));
            }
            return writeTaskTransaction(database, (store, beforeTasks) => {
                ids.forEach(id => store.delete(id));
                if (ids.length) synchronous(writeOptions.getDeletionUpdates(beforeTasks, ids)).forEach(task => store.put(task));
                tasks.forEach(task => store.put(task));
            }, { ...writeOptions, abortMessage, forceCheckpoint: true });
        }

        function undoTaskChanges(database, beforeTasks, afterTasks, writeOptions) {
            const before = new Map(beforeTasks.map(task => [task.id, task]));
            const after = new Map(afterTasks.map(task => [task.id, task]));
            const ids = [...new Set([...before.keys(), ...after.keys()])]
                .filter(id => JSON.stringify(before.get(id)) !== JSON.stringify(after.get(id)));
            return writeTaskTransaction(database, store => {
                let remaining = ids.length;
                for (const id of ids) {
                    const request = store.get(id);
                    request.onsuccess = () => {
                        if (JSON.stringify(request.result) !== JSON.stringify(after.get(id))) {
                            store.transaction.taskConflictError = conflict('Undo conflicts with newer task changes');
                            store.transaction.abort();
                            return;
                        }
                        remaining -= 1;
                        if (remaining) return;
                        for (const changedId of ids) {
                            if (before.has(changedId)) store.put(before.get(changedId));
                            else store.delete(changedId);
                        }
                    };
                }
            }, { ...writeOptions, abortMessage: 'Undo conflicts with newer task changes', forceCheckpoint: true });
        }

        return Object.freeze({
            open,
            close: database => database.close(),
            dbOp,
            readTaskSnapshot,
            getTaskBackupStatus,
            recordTaskBackup,
            recordReminderDelivery,
            writeTaskTransaction,
            addTask: (database, task, writeOptions) => writeTaskTransaction(database, store => store.add(task),
                { ...writeOptions, abortMessage: 'Add task transaction aborted' }),
            updateTask: (database, task, writeOptions) => writeTaskTransaction(database, store => store.put(task),
                { ...writeOptions, abortMessage: 'Update task transaction aborted' }),
            updateTasks: (database, tasks, writeOptions) => writeTaskTransaction(database, store => tasks.forEach(task => store.put(task)),
                { ...writeOptions, abortMessage: 'Update tasks transaction aborted' }),
            deleteTask: (database, id, writeOptions) => deletion(database, [], [id], writeOptions, 'Delete task transaction aborted'),
            deleteTasks: (database, ids, writeOptions) => deletion(database, [], ids, writeOptions, 'Delete tasks transaction aborted'),
            mergeImportedTasks: (database, tasks, ids, writeOptions) => deletion(database, tasks, ids, writeOptions, 'Merge imported tasks transaction aborted'),
            replaceAllTasks: (database, tasks, writeOptions) => writeTaskTransaction(database, store => {
                store.clear();
                tasks.forEach(task => store.put(task));
            }, { ...writeOptions, abortMessage: 'Replace tasks transaction aborted', forceCheckpoint: true }),
            undoTaskChanges,
            getConfig: (database, key) => dbOp(database, stores.config, 'readonly', store => store.get(key)).then(record => record ? record.value : null),
            setConfig: (database, key, value) => dbOp(database, stores.config, 'readwrite', store => store.put({ key, value })),
            deleteConfig: (database, key) => dbOp(database, stores.config, 'readwrite', store => store.delete(key)),
            updateSavedViews,
            clearReviewedRecoveryHistory
        });
    };
})();
