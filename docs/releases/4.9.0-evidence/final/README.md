# Final application evidence

Clean application commit `e7d58e2ce27798253d69b0dd9723cd55dc5c15c2` passed the [59-program checker](check-results.json), [Chromium](matrix-chromium.json), [Firefox](matrix-firefox.json) and [WebKit](matrix-webkit.json) 32-program matrices, actual old-archive upgrade, full-view 10,000×6 correctness supplement and reproducible extracted-PWA checks. All 93 source/verification inputs match the [final freeze](frozen-inputs.json). The [build record](build-result.json) retains the exact clean 797,361-byte archive; no later documentation edit rebuilt it.

The [production summary](production/production-summary.json) covers six actual-domain combinations, 27 saved and individually reviewed PNGs and 12 saved JSON downloads. Native push, deployment, screenshot and browser records retain their individual scopes and original timestamps. Separate reviews supply manual inspection without altering raw flags. The [publication record](../../../acceptance/2026-10-25/publication-4.9.0.json) links the exact native files and offline methods.

[Capture provenance](screenshot-provenance.json) describes the earlier b728fc02 visual capture: identical runtime index, four subsequent exact PNG replacements and the older dac91 helper map. The later 884396 map differs only in `tools/smoke_playwright.py`; this is not a claim that the original capture ran again under that map.

The original `evidence-inventory.json` is an engineering/push archive snapshot from before domain acceptance. Current complete provenance is [inputs-4.9.0.json](../../inputs-4.9.0.json). Linux browser checks are not physical-device, real Safari/iOS, remote-CI or Vercel backend-metadata acceptance.
