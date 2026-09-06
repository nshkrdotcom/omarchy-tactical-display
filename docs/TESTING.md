# Tests and acceptance

## Available automated suite

```bash
make test
bash scripts/validate.sh
bash scripts/validate.sh --require-native
```

Python unittest covers socket parsing/model behavior, real loopback TCP lifecycle, IPv6/UDP and FD ownership, process ancestry/CPU/I/O, storage accounting/mounts, schema/capabilities/events/limits, guarded hold ordering/locking and provider command cleanup. `test_hardening.py` additionally exercises the 8,192-process deep generic-runtime case, 20,000-contact canonical socket/constructive transport state, demand-scoped instance topology including frozen scope, generation-pinned freeze, procfs deadlines, adaptive backoff, subprocess environment reduction, MMDB isolation, NVIDIA fallback and command-rate limiting. The runtime suite starts and tears down real telemetry helpers and checks malformed transport, freeze correlation, EOF shutdown and fail-closed actions.

Node executes the production Settings, Navigation, Protocol, InstrumentModel, Inspection, Palette and Layout modules. It covers composable lenses, search, cross-instrument context, privacy/redaction, malformed/deep/non-finite data, all five modes at multiple densities/sizes, label bounds, selected reservation, contrast, expansion, audio routing focus, machine contributor metrics and bounded dense rendering. It also validates a real production-helper frame against the frontend schema.

Fixtures are fictional and test-only. They never replace real Linux/PipeWire/native integrations. Environment-dependent provider tests may skip when the corresponding real capability is unavailable; a skip is not a pass of that integration.

`scripts/validate.sh` runs the source suites, `scripts/release-gate.py --source-only`, Python and shell syntax checks, Omarchy manifest validation when available, and native QML lint when the Omarchy import tree is available. `--require-native` exits non-zero/77 if native validation cannot run.

## Publication contract regression checks

The repository tests also enforce the file-level marketplace contract that is under source control:

- required root manifest metadata and safe entry points;
- permanent non-`omarchy.*` plugin ID;
- root README with install, update/removal and dependency documentation;
- root MIT license;
- no repository symlinks;
- public documentation references only files that are part of the repository.

Public GitHub visibility, global marketplace ID uniqueness, ownership/permission, exact-commit marketplace scanning and the optional preview image are external submission facts and cannot be proven by unit tests in this repository.

## Release trust gate

Development/source verification is non-mutating:

```bash
python3 scripts/release-gate.py --source-only
```

Before publishing an immutable release, run from a clean worktree after the intended tag exists:

```bash
python3 scripts/release-gate.py --expect-tag v1.0.0
```

The release mode requires the worktree/index (including untracked files) to be clean and `HEAD` to equal the exact tag commit. It does not create or move tags.

## Visual fixtures

```bash
node scripts/render-fixtures.js --out /tmp/tactical-fixtures
```

The generated SVG matrix is developer evidence, not Qt/Wayland screenshots. Read `VISUAL-DESIGN.md` for the native visual matrix. Never feed fixtures to the production backend or present fixture output as live telemetry.

## Keyboard and focus acceptance

Source-level tests protect the shortcut ownership rules, but keyboard focus is compositor/Qt state and must also be exercised on the real Omarchy session. First inspect effective global bindings, then summon the overlay:

```bash
omarchy menu keybindings --print
omarchy-shell shell summon nshkr.tactical-display '{}'
```

If `wtype` is already available, it can make the basic sequence repeatable (do not install it solely for this test):

```bash
wtype '2'
wtype -k Tab -k Return
wtype '/'
wtype 'ssh'
wtype -k Down -k Return
wtype -k Escape
```

Observe all of the following directly:

- The overlay owns keyboard focus immediately after summon and bare `1-5` switch instruments; `Shift+1-5` and `Ctrl`/`Alt`/`Super`-modified digits do not trigger instrument switching.
- Search gives the editor normal text behavior. `Ctrl+A/C/V`, cursor/editing keys, and modified result-navigation keys are not consumed by the overlay; unmodified `Up`/`Down` traverse results and `Enter` focuses the current result.
- `F6` moves into native controls. `Tab`/`Shift+Tab`, `Enter`, and `Space` operate controls without firing field shortcuts. Mouse-click a focusable control and verify the same suppression occurs even without first pressing `F6`; the next `F6`, a field click, or a completed instrument transition restores field shortcuts.
- The instrument picker owns unmodified arrows, `Home`/`End`, bare `1-5`, `Enter`, and `Backspace`; command-modified digits are not intercepted.
- `Escape` dismisses the overlay in one stroke from field navigation, search, the picker, settings/help/capabilities, and focused controls.
- Pointer selection after control focus and reopening after a hide/summon cycle never leaves the overlay in a dead or stale keyboard-focus state.
- `make bindings` only prints Lua. If testing the optional hold binding, review collisions first, add the block manually, reload Hyprland, and verify both `Super+F11` press and the matching F11 release; `omarchy-shell shell hide nshkr.tactical-display` remains the recovery command.

Record this gate as NOT RUN unless it was actually exercised on the target Wayland/Omarchy desktop.

## Real native lifecycle and soak

```bash
python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 1800 --output /tmp/tactical-native.json
python3 scripts/audio-integration.py --run
```

The first command requires Omarchy, Hyprland and Wayland. It repeatedly summons/hides the real overlay, checks exactly one helper, verifies teardown/freshness/sequence progress, records helper and shell RSS/FD/child counts, and performs a 30-minute instrument soak. Defaults fail if helper RSS exceeds 256 MiB, helper FDs exceed 128, helper children exceed 4, helper CPU averages above 75% of one core between soak samples, ready time exceeds 5 seconds, sample latency exceeds 1.5 seconds, same-shell RSS grows more than 128 MiB, same-shell FDs grow by more than 64, or same-shell children grow by more than 16 across lifecycle cycles. These ceilings are configurable arguments for measured host-specific investigation, not permission to waive unexplained growth. Manual pointer/key/bar/hotplug/reload/visual gates still require direct observation.

The audio runner requires `pw-dump`, `pw-play` and a real sink. It creates a temporary silent stream, verifies that the actual stream and route appear, then cleans up its own stream. It does not change defaults, volume or mute.

## Profiling

```bash
python3 scripts/profile.py --instrument all --samples 40 --interval 0.75 --output /tmp/tactical-profile.json
```

This measures backend collection/transport overhead, current/high-water RSS, FD and child counts, adaptive throttle/duty cycle and cardinalities, not QML/GPU frame performance. If the kernel does not expose the procfs direct-child metric, profiling reports `childCount.available=false` instead of crashing; the native lifecycle gate is stricter and fails if it cannot enforce its configured child-process ceilings. Profile each instrument at the responsive target on the real workstation as specified in HANDOFF.md. Keep profiles, logs and screenshots outside the watched plugin tree.

Classify results as PASS (executed), FAIL (executed and failed), PARTIAL (state the exact subset), or NOT RUN (environment unavailable). Missing native tooling is never a successful native test.
