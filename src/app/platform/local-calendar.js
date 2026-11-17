(function (namespace) {
    'use strict';
    function formatDateInputValue(date) {
        const d = date instanceof Date ? date : new Date(date);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }
    function formatTimeInputValue(date) {
        const d = date instanceof Date ? date : new Date(date);
        return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    }
    function createWallDate(date, time) {
        const value = new Date(`${date}T${time}`);
        return Number.isNaN(value.getTime()) ? null : value;
    }
    function legacyStoredDueDateToLocalDate(iso) {
        const date = new Date(iso);
        return new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    }
    function getCurrentTimeZone() {
        return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    }
    namespace.LocalCalendar = Object.freeze({ formatDateInputValue, formatTimeInputValue, createWallDate,
        legacyStoredDueDateToLocalDate, getCurrentTimeZone });
})(window.TaskTracer = window.TaskTracer || {});
