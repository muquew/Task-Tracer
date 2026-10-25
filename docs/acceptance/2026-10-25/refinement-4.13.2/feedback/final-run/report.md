# Final workflow feedback regression — APP 4.13.2

**10/10 targeted real-UI cases passed**, with no browser page errors, on final `index.html` SHA-256 `fb59cc194636eba12251839860d4e42a1d1e60daf3b4b009a30ac68b91b1f1cd`. Inputs were captured before browser launch and remained unchanged afterward. The test tool hash is identical to the successful b925 run; no selector or timing assertion was changed for this final run. The tool is now frozen.

## Results

| Case | Result |
|---|---|
| Search save outside current view | Exactly one persisted task; correct saved-task edit form opened after 7 seconds of focus; search/filter unchanged. |
| Edit project outside current scope | Same persisted ID, correct edited project, unchanged selected project filter. |
| Edit date outside visible calendar | Same persisted ID, correct edited date, unchanged calendar month and selected agenda day. |
| Replace action | Ordinary visible save retained success/Undo; next hidden save opened its own task; later unrelated message cleared old actions. |
| Quick draft | Opening the saved task preserved exact unsubmitted quick-capture text without a new record. |
| Focus pause | Real 7-second focus hold stayed usable, then resumed remaining lifetime: **4.267s**. |
| Hover pause | Real 7-second hover hold stayed usable, then resumed remaining lifetime: **4.240s**. |
| Plain notification pause | Ordinary 3-second message survived a 3.5-second focus hold, then resumed remainder: **2.039s**. |
| Batch Undo focus | Header and notification Undo exactly restored task records and focused a live task control; subsequent Tab did not jump to the top bar. |
| Native input Undo | Ctrl+Z kept native text Undo, input focus and task data/history. |

The final 320/390px outside-view notification screenshots were opened and inspected: the complete message is on the first row, with Open/Undo on the second row. Action text stays horizontal and no control extends outside the viewport. Ordinary success notifications retain their previous compact layout. All 12 final PNG files were opened using view_image.

## Evidence and method

- `results.json`: individual outcomes, case duration and measured resumed timer durations.
- `input-manifest.json`: source/tool SHA-256 values, prelaunch capture time, unchanged-input verification, and unchanged-tool verification against b925.
- 12 PNG screenshots in this directory.
- Stdout: `/tmp/task-tracer-4.13.2-feedback-final-run.log`.
- Older candidate evidence remains untouched under `../first-run/` and `../corrected-layout-check/`. The earlier narrative said 13 PNG files; the correct count is 12 PNG files per successful run.

The tool used an independent ProductionHeaderHandler server, normal deployment CSP, system /usr/bin/chromium and fresh contexts. All tasks were created/edited through actual UI; database evidence was read only. No fake task state, clock replacement, reduced pagination limit or altered notification timeout was used. Scope is the same 10 targeted cases, not the full suite. The real 101-task pagination boundary, physical mobile devices and sidebar-specific long-project scrolling are outside this tool's coverage.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python3 -u tools/workflow_feedback_playwright.py --output-dir /tmp/task-tracer-4.13.2-feedback/final-run
```
