# Security

Task Tracer stores tasks in the browser's IndexedDB and caches its app shell with a service worker. It has no account service or server-side task database. Only the latest published version is maintained; no fixed response time or independent security certification is promised.

## Report a vulnerability

Use the repository's **Security → Report a vulnerability** action if private reporting is enabled. If it is unavailable, open an issue requesting a private reporting channel without publishing exploit details, real task data, or backup files. Include the affected version, browser/OS, a minimal reproduction with synthetic data, and the impact once a private channel is established.

Do not attach personal task exports to public reports. For ordinary bugs, use a normal issue with synthetic examples.

## Data and deployment boundaries

- Local storage is not encryption or a backup service. Other users of the same device/browser profile, extensions with sufficient access, or compromised same-origin code may access task data. Protect the device and profile.
- Clearing site data, browser eviction, a lost device, or changing the site's origin can make local data unavailable. Download exports to a separate location and test restoration. Recovery history stored in the same browser cannot replace that copy.
- Capture links and Web Share Target use URL query parameters. A hosting provider, reverse proxy, browser history, or logs may record their content before the app removes those parameters. Avoid putting sensitive information in such links; review request logging before deployment.
- The static host receives normal asset requests and may retain access logs. The application's local-first design does not imply that hosting infrastructure has no logs.
- Recovery history retains previous task snapshots, including copies of tasks removed from the current list. Checkpoint exports contain that older content. Clearing recovery history removes those stored checkpoints after confirmation; current tasks, in-memory Undo and downloaded files remain, and later task writes can create new checkpoints. Review recovery files before sharing them.
- Task JSON backup restores supported task fields, not saved Smart Views, app settings or recovery checkpoints. Use **Transfer saved views** for a separate views JSON copy; keep separate notes for preferences you need when moving profiles.
- View files contain saved searches, filters and layouts, which may expose private search terms, project names and tags. Review files before sharing and avoid attaching personal view files to public issues. Their checksum detects consistency errors; it does not encrypt contents or authenticate the sender. View import validates the supported schema and merges without replacing existing views, task data or preferences.
- Storage failures may retain an unsaved task form only in page memory. A separately downloaded `task-draft` file can include private raw form text and the original edited task; it is not encrypted, not a task backup and not accepted by task Import. Downloading does not prove that a copy was saved. Refreshing, closing or crashing the page loses memory-only drafts, and browser departure prompts are not guaranteed. Do not attach real draft files to public reports.
- Local diagnostics require an in-app preview and a user download action. They contain application/browser versions, capability/permission status, storage estimates and allowlisted error categories. They exclude task content, saved views, app settings, URLs and raw error messages, and are never uploaded automatically. Review even diagnostic files before posting them publicly; they are not task backups.
- Export integrity checks detect supported file inconsistencies; they are not encryption, a digital signature, or proof of who created a backup. Import only files you trust and inspect the preview before replacing data.
- Deploy over HTTPS on a dedicated origin. Keep TLS verification enabled, avoid third-party runtime scripts, and preserve the security headers in `vercel.json` when deploying to another host. Verify headers on actual responses; the Python development server does not apply Vercel configuration.

The deployment CSP authorizes the exact inline application scripts with SHA-256 hashes and blocks inline event handlers. `python3 tools/security_policy.py --write` refreshes hashes after a script change; the default checks reject stale hashes. Browser tests execute the app under these headers and verify that unsigned scripts and inline handlers are blocked. Inline styles remain allowed because the UI uses dynamic styles. This local test does not prove the production host applies the configuration.

Automatic Vercel analytics/speed-insight script loading has been removed. The application does not request those scripts; hosting access logs and browser/extension behavior remain outside this guarantee. Storage persistence is requested only when a user chooses it in Data safety; a denial does not prevent task access or export.

Security fixes must preserve existing task data and include a regression check for the affected behavior. See [the release gates](docs/product-roadmap.md#release-gates) before publishing changes to storage or imports.

CSV reporting quotes every cell and prefixes formula-like cells (including leading whitespace) with an apostrophe. This reduces formula execution when opening the original export in spreadsheet software; editing or re-saving cells may remove that protection. Use JSON backup for faithful restoration rather than CSV.
