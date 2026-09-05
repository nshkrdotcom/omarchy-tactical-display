# Tactical Display for Omarchy Quattro

Tactical Display is an Omarchy Quattro `overlay` plugin built around one interaction: summon a temporary instrument, understand something about the machine immediately, then dismiss it and leave no permanent dashboard behind.

Version **0.2.0** replaces the original decorative Network Radar/System Reactor prototypes with a single focused instrument: **Connection Field**.

> **See every program on this machine communicating with every remote system in real time.**

## What the display means

The geometry is the data model:

- **center / machine boundary** - this computer;
- **process hubs inside the boundary** - local processes that own visible sockets;
- **remote diamonds at the perimeter** - remote IP systems;
- **right sector** - primarily outbound relationships;
- **left sector** - likely inbound relationships;
- **top sector** - systems with meaningful traffic in both directions at the relationship level;
- **inner loopback node** - localhost relationships;
- **lines** - real process-to-remote socket relationships;
- **moving tracers** - relationship direction, **not measured per-link bandwidth**;
- **line thickness** - socket multiplicity plus any current kernel queue pressure;
- **pulses** - newly observed relationships;
- **dashed/fading links** - recently closed relationships;
- **apertures on the machine boundary** - listening/bound sockets.

Click a process or remote system to isolate the relationships attached to it and inspect PID, executable identity, protocol, service port, socket count, and peer relationships.

## Quattro-native

This repository targets current Omarchy **Quattro / 4.x** and follows the Quattro shell contract:

- one long-running `omarchy-shell` Quickshell process;
- third-party plugin root at `~/.config/omarchy/plugins/<id>/`;
- `kinds: ["overlay"]` and `entryPoints.overlay`;
- an `Item` entry point, never another `ShellRoot`;
- shell-injected `omarchyPath`, `shell`, `manifest`, and `pluginRegistry` properties;
- `open(payloadJson)` / `close()` lifecycle;
- `omarchy-shell shell summon|hide|toggle` for IPC.

Primary references:

- https://plugins.omarchy.org/develop.html
- https://github.com/basecamp/omarchy/blob/quattro/agents/skills/shell-dev.md
- https://github.com/basecamp/omarchy/blob/quattro/manual/32-shell-plugins.md

## Requirements

Runtime requirements are deliberately small:

- Omarchy Quattro / 4.x
- Quickshell/Hyprland supplied by Omarchy
- `python3`
- ordinary Linux procfs

There are no Python packages, daemons, web APIs, DNS lookups, GeoIP databases, packet-capture helpers, root helpers, bundled fonts, or binary dependencies.

## Install / update during development

For the original full repository:

```bash
./scripts/validate.sh
./scripts/install-local.sh
```

For the **0.2 overlay archive**, unzip it directly over the existing repository or installed development copy. The old `RadarInstrument.qml` and `ReactorInstrument.qml` files may remain on disk; `Overlay.qml` no longer references or loads them.

Then validate and restart the shell:

```bash
omarchy plugin validate .
omarchy-restart-shell
```

## Summon it

```bash
omarchy-shell shell summon nshkr.tactical-display '{}'
```

Dismiss:

```bash
omarchy-shell shell hide nshkr.tactical-display
```

Legacy payloads such as `{"instrument":"radar"}` still summon Connection Field so old development keybindings do not break.

## Suggested hold binding

Run:

```bash
./scripts/print-bindings.sh
```

It prints the current Quattro Lua binding pattern:

```lua
o.bind("SUPER + N", "Tactical Display: Connection Field", "omarchy-shell shell summon nshkr.tactical-display '{}'")
o.bind("SUPER + N", nil, "omarchy-shell shell hide nshkr.tactical-display", { release = true })
```

Check `omarchy menu keybindings --print` first and use an unused chord. A toggle alternative is printed as well because release ordering can vary by Hyprland workflow.

## Controls

- **left click process** - isolate that process and inspect its remote relationships;
- **left click remote system** - isolate that system and inspect local processes talking to it;
- **click empty field / selected node again** - clear selection;
- **H / ?** - semantic help overlay;
- **Esc** - close.

No right-click handler is used.

## Telemetry model

`scripts/telemetry.py` reads:

- `/proc/net/tcp`, `tcp6`, `udp`, `udp6` for socket state/endpoints/queues;
- readable `/proc/<pid>/fd` to attribute sockets to the current user's processes;
- `/proc/<pid>/comm`, executable basename, and `argv[0]` only for process identity;
- `/proc/net/dev` for machine-wide RX/TX rate;
- existing system telemetry sources retained from v0.1 for compatibility.

The backend emits both raw `contacts` and an aggregated `network` model containing `processes`, `remotes`, `links`, `listeners`, and a `summary`.

The visualization intentionally aggregates many ephemeral sockets between the same process and remote service into one relationship. That lets the user see **who is talking to whom** instead of drowning in kernel objects.

## Important truth boundaries

- **Inbound is inferred**, not firewall proof. A connection is classed as likely inbound when its local port matches a currently visible listener.
- **Per-link motion is directional**, not a bandwidth meter. Plain procfs does not expose a clean cumulative byte counter for every arbitrary socket, so the plugin does not invent one.
- **Global RX/TX is real machine-wide throughput** from `/proc/net/dev`.
- **Queue pressure is real current kernel queue state**, not historical throughput.
- **Remote identity is the IP address only**. The plugin performs no DNS or GeoIP lookup.
- Process attribution is best-effort and respects Linux permissions; inaccessible sockets appear as unattributed rather than triggering privilege escalation.

## Privacy / security

Tactical Display makes no network requests and writes no telemetry history. It does not use `sudo`, packet capture, raw sockets, firewall mutation, or process killing.

Remote IPs, local process names/PIDs, listener ports, and executable identities can be sensitive on screen. Full process argument lists are deliberately **not** displayed because they may contain secrets. See `docs/SECURITY-PRIVACY.md`.

## Development / validation

```bash
make test
make validate
./scripts/doctor.sh
```

`make validate` runs automated tests, shell syntax checks, a real live telemetry sample, `omarchy plugin validate` when available, and `qmllint` when a usable Omarchy QML import tree is available.

The build environment cannot visually render the final Quattro overlay. The real-host visual/hardening matrix is therefore explicit in `docs/HANDOFF.md` rather than falsely marked complete.

## Repository map

```text
.
├── manifest.json
├── Overlay.qml
├── core/
│   ├── HudSurface.qml
│   ├── Scanlines.qml
│   └── Telemetry.qml
├── instruments/
│   ├── NetworkFieldInstrument.qml   # v0.2 primary instrument
│   ├── RadarInstrument.qml          # legacy, no longer loaded
│   └── ReactorInstrument.qml        # legacy, no longer loaded
├── scripts/
│   ├── telemetry.py
│   ├── doctor.sh
│   ├── install-local.sh
│   ├── print-bindings.sh
│   └── validate.sh
├── tests/
└── docs/
```

## Status

`0.2.0` is the first product-shaped version: one clear network question, one spatial model, truthful semantics, real Linux socket integration, Quattro lifecycle integration, selection/inspection, and automated backend/model tests. Final visual acceptance still belongs on the actual Omarchy workstation.
