# AGENTS.md - Tactical Display

## Mission

This repository is an Omarchy Quattro overlay plugin. Preserve the product principle:

> **The screen becomes an instrument while summoned; on dismiss, the instrument ceases to exist.**

Version 0.2 has one product thesis:

> **See every program on this machine communicating with every remote system in real time.**

Do not regress this into a generic neon dashboard, permanent panel, security scanner, or second Quickshell process.

## Target contract

Target current Omarchy Quattro / 4.x. Before changing shell integration, re-read current upstream:

- `agents/skills/shell-dev.md`
- `manual/32-shell-plugins.md`
- `shell/README.md`
- `shell/shell.qml`
- `shell/services/PluginRegistry.qml`

Repository: https://github.com/basecamp/omarchy/tree/quattro

The entry point must remain an `Item`, not `ShellRoot`. Do not launch another `quickshell` process. `open(payloadJson)` and `close()` are mandatory.

## Current architecture

- `Overlay.qml` - Quattro lifecycle, shared telemetry, per-screen overlay windows.
- `core/Telemetry.qml` - one backend process while open.
- `scripts/telemetry.py` - dependency-free procfs collector and process↔remote aggregation model.
- `core/HudSurface.qml` - intentionally restrained shared instrument surface.
- `instruments/NetworkFieldInstrument.qml` - only primary v0.2 instrument.
- `RadarInstrument.qml` / `ReactorInstrument.qml` - retired prototypes retained only because an overlay zip cannot delete files from an existing checkout. They are not loaded.

Do not duplicate telemetry processes per monitor.

## Semantic law

The visualization must remain truthful:

- center/machine boundary = local machine;
- process hubs = socket-owning local processes;
- remote perimeter nodes = remote IP systems;
- links = real socket relationships;
- right sector = primarily outbound;
- left sector = likely inbound;
- top = mixed/bidirectional relationship set;
- loopback remains inside the machine field;
- listener apertures = bound/listening sockets;
- pulse/fade = lifecycle;
- moving tracer = **direction only**;
- line width = socket multiplicity + kernel queue pressure.

Never represent tracer speed/brightness as measured per-link throughput unless a future backend genuinely measures it.

## Backend model

The JSON frame has:

```text
system      existing machine-wide metrics
contacts    raw visible socket contacts
network
  processes
  remotes
  links
  listeners
  summary
```

Primary visual aggregation is process↔remote-service relationship, not one glyph per kernel socket. Preserve raw `contacts` for debugging and future drill-down.

## Process privacy

Do not expose full process argument lists by default. `/proc/<pid>/cmdline` can contain tokens, passwords, signed URLs, or other secrets. Current code keeps process `comm`, PID, executable basename, and `argv[0]` only.

## Safety / privacy constraints

- no `sudo`, setuid helper, packet capture, raw socket sniffing, or firewall mutation without an explicit new product decision;
- no outbound web calls, reverse DNS, or GeoIP as a hidden default;
- no process/socket killing from a click;
- no persistent telemetry history;
- no claim that inferred inbound traffic is an attack or proves firewall traversal.

## Quickshell / Qt constraints

Keep the per-screen `Variants` `PanelWindow` geometry using anchors. Do not regress to direct `width: parent.width` / `height: parent.height` on the per-screen window path without verifying the Qt/Quickshell issue is fixed on the target stack.

Avoid right-click MouseAreas on layer-shell surfaces until the known synthesized context-menu crash path is verified fixed. Connection Field uses left-click only.

## Visual standard

A screenshot must explain itself without a paragraph:

1. **THIS MACHINE ⇄ THE WORLD** is obvious.
2. Local programs are visibly different from remote systems.
3. The line itself communicates who is connected to whom.
4. Direction is visible.
5. Clicking either side isolates the relationship graph.
6. Decorative chrome never competes with the topology.

If the next agent is tempted to add more rings, HUD boxes, random sweeps, or unrelated animation, stop and justify what data each element encodes.

## Tests

After every change:

```bash
make test
make validate
```

On a real Quattro host:

```bash
./scripts/doctor.sh
omarchy plugin validate .
/usr/lib/qt6/bin/qmllint -I "$OMARCHY_PATH/shell" Overlay.qml core/*.qml instruments/*.qml
```

`qmllint` currently emits some warnings even on Omarchy's own Quattro QML when run outside the full Quickshell metadata environment. Treat parser/type errors as blockers; compare import/Quickshell metadata warnings against an official shell file before attributing them to this plugin.

Then run `docs/HANDOFF.md` exactly.

## Hardening priorities

1. visual layout/collision behavior on the user's real monitor;
2. QML runtime errors on the exact Quattro/Qt/Quickshell build;
3. process attribution quality for browser/terminal/agent workloads;
4. graph behavior under high connection churn;
5. multi-monitor focus and surface teardown;
6. CPU/GPU cost while the overlay is open;
7. final naming/marketplace media only after the instrument is visually convincing.

## Handoff discipline

If you stop before final acceptance, update `docs/HANDOFF.md` with exact host versions, failing action, exact logs, screenshots/observations, and which acceptance cases passed. Never leave only “needs testing.”
