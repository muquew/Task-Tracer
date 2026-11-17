(function (namespace) {
    'use strict';

    function create({ defaultTime, getCurrentTimeZone, localCalendar }) {
        const timeZoneValidity = new Map();
        const timeZonePartFormatters = new Map();

        function normalizeDueDateValue(value) {
            const text = String(value || '').trim();
            if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return '';
            const [year, month, day] = text.split('-').map(Number);
            if (year < 100) return '';
            const date = new Date(`${text}T12:00:00.000Z`);
            if (Number.isNaN(date.getTime())) return '';
            if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return '';
            return text;
        }

        function normalizeDueTimeValue(value) {
            const text = String(value || '').trim();
            if (!/^\d{2}:\d{2}$/.test(text)) return '';
            const [hours, minutes] = text.split(':').map(Number);
            if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return '';
            return text;
        }

        function normalizeTimeZoneName(value) {
            const timeZone = typeof value === 'string' && value.trim() ? value.trim() : getCurrentTimeZone();
            return isValidTimeZoneName(timeZone) ? timeZone : getCurrentTimeZone();
        }

        function isValidTimeZoneName(value) {
            if (typeof value !== 'string' || !value || value.length > 128) return false;
            if (timeZoneValidity.has(value)) return timeZoneValidity.get(value);
            let valid = false;
            try {
                new Intl.DateTimeFormat('en-US', { timeZone: value }).format(new Date(0));
                valid = true;
            } catch (error) {}
            if (timeZoneValidity.size >= 128) timeZoneValidity.delete(timeZoneValidity.keys().next().value);
            timeZoneValidity.set(value, valid);
            return valid;
        }

        function getInstantWallPartsInTimeZone(iso, timeZoneName) {
            const instant = new Date(iso);
            if (Number.isNaN(instant.getTime())) return null;
            const timeZone = normalizeTimeZoneName(timeZoneName);
            let formatter = timeZonePartFormatters.get(timeZone);
            if (!formatter) {
                formatter = new Intl.DateTimeFormat('en-US', {
                    timeZone,
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    hourCycle: 'h23'
                });
                if (timeZonePartFormatters.size >= 64) timeZonePartFormatters.delete(timeZonePartFormatters.keys().next().value);
                timeZonePartFormatters.set(timeZone, formatter);
            }
            const parts = formatter.formatToParts(instant).reduce((acc, part) => {
                if (part.type !== 'literal') acc[part.type] = part.value;
                return acc;
            }, {});
            if (!parts.year || !parts.month || !parts.day || !parts.hour || !parts.minute) return null;
            return {
                date: `${parts.year}-${parts.month}-${parts.day}`,
                time: `${parts.hour}:${parts.minute}`
            };
        }

        function getTimeZoneOffsetMs(instant, timeZoneName) {
            const parts = getInstantWallPartsInTimeZone(instant.toISOString(), timeZoneName);
            if (!parts) return 0;
            const [year, month, day] = parts.date.split('-').map(Number);
            const [hours, minutes] = parts.time.split(':').map(Number);
            return Date.UTC(year, month - 1, day, hours, minutes, 0, 0) - instant.getTime();
        }

        function localDateTimeToInstantISO(dateValue, timeValue, timeZoneName = getCurrentTimeZone()) {
            const date = normalizeDueDateValue(dateValue);
            const time = normalizeDueTimeValue(timeValue) || defaultTime;
            const timeZone = normalizeTimeZoneName(timeZoneName);
            const wallTime = new Date(`${date}T${time}:00.000Z`).getTime();
            const offsets = new Set([-172800000, 0, 172800000].map(delta => getTimeZoneOffsetMs(new Date(wallTime + delta), timeZone)));
            const candidates = [];
            for (const offset of offsets) {
                const instant = wallTime - offset;
                const actualOffset = getTimeZoneOffsetMs(new Date(instant), timeZone);
                offsets.add(actualOffset);
                candidates.push({ instant, delta: instant + actualOffset - wallTime });
            }
            const exact = candidates.filter(candidate => candidate.delta === 0).sort((a, b) => a.instant - b.instant);
            const forward = candidates.filter(candidate => candidate.delta > 0).sort((a, b) => a.delta - b.delta || a.instant - b.instant);
            const selected = exact[0] || forward[0];
            if (!selected) throw new RangeError('Could not resolve the selected local deadline');
            return new Date(selected.instant).toISOString();
        }

        function formatDateInputValue(date) {
            return localCalendar.formatDateInputValue(date);
        }

        function formatTimeInputValue(date) {
            return localCalendar.formatTimeInputValue(date);
        }

        function createWallDate(dateValue, timeValue = defaultTime) {
            const dueLocalDate = normalizeDueDateValue(dateValue);
            if (!dueLocalDate) return null;
            const dueLocalTime = normalizeDueTimeValue(timeValue) || defaultTime;
            return localCalendar.createWallDate(dueLocalDate, dueLocalTime);
        }

        function legacyStoredDueDateToLocalDate(iso) {
            return localCalendar.legacyStoredDueDateToLocalDate(iso);
        }

        function createDueFields(dateValue, timeValue, timeZoneName = getCurrentTimeZone()) {
            const dueLocalDate = normalizeDueDateValue(dateValue);
            if (!dueLocalDate) return clearDueFields();
            const dueLocalTime = normalizeDueTimeValue(timeValue) || defaultTime;
            const dueTimeZone = normalizeTimeZoneName(timeZoneName);
            const dueAt = localDateTimeToInstantISO(dueLocalDate, dueLocalTime, dueTimeZone);
            return createDueFieldsFromInstant(dueAt, dueTimeZone);
        }

        function clearDueFields() {
            return {
                dueDate: null,
                dueAt: null,
                dueLocalDate: null,
                dueLocalTime: null,
                dueTimeZone: null
            };
        }

        function normalizeTaskDueFields(task) {
            const localDate = normalizeDueDateValue(task.dueLocalDate);
            const localTime = normalizeDueTimeValue(task.dueLocalTime);
            const dueAt = normalizeStoredDate(task.dueAt);
            const dueDate = normalizeStoredDate(task.dueDate);
            if (!localDate && !dueAt && !dueDate) return clearDueFields();
            const dueTimeZone = normalizeTimeZoneName(task.dueTimeZone);
            if (dueAt) return createDueFieldsFromInstant(dueAt, dueTimeZone);
            if (localDate) {
                const dueLocalTime = localTime || defaultTime;
                if (dueDate) return createDueFieldsFromInstant(dueDate, dueTimeZone);
                return createDueFields(localDate, dueLocalTime, dueTimeZone);
            }
            if (dueDate) {
                const legacy = legacyStoredDueDateToLocalDate(dueDate);
                return createDueFields(formatDateInputValue(legacy), formatTimeInputValue(legacy));
            }
            return clearDueFields();
        }

        function createDueFieldsFromDate(date, timeZoneName = getCurrentTimeZone()) {
            if (!isValidDate(date)) return clearDueFields();
            return createDueFields(formatDateInputValue(date), formatTimeInputValue(date), timeZoneName);
        }

        function createDueFieldsFromInstant(iso, timeZoneName = getCurrentTimeZone()) {
            const dueTimeZone = normalizeTimeZoneName(timeZoneName);
            const parts = getInstantWallPartsInTimeZone(iso, dueTimeZone);
            if (!parts) return clearDueFields();
            return {
                dueDate: iso,
                dueAt: iso,
                dueLocalDate: parts.date,
                dueLocalTime: parts.time,
                dueTimeZone
            };
        }

        function getTaskDueTimeZone(task) {
            return normalizeTimeZoneName(task?.dueTimeZone);
        }

        function getTaskDueDateKey(task) {
            const dueAt = getTaskDueInstant(task);
            if (dueAt) return getInstantWallPartsInTimeZone(dueAt, getTaskDueTimeZone(task))?.date || '';
            return normalizeDueDateValue(task?.dueLocalDate);
        }

        function getTaskDueTimeValue(task) {
            const dueAt = getTaskDueInstant(task);
            if (dueAt) return getInstantWallPartsInTimeZone(dueAt, getTaskDueTimeZone(task))?.time || defaultTime;
            return normalizeDueTimeValue(task?.dueLocalTime) || defaultTime;
        }

        function hasTaskDueDate(task) {
            return Boolean(getTaskDueDateKey(task));
        }

        function getTaskDueLocalDate(task) {
            return createWallDate(getTaskDueDateKey(task), getTaskDueTimeValue(task));
        }

        function getTaskDueInstant(task) {
            return normalizeStoredDate(task?.dueAt) || normalizeStoredDate(task?.dueDate);
        }

        function getTaskDueSortValue(task) {
            const dueAt = getTaskDueInstant(task);
            if (dueAt) return new Date(dueAt).getTime();
            const date = getTaskDueLocalDate(task);
            return date ? date.getTime() : null;
        }

        function calculateTaskTimeLeft(task, now) {
            const dueAt = getTaskDueInstant(task);
            if (dueAt) return (new Date(dueAt) - new Date(now)) / 60000;
            const localDate = getTaskDueLocalDate(task);
            return localDate ? (localDate - new Date(now)) / 60000 : null;
        }

        function normalizeStoredDate(value) {
            return typeof value === 'string' && !Number.isNaN(Date.parse(value)) ? value : null;
        }

        function isValidDate(date) {
            return date instanceof Date && !Number.isNaN(date.getTime());
        }

        function normalizeTaskRepeatType(value) {
            return ['none', 'daily', 'weekly', 'weekly-days', 'monthly', 'monthly-last', 'custom'].includes(value) ? value : 'none';
        }

        function normalizeTaskRepeatInterval(type, value) {
            const interval = Math.floor(Number(value));
            if (type !== 'custom') return 1;
            if (!Number.isFinite(interval)) return 1;
            return Math.min(365, Math.max(1, interval));
        }

        function normalizeTaskRepeatWeekdays(value) {
            const items = Array.isArray(value) ? value : String(value || '').split(',');
            const seen = new Set();
            return items.map(Number)
                .filter(day => Number.isInteger(day) && day >= 0 && day <= 6)
                .filter(day => {
                    if (seen.has(day)) return false;
                    seen.add(day);
                    return true;
                })
                .sort((a, b) => getWeekdayDisplayIndex(a) - getWeekdayDisplayIndex(b));
        }

        function getTaskRepeatRule(task) {
            const type = normalizeTaskRepeatType(task.repeatType);
            const weekdays = type === 'weekly-days' ? getTaskRepeatWeekdays(task) : [];
            return {
                type,
                interval: normalizeTaskRepeatInterval(type, task.repeatInterval),
                weekdays,
                paused: task.repeatPaused === true
            };
        }

        function getTaskRepeatWeekdays(task) {
            const weekdays = normalizeTaskRepeatWeekdays(task.repeatWeekdays);
            if (weekdays.length > 0) return weekdays;
            const dueDate = getTaskDueDateKey(task);
            return [dueDate ? new Date(`${dueDate}T00:00:00.000Z`).getUTCDay() : 1];
        }

        function getWeekdayDisplayIndex(day) {
            return day === 0 ? 7 : day;
        }

        function hasTaskRepeat(task) {
            return getTaskRepeatRule(task).type !== 'none';
        }

        function calculateNextRepeatDueFields(task, rule) {
            const dateKey = getTaskDueDateKey(task);
            if (!dateKey) return clearDueFields();
            const date = new Date(`${dateKey}T00:00:00.000Z`);
            const time = getTaskDueTimeValue(task);
            const timeZone = getTaskDueTimeZone(task);
            let next;
            if (rule.type === 'weekly-days') {
                next = getNextWeeklyRepeatDate(date, rule.weekdays);
            } else if (rule.type === 'monthly') {
                next = addMonthsClamped(date, 1);
            } else if (rule.type === 'monthly-last') {
                next = getLastDayOfNextMonth(date);
            } else {
                const days = rule.type === 'weekly' ? 7 : rule.type === 'custom' ? rule.interval : 1;
                next = new Date(date);
                next.setUTCDate(next.getUTCDate() + days);
            }
            return createDueFields(next.toISOString().slice(0, 10), time, timeZone);
        }

        function getNextWeeklyRepeatDate(date, weekdays) {
            const selected = weekdays.length > 0 ? weekdays : [date.getUTCDay()];
            for (let offset = 1; offset <= 7; offset += 1) {
                const next = new Date(date);
                next.setUTCDate(date.getUTCDate() + offset);
                if (selected.includes(next.getUTCDay())) return next;
            }
            const fallback = new Date(date);
            fallback.setUTCDate(date.getUTCDate() + 7);
            return fallback;
        }

        function getLastDayOfNextMonth(date) {
            const next = new Date(date);
            next.setUTCDate(1);
            next.setUTCMonth(next.getUTCMonth() + 1);
            next.setUTCDate(getDaysInMonth(next.getUTCFullYear(), next.getUTCMonth()));
            return next;
        }

        function addMonthsClamped(date, months) {
            const next = new Date(date);
            const day = next.getUTCDate();
            next.setUTCDate(1);
            next.setUTCMonth(next.getUTCMonth() + months);
            next.setUTCDate(Math.min(day, getDaysInMonth(next.getUTCFullYear(), next.getUTCMonth())));
            return next;
        }

        function getDaysInMonth(year, monthIndex) {
            return new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
        }

        return Object.freeze({
            normalizeDueDateValue, normalizeDueTimeValue, normalizeTimeZoneName,
            isValidTimeZoneName, getInstantWallPartsInTimeZone, getTimeZoneOffsetMs,
            localDateTimeToInstantISO, formatDateInputValue, formatTimeInputValue,
            createWallDate, legacyStoredDueDateToLocalDate, createDueFields,
            clearDueFields, normalizeTaskDueFields, createDueFieldsFromDate,
            createDueFieldsFromInstant, getTaskDueTimeZone, getTaskDueDateKey,
            getTaskDueTimeValue, hasTaskDueDate, getTaskDueLocalDate,
            getTaskDueInstant, getTaskDueSortValue, calculateTaskTimeLeft,
            normalizeStoredDate, isValidDate, normalizeTaskRepeatType,
            normalizeTaskRepeatInterval, normalizeTaskRepeatWeekdays, getTaskRepeatRule,
            getTaskRepeatWeekdays, getWeekdayDisplayIndex, hasTaskRepeat,
            calculateNextRepeatDueFields, getNextWeeklyRepeatDate, getLastDayOfNextMonth,
            addMonthsClamped, getDaysInMonth
        });
    }

    namespace.TaskDates = Object.freeze({ create });
})(window.TaskTracer = window.TaskTracer || {});
