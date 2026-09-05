# Tactical Display

**Real-time system instrumentation and visual diagnostics for Omarchy Quattro.**

Tactical Display gives you an interactive, HUD-style overlay across your desktop. Summon it with a keystroke, inspect active network sockets, process trees, hardware pressure, disk I/O, or audio routing, and dismiss it instantly.

---

## The Five Instruments

Switch between instruments anytime by pressing `1` through `5`:

| # | Instrument | What You See |
|---|---|---|
| `1` | **Connection Field** | Active network connections mapped in 3D space: local apps in the foreground, remote endpoints along the horizon, and listen sockets on the perimeter. |
| `2` | **Process Topology** | Interactive process ancestry and application groups. Explore parent-child hierarchies and rank by CPU, memory, threads, network, or I/O. |
| `3` | **Machine Anatomy** | Subsystem cutaways (CPU, Memory, Storage, Network, GPU, Thermals) paired with Linux Pressure Stall Information (PSI) and 60-second rolling trends. |
| `4` | **Storage / I/O Flow** | End-to-end data flow: tracks active process read/write throughput down through filesystem mounts to physical block devices. |
| `5` | **Audio Routing** | Live PipeWire audio graph showing active playback/recording streams, routing nodes, and hardware endpoints, with volume and mute controls. |

---

## Key Highlights

- ⚡ **Zero Background Overhead**: The telemetry helper runs only while the overlay is open and terminates cleanly upon dismissal.
- 🔒 **Screen-Share Privacy Mode**: Press `P` at any time to immediately mask process names, IP addresses, PIDs, and desktop transparency.
- ❄️ **Snapshot Freeze**: Press `Space` to freeze the entire visualization in place. You can navigate, inspect, search, and copy details without live data shifting beneath you.
- 🎨 **Theme Adaptive**: Automatically normalizes colors and contrast against your active Omarchy color scheme for maximum readability.
- 🛡️ **Unprivileged & Local-First**: Uses safe kernel metrics (`/proc`, `sysfs`, `pw-dump`). No root access, no packet sniffing, and no cloud analytics.

---

## Quick Start

### 1. Install Plugin
Install Tactical Display into your local Omarchy plugins directory:
```bash
bash scripts/install-local.sh
```

### 2. Enable in Shell
Register and enable the plugin with the Omarchy shell:
```bash
omarchy plugin enable nshkr.tactical-display
omarchy-shell shell rescanPlugins
```

### 3. Add to the Top Bar
Add the compact widget button to your desktop bar:
```bash
omarchy bar put nshkr.tactical-display
```
- **Left-Click**: Toggle the Tactical Display overlay on your focused monitor.
- **Right-Click**: Open the instrument selector.

### 4. Toggle via Keyboard Shortcut
To bind a shortcut in your Hyprland configuration (e.g. `Super + D`):
```bash
omarchy-shell shell toggle nshkr.tactical-display '{}'
```

> **Hold-to-View**: Prefer holding a key to view the overlay and releasing to hide it? Run `bash scripts/print-bindings.sh` to generate a ready-to-use Lua binding block for `~/.config/hypr/bindings.lua`.

---

## Keyboard Controls & Navigation

Tactical Display is fully operable from the keyboard:

| Key | Action |
|---|---|
| `1` – `5` | Switch directly between instruments |
| `Tab` / `Shift+Tab` | Cycle through nodes and entities |
| `Arrow Keys` | Move focus spatially across visible entities |
| `Enter` | Focus and center on the selected entity |
| `X` | Expand / collapse application groups into individual process instances |
| `F` | Isolate selected entity and its direct connections |
| `Space` | **Freeze / Resume** live data collection |
| `/` | **Search** across processes, PIDs, ports, hosts, mounts, and audio streams |
| `P` | Toggle **Screen-Share Privacy Mode** |
| `?` / `H` | Open Legend and keyboard shortcut guide |
| `,` | Open Settings panel |
| `C` | Copy selected entity details to system clipboard |
| `Backspace` | Step back one navigation level |
| `R` | Reset view, filters, and zoom |
| `Escape` | **Dismiss immediately** |
| `F6` | Toggle focus between canvas graph and UI controls |

### Instrument-Specific Controls
- **Connection Field**: `V` cycles connection direction (inbound / outbound / loopback), `N` toggles TCP/UDP, `L` toggles listener ports, `O` toggles loopback.
- **Process Topology**: `E` cycles emphasis ranking (CPU, Memory, Threads, Network, I/O).
- **Machine Anatomy**: `T` toggles the 60-second historical trend graph.
- **Storage & Audio**: `V` cycles display lenses (reads, writes, mounts, devices / playback, capture, muted).

---

## Settings & Customization

Open Settings (`Comma`) to customize:
- **Default Instrument**: Choose which instrument opens first.
- **Refresh Rate**: Adjust collection cadence (`Responsive` ~0.35s, `Balanced` ~0.75s, `Efficient` ~1.5s).
- **Animation Speed**: Adjust transition fluidity (`Vivid`, `Normal`, `Reduced`).
- **Label Density**: Set how many labels appear on dense graphs (`Minimal`, `Balanced`, `Dense`).
- **Audio Controls**: Enable opt-in stream muting and default endpoint selection with one-click undo.
- **Endpoint Naming**: Choose between raw IP addresses, local `/etc/hosts` aliases, or opt-in reverse DNS.

---

## Requirements

- **Host**: [Omarchy Quattro](https://github.com/omarchy/omarchy) 4.0.1+ (Wayland / Hyprland / Quickshell)
- **Python**: Python 3.10 or newer (uses standard library only)
- **Audio (Optional)**: `pipewire` and `wireplumber` (`pw-dump` / `wpctl`) for audio graph and volume control

---

## Development & Testing

```bash
# Run unit and integration test suites
make test

# Run environment diagnostics
bash scripts/doctor.sh

# Validate against host contracts
bash scripts/validate.sh
```

---

## Documentation

For technical specifications, architecture details, and developer docs:
- [Architecture & Design](docs/ARCHITECTURE.md)
- [Data Model & Schemas](docs/DATA-MODEL.md)
- [Configuration Reference](docs/CONFIGURATION.md)
- [Security & Privacy](docs/SECURITY-PRIVACY.md)
- [Visual System & Canvas Renderer](docs/VISUAL-DESIGN.md)
- [Testing Guide](docs/TESTING.md)
- [Operator Handoff](docs/HANDOFF.md)

---

## License

This project is licensed under the [MIT License](LICENSE). Copyright (c) 2026 nshkrdotcom.
