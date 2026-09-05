# Validation Record

## 0.2 build environment - 2026-09-04

The 0.2 Connection Field revision was built/tested in a Linux container, not rendered inside a Wayland/Hyprland graphical session.

Available here:

- Python 3.13.5
- Bash 5.2.37
- Linux procfs

Unavailable here:

- live Omarchy shell
- Quickshell graphical runtime
- Hyprland compositor/session
- target monitor geometry/scaling
- target Qt `qmllint`

## Automated 0.2 results

- **24 tests passed**
- **0 failed**
- real `/proc` TCP listener/connection integration passed;
- PID/process attribution for the test-owned socket passed;
- close-to-ghost lifecycle passed;
- new process↔remote aggregation tests passed;
- multi-socket relationship aggregation passed;
- inbound local-service-port semantics passed;
- listener modeling passed;
- loopback scope passed;
- closed relationship modeling passed;
- live `TelemetryEngine` sampling and CLI JSON emission passed;
- shell script syntax validation is part of `make validate`;
- Python source compiles.

## Prior real-host evidence from the user

Before the 0.2 visual redesign, the user ran on the actual Omarchy Quattro machine:

```bash
omarchy plugin validate .
```

It returned silently, indicating successful plugin validation.

The user also ran Qt 6.11.2 `qmllint` against both this plugin and Omarchy's own `shell/services/PluginRegistry.qml`. The official first-party file produced the same classes of `qs.Commons` import and `QProcess::ExitStatus` metadata warnings, plus many unqualified-access warnings. Therefore those specific external-linter warnings are environmental/tool-context noise unless the plugin produces additional parser/type/runtime failures.

The prior Radar and Reactor both successfully rendered on the real host. This proves the basic third-party overlay discovery/summon path worked before 0.2. It does **not** prove the new Connection Field QML is visually or runtime-correct.

## Remaining 0.2 gates

Run on the user's actual Quattro workstation:

```bash
omarchy plugin validate .
omarchy-restart-shell
omarchy-shell shell summon nshkr.tactical-display '{}'
```

Then complete `docs/HANDOFF.md`.

The most important remaining gate is visual: the user already rejected the original instruments as conceptually lame. 0.2 must make process→remote relationships obvious without explanation.
