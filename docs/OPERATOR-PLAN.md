# Tactical Display: operator mission control

Implementation branch: `feat/operator-mission-control`  
Reviewed baseline: `d47f663`  
Plan date: 2026-09-07  
Personal copy: `~/Documents/Tactical-Display/operator-mission-control.md`

## Product direction and review

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
6. [Qt Quick accessibility](https://doc.qt.io/qt-6/qtquick-accessibility.html) and [keyboard focus](https://doc.qt.io/qt-6/qtquick-input-focus.html): give controls names, conventional focus behavior and keyboard equivalents; preserve Escape as immediate dismissal and editor ownership of typing.

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
- Baseline sandbox run: 105 Python tests; three socket tests blocked by sandbox permissions, four environment skips. These were environment failures, not implementation regressions. The interrupted outside-sandbox run must be repeated to obtain a complete result.
- Planning/research complete; implementation not yet started.

## Follow-on opportunities

After the milestones above are implemented and reviewed, continue with evidence-driven refinements: configurable attention thresholds, richer pressure/contributor correlation, saved investigation presets that contain no raw host identities, accessible graph summaries, aggregate session export, and profiling-guided renderer improvements. These extensions require their own failing behavior tests and measured UX justification. No process killing, firewall changes, package installation or automatic audio routing is part of this plan.
