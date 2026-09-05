# Testing

## Automated suite

Run:

```bash
make test
```

The dependency-free `unittest` suite covers:

- Quattro manifest and entry-point contract;
- no symlinks;
- `Item` + `open()` + `close()` lifecycle;
- one-shell-host pattern;
- fullscreen layer-shell primitives;
- avoidance of the known per-screen direct parent-width/height binding pattern;
- no right-click MouseAreas;
- procfs IPv4/IPv6 parsing;
- TCP socket parsing and direction classification;
- real TCP listener/connection discovery via `/proc`;
- PID/process attribution for a real socket owned by the test process;
- close-to-ghost lifecycle;
- process↔remote aggregation;
- multiple sockets collapsing into one relationship;
- listener-vs-remote modeling;
- loopback scope;
- inbound service-port semantics;
- closed relationship retention;
- live `TelemetryEngine` frame and CLI JSON output;
- required docs and runtime-script permissions.

## Validation suite

```bash
make validate
```

Adds:

- shell-script syntax checks;
- live backend JSON probe;
- `omarchy plugin validate .` when Omarchy is installed;
- `qmllint -I "$OMARCHY_PATH/shell" ...` when available.

A skipped host/QML step is not a pass.

## Real Quattro functional acceptance

Run on the target Omarchy workstation.

### Baseline

```bash
omarchy plugin validate .
omarchy-restart-shell
omarchy-shell shell summon nshkr.tactical-display '{}'
```

Expected immediately:

- header says `NETWORK / LIVE` and `THIS MACHINE ⇄ THE WORLD`;
- local process hubs appear inside the machine boundary;
- remote IP systems appear at the perimeter when external connections exist;
- loopback remains inside the machine field;
- right/left sector labels match outbound/inbound semantics;
- summary counts update.

### Process identity

With the overlay open, start or use a networked program you can identify (browser, `curl`, `ssh`, local dev server). Confirm the process hub name/PID is plausible and clicking it isolates only its attached relationships.

### Outbound acquisition

In another terminal:

```bash
curl -I https://example.com
```

Expected: a new outbound relationship appears or pulses briefly on the right side and may fade quickly after curl exits.

### Listener aperture

```bash
python3 -m http.server 8765
```

Expected: listener count increases and an aperture appears on the machine boundary for the owning Python process. It must **not** create a fake remote system.

### Likely inbound

From another machine on the LAN, connect to that server if network policy permits:

```bash
curl http://TARGET_IP:8765/
```

Expected: a likely-inbound relationship appears on the left side connected to the Python process. This tests the listener-port inference path.

### Selection

- click a process: unrelated graph dims, attached remotes/links stay bright;
- click a remote: unrelated graph dims, attached processes/links stay bright;
- click empty space or the same selected node: clear isolation;
- detail panel remains readable and does not cover the entire graph.

### Lifecycle

- new relationship pulses;
- closed relationship becomes dashed/fades rather than popping immediately;
- `Esc` closes;
- shell `hide` closes;
- hold/release binding closes reliably enough for daily use;
- toggle fallback works.

## Visual acceptance

Test at minimum:

- 1920x1080;
- 2560x1440 or native primary resolution;
- high-DPI/fractional scaling if used;
- actual multi-monitor layout.

Look specifically for:

- node-label collisions;
- remote nodes pushed outside usable content margins;
- detail panel obscuring selected topology;
- excessive line crossings under browser-heavy workloads;
- process labels too small at 1080p;
- visual aliasing/jank at high refresh rate;
- selected/hovered state not repainting;
- layout churn whenever connections come/go.

The release gate is subjective but strict: a first-time viewer should not ask “what radar is this?” They should see a machine, local programs, remote peers, and connections.

## Performance acceptance

With Connection Field open for at least 60 seconds:

```bash
ps -C python3 -o pid,pcpu,rss,args | grep tactical-display
ps -C quickshell -o pid,pcpu,rss,args
```

Repeat under browser/socket churn. Do not invent an arbitrary CPU threshold before measuring the real target hardware; sustained visible shell stutter is a release blocker.
