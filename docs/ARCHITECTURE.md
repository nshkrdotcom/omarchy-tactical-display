# Architecture

## Product boundary

Tactical Display 0.2 is one Quattro `overlay` plugin with one focused instrument: Connection Field.

```text
Hyprland keybind
    |
    v
omarchy-shell shell summon nshkr.tactical-display '{}'
    |
    v
Omarchy Quattro plugin loader
    |
    v
Overlay.qml
    |-- Telemetry.qml ----> python3 scripts/telemetry.py
    |                           |-- /proc/net/{tcp,tcp6,udp,udp6}
    |                           |-- /proc/<pid>/{fd,comm,exe,cmdline(argv0 only)}
    |                           |-- /proc/net/dev
    |                           `-- /proc/{net/dev,uptime}
    |
    `-- Variants(Quickshell.screens)
         `-- PanelWindow per screen
              `-- HudSurface
                   `-- NetworkFieldInstrument
```

There is one telemetry process shared by all monitor surfaces.

## Runtime lifecycle

### Open

1. Quattro loads `Overlay.qml` on summon.
2. Shell-injected plugin properties identify the source directory.
3. `open(payloadJson)` records optional screen/help state.
4. `Telemetry.start()` launches one persistent Python sampler.
5. Per-screen layer-shell windows become visible.
6. The focused Hyprland monitor requests keyboard focus.

### Close

1. release binding, Escape, or `shell hide` calls the plugin close route;
2. surfaces become invisible;
3. backend process is stopped;
4. no telemetry history is written.

## Backend layers

### Raw contacts

`SocketSampler` parses procfs socket tables and emits a best-effort process-attributed contact for each visible socket. It retains recently closed contacts as short-lived ghosts so topology can decay instead of popping.

### Human network model

`build_network_model()` aggregates raw sockets into the objects the visualization actually needs:

```text
processes[]   local socket owners
remotes[]     remote IP systems
links[]       process <-> remote-service relationships
listeners[]   local listening/bound endpoints
summary{}     active counts
```

A `link` groups sockets by:

```text
process + remote IP + relationship kind + protocol + service port
```

For outbound relationships the service port is the remote port. For likely inbound relationships it is the local listening service port. This prevents browser connection churn from becoming hundreds of unrelated dots while retaining socket multiplicity on the relationship.

## Process attribution

Socket inode → process ownership is resolved only through readable `/proc/<pid>/fd` symlinks for the current user. The backend also reads:

- `comm`;
- executable basename;
- `argv[0]` only.

Full argument lists are deliberately discarded for privacy.

If ownership cannot be read, the relationship remains visible as unattributed.

## Direction inference

- `listen` - LISTEN/BOUND or unspecified remote;
- `loopback` - remote address is loopback;
- `inbound` - local port currently corresponds to a visible listener;
- otherwise `outbound`.

This is a useful topology heuristic, not firewall provenance or IDS classification.

## Rendering model

`NetworkFieldInstrument.qml` uses a single procedural Canvas for topology plus QML text/detail overlays.

Layout:

- local processes orbit inside the machine boundary;
- outbound remotes occupy the right sector;
- inbound remotes occupy the left sector;
- mixed remotes occupy a top sector;
- loopback remains inside the machine field;
- links connect process/remote coordinates directly.

Selection does not recompute backend data. It changes render emphasis only.

## Truthful motion

Active links carry continuously moving direction tracers. They communicate *which way the relationship points*, not bytes/sec. Machine-wide RX/TX is shown separately from `/proc/net/dev` because that metric is actually measured.

Kernel socket queue depth may affect link thickness as current pressure, but it is not called throughput.

## Performance

Backend cadence remains 750 ms by default. The Python process persists while the overlay is open rather than being recreated every sample. Canvas repaint is driven by the direction animation plus telemetry/layout changes.

Hardening must measure both backend and `omarchy-shell` CPU on the actual host, especially with many browser connections and high-refresh monitors.
