# CI and advanced-page theme follow-up (2026-10-02)

## Confirmed CI failures

- [Checks run 36977349133](https://github.com/twbeatles/pdf-master/actions/runs/36977349133): Windows access violation during forced garbage collection in `test_system_theme_callback_invoked_and_pruned`; the stack points to a QFluentWidgets stylesheet cleanup lambda. Commit `ab46f77` already removed the forced collection. [Checks run 36977756587](https://github.com/twbeatles/pdf-master/actions/runs/36977756587) passed afterward.
- [Expiry run 36406933115](https://github.com/twbeatles/pdf-master/actions/runs/36406933115): the bare scheduled runner imported `cryptography` through `src.core.update_manifest`, producing `ModuleNotFoundError`. The current expiry script already uses only the standard library, and run `36414602488` passed.

## Changes and prevention

- Add object names to the four advanced subpages and their scroll contents. Central scoped native QSS explicitly paints these surfaces white in light mode and dark in dark mode, instead of inheriting the OS palette. No broad QWidget rule is added to the Fluent path.
- Add a subprocess regression that constructs the real main window with a black application palette, checks all four subpages, and verifies rendered background pixels through light/dark/light transitions. The subprocess uses default settings, suppresses persistence, and isolates temporary cleanup from the user's files.
- Strengthen callback tests to assert that the weakly held host is released and its dead callback is removed, without forcing collection of unrelated Qt objects.
- Run the theme regression sequence twice in CI, fail immediately on either failure, and enable offscreen rendering and Python fault traces for the whole job.
- Run the expiry script with `python -S` in ordinary Checks too, so installed dependencies cannot mask a new third-party dependency in the scheduled script.

## Local validation

- Theme/boundary/foundation/rendering and advanced mode UI tests: 28 passed on each of two runs.
- Menu contrast gate: all four stylesheets passed.
- Dependency-free expiry gate: passed with site-packages disabled.
- `main.py --smoke`: passed with the existing local startup changes present.
- Initial theme-only commit: `8fd30a0`; GitHub Checks run `36981247149` passed.

## Reviewed remaining startup changes

At the user's request, the remaining `main.py` and startup tests are included in a subsequent commit after review:

- Keep the early splash and delayed heavy imports; place imports inside the splash cleanup block, and retain the missing-PyMuPDF preflight before main-window import.
- Use `setStaleLockTime(0)` for a process-lifetime lock and let `tryLock` recover dead-process locks. Do not forcibly delete another instance's lock. This follows the [Qt QLockFile long-lived lock contract](https://doc.qt.io/qt-6/qlockfile.html).
- Distinguish lock contention from permission/storage errors, preserving the intended unguarded startup fallback for unavailable lock storage.
- Declare Win32 function argument/result types explicitly so HWND values remain pointer-sized on 64-bit Windows; report the actual foreground request result.
- Keep the session QApplication alive in tests. Cover aged live locks, crash recovery, storage failure, real splash display, missing assets, and splash cleanup after an import failure.
- Include startup regressions in the twice-run CI sequence. Combined local startup/theme/advanced tests: 35 passed; source smoke passed.
