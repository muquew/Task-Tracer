# V5 production browser rehearsal

The v5 driver is copied from the prior six-context green driver. Its only byte change is EXPECTED_INDEX4a7→89b; ROOT stays/workspace/Task-Tracer. See copy-scope.json. Old driver and old reports remain unchanged.

Local rehearsal on candidate6da3c7293f08c5d16ca73c7a63d8ff74e17358db passed all six fresh contexts: Chromium/Firefox/WebKit at1280×900 and390×844. It keeps normal motion and effective production CSP, real UI create/edit/pending-child main save/completion, all four views, themes/languages/settings return, real JSON download/every-task-field/checksum comparisons, reload and cleanup. Report:local-20261025T210048Z-0230ecaa15/report.json. Five runtime files, actual six helpers and driver hashes stayed equal; all page-error lists are empty and every context/browser/server closed.

preparation-receipt.json records exact command/environment, original checksum results, source/helper/driver fingerprints and three screenshots actually opened. The narrow calendar action capture still contains the transient completion/Undo toast; it is not claimed proof that every lower detail is unobstructed in that frame. Remaining images are action captures, not all individually reviewed.

This is local HTTP rehearsal, not main/Vercel/TLS production acceptance or final73/99. Production remains forbidden until the parent gives the published main/Vercel static-match signal. Then use this same driver and environment in a new production UUID:

```sh
PYTHONDONTWRITEBYTECODE=1 \
TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium \
XDG_CACHE_HOME=/workspace/.cache \
PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright \
LD_LIBRARY_PATH=/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu \
PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 \
python /workspace/design-research/task-tracer-final-delivery-2026-10-26/production-final-v5/driver.py \
  --mode production --url https://todo.muquew.com/
```

The official host-precheck skip only accommodates the established sysroot; it does not skip product cases, TLS certificate validation or CSP. No repository inputs were changed by this rehearsal.
