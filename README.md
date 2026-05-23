<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer icon">
</p>

<h1 align="center">Task Tracer</h1>

<p align="center"><strong>A single-file, local-first PWA for tasks, routines, reminders, and personal review.</strong></p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer">Live Demo</a> ·
  <a href="./README_zh_cn.md">中文说明</a>
</p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer"><img alt="Live demo" src="https://img.shields.io/badge/Live-Demo-2563eb?style=flat-square"></a>
  <img alt="Single file" src="https://img.shields.io/badge/App-Single%20HTML-0f766e?style=flat-square">
  <img alt="PWA" src="https://img.shields.io/badge/PWA-Installable%20%7C%20Offline-059669?style=flat-square">
  <img alt="Languages" src="https://img.shields.io/badge/i18n-ZH%20%7C%20EN-7c3aed?style=flat-square">
  <img alt="Accessibility" src="https://img.shields.io/badge/A11y-Keyboard%20%7C%20Screen%20Reader-d97706?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/License-Personal%20Use-475569?style=flat-square">
</p>

Task Tracer is a personal task workspace that runs in the browser and keeps task data local to the current device/browser profile. It is built for everyday capture, project follow-up, deadline work, recurring routines, local reminders, task archives, and lightweight productivity review without requiring an account or cloud sync.

## Highlights

| Area | What Task Tracer provides |
| --- | --- |
| Capture | Full task dialog, quick add parsing, due date and time, no-date tasks, descriptions, subtasks, projects, and tags. |
| Organization | Project grouping, multi-tag labels, smart search, status filters, saved smart views, manual ordering, and archived history. |
| Planning | List, calendar, timeline, and statistics views with timezone-stable due dates and clear status chips. |
| Execution | Header shortcuts for Today Plan, batch actions, undo, new task, notifications, theme, and the app menu. |
| Routines | Daily, weekly, selected weekdays, monthly, last-day-of-month, and custom interval recurrence. |
| Reminders | Reminder offsets, repeat reminders, snooze, missed-reminder notice, and an explicit browser-delivery limitation note. |
| Review | Completion rate, active overdue rate, archive count, today's completions, completion streak, and recent trend. |
| Data safety | Export/backup, backup health, import preview, merge/replace conflict handling, checksums, pre-replace snapshots, undo, and emergency backup when storage is blocked. |
| Comfort | Responsive layout, light/dark themes, reduced-motion support, keyboard navigation, screen-reader labels, and Chinese/English UI. |

## Everyday Flow

1. Capture a task from the full dialog or with quick add.
2. Use projects for primary grouping and tags for cross-project context.
3. Save repeatable search/filter combinations as smart views.
4. Work from the list view for completion, editing, snoozing, subtasks, archive, batch actions, and manual sorting.
5. Move the current working set into Today Plan and use the header Today button when it is time to focus.
6. Switch to calendar or timeline when date distribution matters more than list order.
7. Check statistics for current workload, overdue pressure, archived history, and recent completion momentum.
8. Export/back up before clearing browser data, changing devices, testing imports, or reinstalling the app.

## Quick Add and Command Palette

Quick add turns compact text into structured task fields:

```text
tomorrow 20:00 Review English #study /Personal
```

This creates `Review English`, due tomorrow at 20:00, tagged `study`, and assigned to the `Personal` project.

The command palette opens with `Ctrl/Cmd + P`. It can start a new task, focus quick add, switch views, open saved views, enter Today Plan, enter batch actions, undo the latest task change, export/back up data, search, and jump to projects.

## Projects, Tags, and Search

Projects are the main grouping layer. A task can belong to one project, such as `Work`, `Personal`, or a named initiative. The project selector narrows the workspace, and the all-project list groups tasks by project.

Tags are flexible secondary labels. A task can have multiple tags such as `study`, `design`, or `follow-up`, making it easier to connect related work across projects.

Search matches task names, descriptions, projects, tags, and subtask text. Scoped search can be mixed with normal keywords:

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

Saved smart views store the current search, project filter, status filter, sort mode, and view. They are useful for repeatable scopes such as overdue work, weekly study, or a project-specific calendar.

## Views

| View | Best for |
| --- | --- |
| List | Daily execution with full task actions, subtasks, reminders, status labels, progress bars, archive controls, and manual ordering. |
| Calendar | Month-based planning with a real calendar grid, month/year navigation, today jump, date details, and no-date grouping. |
| Timeline | Chronological scanning of upcoming or historical tasks by date. |
| Statistics | Personal feedback on completion, active overdue tasks, archive volume, today's completions, streak, and recent trend. |

## Today Plan, Batch Actions, and Undo

Today Plan is a lightweight execution layer. Adding a task to Today Plan does not change its project, tags, due date, archive state, or recurrence rule; it only marks the task as part of today's working set.

Batch Actions mode adds selection checkboxes to the visible list. Selected tasks can be added to Today Plan, marked complete, archived, or deleted together.

Undo restores the task snapshot from before the most recent task-writing operation. It is available from the header undo button, the toast action, the command palette, and `Ctrl/Cmd + Z` when focus is not inside a text field.

## Recurrence and Reminders

Recurring tasks can repeat daily, weekly, on selected weekdays, monthly, on the last day of the month, or after a custom number of days. A recurring task can be paused, and the current occurrence can be skipped without deleting the rule.

Browser notifications are available when the browser supports them and permission is granted. Task Tracer can check reminders while the app is open, repeat reminders at the chosen interval, snooze a reminder, and show missed reminders when the app runs again.

Browser reminders are not a guaranteed system alarm service. Delivery can depend on browser policy, operating system behavior, battery settings, tab lifecycle, and whether the app is opened or woken by the browser.

## Import, Export, and Backup

| Action | Purpose |
| --- | --- |
| Export/Backup | Download complete task JSON with an export ID, checksum, version notes, and latest-backup status update. |
| Import | Preview a JSON file before writing it, including restore checks, task counts, differences, repeated IDs, duplicate names, current-data impact, and same-name conflict choices. |

The restore checklist identifies Task Tracer backup metadata, template compatibility, checksum status, task payload, repeated IDs, local name matches, and the impact of replacing current data. Replace import downloads a pre-import snapshot before overwriting existing tasks. If the checksum fails, replace import requires an explicit risk confirmation; merge mode remains available for safer recovery.

Backup health appears in the app menu and indicates whether data was backed up today, recently, or should be backed up again.

## Install, Offline, and Updates

Task Tracer is a PWA: when the browser supports the standard, it can be installed and opened like an app. The app menu includes an install entry. If the browser does not expose an automatic prompt, the same entry shows manual installation steps for desktop Chrome/Edge, Android Chrome, and iOS Safari.

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
