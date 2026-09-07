"""Preserve process evidence before native-runner cleanup can hide the cause."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class FailureEvidenceTests(unittest.TestCase):
    def test_native_acceptance_summons_private_without_changing_saved_preferences(self):
        spec = spec_from_file_location('native_private_acceptance', ROOT / 'scripts/live-validate.py')
        runner = module_from_spec(spec)
        spec.loader.exec_module(runner)
        with patch.object(runner, 'command', return_value='ok') as command:
            runner.summon_private('machine')
        command.assert_called_once()
        args = command.call_args.args
        self.assertEqual(args[:4], ('omarchy-shell', 'shell', 'summon', runner.PLUGIN))
        self.assertEqual(json.loads(args[4]), {'instrument': 'machine', 'privacy': True})

    def test_evidence_distinguishes_loaded_instance_loss_from_process_exit(self):
        spec = spec_from_file_location('native_failure_evidence', ROOT / 'scripts/live-validate.py')
        runner = module_from_spec(spec)
        spec.loader.exec_module(runner)
        report = {'cycles': [], 'soak': [{'helper': {'pid': 10}, 'shell': {'pid': 20}}]}
        with patch.object(runner, 'matching_helpers', return_value=[10]), \
                patch.object(runner, 'proc_stat', side_effect=lambda pid: {'pid': pid, 'startTicks': 1}):
            evidence = runner.failure_context(report)
        self.assertEqual(evidence['matchingHelpers'], [10])
        self.assertEqual(evidence['lastKnownHelperNow']['pid'], 10)
        self.assertEqual(evidence['lastKnownShellNow']['pid'], 20)
        with patch.object(runner, 'matching_helpers', return_value=[]), \
                patch.object(runner, 'proc_stat', return_value=None):
            self.assertIsNone(runner.failure_context(report)['lastKnownHelperNow'])

    def test_evidence_handles_startup_failure_without_a_known_process(self):
        spec = spec_from_file_location('native_startup_evidence', ROOT / 'scripts/live-validate.py')
        runner = module_from_spec(spec)
        spec.loader.exec_module(runner)
        with patch.object(runner, 'matching_helpers', return_value=[]):
            evidence = runner.failure_context({'cycles': [], 'soak': []})
        self.assertIsNone(evidence['lastKnownShellNow'])
        self.assertIsNone(evidence['lastKnownHelperNow'])
