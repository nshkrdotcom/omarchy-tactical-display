"""Bounded lifecycle diffs. Incomplete observations never prove disappearance."""
from __future__ import annotations
from collections import OrderedDict, deque
from copy import deepcopy
from typing import Any
from .common import stable_id


class EventStore:
    signature_fields = ('state', 'states', 'parentKey', 'sourceKey', 'targetKey', 'mute', 'default', 'socketCount', 'pressure')
    def __init__(self, ttl: float = 4.0, limit: int = 512, entity_limit: int = 24000) -> None:
        self.ttl = max(0.1, min(ttl, 30))
        self.limit = max(1, min(limit, 2048))
        self.entity_limit = entity_limit
        self.previous: dict[str, OrderedDict[str, dict[str, Any]]] = {}
        self.queue: deque[dict[str, Any]] = deque(maxlen=self.limit)
        self.ghosts: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.first_seen: OrderedDict[str, float] = OrderedDict()

    @staticmethod
    def signature(row: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(str(row.get(f, '')) for f in EventStore.signature_fields)

    def update(self, domain: str, rows: list[dict[str, Any]], now: float, complete: bool = True) -> None:
        old = self.previous.get(domain)
        current = OrderedDict((str(r['key']), dict(r)) for r in rows[:self.entity_limit] if 'key' in r)
        complete = complete and len(rows) <= self.entity_limit
        baseline = old is None
        for key, row in current.items():
            self.first_seen.setdefault(key, now)
            self.first_seen.move_to_end(key)
            self.ghosts.pop(key, None)
            changed_fields = [field for field, before, after in zip(self.signature_fields, self.signature(old[key]), self.signature(row)) if before != after] if old and key in old else []
            kind = 'opened' if old is not None and key not in old else 'changed' if changed_fields else None
            if kind:
                event = {'key': stable_id('event', domain, key, kind, now), 'entityKey': key, 'domain': domain, 'kind': kind, 'at': now, 'expiresAt': now + self.ttl}
                if changed_fields:
                    event['changedFields'] = changed_fields
                self.queue.append(event)
        if not baseline and complete:
            for key, row in old.items():
                if key not in current:
                    self.queue.append({'key': stable_id('event', domain, key, 'closed', now), 'entityKey': key, 'domain': domain, 'kind': 'closed', 'at': now, 'expiresAt': now + self.ttl})
                    self.ghosts[key] = {'domain': domain, 'row': row, 'closedAt': now, 'expiresAt': now + self.ttl}
        if old and not complete:
            # Keep unseen entities for a later complete comparison, but never indefinitely grow.
            merged = OrderedDict(old)
            merged.update(current)
            while len(merged) > self.entity_limit:
                merged.popitem(last=False)
            self.previous[domain] = merged
        else:
            self.previous[domain] = current
        self.expire(now)

    def expire(self, now: float) -> None:
        while self.queue and self.queue[0]['expiresAt'] <= now:
            self.queue.popleft()
        for key in list(self.ghosts):
            if self.ghosts[key]['expiresAt'] <= now:
                del self.ghosts[key]
        while len(self.ghosts) > 256:
            self.ghosts.popitem(last=False)
        while len(self.first_seen) > self.entity_limit * 2:
            self.first_seen.popitem(last=False)

    def events(self, now: float) -> list[dict[str, Any]]:
        self.expire(now)
        return list(self.queue)

    def decorate(self, domain: str, rows: list[dict[str, Any]], now: float, ghosts: bool = False) -> list[dict[str, Any]]:
        self.expire(now)
        recent = {e['entityKey']: e for e in self.queue if e['domain'] == domain}
        out = []
        for row in rows:
            r = dict(row)
            r['firstSeenMonotonic'] = self.first_seen.get(r['key'], now)
            r['ageMs'] = max(0, int((now - r['firstSeenMonotonic']) * 1000))
            event = recent.get(r['key'])
            r['event'] = event['kind'] if event else 'steady'
            r['eventAgeMs'] = max(0, int((now - event['at']) * 1000)) if event else None
            r['closed'] = False
            out.append(r)
        if ghosts:
            for key, ghost in self.ghosts.items():
                if ghost['domain'] == domain:
                    r = dict(ghost['row'])
                    r.update(event='closed', closed=True, active=False, closedAgeMs=int((now - ghost['closedAt']) * 1000))
                    out.append(r)
        return out

    def reset_domain(self, domain: str) -> None:
        self.previous.pop(domain, None)
        self.queue = deque((e for e in self.queue if e['domain'] != domain), maxlen=self.limit)
        self.ghosts = OrderedDict((k, g) for k, g in self.ghosts.items() if g['domain'] != domain)


class TrendWindow:
    """Only aggregate samples; no raw socket/process history."""
    def __init__(self, seconds: float = 60, limit: int = 120) -> None:
        self.seconds = min(60, seconds)
        self.rows: deque[dict[str, Any]] = deque(maxlen=limit)

    def add(self, now: float, values: dict[str, Any]) -> list[dict[str, Any]]:
        self.rows.append({'at': now, **values})
        while self.rows and now - self.rows[0]['at'] > self.seconds:
            self.rows.popleft()
        return list(self.rows)
