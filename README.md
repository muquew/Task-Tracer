# Task Tracer

A local-first task workspace for capturing work, planning your day and reviewing progress. No account required.

[Open app](https://todo.muquew.com/) · [Download](https://todo.muquew.com/downloads/task-tracer-5.2.0.zip) · [Releases](https://github.com/muquew/Task-Tracer/releases) · [简体中文](README_zh_cn.md)

| Workspace | Task editor |
| --- | --- |
| ![Today workspace](https://todo.muquew.com/screenshots/task-list-en.png) | ![Task editor](https://todo.muquew.com/screenshots/add-task-en.png) |

## Features

- **Today:** choose existing tasks, add or remove them from today's plan, then return to Today and finish work. Unfinished earlier plans remain available.
- **Tasks:** list, calendar and timeline with search, reusable tags, saved views, batch actions and archives. Open a task directly from its title.
- **Projects:** browse workloads and upcoming tasks, search projects and rename them with Undo.
- **Review:** start with completion activity over the last seven days. Open a total or day bar to inspect matching tasks, then return to the same review.
- **Capture:** quick text entry, descriptions, subtasks, due dates, reminders and recurring tasks.
- **Back up:** JSON export, import previews, merge, recovery history and CSV reports.
- **Personalize:** four themes, light/dark appearance, Chinese and English, keyboard controls and responsive layouts.
- **Work offline:** browser-local storage and optional PWA installation.

## Get started

1. Choose **Add task** in the top bar. The adjacent arrow opens Quick capture, for example `tomorrow 20:00 Read #study /Personal`.
2. Plan in **Today**, organize in **Tasks** and **Projects**, and check progress in **Review**.
3. Open **Settings & data** at the bottom of the sidebar for appearance, backups, reminders, installation and updates.

Quick capture accepts dates, times, `#tags` and `/projects`. Reuse existing names with spaces, or quote a new name: `Read /"Personal learning" #"Deep work"`. In task search, use `project:"Personal learning" tag:"Deep work"` to find those exact names; ordinary words still search across task text.

Search completed work with `completed:week` for the last seven local calendar days, including today, or `completed:2026-11-17` for one day. These conditions also include completed archive records; explicit status and project filters still apply.

## Back up and restore

- Tasks stay in the current site's browser storage; there is no account, server backup, automatic cross-device sync or shared workspace. Another browser profile, domain or port has separate data.
- Under **Settings & data → Backups & transfer**, export **task JSON** and a separate **saved-views JSON**. Keep downloaded copies outside the browser before clearing site data, changing devices or downgrading.
- Task JSON excludes saved views, appearance preferences and recovery history. CSV is a report and cannot restore tasks.
- To restore, inspect the import preview and choose merge or replace. Export the current tasks before replacing them; import saved views separately.
- Local recovery history shares browser storage. Clearing site data, private browsing sessions ending or browser storage cleanup can remove it along with your tasks. Confirm your downloaded files exist; drafts and recovery history do not replace an external backup.

## Common questions

- **Update the app:** open **Settings & data → Help & about → Check for updates**. Save pending work, wait until the update is ready, then refresh and close older app windows.
- **Missing tasks:** check project, search, status and archive filters, then confirm the browser profile and site address.
- **Cannot save:** copy important text or download the available emergency backup/draft before adjusting storage permissions or retrying. Unsaved forms and Quick capture may be lost on refresh; draft files are not task backups.
- **Offline and installation:** visit online first and let caching finish. After browser storage is cleared, reconnect to cache the app again. Installation depends on browser/OS support.
- **Reminders:** check app settings and browser permissions. Delivery after closing the app is not guaranteed.

## Run locally or deploy

Download and extract the complete archive. Run this command **inside the extracted app directory**. The portable app needs no Node.js packages, build or backend:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

Open [localhost:8080](http://127.0.0.1:8080/). Serve through HTTP rather than opening `index.html` as a file. On Windows, use `py -3 -m http.server 8080 --bind 127.0.0.1` if `python3` is unavailable. Stop the server with Ctrl+C.

- For hosting, deploy the complete app to a dedicated HTTPS origin. On Vercel, retain `vercel.json` so its security headers are applied.
- Keep the service worker, language files and icons together. A different domain or port has separate browser storage; transfer tasks with JSON backups.
- For downloaded releases, compare the ZIP against its accompanying SHA-256 file before use.

## Source layout and development

Application source is in `src/`, public assets in `public/`, development tools in `scripts/`, and verification in `tests/`. The deployable site is generated into `dist/site`; serve that directory rather than the repository root.

For a source checkout, run `npm run dev` with Node.js 22+ and Python 3.12+. See the [development guide](https://github.com/muquew/Task-Tracer/blob/main/CONTRIBUTING.md) for setup and commands, and [architecture](https://github.com/muquew/Task-Tracer/blob/main/docs/architecture.md) for module responsibilities and deployment boundaries.

## Feedback and license

- [Report a bug or suggest a feature](https://github.com/muquew/Task-Tracer/issues/new/choose): include the app version, browser/OS and steps to reproduce. Diagnostic downloads are available under **Help & about**; review them before sharing and never post personal backups or drafts.
- Report vulnerabilities privately using [Security reporting](https://github.com/muquew/Task-Tracer/blob/main/SECURITY.md).
- [LICENSE](LICENSE) permits personal non-commercial use. Commercial use requires prior written permission from **muquew**. Preserve [third-party notices](THIRD_PARTY_NOTICES.md) when redistributing permitted copies.
