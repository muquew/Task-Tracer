<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer icon">
</p>

<h1 align="center">Task Tracer</h1>

<p align="center"><strong>A local-first, offline-ready PWA for personal tasks, routines, and reminders.</strong></p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer">Live Demo</a> · <a href="./README_zh_cn.md">中文说明</a>
</p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer"><img alt="Live demo" src="https://img.shields.io/badge/Live-Demo-2563eb?style=flat-square"></a>
  <img alt="PWA" src="https://img.shields.io/badge/PWA-Offline-059669?style=flat-square">
  <img alt="IndexedDB" src="https://img.shields.io/badge/Data-IndexedDB-0f766e?style=flat-square">
  <img alt="Languages" src="https://img.shields.io/badge/i18n-ZH%20%7C%20EN-7c3aed?style=flat-square">
  <img alt="Accessibility" src="https://img.shields.io/badge/A11y-Keyboard%20%7C%20Screen%20Reader-d97706?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/License-Personal%20Use-475569?style=flat-square">
</p>

Task Tracer is a single-user task manager for planning tasks, recurring routines, local reminders, and long-term personal task history. It keeps projects, tags, dates, subtasks, archives, and statistics in one browser-local app.

It works well for study plans, personal operations, project follow-ups, routine reviews, and task lists where ownership, organization, reminders, and clear status matter more than team collaboration or cloud sync.

## Feature Map

| Area | Included |
| --- | --- |
| Task lifecycle | Create, edit, complete, mark incomplete, delete, archive, restore from archive, clear completed tasks, and archive completed tasks. |
| Fast entry | Quick add parses lightweight text such as `tomorrow 20:00 Review English #study /Personal` into title, date, time, tag, and project fields. |
| Dates and deadlines | Optional local date and time, no-date tasks, timezone-stable display, timezone-aware legacy normalization, live countdowns, progress bars, and status colors. |
| Status model | Safe, warning, urgent, overdue, completed, archived, and no-deadline states are shown with distinct labels and visual treatment. |
| Subtasks | Add subtasks, edit subtask text inline, complete subtasks independently, and track subtask progress on the parent task. |
| Recurring tasks | Daily, weekly, selected weekdays, monthly, last-day-of-month, and custom-day recurrence; skip the current occurrence or pause recurrence without losing the task. |
| Reminders | Reminder offset, repeat reminder interval, snooze, missed-reminder catch-up, notification permission handling, and clear background-delivery messaging. |
| Projects and tags | One primary project per task, multiple tags per task, project-scoped views, tag chips, and project/tag-aware search. |
| Search and filters | Search task names, descriptions, projects, tags, and subtasks; use scoped search syntax for project, tag, status, and due-date queries. |
| Sorting and ordering | Smart sorting, newest-created order, due-date order, alphabetical order, manual drag-and-drop order, touch reorder, and keyboard reorder. |
| Views | List, calendar, timeline, and statistics views for daily work, date review, chronological scanning, and personal productivity feedback. |
| Data portability | JSON export, import preview, duplicate-name and duplicate-ID checks, same-name conflict choices, replace mode, merge mode, versioned local backups, and backup health status. |
| Storage safety | Startup IndexedDB write probe, privacy-mode storage blocking detection, protected storage-unavailable mode, emergency backup from the current memory snapshot, and retry after browser settings change. |
| PWA behavior | Menu-based install entry, manual install guidance, offline loading, app icons, and update-ready refresh prompts. |
| Comfort and polish | Light/dark themes, responsive layout, reduced-motion support, smooth state transitions, and bilingual UI. |
| Accessibility | Keyboard navigation, visible focus, dialog focus trap, screen-reader labels, live status announcements, and automated axe checks. |
| Command palette | `Ctrl/Cmd + P` opens commands for new tasks, quick add, search, view switching, export, backup, and project switching. |

## Core Workflow

Task Tracer starts from a simple list, then adds structure only where it helps:

1. Add tasks from the full form, or use quick add for compact entries with date, time, `#tag`, and `/project` tokens.
2. Work from the list view for everyday actions such as complete, snooze, edit, archive, delete, and manual reorder.
3. Switch to calendar or timeline view when date distribution matters more than list order.
4. Use statistics to review completion rate, active overdue rate, archived volume, today's completions, and completion streak.
5. Use the backup health status before clearing browser data, switching devices, or testing imports.

## Fast Entry and Commands

Quick add accepts compact task text. For example, `tomorrow 20:00 Review English #study /Personal` creates a task named `Review English`, due tomorrow at 20:00, tagged `study`, and assigned to `Personal`.

The command palette opens with `Ctrl/Cmd + P`. Type a command, view name, or project name, then press Enter to run it.

## Projects, Tags, and Search

Projects are the main grouping layer. A task belongs to one project, such as `Work`, `Personal`, or a named product. The project selector narrows the task list, and the all-project smart view keeps tasks grouped by project.

Tags are flexible secondary labels. A task can have multiple tags, such as `design`, `exam`, or `follow-up`. Tags are useful when related work crosses project boundaries.

Search matches task names, descriptions, project names, tags, and subtask text. Projects organize the primary task space, while tags add extra searchable meaning across project groups.

Scoped search can be typed directly into the search box and combined with normal keywords:

| Query | Finds |
| --- | --- |
| `project:Work` | Tasks whose project name contains `Work`. |
| `tag:study` or `#study` | Tasks with a matching tag. |
| `status:active` | Active, unfinished tasks. |
| `status:completed` | Completed tasks. |
| `status:archived` | Archived tasks, even when the main filter is set to active. |
| `status:overdue` | Unfinished tasks that are already overdue. |
| `status:no-deadline` | Tasks without a due date. |
| `status:repeat` | Recurring tasks. |
| `due:today` | Tasks due today. |
| `due:tomorrow` | Tasks due tomorrow. |
| `due:week` | Tasks due in the next seven days. |
| `due:2025-05-20` | Tasks due on a specific local date. |
| `due:no-deadline` | Tasks without a due date. |
| `project:Work tag:report` | Tasks matching both scopes. |

Search values are space-separated. For multi-word project or tag names, use a distinctive part of the name, such as `project:Work` instead of `project:Work Plan`.

## Views

| View | Purpose |
| --- | --- |
| List | Daily task execution with full actions, subtasks, status chips, reminders, archive controls, and manual ordering. |
| Calendar | Monthly date review with previous/next month, previous/next year, today jump, visible day layout, date details, and no-date grouping. |
| Timeline | Chronological grouping for scanning upcoming or historical workload by date. |
| Statistics | Completion rate, active overdue rate, archived count, today's completions, current streak, and recent completion trend. |

## Import, Export, and Backup

Task Tracer keeps the data controls separate so each action has a clear purpose.

| Action | Purpose |
| --- | --- |
| Export | Download the current task set as JSON for transfer, manual inspection, or storage. |
| Import | Read a JSON file, show a preview, report imported task count, duplicate names, repeated task IDs, and current-data impact, then replace, merge, keep both, skip, or replace same-name local tasks after confirmation. |
| Backup | Download a versioned snapshot with schema notes, local dates, reminder timing, repeat rules, completion dates, and archive state. The menu also shows whether the latest backup is healthy or due. |

Backups record the latest backup time locally. When task data exists, Task Tracer can show whether data was backed up today, backed up recently, or should be backed up again.

## Install and Updates

Task Tracer can be installed from the app menu when the browser exposes an install prompt. If the browser does not provide an automatic prompt, the same menu entry shows manual installation steps for desktop Chrome/Edge, Android Chrome, and iOS Safari.

When a newer offline app version is ready, Task Tracer shows an update prompt with a refresh action so the installed app can move to the latest version without guessing whether the cache has changed.

## Reminder Model

Browser notifications are available when the browser supports them and the user grants permission. Task Tracer can schedule reminder checks while the app is open, repeat reminders at a chosen interval, snooze a reminder, and surface missed reminders when the app runs again.

Browser-based reminders are not a guaranteed system alarm service. Delivery can depend on browser policy, operating system behavior, battery settings, tab lifecycle, and whether the app is opened or woken by the browser.

## Data and Privacy

Task data is stored in the current browser's IndexedDB. Task Tracer does not require an account and does not upload task content to a server by default.

If the browser blocks local storage, Task Tracer stops task-writing actions and shows a storage-unavailable state instead of pretending changes can be saved. When an in-memory task snapshot is still available, download the emergency backup before refreshing or closing the page. After changing privacy settings, use Retry to re-check local storage.

Before changing browsers, clearing site data, reinstalling the app, or moving devices, use Back Up Now or Export to download a JSON file.

## Screenshots

| Task List | Add Task |
| --- | --- |
| <img src="./screenshots/task-list-en.png" alt="Task Tracer task list"> | <img src="./screenshots/add-task-en.png" alt="Task Tracer add task dialog"> |

## Run

Use the hosted app:

```text
https://todo.muquew.com/
```

Or run it locally:

```bash
git clone https://github.com/muquew/Task-Tracer.git
cd Task-Tracer
python3 -m http.server 8080
```

Then open:

```text
http://127.0.0.1:8080/
```

## License

Task Tracer is licensed for personal non-commercial use. Personal task management, learning, research, and evaluation are allowed. Commercial use, paid distribution, or integration into commercial services requires prior written permission from `muquew`.

See [LICENSE](./LICENSE) for the full terms.
