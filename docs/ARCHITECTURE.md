# Architecture and implementation decisions

## Boundaries

```text
Quattro shell (one existing long-running Quickshell)
  |-- BarWidget.qml -> native bar styling/lifecycle; no sampler
  `-- Overlay.qml (hosted Item, open/close, selected monitor)
        |-- Configuration (native inline settings, unknown-field-preserving)
        |-- NavigationController (selection/context/history/freeze)
        |-- Telemetry (one supervised Process, NDJSON validation)
        |     `-- scripts/telemetry.py
        |           `-- td_telemetry/{processes,network,machine,storage,audio,hardware,enrichment}
        |                 -> normalized entities + capability map + bounded events
        `-- selected PanelWindow / TacticalDisplayShell
              -> InstrumentModel -> Layout -> Draw / Field
              -> InspectionPanel, CommandSheet, Trend
```

`model/` separates configuration, typed navigation intent, telemetry validation, instrument transformations and inspection. `visual/` owns stable layout, collision/label budgets, palette contrast and rendering. No instrument delegate reads Linux files or spawns commands. One shared renderer has **five distinct semantic model/layout/drawing paths**, not five labels over a generic percentage dashboard.

## Changes to the supplied plan

**Use the actual native settings API.** Tagged Quattro exposes `shell.updateEntryInline`; the release merges existing inline entry keys before calling it because the host replaces that entry's fields. A second private configuration file would create conflicting authorities. Newer settings versions are read-only. A missing enablement entry yields explicit session-only behavior.

**Aggregate first, expand deliberately.** Default/focused Connection Field retains application relationships; `X` reveals individual process instances. Following a shared remote must not accidentally select every unrelated application. Process Topology unfolds small trees immediately and collapses large application populations until selected/searched. Audio focus follows directed paths all the way from the selected sink to its upstream streams, without traversing sideways across unrelated routes.

**Retain the proven fallback, add measured kernel capability.** The baseline procfs endian/parser behavior remains covered by its original tests. inet_diag is optional, deadline/length checked, and retried conservatively; procfs still supplies UDP and fallback socket state. The former inode/PID-only ownership and generic-runtime grouping were replaced, not perpetuated.

**Do not fabricate storage attribution.** fdinfo `mnt_id` exposes a structural open-descriptor association only. Process and device rates retain their separate denominators. Capacity is queried in a timed, killable child for an allowlist of local filesystem types; remote/FUSE capacity is unavailable rather than risking an uninterruptible synchronous call in the shell.

**Freeze the data that details will inspect.** A helper-side full snapshot is independently retained, correlated by request ID. QML receives the bounded transport snapshot. Later child-socket pages come from that exact frozen full snapshot. A restarted helper reports the frozen data ended/unavailable and never silently substitutes new live details.

**Lifecycle before decoration.** The manifest does not set `keepLoaded`; Quattro unloads the overlay. Close drops UI/history and stops the helper immediately. Linux parent-death signals and command timeouts bound helper/provider teardown. Native hold invocation uses runtime-directory locking and release tombstones to prevent asynchronous press/release reordering. No free-running visual heartbeat is needed to make an idle system appear busy.

## Lifecycle and monitors

The summon screen is captured from the payload or focused Hyprland monitor; otherwise the first current screen is used. Only that PanelWindow is visible and keyboard-exclusive. Other monitors remain unobstructed. On hot-unplug, select the current focused/first remaining screen; with no screens, hide the session. Backend ownership sits above Variants, so changing screens cannot multiply samplers. The host's openPanelIds guards a stale queued cold-summon payload after a hide.

Process restart is capped at six retries with exponential backoff up to 30 seconds; three good frames reset the consecutive-failure count. Freshness uses an active-only clock. Transport validation rejects malformed/deep/oversized objects before they reach rendering. Open normal state never needs a new Quickshell or external graphics engine.

## Context and UI state

The context carries process instance, application, remote, mount, device, audio and subsystem keys, never only a recyclable PID. Missing destination context produces a notice and retains the available view. Focus history is capped at 24. Selection survives replacement snapshots; a departed selected record remains inspectable until reset/back/close. Freeze is not persisted. Preferences and last instrument use native inline settings; raw history does not.

Application identity prefers meaningful application/cgroup data, then canonical executable identity and ownership, with runtime ancestry/instance disambiguation for generic interpreters. Network groups and process groups use the same IDs. Audio process metadata is client-reported and is explicitly not a security identity.

## Limits and deliberate extensions

All source paths exist; no rendering fixture or dummy provider is a production fallback. Optional stream rerouting requires an API with safely validated route/serial semantics; it is not implemented by guessing wpctl commands. Workspace/Agent Topology remains gated behind P0 target acceptance, as required by the supplied plan. There is no persistent replay database, privileged eBPF, traffic capture, process killer, mount manager or cloud service.

See DATA-MODEL.md for field semantics and limits, UPSTREAM-CONTRACT.md for the runtime evidence, and TRACEABILITY.md for file/test mappings.
