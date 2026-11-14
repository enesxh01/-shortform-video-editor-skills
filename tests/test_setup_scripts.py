import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SetupScriptTests(unittest.TestCase):
    def test_unix_setup_installs_extras_skills_and_runs_doctor(self):
        script = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
        self.assertIn('pip install -e "${ROOT}[audio,visual,download]"', script)
        self.assertIn('bash "$ROOT/scripts/install.sh" "$DEST"', script)
        self.assertIn('shortform_editor.cli doctor', script)
        self.assertIn("ffmpeg", script)
        self.assertIn("ffprobe", script)
        self.assertIn("3.10", script)
        bash = shutil.which("bash")
        if bash:
            subprocess.run([bash, "-n", str(ROOT / "scripts" / "setup.sh")], check=True)
            subprocess.run([bash, "-n", str(ROOT / "scripts" / "install.sh")], check=True)

    def test_windows_setup_installs_extras_skills_and_runs_doctor(self):
        script = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")
        self.assertIn('"${Root}[audio,visual,download]"', script)
        self.assertIn('install.ps1', script)
        self.assertIn('shortform_editor.cli doctor', script)
        self.assertIn('Get-Command ffmpeg', script)
        self.assertIn('Get-Command ffprobe', script)
        self.assertIn('[version]"3.10"', script)
        self.assertLess(script.index('$PythonCommand = $null'), script.index('$PythonCandidates = @()'))
        self.assertIn('Executable = "python"', script)
        self.assertIn('Executable = "py"', script)
        self.assertIn('if ($ParsedVersion -ge [version]"3.10")', script)


if __name__ == "__main__":
    unittest.main()
