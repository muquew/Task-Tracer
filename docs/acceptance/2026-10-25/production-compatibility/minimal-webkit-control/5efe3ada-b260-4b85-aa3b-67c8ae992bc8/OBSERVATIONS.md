# Independent WebKit offline control

WebKit 26.5, 2026-10-25 13:37:30–13:37:33 Beijing time. This fixture does not import, read or modify Task Tracer application files.

1. **Online warmup:** both fresh localhost contexts load the minimal fixture, acquire an active service-worker controller and cache, and complete a controlled reload with HTTP 200 and `from_service_worker=true`.
2. **`context.set_offline(True)`:** reload and a new-page navigation both fail with `WebKit encountered an internal error`. The old document remains visible; that does not establish a successful reload. The new page remains blank.
3. **Server unavailable:** another fresh localhost origin and context is warmed, its own HTTP server is stopped, and reload succeeds with HTTP 200/from-service-worker and the exact fixture body SHA.

All three saved screenshots were opened using `view_image`; see `visual-review.json` for the accepted scope. `captured-executor-session-11510-output.log` preserves a transcript of the actual returned executor output. Original raw fixture, runner, report and screenshots remain unchanged and bound by the original `evidence-sha256.json`; post-run metadata is bound separately.

The observed discrepancy reproduces without Task Tracer. It supports treating the context-offline result as a limitation of this automation/runtime path under these conditions. It neither replaces the failed production acceptance nor proves real Safari, real devices, system-offline operation or all WebKit versions fail.
