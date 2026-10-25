# Task Tracer 4.11.0 — static distribution

This archive contains the browser application, deployment headers, icons, translations, third-party notices and an SHA-256 integrity manifest. It does not contain an account service, cloud sync or a payment service.

## Using the workspace

A new workspace starts empty. **Try example tasks** optionally adds three labeled ordinary tasks with reminders off; they can be edited, deleted or undone. Empty workspaces are not repopulated on reload. **Settings & data → Help & about → Help and support** opens actions and shortcuts first, with capture, search, dates, backup, offline and privacy details in expandable sections. Diagnostics are also directly available in **Help & about**, even when storage is blocked.

Use **Add task** in the top bar to open Quick capture. Review the parsed deadline, project and tags, then add the task or choose **More options** to carry the text into the full form. Description and subtasks are in the main form; tags, reminders and recurrence expand under **More settings**. The sidebar opens all tasks, your manually chosen **Today’s plan**, projects and saved views. On narrow screens, the navigation button at the top opens the sidebar. Search and project/status filters continue to apply to the complete workspace, including tasks beyond the displayed page. **Save view** stores the current search, filters and view; saved views can then be reopened from the sidebar.

List, Calendar, Timeline and Statistics are always available in the desktop sidebar and the mobile bottom navigation, including when the search and filter tools are collapsed. Open **Settings & data** for five category panels: **Appearance & language**, **Backups & transfer**, **Reminders & installation**, **Task maintenance**, and **Help & about**. Only the selected panel is shown, and the current category is retained while the page stays open. Returning to a task view preserves the current filters and any unfinished Quick capture text. Archive completed and Delete completed are in **Task maintenance** and act on completed, unarchived tasks across the workspace; they do not use the current project or search filter.

Language and appearance controls are in **Settings & data → Appearance & language**. Choose **简体中文** or **English** for the interface, and **Light**, **Dark** or **System** for appearance. System follows that window’s operating-system color preference. These choices change presentation; they do not translate or rewrite your task names, descriptions, projects or tags.

Mark a task complete with its leading completion control. Open its **Task actions** menu for available actions such as editing, adding it to today’s plan, snoozing, skipping a repeat occurrence, archiving or deleting. Actions that do not apply to a task are unavailable. The top-bar Undo action restores the latest eligible task change; concurrent newer work can make an old Undo unavailable.

The seven-day date index and small month calendar open that date in the full Calendar view. On narrow screens, **Show schedule** opens the calendar from the today-deadline summary. Choosing a day changes what you are viewing, not a task’s deadline. Today’s plan is a manual collection and remains distinct from tasks due today. List, Calendar, Timeline and Statistics continue to use the same task data.

Useful shortcuts include `Ctrl/Cmd + I` to add a task, `Ctrl/Cmd + K` to focus search, and `Ctrl/Cmd + P` to open the command palette. Task menus support arrow keys, Home, End and Escape; closing a dialog returns focus to an available initiating control. Shortcuts do not take over text input during input-method composition.

## Hosting and upgrading

Deploy the files together on a dedicated HTTPS origin. `vercel.json` supplies script-hash CSP and other response headers on Vercel; configure equivalent response headers on another host. The Vercel config also explicitly skips dependency installation and build commands and serves this static directory; Python and npm are not hosting requirements. For local evaluation, extract the archive and run `python3 -m http.server 8080` from its directory. Opening `index.html` as a file is not a supported PWA installation method.

Tasks and recovery history stay in the current browser profile. Export a backup before changing domains, moving devices, clearing site data, or upgrading. Close older app tabs before reopening the new version. Recovery points do not protect against loss of the browser profile or device. Browser reminders depend on the app/browser lifecycle and are not guaranteed system alarms.

The interface update keeps database version 2, task backup JSON 2.4 and saved-view file 1.1, with saved-view 1.0 import support. Keeping these formats does not make every older interface compatible with newer settings or view scopes; follow the older-window guidance below.

## Tasks, dates and large workspaces

New or changed deadlines use the current device timezone. If a clock change skips the entered wall time, it moves forward by the gap; if the time occurs twice, the first occurrence is used. Check the actual displayed deadline. Editing other fields without changing the date/time preserves the stored instant, including a previously stored second occurrence. Repeated tasks advance their calendar date in the task's stored timezone, independently of the device timezone.

Time-dependent search, today’s plan, overdue filters and statistics are refreshed on minute checks and when the page becomes visible again. Refresh can wait while a dialog, inline edit, text selection, drag or selected batch operation is active. Browsers may suspend timers in the background; this is not an exact-time background service. The overdue rate counts overdue ongoing tasks divided by ongoing tasks with deadlines; completed, archived and undated tasks are excluded from that denominator.

During input-method composition, Enter, Escape and arrow keys remain with text entry. Batch mode starts with 100 task entries and supports Show more. **Select all matching** selects the entire search/project/status scope, including tasks not yet displayed; the selection count shows the operation's scope. Loading more retains selection, while range changes drop selections outside the new scope. Newer concurrent changes can withhold or invalidate Undo rather than overwrite newer data.

Ordinary and batch lists/timelines start with 100 matching tasks. Calendar undated tasks and selected-day details each start at 100 with independent Show more controls, including batch mode; matching counts and search still cover all tasks. Manual ordering outside batch mode retains full-list rendering costs.

## Backups, imports and recovery

Open **Settings & data → Backups & transfer → Recovery history** to preview a selected checkpoint's task names/statuses, beginning with 100 rows and full counts. Export this recovery point downloads importable task JSON 2.4, including empty checkpoints, without updating current-task backup coverage. Clear recovery history requires separate confirmation and removes only local checkpoints; if history changed, review the refreshed list and confirm again. Current tasks, views, settings, downloaded files and Undo remain. Deleted tasks may still have copies in old checkpoints, and later task writes create new checkpoints.

After starting a task JSON download, the app records the offered snapshot’s task revision and export date in this browser; these are local coverage records, not new task JSON fields. A download starting does not prove the file was saved or retained: inspect the actual file and keep an external copy. Changed tasks or older date-only export records require another export before coverage can be considered current. JSON and CSV export each read a consistent task snapshot without refreshing the visible task list.

JSON backup restores supported task fields, including subtasks, projects, tags, schedules, reminders and today’s plan. It excludes saved views, app settings and recovery checkpoints. Use **Settings & data → Backups & transfer → Transfer saved views**, under **Other data tools**, for a separate views JSON file (new exports use 1.1; imports also accept 1.0; up to 12 views and 1 MiB). Its import preview shows additions, duplicates and capacity skips; it preserves existing views and never evicts them to make space. If another window changes the views, review the updated preview before confirming again. View files can contain private search terms, project names and tags. Task-file reading can be cancelled, and changes while an import preview is open require a fresh review and safety confirmation. Merge conflict rows load in batches of 100; the selected bulk action applies to all matching names, while changing it resets individual row choices. CSV, also in **Other data tools**, exports all tasks for spreadsheet reports and prefixes formula-like cells with an apostrophe; it cannot be imported for restoration or counted as a backup.

## Unsaved work and storage failures

Edited task forms ask whether to continue editing or discard changes before Cancel, close-icon, Escape or backdrop closure. Browser departure warnings are requested for nonblank quick-add text, an unsaved task form or retained draft queue and remain subject to browser rules. Drafts are not automatically written to persistent storage or a server; save or copy important text before leaving.

If storage fails with unsaved quick-add text, that field stays read-only and selectable for copying. Retry reconnects storage in the same page while quick-add text or retained forms remain, keeping the original text and captured source details. After recovery, explicitly submit again; Retry does not replay the add. Quick-add text is only in page memory and is not part of the full-form draft download. Copy it outside the app before refresh or close; a crash can still lose it.

When a storage failure interrupts an edited form, a banner retains it only in this page's memory. Download unsaved drafts exports all retained forms as a separate `task-draft` JSON reference file, not an importable task backup; verify that the file was saved. Retry reconnects storage in the same page while drafts remain. Resume editing opens the next draft after storage is available and respects stale-edit checks; finish the current form first. Discarding the next retained draft requires confirmation. Refreshing, closing or crashing the page loses memory-only drafts. Draft files may contain private unsaved text and the original edited task; review before sharing.

## Saved views and older interfaces

Before changing saved views in 4.7 or newer, close or refresh all older app tabs and installed-app windows: versions before 4.7 can read typed scope objects as All projects and write that interpretation back. Keep a views 1.1 export before downgrading; old apps cannot import it, so return to 4.7 or newer to restore the views. Unchanged task/database formats do not make new view configurations compatible with old interfaces.

Project scopes distinguish real names such as `all` and `__none__` from All projects and tasks without a project. A saved project that is currently absent stays empty. Up to 12 distinct views can be saved. Adding another at capacity keeps existing views and the name draft; a matching search/filter/layout can still update its existing view.

The saved-view × opens a confirmation naming that view, with Cancel focused by default. Only explicit deletion removes the selected view; tasks remain unchanged. View deletion cannot be undone, so export a views file first if you need to retain it.

## Offline use and diagnostics

Offline startup requires a completed initial app-shell cache. HTML includes its own matching translation data if an external language request fails; this does not replace caching the other required files. Old open windows retain their installed worker policy. Deploy all files together, save drafts before refreshing, and close older windows after upgrading. Clearing site data also removes the offline copy.

**Settings & data → Help & about → Review diagnostic information** opens a local JSON preview with a separate download action. The same action is available in **Help and support**. The report contains app/browser versions, capabilities, permission status and storage estimates; it excludes task content, saved views, app settings, URLs and raw error messages. Nothing is uploaded automatically. Diagnostic files are not task backups.

## Integrity and licensing

Verify the archive against its accompanying `.zip.sha256` file before extraction. The builder uses an explicit 23-file source list, plus generated `integrity.json`, rather than including whole resource directories. `integrity.json` lists the exact file hashes, source commit and whether it was built from a modified working tree. These hashes detect accidental changes; they are not a publisher signature or a commercial entitlement.

The included `LICENSE` permits personal non-commercial use. Commercial use requires a separate agreement from the copyright owner, muquew; possession of this archive alone grants no commercial authorization. A buyout or professional edition is planned, but price, payment, private support and issued commercial terms remain undecided. Keep the project license and `THIRD_PARTY_NOTICES.md` with redistributed copies; the latter includes the Tabler Icons MIT notice.

Source, development instructions and security reporting: https://github.com/muquew/Task-Tracer
