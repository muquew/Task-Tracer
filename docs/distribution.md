# Task Tracer — static distribution

A local-first task workspace with projects, calendar, recurring tasks and backups. No account or task server is required.

## Run

- Extract the complete archive. Serve it over HTTPS, or use a trusted localhost server: `python3 -m http.server 8080 --bind 127.0.0.1`.
- Keep all files together, including the service worker, language files, icons and `vercel.json` deployment headers. Opening `index.html` as a local file does not provide the complete PWA experience.
- Verify the archive with its `.zip.sha256` file. `integrity.json` lists 23 payload hashes and build metadata; hashes are not encryption or publisher signatures.

## Use

- **Add task** opens the full form; its adjacent arrow opens Quick capture. List, Calendar, Timeline and Stats share the same tasks.
- **Settings & data** contains appearance/language, backups, reminders/installation, maintenance and help. Four workspace themes support light and dark appearance.
- Tasks stay in this browser profile. Export task JSON and separate saved-view JSON before moving devices, clearing site data or downgrading.
- Task JSON restores supported task fields; it excludes views, preferences and recovery history. CSV is a report, not a restorable backup.
- Local recovery history shares browser storage. Keep an actual downloaded copy elsewhere and inspect import previews before replacing tasks.
- Save important text before refreshing: unsubmitted capture and retained drafts may exist only in page memory.
- Use **Help & about → Check for updates**; resolve drafts first and refresh when the update is ready. Close older app windows after upgrading.
- Offline startup needs a completed initial cache. Installation and notifications depend on the browser/OS; delivery after closing the app is not guaranteed.

## License and support

- [LICENSE](../LICENSE) permits personal non-commercial use. Commercial use requires separate agreement with copyright owner muquew; purchase terms remain undecided.
- Preserve the license and `THIRD_PARTY_NOTICES.md` when redistributing permitted copies.
- Source, help and security reporting: https://github.com/muquew/Task-Tracer
