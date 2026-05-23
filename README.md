<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer icon">
</p>

<h1 align="center">Task Tracer</h1>

<p align="center"><strong>A single-file, local-first PWA for personal tasks, routines, reminders, and review.</strong></p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer">Live Demo</a> · <a href="./README_zh_cn.md">中文说明</a>
</p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer"><img alt="Live demo" src="https://img.shields.io/badge/Live-Demo-2563eb?style=flat-square"></a>
  <img alt="Single file" src="https://img.shields.io/badge/App-Single%20HTML-0f766e?style=flat-square">
  <img alt="PWA" src="https://img.shields.io/badge/PWA-Installable%20%7C%20Offline-059669?style=flat-square">
  <img alt="Languages" src="https://img.shields.io/badge/i18n-ZH%20%7C%20EN-7c3aed?style=flat-square">
  <img alt="Accessibility" src="https://img.shields.io/badge/A11y-Keyboard%20%7C%20Screen%20Reader-d97706?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/License-Personal%20Use-475569?style=flat-square">
</p>

Task Tracer is a personal task workspace that runs as an installable web app while keeping task data in the current browser. It is designed for everyday task capture, project follow-up, recurring routines, reminders, archives, and personal productivity review without requiring an account or cloud sync.

It fits study plans, personal operations, solo projects, recurring reviews, deadline work, and any task system where local control, clear status, and reliable data export matter.

## What You Can Do

| Need | Task Tracer supports |
| --- | --- |
| Capture tasks quickly | Full task form, quick add parsing, due date/time, no-date tasks, subtasks, projects, and tags. |
| Organize a growing list | Project grouping, multi-tag labeling, scoped filters, smart search, saved smart views, archived history, and manual order. |
| Plan by time | List, calendar, timeline, live countdowns, status chips, progress bars, and timezone-stable dates. |
| Execute today's work | Add tasks to Today Plan, enter a focused execution mode, and remove tasks from the plan without changing the task itself. |
| Work in batches | Select visible tasks and complete, archive, delete, or add them to Today Plan together. |
| Handle routines | Daily, weekly, selected weekdays, monthly, last-day-of-month, and custom interval recurrence. |
| Stay aware | Browser reminders, reminder offsets, repeat reminders, snooze, missed-reminder notice, and clear delivery limits. |
| Review progress | Completion rate, active overdue rate, archived count, today's completions, streak, and recent trend. |
| Protect data | Undo recent task changes, export/backup, import preview, merge/replace conflict handling, backup health, and emergency backup when storage is blocked. |
| Use it comfortably | Responsive layout, light/dark themes, reduced-motion support, keyboard navigation, screen-reader labels, and Chinese/English UI. |

## Everyday Workflow

1. Add a task from the full dialog, or type a compact quick-add entry.
2. Save frequent search and filter combinations as smart views when a list becomes part of your routine.
3. Work from the list view for completion, edit, snooze, archive, delete, subtasks, batch actions, and manual ordering.
4. Add selected tasks to Today Plan and use the header Today Plan button when it is time to focus.
5. Switch to calendar or timeline when the date distribution matters more than list order.
6. Use statistics to review active workload, completion behavior, archived history, and recent momentum.
7. Export/back up before changing browsers, clearing site data, or testing imported files.

## Quick Add

Quick add turns lightweight text into structured task fields.

```text
tomorrow 20:00 Review English #study /Personal
```

This creates a task named `Review English`, due tomorrow at 20:00, tagged `study`, and assigned to the `Personal` project.

The command palette opens with `Ctrl/Cmd + P`. It can start a new task, focus quick add, switch views, open saved views, enter Today Plan, enter batch actions, undo the last task change, export/back up data, search, and jump to projects.

## Projects, Tags, and Search

Projects are the primary grouping layer. Each task belongs to one project such as `Work`, `Personal`, or a named initiative. The project selector narrows the workspace, and the all-project list keeps tasks grouped by project.

Tags are flexible secondary labels. A task can have multiple tags such as `study`, `design`, or `follow-up`. Tags help connect related work across different projects.

Search matches task names, descriptions, projects, tags, and subtask text. Scoped search can be combined with normal keywords:

| Query | Finds |
| --- | --- |
| `project:Work` | Tasks whose project name contains `Work`. |
| `tag:study` or `#study` | Tasks with a matching tag. |
| `status:active` | Active unfinished tasks. |
| `status:completed` | Completed tasks. |
| `status:archived` | Archived tasks. |
| `status:overdue` | Unfinished overdue tasks. |
| `status:no-deadline` | Tasks without a due date. |
| `status:repeat` | Recurring tasks. |
| `due:today` | Tasks due today. |
| `due:tomorrow` | Tasks due tomorrow. |
| `due:week` | Tasks due in the next seven days. |
| `due:2025-05-20` | Tasks due on a specific local date. |
| `due:no-deadline` | Tasks without a due date. |
| `project:Work tag:report` | Tasks matching both scopes. |

For multi-word project or tag names, search by a distinctive part of the name.

Saved smart views store the current search, project, status filter, sort mode, and view. They are useful for repeatable scopes such as `project:Work status:overdue`, `tag:study due:week`, or a project-specific calendar view.

## Today Plan, Batch Actions, and Undo

Today Plan is a lightweight execution layer. The header target button opens it directly. Adding a task to Today Plan does not change its project, tags, due date, archive state, or recurrence rule; it only marks the task as part of today's working set.

Batch Actions mode adds checkboxes to the visible list. Selected tasks can be added to Today Plan, marked complete, archived, or deleted together.

Recent task-writing actions can be undone from the toast action, the app menu, or `Ctrl/Cmd + Z` when focus is not inside a text field. Undo restores the task snapshot from before the operation.

## Views

| View | Best for |
| --- | --- |
| List | Daily execution with full actions, subtasks, status labels, reminders, archive controls, and manual ordering. |
| Calendar | Month-based review with real calendar layout, previous/next month, previous/next year, today jump, date details, and no-date grouping. |
| Timeline | Chronological scanning of upcoming or historical tasks by date. |
| Statistics | Personal feedback on completion, overdue active tasks, archived volume, today's completions, streak, and recent trend. |

## Recurrence and Reminders

Recurring tasks can repeat daily, weekly, on selected weekdays, monthly, on the last day of the month, or after a custom number of days. A recurring task can be paused, and the current occurrence can be skipped without deleting the rule.

Browser notifications are available when the browser supports them and permission is granted. Task Tracer can check reminders while the app is open, repeat reminders at the chosen interval, snooze a reminder, and show missed reminders when the app runs again.

Browser reminders are not a guaranteed system alarm service. Delivery can depend on browser policy, operating system behavior, battery settings, tab lifecycle, and whether the app is opened or woken by the browser.

## Import and Export/Backup

| Action | Purpose |
| --- | --- |
| Export/Backup | Download complete task JSON with an export ID, checksum, version notes, and latest-backup status update. |
| Import | Preview a JSON file before writing it. The preview includes a restore checklist, difference summary, task count, repeated IDs, duplicate names, current-data impact, and same-name conflict choices. |

The restore checklist identifies Task Tracer backup metadata, template compatibility, checksum status, task payload, repeated IDs, local name matches, and the impact of replacing current data. When replace import would overwrite existing tasks, Task Tracer downloads a pre-import snapshot first and waits for a second confirmation. If the checksum fails, replace import also requires an explicit risk confirmation; merge mode remains available for safer recovery.

Backup health appears in the app menu and helps indicate whether data was backed up today, recently, or should be backed up again.

## Install, Offline, and Updates

Task Tracer is a PWA, which means it can behave like an installable app when the browser supports that web standard. The app menu includes an install entry. If the browser does not expose an automatic prompt, the same entry shows manual installation steps for desktop Chrome/Edge, Android Chrome, and iOS Safari.

The app shell can load offline after it has been cached. When a newer cached version is ready, Task Tracer shows an update prompt with a refresh action.

## Data and Privacy

Task data is stored in the current browser's IndexedDB. Task Tracer does not require an account and does not upload task content to a server by default.

If the browser blocks local storage, Task Tracer enters a storage-unavailable mode instead of pretending changes can be saved. When an in-memory task snapshot is still available, download the emergency backup before refreshing or closing the page. After changing browser privacy settings, use Retry to re-check local storage.

Before changing browsers, clearing site data, reinstalling the app, or moving devices, use Export/Backup to download a JSON file.

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
