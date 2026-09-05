# Tactical Display implementation rules

Read README.md, docs/HANDOFF.md, docs/VALIDATION.md and docs/TRACEABILITY.md before changing this code. The supplied authoritative spec is preserved in docs/specification/. Target runtime contract: tagged Omarchy v4.0.1; verify installed source before upgrading it.

1. Keep one hosted Item overlay and one lightweight native bar widget. No ShellRoot, second Quickshell, privileged daemon, hidden install hook or backend while closed.
2. Production input comes from td_telemetry providers. Fixtures are test-only. Never advertise inferred origin, FD-to-mount associations, RSS sums or audio gain as stronger measurements than they are.
3. Keep PID+start-tick identities, per-provider capability/freshness, monotonic deltas, incomplete-snapshot suppression, bounded protocol/history/layout work and independent frozen inspection.
4. Add a failing behavior test for a regression, implement the real path, run Python plus Node tests. Static QML contract tests are not runtime acceptance. Use actual Quattro/qmllint and screenshot review on the target.
5. Preserve unknown native inline settings. Do not replace shell.json behind the host. Default DNS/actions off; no full argv or environment capture.
6. Put logs, profiles and screenshots OUTSIDE the watched plugin tree during target testing. Keep private runtime observations out of release fixtures/evidence.
7. Leave source, tests, docs and manifests consistent. Never mark NOT RUN as PASS. Do not call visual/native acceptance complete without the target evidence.
8. Delivery is an overlay against the exact supplied baseline: only changed/new paths; explicit OVERLAY_DELETE.txt; checksum verification and pristine reconstruction. Do not include caches, credentials, font binaries or whole baseline archives.

Architecture boundaries: td_telemetry -> schema-3 NDJSON -> Protocol.js -> InstrumentModel/Navigation -> Layout/Draw -> QML field and shared shell. Pure JS is shared verbatim with Node tests. Public helper commands are an allowlist, not arbitrary shell execution. Runtime dependency policy is stdlib-first; Node is test-only.

Commands: `make test`, `bash scripts/validate.sh --require-native`, `python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 1800 --output /tmp/tactical-native.json`. The latter takes/relinquishes overlay keyboard focus; run only with operator consent. All optional gates and known limitations are explicit in the handoff.
