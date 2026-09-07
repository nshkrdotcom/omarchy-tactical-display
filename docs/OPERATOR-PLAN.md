# Tactical Display: operator mission control

Implementation branch: `feat/operator-mission-control`  
Reviewed baseline: `d47f663`  
Plan date: 2026-09-07  
Personal copy: `~/Documents/Tactical-Display/operator-mission-control.md`

## Product direction and review

### Locked user constraint: header and launch consistency

The main title's existing font sizing and the top-right action rail's existing placement are protected. Do not redesign, rescale or move them. The native bar panel is the reference for ordinary use. The reviewed baseline already has a separate fullscreen `Overlay.qml` with larger typography; earlier IPC validation exercised that path, not the clicked native panel. That distinction must be explicit in evidence and documentation.

Resolution (updated to the user's explicit overlay requirement): preserve existing click and IPC launch behavior; make the clicked panel's presentation the only shared presentation. Remove the alternate font, header, spacing and opacity branches from `ThemeAdapter` and `TacticalDisplayShell`, retaining the existing native values. Preserve the main title's `Style.font.subtitle` binding and the native action rail's order, spacing and right alignment. Both hosts use the same content component. The fullscreen host uses Omarchy's existing `Ui.BorderSurface` with the same popup border specification and eight-unit padding as `Ui.KeyboardPanel`; only window bounds, anchoring and focus lifecycle remain host-specific. No new router, launch option, typography preference or system/bar configuration change is needed. TDD first locks native typography and header geometry across widths and host theme changes, then tests shared host wiring; native pointer-click and IPC captures are separate acceptance evidence. Record unverified cases honestly.

Primary-source basis: [Qt QML reusable types](https://doc.qt.io/qt-6/qtqml-documents-definetypes.html) supports one shared component, and [Qt Quick Layouts](https://doc.qt.io/qt-6/qtquicklayouts-overview.html) owns child sizing and alignment. [Quickshell PanelWindow](https://quickshell.org/docs/v0.2.1/types/Quickshell/PanelWindow/) anchors determine the window extent, not the content's font scale. Installed Omarchy `Ui/KeyboardPanel.qml` and `Ui/BorderSurface.qml` supply the actual host padding, border and popup-theme contract. Fullscreen exists for keybinding/IPC, selected-monitor and hold-to-inspect use; bar clicks use a bounded bar-anchored panel. None of these use cases requires different internal typography.

The five instruments already answer structural questions well: network relationships, process ancestry, resource contributors, storage topology, and audio routes. The Python helper has unusually strong containment: bounded collection, truthful missing counters, explicit capabilities, exact-generation freeze, isolated optional providers, and ephemeral lifetime. Keep these properties.

The current operator must assemble the story manually. Lifecycle changes disappear after four seconds, trends cannot be interrogated, selected entities cannot be kept together across instruments, and high resource usage has little explanation. The next release should answer: **What needs attention? What changed? What should I inspect? Did my intervention help?**

Review findings:

- `EventStore` already emits bounded, trustworthy lifecycle events, suppressing invented closes after incomplete scans. Build session history from these events rather than inferring disappearance from a truncated frontend frame.
- `Trend.qml` plots real aggregate samples, but has no time cursor, scale labels, time-window choice, or clear gaps after acquisition stops. Its dual-series distinction primarily relies on color.
- `NavigationController` centralizes freeze, context and privacy. Put investigation state here; keep derived models pure and testable with Node.
- The field has stable layout and label budgets. Preserve its spatial grammar and native panel perimeter. Add concise operator chrome and a scrollable briefing, avoiding a permanent grid that shrinks the field.
- Capabilities are detailed but buried. Surface stale/partial evidence directly in findings and baseline comparisons.
- Existing privacy covers inspection and clipboard output. Extend it to every new identity-bearing string, including retained history and pins; clear session state on dismissal.

## Research and design constraints

Research used primary sources before implementation:

1. [Linux PSI documentation](https://docs.kernel.org/accounting/psi.html): PSI measures time stalled on CPU, memory and I/O. `some` and `full` have different meanings; system-level CPU `full` is undefined. Show the measured window and stall percentage, never infer contention solely from CPU utilization. Numerical attention thresholds below are product heuristics, not kernel recommendations.
2. [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/): actionable symptoms and simple, understandable rules reduce operator noise. Use explanatory findings with evidence and an inspection destination. Do not introduce background notifications or pretend correlation identifies a root cause.
3. [Qt Quick performance guidance](https://doc.qt.io/qt-6/qtquick-performance.html): avoid blocking work in UI updates, profile actual costs, and limit unnecessary object/binding work. Keep a single helper; use bounded records and sample-driven drawing, and load the briefing on demand.
4. [Qt Canvas](https://doc.qt.io/qt-6/qml-qtquick-canvas.html): repainting image-backed canvases can entail texture uploads. Trend inspection should repaint only for changed samples, geometry, theme or cursor; no continuous visual timer.
5. [W3C use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) and [pause, stop, hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html): communicate states with words/shapes as well as color and retain explicit freeze/reduced-motion paths. Apply these principles to Qt controls without claiming a WCAG certification.
6. [Qt Quick accessibility](https://doc.qt.io/qt-6/accessible-qtquick.html) and [keyboard focus](https://doc.qt.io/qt-6/qtquick-input-focus.html): give controls names, conventional focus behavior and keyboard equivalents; preserve Escape as immediate dismissal and editor ownership of typing.

## Implementation milestones

### 1. Explainable operator briefing

Implement a pure `model/Operator.js` and an on-demand `core/OperatorSheet.qml`. Add an always-reachable `A Briefing` entry in the instrument rail and an unmodified `A` shortcut.

- Rank memory/I/O full-stall symptoms, CPU/memory/I/O some-stall pressure, low available memory, low local filesystem capacity, and degraded providers.
- Every finding includes severity text, measured evidence, provenance/limits, a practical inspection suggestion, and a typed destination.
- Starting attention thresholds: some PSI avg10 >=5% (elevated >=20%), memory/I/O full avg10 >=2% (elevated >=10%), available RAM <10% (<5% elevated), available filesystem capacity <10% (<3% elevated). These are transparent triage heuristics; no automatic host actions.
- High CPU without PSI is a usage observation, not a contention diagnosis. Storage busy time is not saturation on parallel devices. RSS is never summed into a supposedly exact host-memory total.
- Missing, inactive or stale counters must not become healthy zeros. Use provider-specific freshness and explicitly qualify incomplete data.
- Keep the briefing concise with bounded findings, low-noise empty states and direct jumps into the relevant instrument/entity.

### 2. Session activity and investigation continuity

- Retain at most 120 lifecycle records for five minutes while a surface is open. Deduplicate repeated event frames; only consume backend events; preserve the old four-second field effects.
- Filter the timeline by instrument/domain and event kind (opened/changed/closed). Show age, name/alias, event type, and origin.
- Reset history when the helper timeline restarts; never merge different helper epochs. A frozen view keeps the displayed timeline stable; collection may continue separately.
- Allow direct inspection of retained events. If an entity no longer exists, clearly report that it ended or is outside collected scope, rather than selecting a reused PID.
- Pin up to eight entities for the current session, retaining only lightweight identity and scalar metrics. Navigate among them across instruments; unpin individually and clear as a group. Show “not observed” rather than claiming exit from an incomplete collection.
- Privacy redacts rendered history and pins dynamically, including names remembered before privacy was enabled. Session state is cleared when dismissed.

### 3. Baseline and handoff

- Capture one compact aggregate baseline on demand, including provider timestamps, CPU, available/used memory, PSI, host RX/TX and measured storage rates.
- Compare current or frozen observations to the baseline using signed deltas and correct units (CPU/PSI percentage points). Unknown values remain unknown, and provider gaps/staleness qualify comparisons.
- Show baseline age and clear/replace actions. No unbounded full-frame archive and no fabricated process/network byte attribution.
- Copy a concise operator report containing observation time, live/frozen status, findings, baseline deltas, pins and recent activity. Construct the report explicitly so privacy mode cannot leak raw retained objects, paths, addresses or keys.

### 4. Interactive trend graphics

- Extract a pure `visual/TrendModel.js` for 15/30/60-second windows, timestamp-based geometry, finite bounds, measured sample statistics and cursor selection.
- Split paths at missing counters and acquisition gaps; never interpolate through unknown observations.
- Add scale values, time range and current/min/max summaries. CPU uses a fixed 0–100% host scale; byte/rate plots use a shared measured scale.
- Differentiate paired traces by solid/dashed strokes plus explicit Read/Write and Receive/Transmit text.
- Support pointer hover/scrub and keyboard Left/Right/Home/End inspection with a visible cursor and timestamp. Returning to live releases the inspection cursor. No animation loop.
- Extend aggregate history with CPU/memory/I/O PSI to inspect pressure over time; retain protocol bounds and missing-value semantics.

### 5. UX refinement and validation

- Preserve native header/Close geometry, style-token spacing, search editing and F6 control focus. The briefing scrolls within small panels; controls have accessible names and visible focus.
- Show selected-entity pin state in inspection. Make clipboard feedback visible and nonpersistent.
- Improve data-source status accessibility and keyboard activation where review finds gaps.
- Document every shortcut, state lifetime, threshold and evidence limitation. Keep the personal plan copy current with executed results and remaining acceptance work.
- Inspect native captures at the available host size plus synthetic light/dark, missing, dense, privacy and reduced-motion cases. Do not label fixture rendering as a native screenshot.

## TDD and delivery procedure

For each milestone: write behavior-focused regression tests, execute them and record the expected failure, implement the smallest coherent behavior, run the targeted suite, refine, then run the relevant existing regressions. Tests should exercise production model functions and meaningful state transitions, not merely duplicate implementation strings. Add native QML tests where possible for input/state integration, and use source contracts only for host wiring that cannot be exercised headlessly.

Test matrix: missing/null/non-finite counters; PSI semantics; stale/inactive/partial capabilities; event duplicate/reordering/expiry/restart; immutable frozen state; bounds under dense input; PID reuse; privacy toggles after retention; correct delta signs/units; gap-aware graph paths; cursor bounds; theme changes; compact layout; keyboard/modal focus; helper lifecycle.

Commit after the planning baseline and after each working implementation milestone. Verify `git branch --show-current` before every commit/push; push only `feat/operator-mission-control` to `origin`, never force-push or merge. Run `make test`, source release validation, Omarchy validation and native lint. The native lifecycle runner and visual/input checks are separate evidence. Store generated logs/captures under `/tmp` or Documents, outside the watched plugin tree.

## Execution record

- Branch created from clean `main` at `d47f663`.
- Baseline: 105 Python tests and 59 JavaScript tests passed outside the initial restrictive sandbox, with one real-filesystem capability skip. The earlier sandbox socket failures were environment restrictions, not application regressions.
- Milestones 1–4 implemented and pushed in `d403fc2`, `1fcb20a` and `1e06ee4`: qualified attention, bounded session activity, pins, aggregate baseline/report, late-freeze handling, exact entity navigation and interactive usage/PSI trends.
- TDD refinement found and fixed native property-name collision, late-freeze history rewind, selected-control focus invisibility, actual ScrollView scrolling, live delegate focus loss, missing-import lint permissiveness, private alias mismatch, missing network instance scope, and keyboard-inaccessible provider status. New behavior tests were run failing before their implementations; complete regressions were rerun after correction.
- 2026-09-07 automated validation: 109 Python tests (one filesystem capability skip), 87 JavaScript tests, production Qt controller/surface interaction tests, source release checks, syntax, Omarchy manifest and native import lint pass. Portable Qt surface tests use isolated host-style/clipboard adapters, not the native shell.
- Native 1280×800 scale-1 private overlay: actual shell restart/summon, briefing, keyboard baseline capture, current-metric pin, 120-record activity, freeze/resume, usage-to-PSI switch, keyboard-held trend cursor, Space live return and Escape dismissal exercised. Private native captures are outside the watched tree under `/tmp/tactical-*-native-private.png`. Host logs show no plugin QML errors. Full lifecycle/soak, native bar pointer behavior, light/high-DPI/hotplug and complete visual matrix remain separate acceptance gates; they are not implied by these passes.

## Follow-on opportunities

### Shared native presentation: completed fix

- Reproduced four failing Qt assertions before implementation: all three width cases used the overlay's larger title, and the theme selected general instead of popup colors. Removed the alternate surface-style branches, retaining every native header value and the native panel's existing geometry. Fullscreen now uses the host's existing popup border component and native content insets. No routing or manifest changes.
- Full automated validation passed: 113 Python tests (one real-filesystem capability skip), 91 JavaScript tests, Qt component/controller tests, release/source checks, Omarchy manifest validation and native import lint. Header regressions cover 900/1260/1900 logical widths, native-small/larger font profiles, control order/right alignment, and live popup palette/font updates.
- Native 1280×800 scale-1 acceptance used the actual TD pointer-click route and IPC route with Machine Anatomy/privacy. Captures: `/tmp/tactical-shared-native-click-private.png`, `/tmp/tactical-shared-overlay-private.png`. Title/status, action rail and instrument rail image regions match after accounting for host translation (ImageMagick AE zero at 1% color tolerance). The native card began at x=5,y=31 on this effective host style; fullscreen began at x=0,y=0. Each retained the same ten-pixel border-plus-padding inset. The clicked briefing and fullscreen trend were also inspected. Test-induced privacy preference was restored; opened surfaces were closed. No system font, bar or monitor configuration changed.
- Native input automation used the standard wlr virtual-pointer protocol for a real compositor pointer click; the test client and generated protocol files remain outside the source tree in `/tmp/tactical-pointer-check.wAn1rl`. Hyprland's `send_shortcut` was not treated as reliable pointer-click evidence.
- The separate second ten-minute lifecycle attempt (`/tmp/tactical-operator-native-rerun.json`) again passed 50 cycles but lost the loaded plugin after 87 soak observations (~261 seconds). Pre-cleanup evidence showed its helper was gone while the same shell process remained alive. Neither attempt establishes the cause or a passed ten-minute soak. Allowlisted dismissal/host/destruction logging is now available to investigate that issue. Full native theme/high-DPI/hotplug and GPU frame-time matrices remain unverified.

Latest refinement verification: 111 Python tests (one filesystem capability skip), 91 JavaScript tests, native lint and source/manifest validation pass. Native large-type component coverage also caught and fixed briefing-title overlap; the title now wraps within its allotted width. The real PipeWire silent-stream integration passed (one stream, two links). Forty samples for each of five instruments measured p95 collection times of 42–54 ms and peak sampler RSS below 33 MiB on this host, while the native machine soak was active. These measurements do not establish GPU frame time.

The first native acceptance attempt completed all 50 open/close cycles, then failed after 126 soak observations (~379 seconds): the host returned `unknown` for plugin diagnostics beyond the runner's bounded retry. The shell process remained running and its logs contained no plugin error. The cause of the lost loaded instance is not established. This remains a failed ten-minute gate, not a successful soak. Evidence: `/tmp/tactical-operator-native.json`. A separate clean rerun is required; do not overwrite this failed-run record.

### Review-driven refinement tranche

Native review exposed routine process-state churn and centered timeline labels; source review also found PipeWire raw-kind/field-alias mismatch and independently stale mount capacity. Add tests before fixing these cases. Deliver an opened-plus-closed activity filter that preserves full retained history, allowlisted changed-field explanations without before/after identity values, left-aligned timeline rows, actual PipeWire media-class aliases, and independent capacity expiry. Give each paired trend a wrapping numeric legend and exercise both at 440-pixel width. Develop in an isolated source copy while the full native soak runs, then apply the reviewed patch to the feature branch and repeat full validation and native smoke checks. This changes no collection permissions or host actions.

After the milestones above are implemented and reviewed, continue with evidence-driven refinements: configurable attention thresholds, richer pressure/contributor correlation, saved investigation presets that contain no raw host identities, accessible graph summaries, aggregate session export, and profiling-guided renderer improvements. These extensions require their own failing behavior tests and measured UX justification. No process killing, firewall changes, package installation or automatic audio routing is part of this plan.
