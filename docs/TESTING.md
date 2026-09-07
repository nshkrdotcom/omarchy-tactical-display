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

## Operator model and Qt interaction tests

The Node suite also executes `Operator`, `Scroll` and `TrendModel`: evidence freshness and PSI semantics, privacy parity with the field, exact key retention, high-churn bounds, late freeze ordering, baseline units, timestamp-gap path segmentation, measured scales and cursor navigation. Python exercises actual engine PSI history. When Qt Test is installed, `tests/qml` runs the production controller and `tests/qml_surfaces` exercises the real briefing, trend and shared shell: compact scrolling, delegate focus preservation, chosen-state focus borders, keyboard status activation and chart inspection.

Component tests use isolated `qs.Commons` style and Quickshell clipboard adapters because the native host's statically linked plugin modules are not loadable by standalone `qmltestrunner`. They do not substitute fake telemetry into production and are not native screenshot evidence. Native lint uses a temporary external `qs` import mapping and treats unresolved imports as errors; its regression test verifies both valid host imports and a deliberately missing module. Dynamic host-property warnings still require runtime verification.

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

## Native bar-panel geometry acceptance

Open Tactical Display by clicking its actual bar widget. The resulting surface must use Omarchy `Panel`/`KeyboardPanel` card geometry: the top bar remains visible and interactive, the panel stays inside the host-computed monitor/bar/gap bounds, and smaller outputs clamp rather than clip. Each surface must present exactly one outer frame using Omarchy's popup border specification. The fullscreen host uses `BorderSurface`; there is no separate Tactical viewport frame. On a 1280x800 scale-1 host with a 26px top bar, x=10..1270 and y=36..790 applies only when the effective shell gap is 10; actual shell style and geometry are authoritative.

Compare pointer-click and IPC launches with the same instrument and privacy setting. Title, caption and button fonts, button order, control padding, popup colors and content-relative edge clearances must match. The clicked panel's bar offset/gaps and the overlay's monitor extent are expected to differ. `tests/qml_surfaces/tst_surfaces.qml` executes production shared-header geometry at 900, 1260 and 1900 logical pixels, and live native-theme token changes with deliberately different general/popup inputs. Source contracts separately require both hosts to use that shared presentation and all four border content insets. These tests do not replace native screenshot comparisons.

Verify left-click toggle, right-click picker, outside-click dismissal, Escape, and switching between bar popouts. The bar path must not reintroduce full-output centering or generic `PanelKeyCatcher` key semantics; Tactical Display keeps its own keyboard router inside the native `KeyboardPanel`.

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
- The instrument picker owns unmodified arrows, `Home`/`End`, `Enter`, and `Backspace`; while the picker is visible, the Tactical surface routes bare `1-5` directly to instrument selection so child focus cannot swallow them. Command-modified digits are not intercepted.
- `Escape` dismisses the overlay in one stroke from field navigation, search, the picker, settings/help/capabilities, and focused controls.
- Pointer selection after control focus and reopening after a hide/summon cycle never leaves the overlay in a dead or stale keyboard-focus state.
- `make bindings` only prints Lua. If testing the optional hold binding, review collisions first, add the block manually, reload Hyprland, and verify both `Super+F11` press and the matching F11 release; `omarchy-shell shell hide nshkr.tactical-display` remains the recovery command.

Record this gate as NOT RUN unless it was actually exercised on the target Wayland/Omarchy desktop.

## Real native lifecycle and soak

```bash
python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 600 --output /tmp/tactical-native.json
python3 scripts/audio-integration.py --run
```

The first command requires Omarchy, Hyprland and Wayland. Its lifecycle phase repeatedly summons/hides the real overlay and rotates through all five instruments, checking exactly one helper, teardown, freshness, sequence progress, and helper/shell RSS/FD/child counts. Its 10-minute soak then opens one instrument once and holds it steady (default `machine`; override with `--soak-instrument`) while checking helper CPU/memory/FD/child/sample-latency containment and same-shell RSS/FD/child growth. Keeping the soak fixed avoids turning repeated `summon` calls on an already-open panel into a synthetic mode-switch mechanism; per-instrument profiles plus the lifecycle rotation already cover all instruments. Defaults fail if helper RSS exceeds 256 MiB, helper FDs exceed 128, helper children exceed 4, helper CPU averages above 75% of one CPU core between soak samples, ready time exceeds 5 seconds, sample latency exceeds 1.5 seconds, or same-shell RSS/FD/child growth exceeds 128 MiB/64/16 in either lifecycle or soak evidence. These ceilings are configurable arguments for measured host-specific investigation, not permission to waive unexplained growth. Manual pointer/key/bar/hotplug/reload/visual gates still require direct observation.

The audio runner requires `pw-dump`, `pw-play` and a real sink. It creates a temporary silent stream, verifies that the actual stream and route appear, then cleans up its own stream. It does not change defaults, volume or mute.

Native lifecycle/soak launches explicitly request privacy for that invocation, so automated desktop checks do not display host identities or change the saved privacy preference. Avoid editing files anywhere in the watched plugin tree during a soak: Omarchy intentionally reloads changed plugins, dismissing the open surface and invalidating that run. Keep evidence and any concurrent development outside the plugin tree.

On native-runner failure, `failureContext` records matching helpers and the last known helper/shell process state **before cleanup**. This distinguishes a missing loaded plugin instance from exited processes without allowing automatic hide/unload to erase that evidence. Compare `startTicks` with prior samples before interpreting a reused PID. The runner does not relax its limits or silently reopen a lost instance.

Overlay lifecycle debug lines distinguish an explicit plugin hide request (`escape`, `back`, `close-control`, `native-panel`, `no-screens`) from host close and component destruction. The reason is allowlisted and contains no entity identity or payload. A host close without a preceding hide request is not evidence of a keyboard dismissal inside the plugin. Inspect these with `quickshell log -p "$OMARCHY_PATH/shell" --no-color` when a native run loses its instance.

## Profiling

```bash
python3 scripts/profile.py --instrument all --samples 40 --interval 0.75 --output /tmp/tactical-profile.json
```

This measures backend collection/transport overhead, current/high-water RSS, FD and child counts, adaptive throttle/duty cycle and cardinalities, not QML/GPU frame performance. If the kernel does not expose the procfs direct-child metric, profiling reports `childCount.available=false` instead of crashing; the native lifecycle gate is stricter and fails if it cannot enforce its configured child-process ceilings. Profile each instrument at the responsive target on the real workstation. Keep profiles, logs and screenshots outside the watched plugin tree.

Classify results as PASS (executed), FAIL (executed and failed), PARTIAL (state the exact subset), or NOT RUN (environment unavailable). Missing native tooling is never a successful native test.
