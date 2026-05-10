<p align="center">
  <img src="./fav/android-chrome-192x192.png" width="88" height="88" alt="Task Tracer icon">
</p>

<h1 align="center">Task Tracer</h1>

<p align="center">Deadline-based task management in a compact offline-ready PWA.</p>

<p align="center">
  <a href="https://todo.muquew.com/">Live Demo</a> · <a href="./README_zh_cn.md">中文说明</a>
</p>

<p align="center">
  <a href="https://todo.muquew.com/"><img alt="Live demo" src="https://img.shields.io/badge/Live-Demo-2563eb?style=flat-square"></a>
  <img alt="PWA" src="https://img.shields.io/badge/PWA-Offline-059669?style=flat-square">
  <img alt="IndexedDB" src="https://img.shields.io/badge/Data-IndexedDB-0f766e?style=flat-square">
  <img alt="Internationalization" src="https://img.shields.io/badge/i18n-ZH%20%7C%20EN-7c3aed?style=flat-square">
  <img alt="Accessibility" src="https://img.shields.io/badge/A11y-Keyboard-d97706?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/License-Personal%20Use-475569?style=flat-square">
</p>

Task Tracer is a deadline-based task management PWA for personal planning, study routines, and recurring work. It keeps task data in the browser, works offline after loading, and focuses on clear deadline status, reminders, project grouping, tags, subtasks, archiving, import safety, and local backup.

## Features

- Deadline tracking: safe, warning, urgent, overdue, completed, and no-deadline states.
- Task management: add, edit, delete, complete, restore, archive, and recover tasks.
- Subtasks: break a task into smaller steps and track subtask progress.
- Reminders: choose reminder timing, repeat reminders, snooze a reminder, and see missed reminders when the app wakes up.
- Projects and tags: use one project as the main grouping for a task, and use multiple tags for cross-cutting labels.
- Search and filters: search task names, descriptions, projects, and tags; switch between active, completed, archived, overdue, and no-deadline views.
- Sorting: smart sorting, newest created, due date, alphabetical order, and manual drag-and-drop order.
- Import preview: review task count, duplicate names, and replacement impact before imported data replaces current tasks.
- Local data: IndexedDB persistence with JSON import, export, and versioned backup downloads.
- PWA support: app shell caching, offline loading, and installable browser experience.
- Themes and languages: light/dark themes, Simplified Chinese, and English.
- Accessibility: keyboard-friendly controls, focus management, screen-reader labels, and live status announcements.

## Projects, Tags, and Search

Projects are the primary grouping layer. A task belongs to one project, such as Work, Personal, or a named product. The project selector narrows the task list, and the all-project smart view groups tasks by project.

Tags are flexible secondary labels. A task can have multiple tags, such as `design`, `urgent`, or `follow-up`. Tags are useful when related work crosses project boundaries.

Search currently matches task names, descriptions, project names, and tags. In other words, projects help organize the list, while tags add extra searchable meaning across those project groups.

## Data Files

- Export: downloads the current task data as a JSON file for transfer, inspection, or manual storage.
- Import: reads a JSON file, shows a preview, then replaces current task data after confirmation.
- Backup: downloads a versioned local snapshot, records the latest backup time, and includes notes about the backup schema.

## Screenshots

| Task List | Add Task |
| --- | --- |
| <img src="./screenshots/task-list-en.png" alt="Task Tracer task list"> | <img src="./screenshots/add-task-en.png" alt="Task Tracer add task dialog"> |

## Usage

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

## Data and Privacy

Task Tracer stores task data in the current browser's IndexedDB. It does not require an account and does not upload task content to a server by default. Before changing browsers, clearing site data, or moving devices, use Back Up Now or Export to download a JSON file.

Browser reminders depend on the page being open or woken by the browser. Task Tracer can catch missed reminders when the app runs again, but it cannot guarantee system-level background delivery on every platform.

## Technical Notes

- Main app: `index.html`
- Language resources: `resources/zh-CN.json`, `resources/en.json`
- PWA Service Worker: `sw.js`
- Deployment security headers: `vercel.json`
- Validation: static consistency checks and Playwright browser smoke tests

## License

Task Tracer is licensed for personal non-commercial use. Personal task management, learning, research, and evaluation are allowed. Commercial use, paid distribution, or integration into commercial services requires prior written permission from `muquew`.

See [LICENSE](./LICENSE) for the full terms.
