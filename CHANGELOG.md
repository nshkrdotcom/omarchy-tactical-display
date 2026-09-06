# Changelog

All notable changes to Tactical Display are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Adversarial resource tests, stronger native RSS/FD/child/CPU/latency lifecycle gates, release-tag verification, and a workstation completion handoff.

[Unreleased]: https://github.com/nshkrdotcom/omarchy-tactical-display/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/nshkrdotcom/omarchy-tactical-display/releases/tag/v1.0.0