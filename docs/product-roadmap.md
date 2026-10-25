# Product direction and delivery scope

Task Tracer is a local-first personal task workspace for capture, planning, recurring work, reminders and review. The existing product works without an account or task server. Task ownership, export, recovery and offline access must stay independent of an optional purchase service.

## Current stable delivery

The **4.15.1** engineering delivery status is **complete**. [GOAL.md](../GOAL.md), [the stable delivery record](stable-delivery.md) and [final evidence](acceptance/2026-10-26/final-4.15.1/final-full/final-delivery.md) identify the frozen application, canonical archive, actual gate outcomes and publication. The scope is the existing local-first web product; later bug/security fixes and optional features remain normal maintenance.

## Existing product scope

| Need | Current capabilities |
| --- | --- |
| Capture and edit | Complete task editor, Quick capture/direct capture, descriptions, subtasks, projects/tags, local dates/times, repeat and reminder settings, retained drafts and failure recovery. |
| Organize daily work | Today’s plan, project/search/filter/sort/saved views, batching, manual order, completion, archive/delete and Undo. |
| Plan and review | List, calendar, timeline and statistics over the same tasks, scope-aware counts and direct task drilldowns. |
| Protect and move data | Task JSON backup/import/merge/replace, integrity checks, pre-replace snapshots, local recovery history, CSV reports and separate saved-view migration. |
| Use the interface | Chinese/English, four workspace themes with light/dark/System appearance, desktop/narrow layouts, keyboard focus and native-input protection. |
| Operate locally | IndexedDB task storage, cached offline shell, explicit update checking and optional browser installation/notification/storage capabilities. |

Database2, task JSON2.4 and saved-view1.1/1.0-import compatibility are product constraints. Local recovery shares the browser's storage and cannot replace an independent downloaded backup. Browser reminders cannot promise system-alarm delivery after closing the app.

## Release gates

1. **Use the complete product.** Inspect fresh desktop/narrow and Chinese/English/light/dark workflows, including empty/populated/error/disabled states. Complete creation, planning, review, data protection, settings and return paths. Resolve confirmed blocking functional/data-loss defects; preserve useful existing behavior and user content.
2. **Verify one final candidate.** Run the current full checker and declared cross-engine/large-workspace scope, plus checks required by the actual fixes. Bind outcomes to unchanged source and verification inputs; keep failures, interruptions and skipped scopes explicit. Follow [CONTRIBUTING.md](../CONTRIBUTING.md).
3. **Exercise real data paths.** Download and compare synthetic task/view files, restore in a clean profile, verify editing and recurrence, and test the actual prior archive through upgrade/rollback/re-upgrade. Do not infer compatibility from an unchanged schema number alone.
4. **Produce the artifact.** Build reproducible static archives, verify exact payload/manifest/checksum and execute the extracted app for persistence/offline use. Retain the previous verified artifact. A source rollback does not itself restore user data.
5. **Publish and verify.** Apply the authorized GitHub→Vercel flow, match actual HTTPS asset bodies/security headers, then use the deployed app and inspect an actual downloaded backup. The domain supplements local validation. Keep remote CI and Vercel backend provenance separate unless actually queried.
6. **Hand over current instructions.** Provide the final version/commit/artifact, concise acceptance coverage, known capability limits, upgrade/recovery instructions and support route. Keep the product README focused on use and link detailed historical evidence separately.

Physical phones, OS installation/background notifications, native IME and screen readers need their own [real-device records](manual-device-checklist.md). Leave unexecuted items blank or explicitly unexecuted rather than filling them from synthetic viewports. Those separate capability limits must be stated; they do not require inventing hardware results to complete the bounded web release.

## Commercial decisions remain separate

Muquew has confirmed copyright ownership. The public [personal non-commercial license](../LICENSE) can remain while the owner issues separate commercial rights. The preferred direction is a buyout or professional edition, but price, payment, private support and formal commercial terms remain undecided. Engineering acceptance does not create a purchase offer or grant rights. See [the commercial plan](commercial-plan.md); do not introduce payment checks that block access to existing task data.

Accounts, cloud sync, collaboration and subscriptions are not implemented by this scope. Any such feature requires a separate product and operating model decision. Optional features and paid-launch decisions are tracked separately from current engineering acceptance.

## Historical release records

The published [4.15.0](releases/4.15.0.md), [4.14.0](releases/4.14.0.md), [4.13.0](releases/4.13.0.md), [4.12.0](releases/4.12.0.md), [4.10.1](releases/4.10.1.md), [4.9.0](releases/4.9.0.md), [4.8.6](releases/4.8.6.md) and [4.8.5](releases/4.8.5.md) retain their original implementations, acceptance outcomes and failed attempts. The current [4.15.1 record](releases/4.15.1.md) has its own input identities and outcomes. Earlier program counts, measurements and deployments remain historical. [Browser compatibility](browser-compatibility.md) and [performance evidence](performance.md) explain their declared scopes.
