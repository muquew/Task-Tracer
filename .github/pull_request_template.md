## Problem and result

Describe the user-visible problem and the resulting behavior. Link the relevant issue when available.

## Validation

List the checks actually run and their results. Explain checks not run. Use synthetic task data; do not attach personal exports or browser profiles.

- Use `npm run check` for static checks and `npm run styles:check` when styles change.
- Use `npm run test:report` for the full suite with `dist/check-results.json`; use `npm run test:browsers -- --browser chromium --group capture` for a targeted browser group, changing the engine and group as needed. State the actual scope; targeted runs do not represent the complete matrix.

## Compatibility and remaining risks

Describe effects on stored tasks, imports, recurrence, offline use or upgrades when relevant. For other changes, write “No data-format change.” See [Development](../README.md#development-and-contributions) for setup and checks. Keep app/cache versions and translations aligned; regenerate CSP hashes after inline-script changes.
