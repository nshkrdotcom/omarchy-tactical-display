# Tactical Display 1.0.0 hardening handoff

This handoff is for the next agent running on the actual Omarchy Quattro workstation. The hardening pass was implemented against the supplied 1.0.0 repository and intentionally preserves the existing product/UI model while tightening resource containment, lifecycle supervision, optional-provider isolation and release validation.

## What changed

- Network snapshots now keep each full socket record once in a helper-only canonical store. Aggregate relationships retain socket keys/counts, while the per-process relationship layer is demand-scoped to at most 64 application groups currently expanded/carried as Connection Field context instead of being rebuilt globally. Detail paging resolves keys against the pinned store.
- Freeze now pins the current immutable-by-replacement snapshot generation and socket store instead of `deepcopy`-ing the entire object graph. Live collection proceeds by replacing the live generation. Expanding/collapsing while frozen derives only the requested instance layer from the pinned store and returns a replacement bounded frozen view without mutating the capture.
- Transport is constructed to a 1.5 MiB target with deterministic per-collection byte shares and a 4 MiB emergency ceiling. The old repeated whole-frame JSON/halve loop is gone. `limits.omitted`, `transportBytes`, `transportTargetBytes`, `adaptiveThrottleLevel`, `targetIntervalSeconds`, and `samplerDutyCycle` expose containment decisions.
- Generic-runtime process grouping (Python/Node/Java/BEAM/etc.) uses ancestry path compression rather than repeated ancestor walks. The adversarial 8,192-process chain test dropped from roughly 8.5 seconds before the change to roughly 50 ms in the implementation environment.
- `/proc` PID discovery and socket-table collection now use absolute deadlines. Socket collection has one global contact/work budget across TCP4/TCP6/UDP4/UDP6 rather than effectively granting each table a fresh full limit.
- Expensive socket-FD ownership is multi-rate. Cached ownership is reused between full scans, with a short bounded scan for newly observed inodes so new connections do not remain needlessly unattributed.
- The engine adaptively increases its effective interval after sustained high sampler duty cycle and slowly recovers after sustained low duty cycle. This is visible in telemetry limits/capabilities rather than silently pretending the requested cadence was met.
- The principal helper is launched through Quickshell as fixed `/usr/bin/python3` with `clearEnvironment`, and provider subprocesses resolve executables against a fixed system path; both receive a reduced user-session environment so PYTHONPATH/user-site and dynamic-loader overrides are not propagated. External commands remain argv-only, output/time bounded, process-group-contained and reaped.
- Offline MaxMind enrichment no longer opens or queries the database in the principal telemetry helper. One bounded one-shot `mmdb_worker.py` process performs lookup/open work and is killed on timeout, close or privacy activation. It can load a system-installed `maxminddb` package while `PYTHONNOUSERSITE=1` prevents user-site package injection. DNS remains a separate isolated worker.
- `pw-dump` output is limited to 2 MiB. `nvidia-smi` is now a true fallback and is not launched when DRM sysfs already supplied a GPU observation.
- The helper command flood limit is a real 32-record/second sliding-window limit rather than a counter reset by pipe read boundaries.
- QML helper supervision now distinguishes process-started from telemetry-ready. A valid schema-3 snapshot is required before `ready`; first-frame, stale-progress and repeated-invalid-record watchdogs restart the helper through the existing bounded six-retry backoff. Retry performs a real helper restart. `/usr/bin/python3` is used explicitly on the Omarchy/Arch target with a cleared/reduced environment. Stop/restart sends SIGTERM and escalates to SIGKILL after 1.2 seconds; QML destruction uses immediate SIGKILL.
- Frontend schema validation now also bounds PipeWire `clients` and `ports` collections.
- Native lifecycle validation records helper/shell RSS, FD counts and child counts, helper CPU, ready latency and sample latency; it enforces configurable helper ceilings and shell growth ceilings while still verifying one helper, sequence progress and teardown.
- `scripts/release-gate.py` adds source/repository invariants and an exact-tag/clean-tree release check.

## Tests added/strengthened

`tests/test_hardening.py` covers:

- 8,192-process generic-runtime ancestry complexity;
- canonical socket detail storage, key-only relationship models and demand-scoped instance topology;
- generation-pinned freeze behavior;
- constructive high-cardinality transport bounds;
- absolute procfs socket deadlines;
- stripped Python/loader injection environment;
- main-helper MMDB isolation;
- NVIDIA vendor-tool fallback behavior;
- adaptive sampler backoff;
- sliding-window command-rate limiting.

The QML contract tests require valid-frame readiness/watchdogs and the fixed interpreter path. Repository tests require this handoff and the release gate. The shared-renderer stress assertion was tightened from 3 seconds to 750 ms for the measured model/layout section.

## Implementation-environment evidence

- Final non-native Python pass: **91 tests passed**, with 3 environment-dependent provider integrations skipped because this environment lacks permitted inet_diag, a controlled non-loopback route, and PipeWire. The intentionally retained 50-rapid-helper-cycle test is excluded from that count for the sandbox limitation documented below.
- Final Node production-model/layout pass: **59 tests passed**. Python compile, shell syntax, `git diff --check`, README/license invariants and `scripts/release-gate.py --source-only` also passed.
- The adversarial 8,192-process generic-runtime chain is roughly **50 ms** here versus roughly **8.5 s** before path compression.
- A 20,000-contact production-style aggregate-only synthetic run measured roughly **273 ms** aggregate modeling and **55 ms** constructive transport, emitted about **366 KiB**, and reached about **177 MiB** Python-process high-water RSS. This is synthetic stress evidence, not a target-workstation guarantee; the audited pre-hardening worst case was roughly 2 s aggregate modeling plus 2.24 s transport with about 397 MiB peak.
- An 8-sample real local Connection Field backend profile at the 0.35 s target measured ~**6.6 ms p50**, **7.3 ms max**, and ~**2.3% of one CPU core** in this environment. The procfs direct-child metric is absent here, so that profile correctly reported `childCount.available=false`.

## Required Omarchy completion gates

Run these from the installed repository on the real workstation. Do not mark a native item PASS unless it actually executes.

```bash
cd ~/.config/omarchy/plugins/nshkr.tactical-display

bash scripts/doctor.sh
bash scripts/validate.sh --require-native
omarchy plugin validate .

python3 scripts/profile.py --instrument connection --samples 120 --interval 0.35 --output /tmp/tactical-profile-connection.json
python3 scripts/profile.py --instrument processes  --samples 120 --interval 0.35 --output /tmp/tactical-profile-processes.json
python3 scripts/profile.py --instrument machine    --samples 120 --interval 0.35 --output /tmp/tactical-profile-machine.json
python3 scripts/profile.py --instrument storage    --samples 120 --interval 0.35 --output /tmp/tactical-profile-storage.json
python3 scripts/profile.py --instrument audio      --samples 120 --interval 0.35 --output /tmp/tactical-profile-audio.json

python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 1800 --output /tmp/tactical-native.json
python3 scripts/audio-integration.py --run
```

Review all profile outputs for sample p95/max, current/high-water RSS, FD/child counts, adaptive throttle level/duty cycle and transport truncation. `childCount.available=false` means that procfs metric is absent; profiling remains usable, but the native lifecycle gate intentionally fails because it cannot enforce the child ceiling. The native lifecycle runner defaults to: 256 MiB helper RSS, 128 helper FDs, 4 helper children, 75% of one CPU core between soak samples, 5 s ready latency, 1.5 s sample latency, 128 MiB same-shell RSS growth, 64 same-shell FD growth and 16 same-shell child growth. Adjust a ceiling only after determining that the observed baseline is legitimate, and document why.

## Native behavior that specifically needs direct verification

1. **Helper stop semantics.** Verify the implemented target path directly: normal stop/watchdog restart must send SIGTERM and, if the helper remains alive for 1.2 seconds, `Process.signal(9)` must force termination; QML destruction uses immediate SIGKILL. Confirm Quickshell emits `onExited`, the child is reaped, restart happens only when intended, and there is never a surviving telemetry helper after hide, destruction, watchdog restart or shell restart.
2. **Exclusive-keyboard failure recovery.** With the overlay visible, induce a helper failure/stall and confirm Escape still dismisses immediately and the shell stays responsive while watchdog recovery occurs.
3. **Responsive-profile system impact.** Exercise real high-process/high-socket workloads. Confirm adaptive backoff engages before the overlay becomes materially invasive and returns toward the requested profile when the machine settles.
4. **PipeWire.** Run the real audio integration, repeatedly enter/leave Audio Routing, and verify the 2 MiB `pw-dump` budget is not too low for the workstation graph. If it is, increase it narrowly with measured evidence rather than restoring the generic 8 MiB command ceiling.
5. **Optional audio actions.** With `tdAudioActions` explicitly enabled, verify mute/default/undo and the documented PipeWire serial/object race behavior. Observation must remain the default.
6. **MMDB.** If a real local MaxMind database is available, verify asynchronous enrichment, missing-module behavior, invalid/slow paths, privacy cancellation and close cleanup. No database open/query may occur in the principal helper.
7. **DNS privacy.** Enable DNS naming, observe worker activity, then activate privacy and confirm workers/pending requests are immediately cleared and no further PTR queries are issued.
8. **GPU.** On NVIDIA hardware verify DRM sysfs suppresses `nvidia-smi` when sufficient GPU telemetry exists, and that `nvidia-smi` runs only when the sysfs GPU observation is absent. Also test non-NVIDIA hardware.
9. **Monitor/hotplug and shell reload.** Complete the manual gates reported by `live-validate.py`: monitor hotplug, keyboard hold/release, bar orientation/clicks, hot reload, shell restart and the visual matrix in `docs/VISUAL-DESIGN.md`.
10. **Demand-scoped expansion and transport truncation UX.** Repeatedly expand/collapse applications in live and frozen Connection Field and verify aggregate data remains visible until the requested instance layer arrives, no unrelated instance graph is streamed, and frozen expansion remains tied to the captured generation. Then create a deliberately high-cardinality real workload and verify `limits.omitted`/density status remains understandable. Transport omissions are intentionally reported rather than pretending every omitted entity remains searchable in that frame.
11. **Fixed interpreter/environment.** Confirm `/usr/bin/python3` is the correct system interpreter on the supported Omarchy target; confirm Quickshell accepts `clearEnvironment`, `environment` and `Process.signal(...)`; and confirm the helper imports the plugin package from its working directory without relying on user-site/PYTHONPATH state. Inspect the actual child environment to ensure the explicit Wayland/DBus/PipeWire/session variables are sufficient.

## Release gate

Before tagging/publishing 1.0.0, after all native fixes are committed and the worktree is clean:

```bash
python3 scripts/release-gate.py --source-only
git status --short
git tag -a v1.0.0 -m 'Tactical Display 1.0.0'
python3 scripts/release-gate.py --expect-tag v1.0.0
```

If the release tag already exists upstream, do **not** silently move it. Resolve release/tag policy explicitly and then run the exact-tag check against the intended immutable release commit.

## Documentation/release invariants

- Version remains **1.0.0**.
- `CHANGELOG.md` dates 1.0.0 as **2026-09-06** and includes this hardening buildout.
- Keep the README badge block, `preview.png` image placement, overall section structure and exact final License section unchanged.
- Do not weaken procfs permissions, add sudo/capabilities, introduce packet capture/eBPF, add a resident daemon, or turn optional DNS/MMDB into automatic network/download behavior.
- Keep evidence/profile/log files outside the watched plugin checkout.

## Environment limitations of this handoff

The implementation environment could exercise Linux procfs/socket behavior, Python unit/integration tests and Node production model/layout code, but it is not the target Omarchy/Hyprland/Wayland desktop. Native QML import/lint/runtime behavior, actual shell resource growth, compositor focus/hotplug, PipeWire session behavior, NVIDIA tooling, real MMDB enrichment and the long-running 30-minute native soak must therefore be completed on the workstation using the gates above. The source-level 50-cycle helper lifecycle test also could not complete in this sandbox after roughly 40-45 rapid launches because the execution environment began throttling/freeze-blocking new child launches; no leaked helper was observed afterward. Do not weaken that test: rerun the complete 50-cycle gate in the real Omarchy environment and treat any target-side stall as a defect.
