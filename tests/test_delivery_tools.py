"""Security and observation semantics for actual delivery/operator paths."""
from pathlib import Path
import unittest

from td_telemetry.audio import normalize_graph
from td_telemetry.storage import parse_mountinfo
ROOT=Path(__file__).resolve().parents[1]




class DeliveryTests(unittest.TestCase):


    def test_audio_pid_inherits_client_instance_identity(self):
        raw=[{'id':10,'type':'PipeWire:Interface:Client','info':{'props':{'application.process.id':'42','object.serial':100}}},
             {'id':11,'type':'PipeWire:Interface:Node','info':{'props':{'client.id':10,'media.class':'Stream/Output/Audio','object.serial':101}}}]
        graph=normalize_graph(raw,{42:{'key':'process:42:900','groupKey':'app:unit'}},'cookie')
        node=graph['nodes'][0]
        self.assertEqual(node['pid'],42);self.assertEqual(node['processKey'],'process:42:900')
        self.assertIn('client-reported',node['ownershipProvenance'])

    def test_mount_control_characters_never_probe_a_different_cleaned_path(self):
        rows=parse_mountinfo('24 1 8:1 / /private\\012name rw - ext4 /dev/sda1 rw\n25 1 8:2 / /home rw - ext4 /dev/sda2 rw\n')
        self.assertFalse(rows[0]['capacitySafePath']);self.assertTrue(rows[1]['capacitySafePath'])

    def test_operator_tools_do_not_offer_fixture_live_substitutes(self):
        text=(ROOT/'scripts/live-validate.py').read_text()
        self.assertIn('WAYLAND_DISPLAY',text);self.assertIn('return 77',text)
        self.assertIn('diagnostics',text);self.assertIn('matching_helpers()',text)
        for term in ('--max-helper-cpu-percent','--max-helper-children','--max-ready-ms','helperCpuPercentOneCore','childCount'):
            self.assertIn(term,text)
        self.assertNotIn('fixtures/scenarios',text)
        self.assertIn('release = true',(ROOT/'scripts/print-bindings.sh').read_text())
        self.assertIn('ignore_mods = true',(ROOT/'scripts/print-bindings.sh').read_text())