# Changelog

## 0.2.0 - 2026-09-04

Product reset after live visual review:

- replaced the original Network Radar/System Reactor presentation with one focused **Connection Field** instrument;
- local processes now appear as inner machine-owned hubs;
- remote IP systems now appear as external peers;
- real process↔remote socket relationships are rendered as links;
- outbound, likely inbound, mixed, and loopback geometry now carries actual semantic meaning;
- multiple kernel sockets aggregate into a human-readable process↔remote-service relationship;
- moving tracers show direction only, explicitly not fake per-link bandwidth;
- listener sockets render as machine-boundary apertures;
- new relationships pulse; recently closed relationships decay;
- process/remote click isolation and inspection added;
- backend emits a structured `network` model in addition to raw contacts;
- process attribution now carries executable/argv0 identity while deliberately discarding full command arguments;
- manifest, bindings, docs, tests, architecture, security model, and handoff updated;
- automated suite expanded to 24 passing tests.

Prior real-host evidence: Quattro plugin validation passed and both v0.1 overlays rendered. Connection Field itself still requires live visual/runtime hardening on the target host.

## 0.1.0 - 2026-09-04

Greenfield implementation for Omarchy Quattro:

- one on-demand Quattro overlay with payload-selected instruments;
- Network Radar prototype;
- System Reactor prototype;
- dependency-free Linux procfs/sysfs backend;
- multi-monitor layer-shell presentation with one shared backend;
- Omarchy theme integration;
- automated tests and validation tooling;
- architecture/security/testing/visual-design/handoff documentation.
