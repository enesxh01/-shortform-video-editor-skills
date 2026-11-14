import unittest
from unittest.mock import patch

from shortform_editor.cli import PipelineError, run_checked


class FakeProcess:
    def __init__(self, *args, **kwargs):
        self.returncode = -15
        self.terminated = False
        self.calls = 0

    def communicate(self):
        self.calls += 1
        if self.calls == 1:
            raise KeyboardInterrupt()
        return "", ""

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class SubprocessCancellationTests(unittest.TestCase):
    def test_keyboard_interrupt_terminates_child_process(self):
        with patch("shortform_editor.cli.subprocess.Popen", FakeProcess) as popen:
            with self.assertRaises(KeyboardInterrupt):
                run_checked(["long-running-command"])
            self.assertTrue(popen.return_value.terminated)

    def test_nonzero_child_exit_becomes_pipeline_error(self):
        class FailedProcess:
            returncode = 2
            def __init__(self, *args, **kwargs):
                pass
            def communicate(self):
                return "", "synthetic failure"

        with patch("shortform_editor.cli.subprocess.Popen", FailedProcess):
            with self.assertRaisesRegex(PipelineError, "synthetic failure"):
                run_checked(["bad-command"])


if __name__ == "__main__":
    unittest.main()
