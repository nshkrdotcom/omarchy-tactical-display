# Tactical Display

**Five local instruments over your desktop. Summon, inspect, dismiss.**

Version **1.0.0-rc.1**, targeting **Omarchy Quattro 4.0.1**. The runtime implementation is present for all five required instruments. This is a release candidate awaiting the real-desktop acceptance gates, not a claim that a headless test environment certified the desktop. See [validation](docs/VALIDATION.md) for executed evidence and [handoff](docs/HANDOFF.md) for the exact remaining gates.

| Instrument | What the geometry reveals |
|---|---|
| Connection Field | Local applications on a near plane, remote systems on a horizon, listeners at the machine boundary; real aggregated relationships and recent changes. |
| Process Topology | Application/cgroup islands, process-instance ancestry, and CPU, memory, thread, network or I/O emphasis. |
| Machine Anatomy | Resource cutaways, pressure and measured contributors; no simulated hardware bus. |
| Storage / I/O Flow | Process accounting, open-descriptor associations, mounts, logical layers and backing block devices. |
| Audio Routing | Actual PipeWire streams, channel links, routing nodes, sinks/sources and physical devices. |

## Install or apply the overlay

This delivery is an **incremental overlay against the supplied 0.2.0 Repomix**, not a standalone checkout. Follow [the guarded apply procedure](docs/HANDOFF.md#apply-the-overlay) before running anything. It verifies the baseline, backs it up, applies only the changes, and removes the six explicitly retired QML files.

For a complete, already-overlaid development checkout, `bash scripts/install-local.sh` is a create-only installer into `~/.config/omarchy/plugins/nshkr.tactical-display`. It refuses an existing installation and does not enable anything or edit the bar. The ordinary Omarchy plugin distribution path needs no install hook, privileged daemon, package download or build step.

Runtime requirements: the Quattro 4.0.1 host/Qt Quick stack and Python 3 (3.10+ language features). PipeWire's `pw-dump` enables the audio graph; WirePlumber's `wpctl` enables explicitly opted-in actions. Missing optional tools produce capability explanations, not fabricated data. Node.js is **development-only** for model/layout tests. No pip install is required for normal runtime.

```bash
omarchy plugin validate ~/.config/omarchy/plugins/nshkr.tactical-display
omarchy-shell shell rescanPlugins
omarchy plugin enable nshkr.tactical-display
omarchy-shell shell summon nshkr.tactical-display '{"instrument":"connection"}'
omarchy-shell shell hide nshkr.tactical-display
omarchy-shell shell toggle nshkr.tactical-display '{}'
```

Omarchy's own enablement can place a bar widget. The plugin does not rearrange your bar. To explicitly place or move it using the native tooling:

```bash
omarchy bar put nshkr.tactical-display
omarchy bar move nshkr.tactical-display --section right --index 0
```

Left-click toggles on the focused monitor; right-click opens the instrument picker. Vertical bars always use the compact `TD` affordance. Idle bar state is the remembered instrument, not a pretend live activity indicator. There is **one shared helper per open session**, not one per monitor.

## Interaction

| Key / gesture | Effect |
|---|---|
| `1` - `5`; `I` | Select instrument; reopen picker. |
| Pointer hover/click; arrows; Tab / Shift-Tab | Inspect/select; traverse entities, including density-budget omissions. |
| Enter / double-click; `F`; `X` | Focus; isolate/unisolate; expand/collapse an application. |
| Escape; Backspace; `R` | Close Tactical Display immediately; back one UI/focus level; reset the current view. |
| `/`; Space; `D` | Search; freeze/resume an exact snapshot; expand detail and paged socket records. |
| `?` / `H`; comma; `P`; `C` | Legend; settings; privacy; copy the curated selected detail. |
| `F6` | Switch between field traversal and normal Qt control traversal. |
| Connection `V` / `N` / `B`, `L` / `O` | Origin, protocol, lifecycle lenses; listeners / loopback. |
| Process `E`; Storage/Audio `V`; Machine `T` | Resource emphasis; topology lens; bounded aggregate trend. |

Selection uses stable instance IDs. Unknown/missing data remains unknown. A selected departed entity keeps its inspection record rather than selecting a recycled PID. Freeze holds the helper's exact full snapshot, including later paged details; live collection continues, bounded, in the background. Switching instruments resumes live state. Search and detail remain usable while frozen.

For hold-to-view, `bash scripts/print-bindings.sh` prints a **reviewable Lua block** for Quattro's `~/.config/hypr/bindings.lua`. It does not install bindings. The helper serializes press/release IPC, handles release-before-press races and ignores unrelated key releases. See the full hold acceptance procedure in [handoff](docs/HANDOFF.md).

## Truth and privacy

Connection origin is **inferred** from visible listeners/bindings, not proof of who called `connect()`. The default works through unprivileged procfs; optional `inet_diag` exposes TCP counters only where the kernel supplies them. ACKed/received byte deltas are goodput, not wire bandwidth. Line width encodes socket multiplicity, not an invented rate. Listener backlog is not labeled as bytes.

Storage process rates and device rates are separately measured. Dashed process-to-mount edges mean **open descriptors**, never a per-mount share of a process's bytes. RSS can count shared pages more than once. Audio gain is not a level meter. Every detail surface names its provenance.

No root, sudo, packet capture, cloud endpoint intelligence, analytics, command-line argument ingestion, or persistent traffic history. Local aliases and `/etc/hosts` work offline. Reverse DNS is opt-in and can contact your configured resolver; privacy mode suppresses it. User-supplied offline MMDB enrichment is optional. Screen-share privacy hides identifiers and the desktop, but **is not a security boundary**.

## Development and evidence

```bash
make test
bash scripts/validate.sh
bash scripts/doctor.sh
node scripts/render-fixtures.js --out /tmp/tactical-fixtures
python3 scripts/profile.py --instrument all --samples 40 --interval 0.75 --output /tmp/tactical-profile.json
```

`validate.sh --require-native` returns nonzero when native validation cannot run. Unavailable integration tests are explicit skips, not passes. Fixture previews execute the production layout/drawing code but **are not Qt/Wayland screenshots**. Never present them as live telemetry or desktop validation.

The live runner requires an explicit `--run`, an actual Omarchy session, and an evidence path outside the watched plugin directory. It never launches a replacement shell or substitutes a fixture backend.

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [data semantics](docs/DATA-MODEL.md) · [configuration](docs/CONFIGURATION.md) · [security/privacy](docs/SECURITY-PRIVACY.md) · [visual system](docs/VISUAL-DESIGN.md) · [tests](docs/TESTING.md) · [Quattro contract](docs/UPSTREAM-CONTRACT.md) · [traceability](docs/TRACEABILITY.md) · [validation](docs/VALIDATION.md) · [operator handoff](docs/HANDOFF.md).

The supplied requirements remain available under `docs/specification/`. Workspace/Agent Topology, persistent replay, privileged tracing and stream rerouting are not disguised as completed features; their conditional extension gates are documented in the handoff.
