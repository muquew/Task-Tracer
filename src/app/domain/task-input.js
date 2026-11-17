(function (namespace) {
    'use strict';

    function normalizeTaskProject(value) {
        return typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : '';
    }

    function normalizeTaskTags(tags) {
        if (!Array.isArray(tags)) return [];
        const seen = new Set();
        return tags.map(tag => String(tag || '').trim().replace(/^#/, '').replace(/\s+/g, ' '))
            .filter(Boolean)
            .filter(tag => {
                const key = tag.toLowerCase();
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
    }

    function parseTagsInput(value) {
        const source = String(value || '');
        const tags = [];
        let offset = 0;
        while (offset < source.length) {
            const quoted = source.slice(offset).match(/^\s*"((?:[^"]|"")*)"\s*(?:,|$)/);
            if (quoted) {
                tags.push(quoted[1].replace(/""/g, '"'));
                offset += quoted[0].length;
            } else {
                const comma = source.indexOf(',', offset);
                const end = comma === -1 ? source.length : comma;
                tags.push(source.slice(offset, end));
                offset = end + 1;
            }
        }
        return normalizeTaskTags(tags);
    }

    function formatTagsInput(tags) {
        return normalizeTaskTags(tags).map(tag => /[,"]/.test(tag) ? `"${tag.replace(/"/g, '""')}"` : tag).join(', ');
    }

    function tokenizeTaskInput(input) {
        const source = String(input || '').trim();
        const tokens = [];
        let start = 0;
        let quoted = false;
        let escaped = false;
        for (let index = 0; index < source.length; index += 1) {
            const character = source[index];
            if (escaped) { escaped = false; continue; }
            if (quoted && character === '\\') { escaped = true; continue; }
            if (character === '"') {
                const prefix = source.slice(start, index);
                if (quoted || !prefix || /^(?:[/#]|(?:project|p|tag|tags|status|state|due|date|completed):)$/i.test(prefix)) quoted = !quoted;
            }
            if (!quoted && /\s/.test(character)) {
                if (index > start) tokens.push(source.slice(start, index));
                start = index + 1;
            }
        }
        if (start < source.length) tokens.push(source.slice(start));
        return tokens;
    }

    function readTaskInputValue(tokens, index, prefix, names) {
        const raw = tokens[index].slice(prefix.length);
        if (!raw) return null;
        if (raw.startsWith('"')) {
            if (!raw.endsWith('"') || raw.length < 2) return null;
            try {
                const value = JSON.parse(raw);
                return typeof value === 'string' && value.trim() ? { value, consumed: 1, exact: true } : null;
            } catch { return null; }
        }
        let match = null;
        let caseExact = false;
        for (const name of names) {
            const words = name.split(' ');
            if (words.length < 2 || index + words.length > tokens.length) continue;
            const following = tokens.slice(index + 1, index + words.length);
            if (following.some(token => /^[/#]|^(?:project|p|tag|tags|status|state|due|date|completed):/i.test(token))) continue;
            const candidate = [raw, ...following].join(' ');
            if (candidate.toLowerCase() !== name.toLowerCase()) continue;
            const sameCase = candidate === name;
            if (!match || words.length > match.consumed || (words.length === match.consumed && sameCase && !caseExact)) {
                match = { value: name, consumed: words.length, exact: true };
                caseExact = sameCase;
            }
        }
        return match || { value: raw, consumed: 1, exact: false };
    }

    function parseQuickAddInput(rawInput, { names, now, dates }) {
        const context = { now: new Date(now), dates };
        const tokens = tokenizeTaskInput(rawInput);
        const contentTokens = [];
        const tags = [];
        let project = '';
        for (let index = 0; index < tokens.length; index += 1) {
            const token = tokens[index];
            if (token.startsWith('#') && token.length > 1) {
                const parsed = readTaskInputValue(tokens, index, '#', names.tags);
                if (parsed) { tags.push(parsed.value); index += parsed.consumed - 1; continue; }
            }
            if (token.startsWith('/') && token.length > 1) {
                const parsed = readTaskInputValue(tokens, index, '/', names.projects);
                if (parsed) { project = parsed.value; index += parsed.consumed - 1; continue; }
            }
            contentTokens.push(token);
        }
        const consumed = new Set();
        let date = '';
        let time = '';
        contentTokens.forEach((token, index) => {
            if (!date) {
                const parsedDate = parseQuickAddDateToken(token, context);
                if (parsedDate) {
                    date = parsedDate;
                    consumed.add(index);
                    return;
                }
            }
            if (!time) {
                const parsedTime = parseQuickAddTimeToken(token);
                if (parsedTime) {
                    time = parsedTime;
                    consumed.add(index);
                }
            }
        });
        const implicitDate = Boolean(time && !date);
        if (implicitDate) date = dates.formatDateInputValue(context.now);
        return {
            implicitDate,
            name: contentTokens.filter((_, index) => !consumed.has(index)).join(' ').trim(),
            date,
            time,
            project: normalizeTaskProject(project),
            tags: normalizeTaskTags(tags)
        };
    }

    function parseQuickAddDateToken(token, context) {
        const text = String(token || '').trim();
        const lower = text.toLowerCase();
        const relativeDates = new Map([
            ['今天', 0], ['今日', 0], ['today', 0], ['昨天', -1], ['昨日', -1],
            ['yesterday', -1], ['前天', -2], ['明天', 1], ['tomorrow', 1], ['后天', 2]
        ]);
        if (relativeDates.has(lower)) return formatDateWithOffset(relativeDates.get(lower), context);
        const weekday = parseQuickAddWeekdayToken(lower, context);
        if (weekday) return weekday;
        const fullDate = text.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/);
        if (fullDate) return formatQuickDateParts(Number(fullDate[1]), Number(fullDate[2]), Number(fullDate[3]), false, context);
        const monthDay = text.match(/^(\d{1,2})[-/](\d{1,2})$/) || text.match(/^(\d{1,2})月(\d{1,2})日?$/);
        if (monthDay) return formatQuickDateParts(context.now.getFullYear(), Number(monthDay[1]), Number(monthDay[2]), true, context);
        return '';
    }

    function parseQuickAddWeekdayToken(text, context) {
        const match = String(text || '').trim().match(/^(?:(本|这|上上|下下|上|下))?(?:周|星期|礼拜)([一二三四五六日天1-7])$/);
        if (!match) return '';
        const day = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 日: 0, 天: 0,
            1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 0 }[match[2]];
        const today = context.now.getDay();
        let offset;
        if (!match[1]) {
            offset = (day - today + 7) % 7;
        } else {
            const weeks = { 本: 0, 这: 0, 上: -1, 下: 1, 上上: -2, 下下: 2 }[match[1]];
            offset = (day + 6) % 7 - (today + 6) % 7 + weeks * 7;
        }
        return formatDateWithOffset(offset, context);
    }

    function parseQuickAddTimeToken(token) {
        const text = String(token || '').trim().replace('：', ':');
        const colonTime = text.match(/^([01]?\d|2[0-3]):([0-5]\d)$/);
        if (colonTime) return `${String(Number(colonTime[1])).padStart(2, '0')}:${colonTime[2]}`;
        const chineseTime = text.match(/^([01]?\d|2[0-3])(?:点|时)([0-5]?\d)?分?$/);
        if (chineseTime) return `${String(Number(chineseTime[1])).padStart(2, '0')}:${String(Number(chineseTime[2] || 0)).padStart(2, '0')}`;
        return '';
    }

    function formatDateWithOffset(days, context) {
        const date = new Date(context.now);
        date.setDate(date.getDate() + days);
        return context.dates.formatDateInputValue(date);
    }

    function formatQuickDateParts(year, month, day, rollPastDates, context) {
        const todayKey = rollPastDates ? context.dates.formatDateInputValue(context.now) : '';
        const lastYear = rollPastDates ? Math.min(9999, year + 8) : year;
        for (let candidateYear = year; candidateYear <= lastYear; candidateYear++) {
            const candidate = context.dates.normalizeDueDateValue(`${String(candidateYear).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`);
            if (candidate && (!rollPastDates || candidate >= todayKey)) return candidate;
        }
        return '';
    }

    function normalizeSearchQuery(value) {
        return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
    }

    function parseSearchQuery(query, names) {
        const parsed = { terms: [], projects: [], tags: [], exactProjects: [], exactTags: [], statuses: [], due: [], completed: [] };
        const tokens = tokenizeTaskInput(query);
        for (let index = 0; index < tokens.length; index += 1) {
            const token = tokens[index];
            if (token.startsWith('#') && token.length > 1) {
                const value = readTaskInputValue(tokens, index, '#', names.tags);
                if (value) {
                    parsed[value.exact ? 'exactTags' : 'tags'].push(value.value.toLowerCase());
                    index += value.consumed - 1;
                    continue;
                }
            }
            const separatorIndex = token.indexOf(':');
            if (separatorIndex <= 0 || separatorIndex === token.length - 1) {
                parsed.terms.push(token);
                continue;
            }
            const field = token.slice(0, separatorIndex);
            const isProject = field === 'project' || field === 'p';
            const isTag = field === 'tag' || field === 'tags';
            const value = readTaskInputValue(tokens, index, token.slice(0, separatorIndex + 1),
                isProject ? names.projects : isTag ? names.tags : []);
            if (!value) { parsed.terms.push(token); continue; }
            if (isProject) parsed[value.exact ? 'exactProjects' : 'projects'].push(value.value.toLowerCase());
            else if (isTag) parsed[value.exact ? 'exactTags' : 'tags'].push(value.value.toLowerCase());
            else if (field === 'status' || field === 'state') parsed.statuses.push(value.value);
            else if (field === 'due' || field === 'date') parsed.due.push(value.value);
            else if (field === 'completed') parsed.completed.push(value.value);
            else parsed.terms.push(token);
            if (isProject || isTag) index += value.consumed - 1;
        }
        return parsed;
    }

    function matchesSearchAlias(value, aliases) {
        return aliases.includes(value);
    }

    function renameProjectQuery(query, previous, next, names) {
        const source = String(query || '');
        const tokens = tokenizeTaskInput(source);
        let offset = 0;
        const spans = tokens.map(token => {
            const start = source.indexOf(token, offset);
            offset = start + token.length;
            return { start, end: offset };
        });
        const replacements = [];
        for (let index = 0; index < tokens.length; index += 1) {
            const prefix = tokens[index].match(/^(?:project|p):/i)?.[0];
            if (!prefix) continue;
            const parsed = readTaskInputValue(tokens, index, prefix, names);
            if (!parsed) continue;
            const value = parsed.value.toLowerCase();
            if (value === previous.toLowerCase() && (parsed.exact || !matchesSearchAlias(value, ['none', 'unassigned', '未分组']))) {
                const unquoted = !parsed.exact && !/[\s"\\]/.test(next)
                    && !matchesSearchAlias(next.toLowerCase(), ['none', 'unassigned', '未分组']);
                replacements.push({ start: spans[index].start, end: spans[index + parsed.consumed - 1].end,
                    value: `${prefix}${unquoted ? next : JSON.stringify(next)}` });
            }
            index += parsed.consumed - 1;
        }
        return replacements.reverse().reduce((value, replacement) => value.slice(0, replacement.start)
            + replacement.value + value.slice(replacement.end), source);
    }

    namespace.TaskInput = Object.freeze({
        normalizeTaskProject, normalizeTaskTags, parseTagsInput, formatTagsInput,
        tokenizeTaskInput, readTaskInputValue, normalizeSearchQuery, matchesSearchAlias,
        parseQuickAddInput, parseSearchQuery, renameProjectQuery
    });
})(window.TaskTracer = window.TaskTracer || {});
