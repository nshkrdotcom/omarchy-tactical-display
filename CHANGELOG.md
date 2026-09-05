# Changelog

All notable changes to Tactical Display are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-05

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

[Unreleased]: https://github.com/nshkrdotcom/omarchy-tactical-display/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/nshkrdotcom/omarchy-tactical-display/releases/tag/v1.0.0
