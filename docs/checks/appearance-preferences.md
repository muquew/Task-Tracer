# Appearance preference check

`tools/appearance_preferences_playwright.py` exercises the native Light, Dark and System preference controls through browser events and ordinary UI operations. It is registered in the complete `tools/check.py` queue and the browser matrix's `appearance` group.

After installing the pinned development dependencies and browser engines, run:

```bash
python3 tools/appearance_preferences_playwright.py --browser chromium
python3 tools/browser_matrix.py --browser all --group appearance --report dist/browser-matrix-appearance.json
```

The prepared cloud machine uses the browser-cache and library settings in [the runtime notes](../cloud-browser-runtime.md). The check does not download browser revisions or dependencies.

## Coverage

Eight cases use fresh contexts and synthetic tasks:

- First use with a light or dark browser color scheme resolves System correctly.
- Existing `theme=light` and `theme=dark` values remain compatible.
- Desktop and narrow-screen preference selection survives reload; explicit Light/Dark stays selected when the browser color scheme changes, while System follows the change.
- Browser color-scheme changes preserve unsaved task fields, pending and edited subtasks, focus, text selection, task DOM nodes and stored task records.
- Two real pages in one context synchronize preferences through actual Web Storage events. Each page resolves System against its own emulated color scheme. The receiving page retains its unsaved draft and original tasks, and the retained draft can still be saved through the ordinary form.

The standalone runner accepts `--case` for a named case and `--artifacts-dir` for its unique evidence directory. Run `--help` to see current choices. It records the actual engine version, completed cases, page/console errors and the hashes of the application HTML, shared UI helpers and this check. Failures retain screenshots and traces where capture succeeds. The matrix additionally binds the run to all release-source and verification inputs.

## Evidence limits

A pass applies to the selected cases and actual engine in that report. The test uses browser media emulation, synthetic tasks and isolated storage; it is not physical operating-system, device, input-method or screen-reader acceptance. It does not establish that the remaining matrix, the complete release queue or production deployment passed. Keep failed and interrupted reports under their original identities when a later run succeeds.
