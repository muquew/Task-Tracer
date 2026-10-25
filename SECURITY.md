# Security

Task Tracer keeps tasks in this browser's IndexedDB. It has no account service or server-side task database. Only the latest published version is maintained.

## Report a vulnerability

- Use this repository's **Security → Report a vulnerability** action when private reporting is enabled.
- If unavailable, request a private reporting channel in an issue without publishing exploit details, real tasks or backup files.
- Provide the affected version, browser/OS, impact and a minimal synthetic reproduction once a private channel is available.
- Ordinary bugs belong in [Support](SUPPORT.md). No fixed response time or independent security certification is promised.

## Data and hosting

- Browser-local storage is not encryption. Other users of the same profile, privileged extensions or compromised same-origin code may access tasks.
- Clearing site data, eviction, a lost device or an origin change can remove local data. Keep downloaded task and view JSON copies outside the browser.
- Recovery history can retain older or deleted task content. Clearing checkpoints does not erase downloaded copies; later writes may create new checkpoints.
- Task JSON excludes saved views, preferences and recovery history. View files and memory-only draft downloads may contain private searches, project names or original task text; review before sharing.
- Checksums detect supported consistency errors; they are not encryption, sender authentication, a publisher signature or commercial entitlement.
- Capture/share URLs can be recorded by browser history, hosts and proxies before parameters are removed. Avoid sensitive content in those links; static hosting may retain access logs.
- Diagnostics require a local preview and manual download. They exclude task content, views, settings, URLs and raw error messages, and never upload automatically.
- CSV quotes cells and prefixes formula-like values. Spreadsheet editing may remove that protection; use JSON for faithful restoration.
- Deploy over HTTPS on a dedicated origin, keep TLS verification enabled and preserve `vercel.json` security headers. The local Python server does not apply those headers.
- CSP authorizes exact inline scripts and blocks inline event handlers. Regenerate its hashes after script changes; see [Contributing](CONTRIBUTING.md).

Report with synthetic data. Never publish personal task backups, saved views, drafts or unredacted diagnostic files.
