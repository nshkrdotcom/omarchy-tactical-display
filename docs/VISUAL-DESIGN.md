# Visual Design Law

## Product question

Connection Field exists to answer one question faster than `ss`, `lsof`, or a dashboard:

> **What programs on this machine are talking to what systems right now?**

If a visual element does not improve that answer, remove it.

## Spatial semantics

The field is not decorative radar.

- **center** - conceptual identity of this machine;
- **machine boundary** - separation between local ownership and outside peers;
- **process hubs inside boundary** - local socket owners;
- **remote diamonds near perimeter** - remote IP systems;
- **right side** - predominantly outbound remote relationships;
- **left side** - predominantly likely-inbound remote relationships;
- **top sector** - remotes participating meaningfully in both directions;
- **inner loopback point** - local host peer identity;
- **listener apertures on boundary** - local ports waiting/bound for work.

Position therefore answers *what side of the relationship is this?* and *what direction class does it belong to?*

## Link semantics

A line exists only because the backend observed one or more real sockets between that process and remote service.

- line direction tracer = outbound/inbound/local relationship direction;
- line thickness = socket multiplicity plus current kernel queue pressure;
- bright acquisition pulse = newly observed relationship;
- dashed/fading link = recently closed relationship;
- selection = unrelated topology dims, attached relationships stay bright.

**Tracer speed is not throughput.** Do not imply otherwise.

## Node semantics

### Local process

Filled circular hub. Size grows gently with active socket count. Label is process name; secondary text is socket count.

### Remote system

Hollow/low-fill diamond. Identity is remote IP. Secondary annotation may show locally-known service labels/ports derived without network lookup.

### Listener

Aperture glyph on the machine boundary aligned to its owning process. It is not rendered as a fake remote peer.

## Motion

Only four continuous/transient motions are justified:

1. directional tracers on active links;
2. acquisition pulse for new relationships;
3. fade-out for recently closed relationships;
4. live status pulse in the shell header.

No sweep line, spinning reactor ring, random particles, noise bursts, or animated ornament should return unless it gains a precise semantic.

## Chrome

The shell surface is intentionally restrained:

- theme background/accent/foreground/urgent colors;
- one top and bottom registration line;
- very faint scanlines;
- no card grid;
- no titlebar;
- no decorative corners framing empty space;
- no permanent settings panel.

The graph is the spectacle.

## Legibility gate

Before release, show a screenshot to someone who has not seen the docs. Within a few seconds they should be able to infer:

- the center represents their machine;
- named local programs own the inner nodes;
- IPs are remote systems;
- lines are connections;
- arrows/tracers indicate direction;
- clicking something probably inspects it.

If they instead say “cool HUD, what is it showing?”, the design has failed.
