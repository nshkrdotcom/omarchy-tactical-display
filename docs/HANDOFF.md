# Operator and next-agent handoff

Target: **Omarchy Quattro 4.0.1**. Delivery: **1.0.0-rc.1 incremental overlay** against the supplied 0.2.0 repository. All five instrument paths and product shell are implemented. Real desktop/layer-shell/font/performance acceptance is still required; read VALIDATION.md before calling this production-certified.

## Apply the overlay

Run in the exact baseline checkout, not an unrelated version. These steps preserve a recovery copy and verify the source before overwriting anything. Replace ZIP with its actual downloaded path.

```bash
ZIP="$HOME/Downloads/nshkr.tactical-display-1.0.0-rc.1-overlay.zip"
cd "$HOME/.config/omarchy/plugins/nshkr.tactical-display"
# Stop and reconcile any unexpected baseline differences rather than forcing them.
unzip -p "$ZIP" OVERLAY_BASELINE.sha256 | sha256sum --check -
BACKUP="$HOME/nshkr-tactical-display-before-$(date +%Y%m%d-%H%M%S).tar.gz"
tar --exclude='./.git' --exclude='./__pycache__' -czf "$BACKUP" .
printf 'Recovery copy: %s\n' "$BACKUP"
omarchy-shell shell hide nshkr.tactical-display
unzip -o "$ZIP" -d .
python3 scripts/apply-overlay-deletions.py
python3 scripts/apply-overlay-deletions.py --apply
sha256sum --check MANIFEST.sha256
sha256sum --check OVERLAY_MANIFEST.sha256
bash scripts/validate.sh --require-native
omarchy plugin validate .
omarchy-shell shell rescanPlugins
omarchy-restart-shell
```

`OVERLAY_DELETE.txt` lists exactly six legacy QML files: HudSurface, MetricReadout, Scanlines, NetworkFieldInstrument, RadarInstrument and ReactorInstrument. The helper rejects traversal/absolute paths and symlink ancestors and deletes only those listed files. Extraction alone cannot remove them. No settings are deleted. Retired empty directories are harmless.

If the plugin is not already enabled, explicitly run `omarchy plugin enable nshkr.tactical-display`. Native enablement can place its widget. Use `omarchy bar put nshkr.tactical-display` for explicit placement or `omarchy bar move nshkr.tactical-display --section right --index 0` to move it. Do not overwrite shell.json with an example configuration.

For rollback, hide the plugin, move the failed plugin directory aside (do not delete the backup), create the original directory and extract your recovery tar there, validate, rescan and restart the shell. This restores the entire saved content rather than leaving added release files behind. Keep any Git metadata/local work separately before moving a development checkout.

## Direct commands and versions

```bash
cd "$HOME/.config/omarchy/plugins/nshkr.tactical-display"
bash scripts/doctor.sh
omarchy plugin list
omarchy-shell shell summon nshkr.tactical-display '{"instrument":"connection"}'
omarchy-shell shell summon nshkr.tactical-display '{"instrument":"processes"}'
omarchy-shell shell summon nshkr.tactical-display '{"instrument":"machine"}'
omarchy-shell shell summon nshkr.tactical-display '{"instrument":"storage"}'
omarchy-shell shell summon nshkr.tactical-display '{"instrument":"audio"}'
omarchy-shell shell toggle nshkr.tactical-display '{}'
omarchy-shell shell hide nshkr.tactical-display
# While open; returns identity-free metrics, not a raw private snapshot:
omarchy-shell shell call nshkr.tactical-display diagnostics '{}'
```

Record `git -C "$OMARCHY_PATH" describe --tags --always`, `git -C "$OMARCHY_PATH" rev-parse HEAD`, `quickshell --version` and `hyprctl version`. The build source review was tag-pinned, not a claim about your installed commit. Check the log destination used by your existing shell launcher; a useful initial journal search is:

```bash
journalctl --user -b --no-pager | grep -Ei 'tactical|nshkr|quickshell|qml'
```

This search is only useful when the launcher's output reaches the user journal. If it does not, capture the existing shell launcher's stderr using its normal session mechanism. Do not launch another Quickshell. Keep logs and screenshots in `/tmp` or a private evidence directory **outside the watched plugin tree**.

## First target gate: compile/load/keyboard

Run `bash scripts/validate.sh --require-native`; save output. A plugin-local QML error is a FAIL to fix before proceeding. For import-metadata warnings, run the same qmllint on the first-party BarWidget/WidgetButton files and keep both logs; do not whitelist all warnings. Confirm native manifest validation, rescan, enablement and a clean shell restart.

Open Connection Field, acknowledge the first-run picker, then exercise 1-5, all arrow/Tab traversal, hover/click/double-click, Enter, F, X, R, /, Space, D, ?, comma, P and F6. F6 must reach every control by ordinary Tab/Shift-Tab without trapping field navigation. Escape must dismiss Tactical Display immediately from every mode, including sheets, search, filters and focused views. Backspace walks back one UI/focus level; R resets the current view. Close button and shell hide must also dismiss immediately. Normal updates must preserve selection; exiting processes must not transfer selection to a recycled PID.

Freeze, inspect multiple socket pages, continue generating live traffic, and confirm the displayed timestamp/details do not change. Resume must not replay an acquisition storm. While frozen, terminate only the sampler PID reported by diagnostics (never the shell); check bounded helper restart and the explicit unavailable frozen-detail behavior. Repeat malformed payloads such as `'[]'` and unknown instruments; they must not crash or execute anything.

## Hold shortcut

```bash
bash scripts/print-bindings.sh > /tmp/tactical-bindings.lua
omarchy menu keybindings --print
# Read the generated block, resolve F10/F11 collisions, then append it ONCE
# using your editor to ~/.config/hypr/bindings.lua.
hyprctl reload
```

The printed Lua uses Super+F10 toggle and Super+F11 hold. Press starts one guarded invocation; release cancels the matching token even if it arrives first. Test: ordinary press/hold/release; release Super before F11; quick tap during a cold plugin load; repeated hold key events; rapid alternating taps; unrelated F11 releases; Escape while held then release; shell reload between uses. Expected: no stranded overlay, duplicate helper, unrelated hide or swallowed ordinary F11 release. After **compositor/keymap reload during an active hold**, use `omarchy-shell shell hide nshkr.tactical-display` if the compositor lost the Lua callback state; do not claim that a reloaded compositor can reproduce a discarded release callback.

The runtime lock/tombstone tests passed here; physical key delivery under Quattro's exclusive layer is NOT RUN and must be checked here before enabling hold as a daily workflow.

## Automatic native lifecycle/soak

The runner intentionally takes and releases keyboard focus; run it when you are not doing other work.

```bash
python3 scripts/live-validate.py --run --cycles 50 --soak-seconds 1800 --output /tmp/tactical-native.json
python3 scripts/audio-integration.py --run
python3 scripts/profile.py --instrument all --samples 120 --interval 0.75 --output /tmp/tactical-profile.json
```

Check exactly one sampler per open, none after hide, successful mode cycling, advancing sequence/freshness, no runaway RSS and no shell crash. Inspect logs for binding/JS/type errors, not just exit codes. The report samples helper/shell CPU ticks/RSS and UI layout counts/timing; it **does not certify** physical keyboard, pointer, hotplug, native screenshots, frame pacing or hot reload. Record those manual gates separately. A short profile is not a 30-minute leak test.

## Controlled real activity

Use existing browser/development workloads as the main dense case. For repeatable local sockets, in another terminal run `python3 -m http.server 8765 --bind 127.0.0.1`, then `curl http://127.0.0.1:8765/`. A TCP listener aperture, loopback relationship and correct process owner should appear. Stop only that test server and verify bounded close ghosts. Use an IPv6 test supported by the suite; skip only with the actual error recorded.

For a true non-loopback inbound case, bind a controlled test server to an approved LAN address and connect from a second device. Do not expose a server to an untrusted network merely for this test. Confirm that the direction is labeled inferred and the local service port is correct. The automated container did not have an appropriate non-loopback address.

For process/storage activity, the existing integration tests spawn actual children and write/fsync/remove temporary files. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_providers.py -v`. Observe I/O rates on the process and backing device where supported. A cached/tmpfs operation need not produce block I/O; do not treat that as evidence for invented device traffic. For dense user work, build a project or copy a disposable file on a known local filesystem; no destructive disks, mounts or partition changes.

For audio, the dedicated runner creates a silent stream and verifies outgoing routes. In the UI, trace an ordinary playback application through routing to its sink/device, and a recording stream from its source. Test pause/mute/default metadata. Optional action testing requires tdAudioActions=true, confirmation, observed state change and undo, then turn actions off again. Device unplug/restore should yield accurate graph changes; never test with a safety-critical call in progress.

## Visual, monitor and reload acceptance matrix

Capture each of five modes at quiet/normal/dense, selected, search, degraded, light/dark and reduced-motion states. Cover 1920x1080 and available 2560x1440/4K fractional scaling. Use your normal desktop capture tool; do not substitute the checked-in SVG fixtures. Verify no primary-label overlaps/clipping, no unreadable selected fields, no accidental per-flow rate semantics, no distracting perpetual movement and no visible update hitch. Record whether an unfamiliar reviewer can explain the geometry and answer the instrument questions in VISUAL-DESIGN.md.

Summon from monitor A and B, then with an explicit `monitor` payload. Other displays must remain unobstructed. Try mixed scales, unplug/replug while closed and open, and restart the shell with multiple monitors. Verify a single helper and no duplicated keyboard focus. Test both horizontal and vertical native bar placement, left-click toggle and right-click picker. Save the previous bar position before changing it and restore that exact value afterwards.

For hot reload, while open touch only `Overlay.qml` (content unchanged), wait for the host's code reload, and repeat selection/instrument switching. Repeat a real `omarchy-restart-shell` and confirm no orphan helper. Native reload/enable/disable/plugin removal must not leave timers/processes. Record resource trends at equivalent points across at least 50 cycles and the 30-minute run.

## Specific remaining gates and conditional extensions

All P0 code paths are implemented; none of the five views is a stub. **Not yet evidenced on an actual desktop:** native QML compilation/import loading, true layer-shell focus/hold behavior, pointer/accessibility traversal, native text/font/high-DPI layout, bar orientation/clicks, monitor hotplug, shell restart/hot reload, rendered frame timing and 30-minute native stability. Those are release blockers for changing rc to a production-certified tag, not items falsely checked complete.

Optional inet_diag integration skipped because this container's kernel returned ENOENT; procfs and binary parser tests passed. Real PipeWire and non-loopback accepted traffic were unavailable. GPU/thermal fields depend on actual target capabilities. Reverse DNS/offline MMDB and wpctl mutation code exist but need explicit opt-in target validation; no resolver or audio mutation was performed here.

Workspace/Agent Topology remains conditional after P0 native acceptance, exactly as the supplied plan requires. Implement only with reliable workspace/project identities and sourced agent states, never a heuristic vendor-specific activity label. Stream rerouting is not implemented because the chosen safe wpctl path does not provide a reliable atomic validated route API; a next agent must add a typed PipeWire/WirePlumber route provider with serial-safe tests before exposing it. No persistent replay, terminal-launch/kill/disconnect/mount management, privileged tracing or audio level meter is claimed.

## Signoff and next-agent output

Update VALIDATION.md and TRACEABILITY.md with exact PASS/FAIL/PARTIAL/NOT RUN, installed commits, commands, logs, real screenshot paths, measurements and reviewer answers. Fix any plugin errors or visual fail criteria; do not merely list them as future polish. Re-run both full suites after fixes. Produce another **incremental overlay against this rc tree**, with explicit deletions, final checksums and pristine reconstruction, and retain the baseline identity for that new overlay. The outer ZIP SHA-256 belongs in the external delivery record; a ZIP cannot contain its own final checksum without a self-reference problem.
