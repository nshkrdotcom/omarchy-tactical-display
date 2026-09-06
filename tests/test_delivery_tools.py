"""Security and observation semantics for actual delivery/operator paths."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from td_telemetry.audio import normalize_graph
from td_telemetry.storage import parse_mountinfo
ROOT=Path(__file__).resolve().parents[1]




class DeliveryTests(unittest.TestCase):


    def test_live_validation_tolerates_packaged_non_git_omarchy_path(self):
        path = ROOT / 'scripts/live-validate.py'
        spec = importlib.util.spec_from_file_location('tactical_live_validate', path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(
                module.omarchy_git_metadata(td),
                {'omarchyPath': td},
            )

    def test_live_validation_records_git_metadata_when_available(self):
        if not shutil.which('git'):
            self.skipTest('git unavailable')

        path = ROOT / 'scripts/live-validate.py'
        spec = importlib.util.spec_from_file_location('tactical_live_validate_git', path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                ['git', 'init', '-q', td],
                check=True,
                capture_output=True,
                text=True,
            )

            probe = Path(td) / 'probe'
            probe.write_text('real git metadata test\n')

            subprocess.run(
                ['git', '-C', td, 'add', 'probe'],
                check=True,
                capture_output=True,
                text=True,
            )

            subprocess.run(
                [
                    'git', '-C', td,
                    '-c', 'user.name=Tactical Display Tests',
                    '-c', 'user.email=tactical@example.invalid',
                    'commit', '-q', '-m', 'probe',
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            metadata = module.omarchy_git_metadata(td)

        self.assertEqual(metadata['omarchyPath'], td)
        self.assertTrue(metadata['omarchyCommit'])
        self.assertTrue(metadata['omarchyVersion'])

    def test_native_soak_retries_transient_diagnostic_rejections(self):
        text = (ROOT / 'scripts/live-validate.py').read_text()
        self.assertIn('def wait_soak_diagnostic(mode: str, timeout: float=1.0)', text)
        self.assertIn('d,retries=wait_soak_diagnostic(mode)', text)
        self.assertIn("'diagnosticRetries':retries", text)

    def test_native_soak_holds_one_instrument_and_checks_shell_growth(self):
        text = (ROOT / 'scripts/live-validate.py').read_text()
        self.assertIn("p.add_argument('--soak-seconds',type=int,default=600)", text)
        self.assertIn("report['soakStatus']='PASS' if a.soak_seconds>=600", text)
        self.assertIn("p.add_argument('--soak-instrument',choices=MODES,default='machine'", text)
        soak = text.split('        if a.soak_seconds:', 1)[1].split("        shell_samples=", 1)[0]
        self.assertIn('mode=a.soak_instrument', soak)
        self.assertIn("report['soakInstrument']=mode", soak)
        self.assertNotIn('last_switch', soak)
        self.assertNotIn('MODES[(MODES.index(mode)+1)%len(MODES)]', soak)
        self.assertIn("'observedSoakShellRssGrowthBytes'", text)
        self.assertIn('Shell RSS growth exceeded configured soak budget', text)

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
        binding_source=(ROOT/'scripts/print-bindings.sh').read_text()
        self.assertIn('release = true',binding_source)
        self.assertIn('ignore_mods = true',binding_source)

    def test_printed_bindings_match_current_hold_cli_and_do_not_mutate_user_bindings(self):
        script=ROOT/'scripts/print-bindings.sh'
        output=subprocess.run(['bash',str(script)],check=True,capture_output=True,text=True,timeout=5).stdout
        self.assertIn('omarchy menu keybindings --print',output)
        self.assertIn('/usr/bin/python3 -B',output)
        self.assertIn(' --token ',output)
        self.assertIn('release = true',output)
        self.assertIn('ignore_mods = true',output)
        self.assertIn('non_consuming = true',output)
        self.assertNotIn('hl.unbind(',output)