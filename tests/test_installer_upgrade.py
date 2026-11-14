import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallerUpgradeTests(unittest.TestCase):
    def test_installer_preserves_existing_skill_before_replacing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "OpenCode Skills"
            old_skill = destination / "shortform-video-editor"
            old_skill.mkdir(parents=True)
            (old_skill / "legacy-user-file.txt").write_text("preserve me", encoding="utf-8")

            if os.name == "nt":
                shell = shutil.which("pwsh") or shutil.which("powershell")
                if not shell:
                    self.skipTest("PowerShell is unavailable")
                script = ROOT / "scripts" / "install.ps1"
                command = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(destination)]
            else:
                shell = shutil.which("bash")
                if not shell:
                    self.skipTest("Bash is unavailable")
                script = ROOT / "scripts" / "install.sh"
                command = [shell, str(script), str(destination)]

            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertTrue((destination / "shortform-video-editor" / "SKILL.md").is_file())
            self.assertTrue((destination / "shortform-video-editor" / "config" / "project-defaults.json").is_file())
            backups_root = destination / ".shortform-backups"
            backup_runs = [path for path in backups_root.iterdir() if path.is_dir()]
            self.assertTrue(backup_runs)
            preserved = backup_runs[-1] / "shortform-video-editor" / "legacy-user-file.txt"
            self.assertEqual(preserved.read_text(encoding="utf-8"), "preserve me")


if __name__ == "__main__":
    unittest.main()
