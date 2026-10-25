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

Release status, supported environments, verified artifacts and known limitations are collected in the [stable delivery guide](./docs/stable-delivery.md). The current published application is 4.15.0; 4.15.1 is undergoing complete delivery acceptance.

## What It Helps With

| Need | Built-in support |
| --- | --- |
| Capture tasks quickly | Full task dialog, quick add parsing, URL capture, install shortcut capture, share target capture, project defaults from the current scope, descriptions, subtasks, tags, due date/time, and no-date tasks. |
| Keep work organized | Project grouping, multi-tag labels, saved views, manual ordering, archives, and batch actions. |
| Plan from different angles | List, calendar, timeline, and statistics views. |
| Work through today | Today's plan, task actions, snooze, skip repeat occurrence, complete/archive/delete, and undo. |
| Manage routines | Daily, weekly, selected weekdays, monthly, last-day-of-month, and custom-day recurrence; repeat rules can be paused. |
| Notice what matters | Reminder offsets, repeat reminders, snooze, missed-reminder notices, and browser limitation guidance. |
| Review progress | Overdue/due-today/undated task entries, seven-day completion bars including retained archived completions, project to-dos, and expandable current-task metrics. |
| Protect local data | Export/backup, backup health, import preview, merge/replace conflict handling, checksum checks, pre-replace snapshots, and emergency backup when storage is blocked. |

## Workspace controls

The desktop sidebar keeps the brand and **List**, **Calendar**, **Timeline** and **Statistics** at the top, with **Settings & data** at the bottom. A separate middle scroll area contains scopes, every project and saved views. Collapsing search and filters keeps view navigation available. On narrow screens, views use the bottom bar; **Open navigation** opens the drawer with the active scope in view, and **Show schedule** opens the calendar. Date navigation does not change task deadlines.

- Choose **Add task** in the top bar to open the full form directly. The adjacent arrow, **Quick capture**, opens compact text entry with a parsed deadline, project and tag preview; **Full form** carries that text into the full form. If Quick capture already has unsubmitted text, **Add task** continues it in the form. `Ctrl/Cmd + I` opens an independent new form. The editor separates task content and subtasks from project, date and tags; **Reminders & repeat** expands below both columns.
- Open **Settings & data** from the header or sidebar, or press `Ctrl/Cmd + M`. Choose one of five category panels: **Appearance & language**, **Backups & transfer**, **Reminders & installation**, **Task maintenance**, or **Help & about**. Settings initially opens **Appearance & language**, then retains the selected category while the page stays open; **Back to tasks** returns to your current view, search, filters and Quick capture text.
- Open **Settings & data → Appearance & language** to choose a **Workspace theme**: **Iris**, **Ocean**, **Pine** or **Berry**. Each native radio preview shows the sidebar, canvas, header and content surfaces; the theme also supplies field, menu, text and selection colours. **Light**, **Dark** and **System** appearance and the interface language remain separate native dropdowns. System follows the operating system; a manual appearance choice stays selected. Theme changes preserve current input, tasks and selections, and user content keeps its original text.
- Mark a task complete with its leading completion control. Open its **Task actions** menu for editing and the other actions available for that task, such as adding it to today's plan, snoozing, skipping a repeat occurrence, archiving or deleting.
- **Today’s plan** is a manually chosen working set. Tasks created while it is active are added to the current plan without changing their deadline. **Due today** and the deadline overview reflect saved dates; a task due today is not otherwise added to the plan automatically.

Workspace themes are saved in this browser profile and keep the existing four preference choices when upgrading. They remain independent of task data and task backups; database 2, task JSON 2.4 and saved-view 1.1/1.0 import compatibility are unchanged. The themes are part of the local application and retain the offline-use boundaries described below.

The [design rules](./DESIGN.md) describe the workspace structure and component principles. The [stable delivery guide](./docs/stable-delivery.md) records current acceptance and publication; [release history](./docs/releases/README.md) retains earlier results.

## Getting Started

A new workspace starts empty. Choose **Add task (+)** in the top bar to enter your first task in the full form, or choose **Try example tasks** in the empty state to add three examples. Examples are clearly labeled, have reminders off, and can be edited, deleted or undone. Refreshing an empty workspace does not add examples automatically. You can backfill a past deadline and edit an overdue task without first moving its date forward. Editing only its name or description keeps the exact stored due instant and timezone, including repeated clock times when daylight saving time ends.

Saving the task includes text left in the subtask input, even if you have not pressed **+**. Use **+** when preparing several subtasks. In List, Calendar or Timeline, if a saved task is hidden by the current filters, calendar day or loaded page, the success message offers **Open task** without changing your view conditions.

The full editor keeps the task title, description and subtasks together, with project, due date and visible tags in a separate details area. **Project** suggests existing names and still accepts a new one. **Today**, **Tomorrow** and **Choose** provide direct date choices; the native **No deadline** checkbox remains available. **Reminders & repeat** expands when needed, and explains that a due date is required.

Temporarily disabling a date, reminder or repeat field preserves its draft value while the form stays open. Saving applies the selected schedule and normalizes disabled values instead of writing an inactive rule. If you clear every day under selected-weekday recurrence, saving asks you to choose at least one day and reveals the error above the action bar; it does not silently fill in days. Deleting another subtask preserves an active inline edit, including its original text and selection.

Open **Settings & data → Help & about → Help and support** for command-palette, diagnostics and support actions, followed by keyboard shortcuts. Expand the capture, search, dates, backup, offline or privacy sections as needed. Diagnostics are also available directly in **Help & about**. Settings and help remain available when local storage is blocked; actions that need task storage keep their storage checks. For troubleshooting and feedback, see [SUPPORT.md](./SUPPORT.md).

## Screenshots

| Task List | Add Task |
| --- | --- |
| <img src="./screenshots/task-list-en.png" alt="Task Tracer task list"> | <img src="./screenshots/add-task-en.png" alt="Task Tracer add task dialog"> |

## Fast Input

Open the **Quick capture** arrow beside **Add task** in the top bar. It turns compact text into structured task fields:

```text
tomorrow 20:00 Review English #study /Personal
```

This creates a task named `Review English`, due tomorrow at 20:00, tagged `study`, and assigned to the `Personal` project. Relative dates also include `yesterday`; Chinese input recognizes 昨天／昨日 and 前天. Check the date preview before saving historical work.

New full-form and Quick capture tasks inherit the selected project. In the scope for tasks without a project, they remain unassigned; in **All projects**, the default is `Inbox`. An explicit `/project` in Quick capture takes priority.

If storage fails while Quick add has text, the input stays read-only and selectable for copying. Retry keeps it in the same page, along with captured source details, even if a retry fails again. After storage recovers, submit explicitly; the app does not automatically replay the failed add. Quick-add text remains memory-only and is not included in the retained full-form draft download, so copy important text before refreshing or leaving.

During input-method composition, Enter, Escape and arrow keys stay with text entry rather than triggering application submission or selection. Finish choosing the text before using the app shortcut.

The command palette opens with `Ctrl/Cmd + P`. It can start a new task, focus quick add, switch views, open saved views, enter today's plan, enter batch actions, undo the latest task change, export/back up data, search, and jump to projects.

Task Tracer also supports direct capture links:

```text
https://todo.muquew.com/?capture=1
https://todo.muquew.com/?add=Buy%20milk
https://todo.muquew.com/?add=Buy%20milk&save=1
```

`capture=1` opens the app focused on quick add. `add=` pre-fills quick add and waits for confirmation. `save=1` saves immediately after the app opens. Capture parameters are removed after processing so refreshing the page does not create duplicates.

Installed PWAs expose a `Quick Capture` shortcut that opens `./?capture=1`. Browsers that support Web Share Target can send shared title, text, and URL to Task Tracer: the title appears in quick add for confirmation, while the shared text and URL are saved into the task description after confirmation.

## Projects, Tags, and Search

A task can belong to one project, such as `Inbox`, `Work` or `Personal`, or remain unassigned. Project selection narrows the workspace; the all-project list groups matching tasks. Rows omit a project badge when the group or project view already identifies it, while cross-project search results retain their project labels.

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

Saved views store the current search, project filter, status filter, sort mode, and view. They are useful for repeatable contexts such as overdue work, weekly study, or a project-specific calendar. Up to 12 distinct views can be saved. At that limit, adding another is refused without removing an existing view, and the name draft stays available. Matching conditions open **Update saved view** with the existing name pre-filled; **Update view** keeps the same shortcut. Remove a view first if you need a new distinct one at capacity.

The saved view's delete control opens a confirmation naming the view, with Cancel focused. Only explicit deletion removes that view; tasks stay unchanged. View deletion cannot be undone, so export a views file first if you need a copy.

Use **Settings & data → Backups & transfer → Transfer saved views**, under **Other data tools**, to export or import a separate views JSON file when moving browsers or devices. Task JSON backups do not contain these views. New exports use views JSON 1.1; imports also accept the older 1.0 format. Files support up to 12 views and 1 MiB; review the import preview before adding them. Project names such as `all` and `__none__` remain exact project selections, separate from All projects and tasks without a project. A saved view for a project that is currently absent stays empty instead of expanding to all projects.

Before changing saved views in 4.7 or newer, close or refresh every older app tab and installed-app window. Versions before 4.7 can interpret typed project scopes as All projects and write that interpretation back. Before downgrading, keep a views 1.1 export outside the browser; older apps cannot read it, so return to 4.7 or newer to restore those views.

View import adds distinct search/filter/layout combinations, keeps existing views and names, and shows duplicate and capacity skips. It never removes existing views to make space. If views change in another window, review the updated counts and confirm again. View files can contain private search terms, project names and tags; check them before sharing. This transfer does not reset the task-backup reminder.

## Views

| View | Best for |
| --- | --- |
| List | Daily execution with task actions, subtasks, deadlines, reminders, archive controls, batch actions, and manual ordering. |
| Calendar | Month planning, date details and no-date grouping; task actions return focus to the original agenda item or date after a redraw. |
| Timeline | Date-grouped work with a compact clock and short status; full deadlines remain available in accessible text and hover details. The list keeps full date presentation. |
| Statistics | Open overdue, due-today or undated to-dos; review seven-day completions and project workload, with current-task metrics available on demand. |

On narrow screens, the three task entries are arranged as readable rows. Statistics follows the current project and search, including explicit search qualifiers, independently of the task-status dropdown. The three workload entries open matching tasks and are disabled at zero; project rows open that project’s to-dos. **Back to statistics** restores the source view after drilling down. Manually changing task scope clears that return context.

The dated seven-day bars, completed-today count and streak use retained tasks with saved completion dates, including archived completions. Archiving completed work therefore keeps it in the review. **Current task summary** is expandable: its task count and completion rate exclude archived tasks, and it lists archives separately. These metrics describe saved tasks rather than productivity over a historical period.

Open **How this is counted** for the review’s calculation notes. Tag-format and recurrence explanations are also available on demand in the task form.

## Today's plan, batch actions, and Undo

Today’s plan is a lightweight execution layer. Adding a task, including creating it from the plan, does not change its project, tags, due date, archive state or recurrence rule. A newly generated repeat occurrence does not inherit the prior occurrence’s manual plan selection. If planned tasks exist but the current search or filters match none, clear those conditions to see the plan again; the app keeps Today’s plan active.

Use the visible **Select** control beside **Filters** to enter batch mode. **More actions** opens a floating action menu while keeping the current scope and selection. Batch Actions mode initially renders 100 matching tasks with selection controls and Show more. **Select all matching** selects the entire current search/project/status result, including unloaded pages; selected tasks can be added to today’s plan, completed, archived or deleted together. **More actions → Move to project** shows the selection count and accepts an existing or new project name; the move supports Undo. Single-task and batch archiving both accept unfinished, unarchived tasks and preserve completion state. Changing the range drops selections outside it. Pagination also applies to batch timeline/calendar sections and any batch sort; non-batch manual ordering retains full rendering.

**Archive completed** and **Delete completed** in **Settings & data → Task maintenance** apply to completed, unarchived tasks across the entire workspace, regardless of the current project, search or filter. The eligible count is shown before acting, and both controls are disabled at zero. Review the confirmation before proceeding. Use batch actions when you need to choose a particular matching set.

Undo reverts the most recent task change while its task state is still current. A newer concurrent task change can withhold or invalidate that Undo, preserving the newer data; review the current tasks and start a fresh action. Use the header button, command palette, or `Ctrl/Cmd + Z` when focus is not inside a text field.

Hovering over a feedback message or focusing one of its controls pauses its remaining display time; leaving resumes the remainder. Using its **Undo** action returns focus to an available task control.

On very narrow screens, the header Undo control uses its icon and retains an accessible name.

## Unsaved Task Forms

Closing an edited task form with Cancel, the close icon, Escape or the backdrop asks whether to continue editing or discard the changes. Continue editing keeps the form contents; Discard closes it. Saving completes before the form can be closed normally. Text still waiting in the subtask input is part of these unsaved changes and retained-draft recovery.

The app requests a browser departure warning while Quick add has nonblank text, a task form has unsaved changes or retained drafts are waiting. Browser rules can limit that warning, especially on mobile. Drafts are not automatically written to browser storage or a server; save or copy important text before leaving, and do not rely on a prompt to survive a crash.

If a storage failure interrupts an edited form, a banner retains its draft only in the current page's memory. **Download unsaved drafts** copies all retained forms to a separate `task-draft` JSON file for reference; it is not a task backup and cannot be restored through task Import. Check that the file was actually saved. With retained drafts, **Retry** reconnects storage without reloading the page; **Resume editing** opens the next draft, while **Discard next draft** requires confirmation. Another open task form must be finished or discarded first. Resumed edits still respect concurrent-change checks. Refreshing, closing or crashing the page loses drafts left only in memory.

## Recurrence and Reminders

Recurring tasks can repeat daily, weekly, on selected weekdays, monthly, on the last day of the month, or after a custom number of days. A recurring task can be paused, and the current occurrence can be skipped without deleting the rule.

Recurrence advances in the task’s saved timezone, independently of the device timezone. Newly set or changed deadlines move forward across a skipped clock time and use the first occurrence of a repeated time. An unchanged date/time edit retains its stored instant; this does not bulk-correct old deadlines. See [date and recovery support](./SUPPORT.md) for the saved-time boundary.

Relative-date search, today's plan, overdue membership and statistics are reconsidered on minute/visibility checks. Active dialogs, inline editing, task-text selection, dragging or selected batch work can defer a rebuild; background timers may be suspended. The overdue rate divides overdue ongoing tasks by ongoing tasks with deadlines, excluding completed, archived and undated tasks from the denominator.

Browser notifications are available when the browser supports them and permission is granted. Task Tracer can check reminders while the app is open, repeat reminders at the chosen interval, snooze a reminder, and show missed reminders when the app runs again.

Snoozing persists the next reminder time, which remains visible on the task. **Notifications are off** is shown when permission or the application setting prevents notification delivery. Scheduling a reminder does not enable notifications or guarantee delivery after the app closes.

Browser reminders are not guaranteed system alarms. Delivery can depend on browser policy, operating system behavior, battery settings, tab lifecycle, and whether the app is opened or woken by the browser.

## Import, Export, and Backup

`Export/Backup` starts a task JSON download with an export ID, checksum and version notes, and records the export operation. Starting a download does not prove that the file was saved or retained; check the downloaded file and keep a copy outside the browser. It restores supported task fields, including subtasks, projects, tags, due dates, repeat/reminder rules and today's plan. It does not include saved views, app settings or recovery checkpoints.

The backup indicator compares the recorded export snapshot with current tasks. Task changes require another export; older date-only export history has unknown coverage rather than establishing that current tasks were exported. A fresh export also does not prove that you kept its file. Task JSON and CSV exports read their task data from a single read-only snapshot without refreshing the current task view. The browser-local backup coverage record refers to the exported task revision and date; it is not an extra field in the task JSON. CSV does not count as a restorable task backup. The optional startup backup reminder skips an open dialog or existing notification; **Settings & data → Backups & transfer** still shows backup status.

`Import` first shows a cancellable file-reading dialog, then previews the task JSON before writing it. Cancelling a read or choosing a newer file prevents an earlier read from replacing your current form or preview. The native radio group explicitly offers **Merge into current tasks** and **Replace all current tasks**, with replacement selected initially. Review the actual outcome: additions, local replacements, skipped entries, retained tasks and resulting total for merge; current-to-file task counts for replacement. Counts and the action label update with the mode and conflict choices. Passed file checks and change details can be expanded.

Same-name conflict controls appear when merge mode is enabled, initially showing 100 rows with **Show more**. The bulk action applies **Keep both**, **Skip import**, or **Replace local** to all matching names, including rows not shown yet. Changing that action resets individual choices; you can then adjust specific rows. Switching from Merge to Replace and back preserves those choices until you change the bulk action.

Merging changes first preserves the current tasks as a local recovery point. Recovery points share browser storage with tasks; keep a downloaded JSON backup outside the browser.

Replace import downloads a pre-import snapshot before overwriting existing tasks. If the checksum fails, replace import requires an explicit risk confirmation; merge mode remains available for safer recovery. A background task refresh makes an open preview stale: the app rebuilds it and resets earlier safety approvals. Review it again and, for replacement, download a fresh snapshot before confirming. If a database conflict closes the preview instead, reopen the file to start a new review.

If browser storage is blocked or becomes unavailable, Task Tracer enters a storage-unavailable mode. When an in-memory task snapshot still exists, the emergency backup button can download that snapshot before the page is refreshed or closed.

### Spreadsheet reporting

Choose **Export all tasks as CSV** under **Settings & data → Backups & transfer → Other data tools** to download all stored tasks, including completed and archived tasks, regardless of the current search or filter. The UTF-8 file includes task details, dates, recurrence fields, tags and subtasks (JSON cells). Spreadsheet formula-like cells receive a leading apostrophe for safer opening. CSV is a reporting format, not an importable backup; keep using JSON backup for task restoration. CSV export does not reset the backup reminder.

## Recovery History and Multiple Tabs

Open **Settings & data → Backups & transfer → Recovery history**, choose a checkpoint and compare the current and target task counts. Expand **Review recovery point tasks** when you need the task names and statuses. The initially collapsed preview uses its own scroll area, starts with 100 rows and offers Show more; it keeps full task/completed/archived counts. Changing the checkpoint resets the preview and replacement confirmation. The restore action names its target count and stays disabled until you tick the replacement confirmation; explicitly confirming then replaces the current task list.

**Export this recovery point** downloads that checkpoint as an importable task JSON 2.4 file, including empty checkpoints, without changing current-task backup coverage. Inspect and retain the actual file. **Clear recovery history** asks for a separate confirmation and removes only stored local checkpoints. If history changed in another window, review the refreshed list and confirm again. Current tasks, views, settings, downloaded files and Undo stay unchanged; a later task write creates new checkpoints.

Task Tracer retains up to 10 checkpoints in the same browser. It saves the task state before the first write and at five-minute write intervals, and always before deletion, import/merge, undo, or recovery. Empty task lists can also be restored. Checkpoints and task changes commit together, so a failed transaction cannot leave a partial recovery. Deleting a task from the current list does not remove its older copies from checkpoints. These checkpoints do not survive clearing site data or losing the device.

When another tab changes tasks, a stale write is rejected and the latest task list is loaded. If the task open in your edit form has changed or was deleted, your draft stays visible: copy the changes you need, cancel, and reopen the latest task before saving. Repeatedly submitting the stale form does not overwrite newer work. Task deletion, clearing/archiving completed tasks, batch deletion and checkpoint restoration also reject an outdated confirmation after the task state refreshes. Review the latest tasks and start the action again. This protects tabs sharing the same browser storage; it is not cross-device sync. After upgrading, close or refresh all older app tabs and offline windows before editing: older cached versions do not participate in revision checks.

## Data safety and large workspaces

Use **Settings & data → Backups & transfer → Review storage status**, under **Other data tools**, to inspect site storage and explicitly request browser persistence. A denied or unsupported request does not block your tasks or exports; persistence cannot replace an external backup. Ordinary lists and timelines initially show 100 matching tasks with **Show more**; search still covers the entire workspace. Timeline groups follow chronological date order, put undated work last and show the full matching count for each displayed date. Calendar undated tasks and a selected day’s details also start at 100 items, with independent Show more controls and full matching counts. Non-batch manual ordering retains full rendering. Batch rendering is paged while selection and actions cover all selected matching tasks. See the [measured performance results](./docs/performance.md).

## Install, Offline, and Updates

Use **Settings & data → Reminders & installation → Install app** to install Task Tracer. If the browser does not expose an automatic install prompt, the same entry shows manual steps for desktop Chrome/Edge, Android Chrome, and iOS Safari.

After the app shell is cached, Task Tracer can load offline. When a newer cached version is ready, the app shows an update prompt with a refresh action. The HTML includes matching language data for startup if a separate translation request fails. Initial offline use still requires a completed online cache; clearing site data removes that copy. Older open windows keep their installed worker policy, so save drafts and close or refresh those windows after upgrading.

**Settings & data → Help & about → Check for updates** checks explicitly and shows the current result: checking, up to date, update ready, offline, unsupported or a failed check. **Refresh** appears when an update is ready. Resolve unfinished Quick capture text, task-form changes and retained drafts before reloading; saving or pending task changes also block the refresh. The app waits for the prepared worker to take control before reloading, without a timed forced refresh.

## Accessibility and Languages

Task Tracer includes Chinese and English UI, synchronized document language, keyboard-friendly controls, labelled icon buttons, focus traps for dialogs, live-region announcements, reduced-motion support, and responsive layouts for desktop and mobile.

## Data and Privacy

Task data is stored in the current browser's IndexedDB. Task Tracer does not require an account and does not upload task content to a server by default.

Before changing browsers, clearing site data, reinstalling the app, or moving devices, use `Export/Backup` for task JSON and **Transfer saved views** for a separate views JSON file, and keep copies outside the browser. Local storage and export checksums do not encrypt task contents.

**Settings & data → Help & about → Review diagnostic information** shows a full JSON preview before you choose to download it. The same action is available in **Help and support**. It contains application/browser versions and capabilities, permission status and storage estimates; it excludes task content, saved views, app settings, URLs and raw error messages. Nothing is uploaded automatically, and a diagnostic file is not a task backup.

Capture/share URLs can contain task text in query parameters. Hosting logs and browser history may record those URLs before the app clears them. See [the security and data boundaries](./SECURITY.md) for deployment guidance.

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

## Development and Release

Run `python tools/check.py --static-only` for consistency checks, or `python tools/check.py --keep-going --report /tmp/task-tracer-checks.json` for the full registered suite. The [contribution guide](./CONTRIBUTING.md) covers pinned dependencies, all three browser engines, data boundaries and reproducible release commands.

Use the [stable delivery guide](./docs/stable-delivery.md) for current acceptance, artifact identity and upgrade/rollback instructions. [Release history](./docs/releases/README.md) retains each version’s actual results and original failures. Report security issues through [SECURITY.md](./SECURITY.md); the [product roadmap](./docs/product-roadmap.md) distinguishes shipped capabilities from commercial decisions.

## License

Task Tracer is licensed for personal non-commercial use. Personal task management, learning, research, and evaluation are allowed. Commercial use, paid distribution, or integration into commercial services requires prior written permission from `muquew`.

See [LICENSE](./LICENSE) for the full terms.

A verified static archive can be built with `python3 tools/build_release.py`; this does not publish it. The [commercial offering plan](./docs/commercial-plan.md) describes proposed owner-controlled distribution and decisions still needed before selling.
