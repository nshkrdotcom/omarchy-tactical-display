"""Event explanations add only changed field names, never raw identity values."""
import unittest
from td_telemetry.events import EventStore


class EventExplanationTests(unittest.TestCase):
    def test_changed_fields_are_bounded_and_identity_free(self):
        events = EventStore()
        events.update('process', [{'key': 'p', 'state': 'S', 'parentKey': 'secret-parent', 'socketCount': 1}], 1)
        events.update('process', [{'key': 'p', 'state': 'R', 'parentKey': 'private-parent', 'socketCount': 2}], 2)
        changed = events.events(2)[0]
        self.assertEqual(changed['changedFields'], ['state', 'parentKey', 'socketCount'])
        self.assertNotIn('secret-parent', str(changed))
        self.assertNotIn('private-parent', str(changed))
        events.update('process', [], 3, complete=False)
        self.assertEqual(len(events.events(3)), 1)

    def test_unchanged_measurements_do_not_emit_change_explanations(self):
        events = EventStore()
        events.update('process', [{'key': 'p', 'state': 'S', 'cpuPercent': 1}], 1)
        events.update('process', [{'key': 'p', 'state': 'S', 'cpuPercent': 50}], 2)
        self.assertEqual(events.events(2), [])
        events.update('process', [], 3)
        self.assertEqual(events.events(3)[0].get('changedFields', []), [])
