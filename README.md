<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer icon">
</p>

<h1 align="center">Task Tracer</h1>

<p align="center"><strong>A local-first, offline-ready PWA for deadline-driven personal task management.</strong></p>

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

Task Tracer is a single-user task manager built around due dates, local reminders, recurring work, and long-term personal task history. It is intentionally browser-local: task data stays in IndexedDB, and the app loads offline after the first visit.

It works well for study plans, personal operations, project follow-ups, routine reviews, and any task list where deadlines, status clarity, and safe local data handling matter more than team collaboration or cloud sync.

## Feature Map

| Area | Included |
| --- | --- |
| Task lifecycle | Create, edit, complete, mark incomplete, delete, archive, restore from archive, clear completed tasks, and archive completed tasks. |
| Deadline handling | Local due date and time, no-deadline tasks, exact due instants, timezone-aware legacy normalization, live countdowns, progress bars, and status colors. |
| Status model | Safe, warning, urgent, overdue, completed, archived, and no-deadline states are shown with distinct labels and visual treatment. |
| Subtasks | Add subtasks, edit subtask text inline, complete subtasks independently, and track subtask progress on the parent task. |
| Recurring tasks | Daily, weekly, monthly, and custom-day recurrence; completing one occurrence creates the next one while preserving the completed record. |
| Reminders | Reminder offset, repeat reminder interval, snooze, missed-reminder catch-up, notification permission handling, and clear background-delivery messaging. |
| Projects and tags | One primary project per task, multiple tags per task, project-scoped views, tag chips, and project/tag-aware search. |
| Search and filters | Search task names, descriptions, projects, and tags; filter by all, active, completed, archived, overdue, and no deadline. |
| Sorting and ordering | Smart sorting, newest-created order, due-date order, alphabetical order, manual drag-and-drop order, touch reorder, and keyboard reorder. |
| Views | List, calendar, timeline, and statistics views for daily work, date review, chronological scanning, and personal productivity feedback. |
| Data portability | JSON export, import preview, duplicate-name reporting, replace mode, merge mode, and versioned local backup downloads. |
| PWA behavior | Installable app experience, offline loading, app icons, and browser-friendly behavior. |
| Comfort and polish | Light/dark themes, responsive layout, reduced-motion support, smooth state transitions, and bilingual UI. |
| Accessibility | Keyboard navigation, visible focus, dialog focus trap, screen-reader labels, live status announcements, and automated axe checks. |

## Core Workflow

Task Tracer starts from a simple list, then adds structure only where it helps:

1. Add tasks with a name, optional description, due date and time, reminders, repeat rule, project, tags, and subtasks.
2. Work from the list view for everyday actions such as complete, snooze, edit, archive, delete, and manual reorder.
3. Switch to calendar or timeline view when due-date distribution matters more than list order.
4. Use statistics to review completion rate, active overdue rate, archived volume, today's completions, and completion streak.
5. Export or back up data before clearing browser data, switching devices, or testing imports.

## Projects, Tags, and Search

Projects are the main grouping layer. A task belongs to one project, such as `Work`, `Personal`, or a named product. The project selector narrows the task list, and the all-project smart view keeps tasks grouped by project.

Tags are flexible secondary labels. A task can have multiple tags, such as `design`, `exam`, or `follow-up`. Tags are useful when related work crosses project boundaries.

Search matches task names, descriptions, project names, and tags. Projects organize the primary task space, while tags add extra searchable meaning across project groups.

## Views

| View | Purpose |
| --- | --- |
| List | Daily task execution with full actions, subtasks, status chips, reminders, archive controls, and manual ordering. |
| Calendar | Monthly due-date review with previous/next month, previous/next year, today jump, visible day layout, date details, and no-deadline grouping. |
| Timeline | Chronological grouping for scanning upcoming or historical workload by date. |
| Statistics | Completion rate, active overdue rate, archived count, today's completions, current streak, and recent completion trend. |

## Import, Export, and Backup

Task Tracer keeps the data controls separate so each action has a clear purpose.

| Action | Purpose |
| --- | --- |
| Export | Download the current task set as JSON for transfer, manual inspection, or storage. |
| Import | Read a JSON file, show a preview, report imported task count, duplicate names, current-data impact, and then replace or merge after confirmation. |
| Backup | Download a versioned snapshot with schema notes, local due dates, exact reminder instants, repeat rules, completion dates, and archive state. |

Backups also record the latest backup time locally, so the app can remind you when active task data has not been backed up recently.

## Reminder Model

Browser notifications are available when the browser supports them and the user grants permission. Task Tracer can schedule reminder checks while the app is open, repeat reminders at a chosen interval, snooze a reminder, and surface missed reminders when the app runs again.

Browser-based reminders are not a guaranteed system alarm service. Delivery can depend on browser policy, operating system behavior, battery settings, tab lifecycle, and whether the app is opened or woken by the browser.

## Data and Privacy

Task data is stored in the current browser's IndexedDB. Task Tracer does not require an account and does not upload task content to a server by default.

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
