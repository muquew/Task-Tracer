<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer icon">
</p>

<h1 align="center">Task Tracer</h1>

<p align="center"><strong>A local-first task workspace for capture, planning, routines, reminders, and personal review.</strong></p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer">Live Demo</a> ·
  <a href="./README_zh_cn.md">中文说明</a>
</p>

<p align="center">
  <a href="https://todo.muquew.com/" rel="noopener noreferrer"><img alt="Live demo" src="https://img.shields.io/badge/Live-Demo-2563eb?style=flat-square"></a>
  <img alt="Single HTML app" src="https://img.shields.io/badge/App-Single%20HTML-0f766e?style=flat-square">
  <img alt="Installable PWA" src="https://img.shields.io/badge/PWA-Installable%20%7C%20Offline-059669?style=flat-square">
  <img alt="Chinese and English" src="https://img.shields.io/badge/i18n-ZH%20%7C%20EN-7c3aed?style=flat-square">
  <img alt="Accessible" src="https://img.shields.io/badge/A11y-Keyboard%20%7C%20Screen%20Reader-d97706?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/License-Personal%20Use-475569?style=flat-square">
</p>

Task Tracer is a personal task manager that runs in the browser and keeps task data on the current device/browser profile. It is made for people who want a capable daily workspace without accounts, servers, or cloud sync as a requirement.

PWA means Progressive Web App: when the browser supports it, Task Tracer can be installed, opened from the operating system like an app, and loaded offline after the app shell has been cached.

## What It Helps With

| Need | Built-in support |
| --- | --- |
| Capture tasks quickly | Full task dialog, quick add parsing, URL capture, install shortcut capture, share target capture, Inbox default, descriptions, subtasks, projects, tags, due date/time, and no-date tasks. |
| Keep work organized | Project grouping, multi-tag labels, saved smart views, manual ordering, archives, and batch actions. |
| Plan from different angles | List, calendar, timeline, and statistics views. |
| Work through today | Today Plan, task actions, snooze, skip repeat occurrence, complete/archive/delete, and undo. |
| Manage routines | Daily, weekly, selected weekdays, monthly, last-day-of-month, and custom-day recurrence; repeat rules can be paused. |
| Notice what matters | Reminder offsets, repeat reminders, snooze, missed-reminder notices, and browser limitation guidance. |
| Review progress | Completion rate, active overdue rate, archive count, today completions, completion streak, and recent completion trend. |
| Protect local data | Export/backup, backup health, import preview, merge/replace conflict handling, checksum checks, pre-replace snapshots, and emergency backup when storage is blocked. |

## Screenshots

| Task List | Add Task |
| --- | --- |
| <img src="./screenshots/task-list-en.png" alt="Task Tracer task list"> | <img src="./screenshots/add-task-en.png" alt="Task Tracer add task dialog"> |

## Fast Input

Quick add turns compact text into structured task fields:

```text
tomorrow 20:00 Review English #study /Personal
```

This creates a task named `Review English`, due tomorrow at 20:00, tagged `study`, and assigned to the `Personal` project.

When quick add text does not include a `/project`, the task is saved to `Inbox` so unprocessed ideas have a predictable place to land.

The command palette opens with `Ctrl/Cmd + P`. It can start a new task, focus quick add, switch views, open saved views, enter Today Plan, enter batch actions, undo the latest task change, export/back up data, search, and jump to projects.

Task Tracer also supports direct capture links:

```text
https://todo.muquew.com/?capture=1
https://todo.muquew.com/?add=Buy%20milk
https://todo.muquew.com/?add=Buy%20milk&save=1
```

`capture=1` opens the app focused on quick add. `add=` pre-fills quick add and waits for confirmation. `save=1` saves immediately after the app opens. Capture parameters are removed after processing so refreshing the page does not create duplicates.

Installed PWAs expose a `Quick Capture` shortcut that opens `./?capture=1`. Browsers that support Web Share Target can send shared title, text, and URL to Task Tracer: the title appears in quick add for confirmation, while the shared text and URL are saved into the task description after confirmation.

## Projects, Tags, and Search

Projects are the main grouping layer. A task belongs to one project such as `Inbox`, `Work`, `Personal`, or a named initiative. The project selector narrows the workspace, and the all-project list groups visible tasks by project.

Tags are flexible secondary labels. A task can have multiple tags such as `study`, `design`, or `follow-up`, which makes related work searchable across projects.

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

Saved smart views store the current search, project filter, status filter, sort mode, and view. They are useful for repeatable contexts such as overdue work, weekly study, or a project-specific calendar.

## Views

| View | Best for |
| --- | --- |
| List | Daily execution with task actions, subtasks, reminders, status chips, progress bars, archive controls, batch actions, and manual ordering. |
| Calendar | Month planning with a real calendar grid, month/year navigation, today jump, date details, and no-date grouping. |
| Timeline | Chronological scanning across upcoming work and completed history. |
| Statistics | Personal feedback on completion, active overdue tasks, archived history, today completions, streak, and recent trend. |

## Today Plan, Batch Actions, and Undo

Today Plan is a lightweight execution layer. Adding a task to Today Plan does not change its project, tags, due date, archive state, or recurrence rule; it only marks the task as part of today's working set.

Batch Actions mode adds selection controls to the visible list. Selected tasks can be added to Today Plan, marked complete, archived, or deleted together.

Undo restores the task snapshot from before the most recent task-writing operation. It is available from the header undo button, toast action, command palette, and `Ctrl/Cmd + Z` when focus is not inside a text field.

## Recurrence and Reminders

Recurring tasks can repeat daily, weekly, on selected weekdays, monthly, on the last day of the month, or after a custom number of days. A recurring task can be paused, and the current occurrence can be skipped without deleting the rule.

Browser notifications are available when the browser supports them and permission is granted. Task Tracer can check reminders while the app is open, repeat reminders at the chosen interval, snooze a reminder, and show missed reminders when the app runs again.

Browser reminders are not guaranteed system alarms. Delivery can depend on browser policy, operating system behavior, battery settings, tab lifecycle, and whether the app is opened or woken by the browser.

## Import, Export, and Backup

`Export/Backup` downloads the complete task JSON with an export ID, checksum, version notes, and latest-backup status update.

`Import` previews a JSON file before writing it. The preview shows restore checks, task counts, differences, repeated IDs, duplicate names, current-data impact, checksum status, and same-name conflict choices.

Replace import downloads a pre-import snapshot before overwriting existing tasks. If the checksum fails, replace import requires an explicit risk confirmation; merge mode remains available for safer recovery.

If browser storage is blocked or becomes unavailable, Task Tracer enters a storage-unavailable mode. When an in-memory task snapshot still exists, the emergency backup button can download that snapshot before the page is refreshed or closed.

## Install, Offline, and Updates

Use the app menu to install Task Tracer. If the browser does not expose an automatic install prompt, the same entry shows manual steps for desktop Chrome/Edge, Android Chrome, and iOS Safari.

After the app shell is cached, Task Tracer can load offline. When a newer cached version is ready, the app shows an update prompt with a refresh action.

## Accessibility and Languages

Task Tracer includes Chinese and English UI, synchronized document language, keyboard-friendly controls, labelled icon buttons, focus traps for dialogs, live-region announcements, reduced-motion support, and responsive layouts for desktop and mobile.

## Data and Privacy

Task data is stored in the current browser's IndexedDB. Task Tracer does not require an account and does not upload task content to a server by default.

Before changing browsers, clearing site data, reinstalling the app, or moving devices, use `Export/Backup` to download a JSON file.

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
