# Validation report — Tactical Display 1.0.0-rc.1

Evidence date: **2026-09-05 UTC**. Baseline: supplied 0.2.0 Repomix, **33 reconstructed files**, original **24 tests passed**, original source checksums matched. No baseline Git commit was supplied. Repomix SHA-256: `464de03ba6b8613276ad89af0d05c507993d91121d7727c7b24a448f1e0f85b1`.

## Release status

The five required instrument implementations and shared product shell are present with real production providers; fixtures are not used by the plugin. This is a **release candidate pending native desktop acceptance**, not a claim of 100% correctness, world-class visual certification, or successful execution on the user's workstation. The current environment cannot compile/load/render Quickshell or operate a Hyprland/PipeWire desktop. That limitation remains a release gate, even though all available automated checks pass.

The runtime integration was reviewed against **Omarchy tag v4.0.1**. A source-tag review is not an installed-host validation. See [UPSTREAM-CONTRACT.md](UPSTREAM-CONTRACT.md), [TRACEABILITY.md](TRACEABILITY.md), and the exact target procedures in [HANDOFF.md](HANDOFF.md). The complete supplied specification is preserved under `docs/specification/`; its PROMPT is explicitly identified as a restatement of the conversation, not a missing uploaded original.

## Executed checks

| Gate | Status | Evidence / exact scope |
|---|---|---|
| Original baseline | **PASS** | 24 tests, 33 source files; supplied manifest checked before modifications. |
| Final Python suite | **PASS with 3 explicit skips** | **74 cases: 71 passed, 3 skipped, 0 failures**, 33.146 s in the working tree; full suite rerun during overlay verification. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v`. |
| Frontend model/layout suite | **PASS** | **57 passed, 0 skipped, 0 failures**. `node --test --test-reporter=spec tests/js/*.test.js`. Executes the production JS model, configuration, navigation, protocol, palette, layout and rendering logic. |
| Python and shell syntax | **PASS** | Python compile checks on 36 source/test scripts; `bash -n` on every shell script. These are not Python static typing or shellcheck results. |
| Real Linux network integration | **PARTIAL** | Real TCP listen/connect/accept/close, loopback, IPv4, IPv6, UDP and shared FD ownership passed; no Internet needed. Controlled non-loopback inbound test skipped as described below. |
| Real process and storage integration | **PASS** | Actual process ancestry/start identity/CPU/I/O/exit, mounted filesystem enumeration and temporary write/fsync counters. Cached/tmpfs activity is not falsely required to produce physical disk traffic. |
| Helper transport/lifecycle | **PASS** | Real subprocess NDJSON, partial lines, malformed input, bounded children/output, EOF teardown, frozen-detail integrity and **50 actual helper start/sample/stop cycles**. This is not 50 native overlay cycles. |
| Hold invocation ordering | **PASS** | Real subprocess/locking tests exercise press/release races, release-before-open, repetition, token/permission/confinement checks. Physical compositor key events remain NOT RUN. |
| Config/privacy/IDs/events/truth | **PASS** | Defaults/schema/unknown-key preservation, protocol rejection, redaction, stable PID/start IDs, counter resets/unknown initial rates, listener backlog units, bounded events/trends and incomplete-scan preservation. |
| Native source contracts | **PARTIAL** | Root Item, entry-point paths/kinds, per-screen helper ownership, optional dependencies and relative imports checked by source tests. A duplicate QML signal handler was reproduced as a failing test and fixed; the lexical guard now passes. These checks do not replace Qt compilation. |
| Deterministic visuals | **PARTIAL** | **50 explicitly labelled fixture SVGs generated** with shared production JS; bounds/density/label allocation and theme contrasts tested. Five representative SVGs and the full metrics index are included. SVG text approximates Qt metrics and these are not native screenshots. |
| Short backend profile | **PASS** | 40 actual all-provider samples; measurements below. Not shell CPU/FPS, an open/closed desktop comparison, or a long leak test. |
| Overlay reconstruction / final checksums | **PASS** | Reconstructed the untouched 33-file baseline, verified its checksum list before extraction, extracted only changed/new paths, ran the guarded six-file deletion helper, compared all final source bytes and executable modes, reran the complete 74-case Python / 57-case frontend suites, checked both checksum manifests, archive CRC and unchanged baseline. Repeated for the final evidence-bearing ZIP. |
| Omarchy manifest validator and native qmllint | **NOT RUN** | No Omarchy, Qt, Quickshell or native import tree installed. The available validator command explicitly reports missing native tools; it does not count them as successes. |
| Real PipeWire graph / controlled audio stream | **NOT RUN** | `pw-dump`/`pw-play` and a PipeWire session unavailable. Structured graph/default/client-ownership parser tests pass; the real graph test skips. Opt-in actions not executed. |
| Native overlay/bar/keyboard/pointer/accessibility | **NOT RUN** | No Wayland/Hyprland session. Includes focus, Escape, hold, picker, search, freeze interaction, horizontal/vertical bar and teardown after host unload. |
| Multi-monitor / scaling / hotplug | **NOT RUN** | Focused/explicit-monitor and fallback paths implemented, but no hardware/session to exercise them. |
| Native screenshots / visual user acceptance | **NOT RUN** | Needs all five instruments, quiet/normal/dense/focus/search/degraded, light/dark/reduced motion, real fonts and scaling on target. |
| Shell restart / hot reload / 50 overlay cycles / 30-minute soak | **NOT RUN** | A real-target runner and manual matrix are supplied. No native stability, frame pacing or memory-leak certification is claimed. |

### Exact Python skip reasons

1. `test_real_inet_diag_when_kernel_allows`: `[Errno 2] inet_diag kernel error`. The procfs fallback and binary length/metric parsers were separately exercised successfully. This kernel error is not a reason to elevate privilege.
2. `test_real_nonloopback_accepted_direction_and_aggregation`: no resolvable non-loopback address for a controlled inbound test. Local accepted TCP sockets and deterministic listener/service classification were tested; true non-loopback acceptance still needs the target gate.
3. `test_real_pipewire_session_when_available`: `pw-dump` not installed. The required provider implementation is real structured PipeWire JSON, not a fixture fallback.

No ignored test failures remain. A skip is not a pass of its underlying integration. The no-session preflights for `live-validate.py --run` and `audio-integration.py --run` also returned **NOT RUN**, not success.

## Measured backend profile

Environment: Linux **6.18.35 x86_64**, glibc **2.41**, Python **3.13.5**, Node **22.16**, Debian container reporting **5 CPUs**. No installed Omarchy/Hyprland/Quickshell/Qt/PipeWire versions exist to report. No ruff, shellcheck or native qmllint result is claimed.

Command: `python3 scripts/profile.py --instrument all --samples 40 --interval 0.25 --output /tmp/tactical-profile.json`.

| Measurement | Actual value |
|---|---:|
| Recorded samples / duration | 40 / 9.764 s |
| Sample duration median / p95 / max | **6.858 / 10.534 / 35.941 ms** |
| Sampler CPU, percentage of one core | **3.444%** |
| Largest serialized frame | **73,389 bytes** |
| Current resident memory, first / last | **94,876 / 95,248 KiB** |
| Maximum resident memory observed | **95,248 KiB** |
| Initial/final entities | 16 processes, 5 relationships, 17 mounts, 0 audio nodes |

All-provider 4 Hz collection deliberately exercises more work than the normal single-instrument profile. The CPU value is the sampler's own CPU; it is not a fabricated whole-shell/vendor-child measurement. This short record cannot establish a 30-minute leak trend. It also cannot justify a universal target CPU/RSS claim. Missing GPU, thermal and audio capabilities were correctly reported as unavailable. Exact raw aggregate measurements are in [evidence/backend-profile.json](evidence/backend-profile.json); no private telemetry entity history is shipped.

## Visual review and corrections

The shared-renderer review addressed aggregate-first Connection Field focus (avoiding an explosion into per-process sockets), unrelated applications leaking into shared-remote focus, process-group expansion at low density, visible storage read/write metadata, screen-space labels reserved for selection, and transitive Audio Routing focus from application through mixer to sink. Machine contributors now use the selected subsystem's metric rather than displaying CPU values under a memory focus. Malformed/Unicode names are bounded; sanitized mount paths are never used to probe a different filesystem path.

Reviewed proxy compositions show a local process plane and remote horizon, ancestry/application islands, a subsystem cutaway, storage planes, and an actual signal-routing board. Light-theme audio and dense selected connections were inspected after the final focus fixes. The examples communicate these meanings in the proxy review, but **the required unfamiliar-user/native screenshot acceptance has not run**. No assertion is made that all native label collisions, control dimensions, accessibility focus, font metrics or compositor performance are already proven correct.

Generate the full matrix using `node scripts/render-fixtures.js --out /tmp/tactical-display-fixtures`. It is test-only and clearly watermarked. Do not turn fixture mode into a production fallback.

## Remaining release gates and intentionally conditional scope

Run [HANDOFF.md](HANDOFF.md) on the actual 4.0.1 desktop, fix any plugin-local compile/runtime/visual failures, then record exact versions, logs, user answers, screenshots, CPU/RSS trends and outcomes. The supplied native runner performs real summon/hide/cycle/soak calls and identity-free diagnostics, not simulated acceptance. Physical interaction, monitor changes and frame assessment still require the operator matrix.

Optional inet_diag, hardware sensors, reverse DNS, local MMDB, and confirmed mute/default/undo paths are implemented with capability gates; unavailable/opt-in target paths were not fabricated as tested. Stream rerouting, terminal launch actions and Workspace/Agent Topology are not claimed: the supplied plan makes these conditional after required acceptance, and reliable agent state / a safe validated route API must precede any such UI. No privileged packet tracing, destructive process/disk/network action or fabricated audio level is shipped.

The ZIP contains only changed/new repository-relative files, six explicit deletion entries, the authoritative docset, current docs/tests, source/overlay/baseline checksums and evidence. Archive SHA-256 is recorded externally to avoid a self-reference. Consult root `OVERLAY_INFO.md` for exact file counts and inventory.

## Artifact verification log

The evidence-bearing release includes [evidence/reconstructed-validation.txt](evidence/reconstructed-validation.txt), the complete successful test/validation output from a pristine overlay reconstruction. The final tree is compared again after tests. Initial noninteractive attempts hit the execution runner time limit; the complete command was subsequently executed to completion in a monitored, separately launched validation process. Those interrupted attempts were not counted as passes. Native tool absence remains explicit in the successful available-gates log. The final ZIP identity and exact inventory are external checksum / OVERLAY_INFO metadata, not a self-referential embedded ZIP checksum.
