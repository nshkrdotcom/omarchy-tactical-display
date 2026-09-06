# Architecture and implementation decisions

## Boundaries

```text
Quattro shell (one existing long-running Quickshell)
  |-- BarWidget.qml -> native bar styling/lifecycle; no sampler
  |     `-- Panel.qml -> Omarchy Panel / KeyboardPanel geometry
  |           |-- Configuration + NavigationController + one Telemetry helper
  |           `-- TacticalDisplayShell
  `-- Overlay.qml (hosted Item, shell/compositor fullscreen route)
        |-- Configuration (native inline settings, unknown-field-preserving)
        |-- NavigationController (selection/context/history/freeze)
        |-- Telemetry (one supervised Process, NDJSON validation)
        |     `-- scripts/telemetry.py
        |           `-- td_telemetry/{processes,network,machine,storage,audio,hardware,enrichment}
        |                 -> normalized entities + capability map + bounded events
        `-- selected PanelWindow / TacticalDisplayShell

TacticalDisplayShell -> InstrumentModel -> Layout -> Draw / Field
                     -> InspectionPanel, CommandSheet, Trend
```

`model/` separates configuration, typed navigation intent, telemetry validation, instrument transformations and inspection. `visual/` owns stable layout, collision/label budgets, palette contrast and rendering. No instrument delegate reads Linux files or spawns commands. One shared renderer has **five distinct semantic model/layout/drawing paths**, not five labels over a generic percentage dashboard.

## Design decisions

**Use the actual native settings API.** Tagged Quattro exposes `shell.updateEntryInline`; the release merges existing inline entry keys before calling it because the host replaces that entry's fields. A second private configuration file would create conflicting authorities. Newer settings versions are read-only. A missing enablement entry yields explicit session-only behavior.

**Aggregate first, normalize details once.** Default/focused Connection Field retains application relationships; `X` reveals individual process instances. The helper stores each full socket observation once in a canonical generation-local store. Aggregate relationships are built every relevant sample; the per-instance network layer is demand-scoped to only the application groups currently expanded or carried as Connection Field context, and is regenerated immediately when that scope changes. Both layers retain socket keys/counts rather than duplicate child dictionaries; inspection pages resolve those keys on demand. Following a shared remote must not accidentally select every unrelated application. Process Topology unfolds small trees immediately and collapses large application populations until selected/searched. Audio focus follows directed paths all the way from the selected sink to its upstream streams, without traversing sideways across unrelated routes.

**Retain the portable fallback, add measured kernel capability.** Procfs endian/parser behavior remains covered by regression tests. inet_diag is optional, deadline/length checked, and retried conservatively; procfs still supplies UDP and fallback socket state. The former inode/PID-only ownership and generic-runtime grouping were replaced, not perpetuated.

**Do not fabricate storage attribution.** fdinfo `mnt_id` exposes a structural open-descriptor association only. Process and device rates retain their separate denominators. Capacity is queried in a timed, killable child for an allowlist of local filesystem types; remote/FUSE capacity is unavailable rather than risking an uninterruptible synchronous call in the shell.

**Freeze the data that details will inspect without copying the graph.** Each sample is immutable-by-replacement at the engine boundary. Freeze pins references to that exact full generation and its canonical socket store, correlated by request ID; subsequent live samples replace the live generation instead of mutating the frozen one. QML receives the bounded transport snapshot. If `X` changes instance scope while frozen, the helper derives only those requested instance relationships from the pinned socket generation and returns a replacement bounded frozen view without mutating the pinned snapshot. Later child-socket pages come from that exact generation. A restarted helper reports the frozen data ended/unavailable and never silently substitutes new live details.

**Lifecycle before decoration.** The manifest does not set `keepLoaded`; Quattro unloads the overlay. Close drops UI/history and stops the helper immediately. QML distinguishes process-started from telemetry-ready: a schema-valid first frame is required, stale sequence progress and repeated invalid records trigger bounded helper restart, and manual Retry restarts rather than merely reconfigures a suspect helper. Stop/restart sends SIGTERM to the principal helper and escalates to SIGKILL after 1.2 seconds if it has not exited; destruction uses immediate SIGKILL because no teardown timer can safely outlive the QML object. Linux parent-death signals and command timeouts bound provider teardown. Native hold invocation uses runtime-directory locking and release tombstones to prevent asynchronous press/release reordering. No free-running visual heartbeat is needed to make an idle system appear busy.

## Resource containment

Collection limits apply before and during work, not only at the wire boundary. Process discovery, process-file reads and grouping share one absolute scan deadline and cap 8,192 retained processes; generic-runtime ancestry uses path compression so a deep Python/Node/BEAM tree is near-linear rather than repeatedly walking ancestors. Socket state uses one global contact/deadline budget across protocol/family tables. Full FD ownership scans are multi-rate, with only a short bounded scan for newly observed inodes between full passes. Per-process network relationships are not rebuilt globally: the UI sends a bounded application-group scope, and the helper derives only that scoped instance layer.

Transport is constructed to a 1.5 MiB target with deterministic collection byte shares and a 4 MiB emergency protocol ceiling. It does not repeatedly serialize and halve a completed full graph. `limits` reports target/actual transport bytes, truncation/omission counts, target/effective cadence, adaptive throttle level and sampler duty cycle. After sustained high duty cycle the engine lengthens its effective sample interval; after sustained low duty it recovers gradually. Optional audio/hardware/capacity/enrichment sources retain their longer independent cadences.

The principal helper is launched as `/usr/bin/python3` with Quickshell `clearEnvironment` and a reduced user-session environment; provider commands likewise resolve executables against a fixed system path and run with a reduced environment. User-site/PYTHONPATH/dynamic-loader overrides are not propagated. Provider commands retain argv-only invocation, output/time ceilings, process-group cleanup and parent-death protection. DNS and local-MMDB work are isolated into killable workers. MaxMind database open/query never runs in the principal telemetry helper. `nvidia-smi` is a fallback only when DRM sysfs produced no GPU observation.

## Lifecycle and monitors

Bar-button presentation is owned by Omarchy `Panel` + `KeyboardPanel`: the clicked bar item supplies the anchor, and the host computes available monitor space, bar-edge offset, outer gaps, and clamping. The Tactical surface therefore does not cover the bar when opened from the bar. The shell/compositor summon route remains fullscreen: its screen is captured from the payload or focused Hyprland monitor; otherwise the first current screen is used. Only that fullscreen PanelWindow is visible and keyboard-exclusive. Other monitors remain unobstructed. On hot-unplug, select the current focused/first remaining screen; with no screens, hide the session. Backend ownership sits above Variants, so changing screens cannot multiply samplers. The host's openPanelIds guards a stale queued cold-summon payload after a hide.

Process restart is capped at six retries with exponential backoff up to 30 seconds; three good frames reset the consecutive-failure count. Freshness uses an active-only clock. Transport validation rejects malformed/deep/oversized objects before they reach rendering. Open normal state never needs a new Quickshell or external graphics engine.

## Context and UI state

The context carries process instance, application, remote, mount, device, audio and subsystem keys, never only a recyclable PID. Missing destination context produces a notice and retains the available view. Focus history is capped at 24. Selection survives replacement snapshots; a departed selected record remains inspectable until reset/back/close. Freeze is not persisted. Preferences and last instrument use native inline settings; raw history does not.

Application identity prefers meaningful application/cgroup data, then canonical executable identity and ownership, with runtime ancestry/instance disambiguation for generic interpreters. Network groups and process groups use the same IDs. Audio process metadata is client-reported and is explicitly not a security identity.

## Limits and deliberate extensions

All source paths exist; no rendering fixture or dummy provider is a production fallback. Optional stream rerouting requires an API with safely validated route/serial semantics; it is not implemented by guessing wpctl commands. Workspace/Agent Topology is outside the 1.0.0 scope and should only be added when reliable workspace/project identities and sourced agent states exist. There is no persistent replay database, privileged eBPF, traffic capture, process killer, mount manager or cloud service.

See DATA-MODEL.md for field semantics and limits, UPSTREAM-CONTRACT.md for the Omarchy runtime contract, and TESTING.md for automated and native acceptance coverage.