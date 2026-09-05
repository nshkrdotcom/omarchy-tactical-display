# Tests and acceptance

## Available automated suite

```bash
make test
bash scripts/validate.sh
bash scripts/validate.sh --require-native
```

Python unittest covers socket parsing/model behavior, real loopback TCP lifecycle, IPv6/UDP and FD ownership, process ancestry/CPU/I/O, storage accounting/mounts, schema/capabilities/events/limits, guarded hold ordering/locking and provider command cleanup. The runtime suite starts and tears down real telemetry helpers and checks malformed transport, freeze correlation, EOF shutdown and fail-closed actions.

Node executes the production Settings, Navigation, Protocol, InstrumentModel, Inspection, Palette and Layout modules. It covers composable lenses, search, cross-instrument context, privacy/redaction, malformed/deep/non-finite data, all five modes at multiple densities/sizes, label bounds, selected reservation, contrast, expansion, audio routing focus, machine contributor metrics and bounded dense rendering. It also validates a real production-helper frame against the frontend schema.

Fixtures are fictional and test-only. They never replace real Linux/PipeWire/native integrations. Environment-dependent provider tests may skip when the corresponding real capability is unavailable; a skip is not a pass of that integration.

`scripts/validate.sh` runs the source suites, Python and shell syntax checks, Omarchy manifest validation when available, and native QML lint when the Omarchy import tree is available. `--require-native` exits non-zero/77 if native validation cannot run.

## Publication contract regression checks

The repository tests also enforce the file-level marketplace contract that is under source control:

- required root manifest metadata and safe entry points;
- permanent non-`omarchy.*` plugin ID;
- root README with install, update/removal and dependency documentation;
- root MIT license;
- no repository symlinks;
- public documentation references only files that are part of the repository.

Public GitHub visibility, global marketplace ID uniqueness, ownership/permission, exact-commit marketplace scanning and the optional preview image are external submission facts and cannot be proven by unit tests in this repository.

## Visual fixtures

```bash
node scripts/render-fixtures.js --out /tmp/tactical-fixtures
```

The generated SVG matrix is developer evidence, not Qt/Wayland screenshots. Read `VISUAL-DESIGN.md` for the native visual matrix. Never feed fixtures to the production backend or present fixture output as live telemetry.

## Real native lifecycle and soak

```bash
python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 1800 --output /tmp/tactical-native.json
python3 scripts/audio-integration.py --run
```

The first command requires Omarchy, Hyprland and Wayland. It repeatedly summons/hides the real overlay, checks exactly one helper, verifies teardown and freshness, and performs a 30-minute instrument soak. Manual pointer/key/bar/hotplug/reload/visual gates still require direct observation.

The audio runner requires `pw-dump`, `pw-play` and a real sink. It creates a temporary silent stream, verifies that the actual stream and route appear, then cleans up its own stream. It does not change defaults, volume or mute.

## Profiling

```bash
python3 scripts/profile.py --instrument all --samples 40 --interval 0.75 --output /tmp/tactical-profile.json
```

This measures backend collection/serialization overhead, not QML/GPU frame performance. Keep profiles, logs and screenshots outside the watched plugin tree.

Classify results as PASS (executed), FAIL (executed and failed), PARTIAL (state the exact subset), or NOT RUN (environment unavailable). Missing native tooling is never a successful native test.
