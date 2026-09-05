# Tests and acceptance

## Available automated suite

```bash
make test
bash scripts/validate.sh
bash scripts/validate.sh --require-native
```

Python unittest covers preserved socket parsing/model tests, real loopback TCP listener/client/accepted/closed lifecycle, IPv6 and UDP, actual FD ownership including shared sockets, process ancestry/CPU/I/O, real temporary fsync writes/mounts, schema/capabilities/events/limits, guarded hold ordering/locking and provider command cleanup. The runtime suite creates and tears down **50 actual telemetry helpers**, checks partial stdin frames/malformed commands/freeze correlation/EOF shutdown and fails closed for unapproved actions. This is not 50 desktop opens.

Node executes the same production Settings, Navigation, Protocol, InstrumentModel, Inspection, Palette and Layout functions. It checks composable lenses, fuzzy search, cross-instrument instance context, stability, privacy/copy redaction, malformed/deep/non-finite data, all five modes at quiet/normal/dense and multiple sizes, collision-free primary labels, selected reservation, contrast, explicit expansion, directed Audio focus, metric-aware Machine focus and dense render bounds. It also starts the **real production helper** and validates its frame with the frontend schema.

Fixtures are deliberately fictional and only imported by tests/render tooling. Deterministic fixture edge cases do not replace real Linux/PipeWire/native integrations. A missing inet_diag capability, non-loopback test address or PipeWire session results in a reasoned skip. Check the skipped list on the real target; do not count it as passed.

The validation script runs source tests, Python compilation without bytecode output, shell syntax, manifests/checksums, then installed native manifest validation and QML lint when available. Exit 77 under `--require-native` means an environment-dependent gate was unavailable, not success. The normal non-native mode reports PARTIAL explicitly.

## Visual fixtures

```bash
node scripts/render-fixtures.js --out /tmp/tactical-fixtures
```

50 SVG combinations plus metrics are developer evidence, not Qt captures. Read VISUAL-DESIGN.md for what was actually inspected and the target matrix. Never remove their test labels or feed them to the production backend to claim a live test.

## Real native lifecycle and soak

```bash
python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 1800 --output /tmp/tactical-native.json
python3 scripts/audio-integration.py --run
```

The first requires actual Omarchy, hyprctl and a Wayland session, takes keyboard focus as it cycles the overlay, checks the native read-only diagnostic method, validates exactly one helper at each open, verifies helper exit after hide, samples real helper/shell CPU counters/RSS and cycles modes through a 30-minute soak. Its report leaves pointer/key/hold/bar/hotplug/reload/visual gates explicitly NOT RUN. Read and exercise those separately. A shorter run never qualifies as the 30-minute gate.

The audio runner requires real pw-dump/pw-play and a sink. It plays 12 seconds of generated silence in a temporary WAV, verifies the actual stream and outgoing PipeWire route, then terminates its own stream. It does not alter defaults/volume/mute, perform a destructive device change or use fixture routes. Missing session/sink/tools exits 77.

## Profiling

```bash
python3 scripts/profile.py --instrument all --samples 40 --interval 0.75 --output /tmp/tactical-profile.json
```

Reports actual sample p50/p95/max, JSON frame size, own CPU time and current/high-water RSS, counts and capability statuses. No raw process/socket names are saved. This measures backend collection/serialization overhead, not QML model/layout or GPU frames. Native diagnostics add rendered counts and measured QML layout milliseconds; the live runner records real process stats. Review CPU deltas per clock tick and RSS across comparable points, not one high-water sample as a leak verdict.

For desktop frame hitches, run the existing shell with its supported Qt/Quickshell profiling tools only after preserving the normal launch environment; do not start a second competing shell. Save observations and actual timings, compare closed/open idle, generate a realistic workload and inspect every mode. Exact manual recipes and pass/fail criteria are in HANDOFF.md.

## Overlay acceptance

The delivered ZIP is tested over a pristine reconstructed baseline, deletion metadata applied, final files compared byte-for-byte, complete automated tests rerun and both checksum manifests verified. OVERLAY_BASELINE.sha256 verifies the supplied baseline before extraction. MANIFEST.sha256 covers the final content tree except checksum self/cyclic entries; OVERLAY_MANIFEST.sha256 covers ZIP payload except itself. Untracked caches/.git are not product content.

Classify gates as PASS (executed), FAIL (executed and failed), PARTIAL (state exact subset), or NOT RUN (missing environment). Native command not installed is never a successful native test.
