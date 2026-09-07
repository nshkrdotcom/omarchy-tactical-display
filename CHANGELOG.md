# Changelog

All notable changes to Tactical Display are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Activity change explanations and an opened-plus-closed filter for scanning lifecycle changes without deleting routine state events.

- Operator briefing with explainable PSI and capacity findings, provider quality and exact-entity inspection links.
- Five-minute bounded activity history, instrument/lifecycle filters, eight session pins with current metrics, aggregate baseline comparison and a privacy-aware clipboard report.
- Interactive 15/30/60-second trends, usage/PSI lenses, missing-data gaps, measured scales, solid/dashed paired traces and pointer/keyboard inspection.
- Production-model regression tests and real Qt controller/control tests, with isolated style and clipboard adapters for portable component testing.

### Fixed

- Audio pin/event aliases follow actual PipeWire media classes; mount pins expire cached capacity independently of provider freshness.
- Activity has a consistent left reading edge, and paired trends retain both numeric legends at compact widths.

- Live activity refresh now preserves focused delegates; selected buttons retain a visible focus outline.
- Command sheets scroll the actual Flickable to reveal keyboard-focused controls.
- Late freeze replies preserve prior activity without mixing in future events; retained aliases match the field.
- Exact relationship and demand-scoped process pins can be reopened without falling back to another entity.
- Native lint maps Quickshell's `qs` import root and fails on missing imports.
- Provider status supports keyboard and accessibility activation with visible focus.

## [1.0.0] - 2026-09-06

### Added

- Initial release of Tactical Display for Omarchy Quattro on Wayland / Hyprland.
- Five interactive instruments:
  - **Connection Field**: 3D spatial mapping of local and remote network relationships.
  - **Process Topology**: Interactive process ancestry, application groups, and resource ranking.
  - **Machine Anatomy**: Subsystem cutaways (CPU, Memory, Storage, Network, GPU, Thermals) with Pressure Stall Information (PSI) and trend tracking.
  - **Storage / I/O Flow**: End-to-end data flow from process I/O through filesystem mounts to physical block devices.
  - **Audio Routing**: Live PipeWire audio graph with stream links, node status, and volume/mute controls.
- Compact desktop bar widget for Omarchy shell with single-click toggle and right-click instrument picker.
- Instant Screen-Share Privacy Mode (`P`) to mask sensitive process names, network endpoints, and desktop background.
- Snapshot Freeze (`Space`) to pause live updates for steady inspection and detail copying.
- Full keyboard navigation, entity search (`/`), isolation mode (`F`), and application expansion (`X`).
- Automatic contrast and color normalization adapting to the active Omarchy theme.
- Resource-hardened telemetry internals with a canonical socket-detail store, key-only relationships, demand-scoped per-process network topology (including frozen on-demand expansion), generation-pinned freeze snapshots, and constructive byte-budgeted transport below the 4 MiB protocol ceiling.
- Absolute process/socket work deadlines, near-linear generic-runtime ancestry grouping, multi-rate socket ownership, and adaptive sampler backoff under sustained collection load.
- Valid-frame/staleness helper supervision with bounded restart recovery, fixed system-Python launch, cleared/reduced principal-helper environment, SIGTERM-to-SIGKILL teardown escalation, true sliding-window command flood protection, and stricter frontend collection validation.
- Isolated optional MMDB lookups, bounded PipeWire dump size, NVIDIA vendor-tool fallback-only polling, and reduced subprocess environment/PATH authority.
- Adversarial resource tests, stronger native RSS/FD/child/CPU/latency lifecycle gates, and release-tag verification.

### Changed

- Routed bar-button presentation through Omarchy's native `Panel`/`KeyboardPanel` geometry, matching BEAM Deck so the top bar remains exposed and the host owns monitor gaps, bar-edge offsets, and clamping; shell/compositor invocation retains the fullscreen overlay route.
- Matched the native bar panel more closely to BEAM Deck: removed Tactical-specific outer content padding on the panel path, adopted Omarchy popup background/text and native title/body/caption typography, tightened major control/modal spacing, and retained only the host border; fullscreen summon keeps its Tactical-specific spacing and continuous 2px theme-accent viewport frame.
- Set the native release-acceptance soak to 10 minutes after real-host lifecycle/profile coverage demonstrated stable helper and shell resources; the soak remains fixed to one instrument to avoid synthetic re-summon behavior.
- Aligned fullscreen-overlay keyboard handling with current Omarchy Quattro conventions: editors and command sheets receive first refusal, command-modified keys are not hijacked, bare `1`-`5` picker selection is routed by the fullscreen shell while the picker is visible, and field/control focus is restored deterministically after modal, search, pointer, and instrument transitions.
- Clarified the distinction between Tactical Display's fullscreen-overlay key handling and Omarchy panel navigation so panel-reserved navigation conventions are not copied into the overlay where they would conflict with product-specific shortcuts.
- Documented the optional global-binding workflow and a real-host keyboard/focus acceptance matrix for final Omarchy validation.
- Corrected fixture-renderer keyboard hints so `Escape` is documented as immediate close and `Backspace` as navigation back.

### Fixed

- Aligned the header status/session block on the same title and purpose baselines as the left identity block, removing button-padding drift from the top-right chrome.
- Fixed the printed press-and-hold Lua binding to invoke `scripts/invoke.py` with its required `--token` argument and the fixed `/usr/bin/python3` interpreter.
- Hardened keyboard ownership around focused editors and controls so text entry, standard modified shortcuts, and control interaction are not intercepted by overlay-level commands.
- Fixed picker digit routing so modified number keys do not switch instruments and unmodified `1`-`5` selection works reliably regardless of which picker child owns focus.
- Fixed focus restoration after sheets, search, pointer interaction, and instrument changes so keyboard navigation reliably returns to the intended field or control surface.
- Hardened native acceptance tooling for packaged non-Git Omarchy installs, transient diagnostics IPC, and fixed-instrument long soaks with explicit shell-growth containment.

[1.0.0]: https://github.com/nshkrdotcom/omarchy-tactical-display/releases/tag/v1.0.0
