# Tactical Display 0.2 - Agent Handoff

## Read this first

Version 0.2 intentionally abandons the original Network Radar/System Reactor product presentation. The Quattro lifecycle/backend plumbing survived; the primary instrument did not.

The approved product thesis is now:

> **See every program on this machine communicating with every remote system in real time.**

The next agent's job is **run on the real Omarchy workstation -> observe -> debug -> visually harden -> finalize**. Do not resurrect decorative radar rings or the reactor as the main experience unless the user explicitly reverses this decision.

## What changed in 0.2

Implemented:

- one focused **Connection Field** instrument;
- local process hubs inside a semantic machine boundary;
- remote IP systems around the external perimeter;
- outbound/right, likely-inbound/left, mixed/top, loopback/inner spatial sectors;
- real process↔remote relationship links aggregated from visible kernel sockets;
- directional tracers that explicitly do **not** claim per-link bandwidth;
- line thickness from socket multiplicity + real kernel queue pressure;
- listener apertures attached to local process ownership instead of fake remote contacts;
- new relationship pulses and closed relationship decay;
- click-to-isolate process or remote topology;
- process/remote detail panel;
- real summary counts and machine-wide RX/TX;
- richer backend `network` model in addition to raw `contacts`;
- process executable/argv0 identity without exposing full command arguments;
- updated docs/tests/bindings/manifest.

Legacy files `RadarInstrument.qml` and `ReactorInstrument.qml` may still exist after applying the incremental zip because an unzip overlay cannot delete files. `Overlay.qml` does not reference them.

## Current runtime architecture

```text
Omarchy shell summon
    -> Overlay.qml
       -> one Telemetry.qml backend
          -> scripts/telemetry.py
             -> raw socket contacts
             -> network aggregation model
       -> per-screen PanelWindow
          -> HudSurface
             -> NetworkFieldInstrument
```

Quattro assumptions were rechecked against current docs before this build:

- third-party plugins live under `~/.config/omarchy/plugins/<id>/`;
- overlay entry point is an `Item`;
- plugin shares the long-running shell process;
- overlay exposes `open(payloadJson)` / `close()`;
- `omarchy-shell shell summon|hide|toggle` is canonical IPC.

## Known validation already achieved by the user on the prior version

On the actual Quattro host, `omarchy plugin validate .` completed silently/successfully. The user's `qmllint` invocation also demonstrated that `qs.Commons` and `QProcess::ExitStatus` warnings occur when linting Omarchy's own `PluginRegistry.qml` under the same command, so those warnings alone are not evidence of a plugin defect.

Do not waste time trying to make external `qmllint` completely warning-free if identical environment warnings occur on first-party Quattro QML. Runtime errors and plugin-specific lint/parser errors still matter.

## First 0.2 target-host session

Apply the incremental archive over the existing development plugin/repository, then:

```bash
cd ~/.config/omarchy/plugins/nshkr.tactical-display
omarchy plugin validate .
omarchy-restart-shell
omarchy-shell shell summon nshkr.tactical-display '{}'
```

If it does not render:

```bash
qs log -p "$OMARCHY_PATH/shell" --tail 200
```

Capture exact QML/runtime errors before changing code.

## Visual acceptance - the most important gate

The first five seconds matter more than any automated test.

Expected first impression:

1. `NETWORK / LIVE` and `THIS MACHINE ⇄ THE WORLD` establish the idea immediately.
2. Named local programs are visibly inside the machine boundary.
3. Remote IP systems are visibly outside.
4. Lines make ownership/peer relationships obvious without reading a legend.
5. Direction tracers make outbound vs inbound visually understandable.

Release blocker:

> A first-time viewer says “cool HUD/radar, but what is it showing?”

If that happens, fix hierarchy/layout before adding features.

## Functional acceptance matrix

### A. Existing browser/session traffic

Open Connection Field while Chrome/terminal/agent tools have network activity.

Confirm:

- recognizable user-owned network processes appear where permissions allow;
- remote systems do not overlap so badly that addresses become meaningless;
- browser-heavy connection counts aggregate into readable process↔remote links rather than one glyph per socket;
- clicking Chrome/Codex/etc. isolates its peer set.

### B. Outbound acquisition

```bash
curl -I https://example.com
```

Expected: outbound relationship appears/pulses on the right and may then decay after curl exits.

### C. Listener

```bash
python3 -m http.server 8765
```

Expected:

- Python process appears/updates;
- listener count increases;
- aperture appears on machine boundary;
- no fake remote node is created merely because a socket is listening.

### D. Likely inbound

From another LAN machine, if policy permits:

```bash
curl http://TARGET_IP:8765/
```

Expected: peer appears on the left and connects to the Python process. The UI may say inbound, but never attack/threat.

### E. Loopback

```bash
curl http://127.0.0.1:8765/
```

Expected: localhost relationship stays inside the machine field rather than being placed in the outside world.

### F. Selection

- click local process -> unrelated topology dims;
- click remote IP -> unrelated topology dims;
- detail panel matches selected node;
- click selected node or empty field -> clears selection;
- hover highlight is responsive and does not cause shell jank.

### G. Lifecycle

- new relationship pulse is visible but not obnoxious;
- closed relationships fade/dash instead of popping;
- Escape closes;
- `shell hide` closes;
- repeated summon/hide 20x leaves no stranded layer-shell window;
- backend process exists only while open.

### H. Hold binding

Use `./scripts/print-bindings.sh`. Verify press opens/release closes, then verify toggle fallback. Keep Escape as recovery.

### I. Multi-monitor

- no `screen` payload: every output renders;
- only focused output owns exclusive keyboard focus;
- no duplicate telemetry backend per output;
- optional `{"screen":"DP-1"}` targeting still works;
- graph scales without labels clipping on each output.

## Layout hardening priorities

The current layout is deterministic/semantic, but real visual QA is still required.

Inspect these first:

1. **process label collisions** with 10-18 active user processes;
2. **remote label collisions** with 20-36 active remotes;
3. line crossing under browser-heavy workloads;
4. whether inbound/red looks like “malicious” rather than simply direction;
5. whether top `BIDIRECTIONAL` sector is actually useful or visually confusing;
6. detail panel covering a selected remote on the right side;
7. whether 1080p text is too small;
8. whether 4K/fractional scaling makes geometry too sparse;
9. layout churn as remotes appear/disappear;
10. whether localhost deserves a better multi-process representation than one shared loopback peer node.

Do not solve these by adding more HUD chrome. Solve them in topology/layout.

## Backend truth boundaries

### Reliable

- socket existence/state from procfs;
- local/remote endpoints;
- current kernel tx/rx queue depth;
- current-user process attribution when `/proc/<pid>/fd` is readable;
- machine-wide RX/TX from `/proc/net/dev`;
- lifecycle timing inside the sampler.

### Heuristic / best effort

- likely inbound vs outbound based on local listener-port correlation;
- unavailable process ownership becomes unattributed.

### Deliberately not claimed

- packet contents;
- per-link historical throughput;
- firewall path/provenance;
- remote hostname/company/geolocation;
- attack/threat classification.

If a future iteration wants real per-link byte rates, add a data source that genuinely exposes cumulative per-socket counters and document its privilege/performance implications. Do not infer throughput from animation.

## Privacy hardening

The backend now discards full command arguments and keeps argv0/executable identity only. Verify no future debug UI accidentally exposes raw `/proc/<pid>/cmdline`.

A presentation-redaction mode may be valuable later because IPs/PIDs remain sensitive. Do not add silent DNS/GeoIP as a shortcut to prettier labels.

## Performance hardening

With overlay open:

```bash
ps -C python3 -o pid,pcpu,rss,args | grep tactical-display
ps -C quickshell -o pid,pcpu,rss,args
```

Stress with browser tabs, local dev servers, SSH, and connection churn. Measure at the actual monitor refresh rate. If procfd scanning becomes expensive, first add a short TTL cache for inode→process ownership rather than scraping repeated CLI output every sample.

## Automated gates

```bash
make test
make validate
```

Current build-environment suite contains 24 tests and covers the new network aggregation semantics as well as real procfs socket integration.

On the actual host also run:

```bash
omarchy plugin validate .
/usr/lib/qt6/bin/qmllint -I "$OMARCHY_PATH/shell" Overlay.qml core/*.qml instruments/*.qml
```

Compare known environment warnings against first-party Omarchy QML before labeling them plugin failures.

## Final definition of done

Do not call 0.2 hardened/final until:

1. automated tests pass;
2. plugin validation passes on current Quattro;
3. no plugin-specific QML parser/runtime errors remain;
4. visual thesis is obvious within a few seconds;
5. browser/SSH/curl/dev-server real workloads produce understandable topology;
6. process and remote selection work;
7. new/closed lifecycle works;
8. hold + toggle + Escape paths work;
9. multi-monitor behavior is green or support is explicitly narrowed;
10. measured shell/backend performance is acceptable;
11. install/restart/disable/re-enable/remove lifecycle is clean;
12. marketplace media demonstrates the topology itself, not decorative effects.

Until then, status is: **implemented, automated-model-tested, prior Quattro plugin plumbing validated, pending live visual hardening of Connection Field**.
