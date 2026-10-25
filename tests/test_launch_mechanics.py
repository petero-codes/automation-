import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "final_bot"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.window_manager import (
    is_vscode_window,
    is_excel_window,
    find_target_window,
)
from tasks.shared import (
    get_vscode_executable,
    get_excel_executable,
    launch_code_process,
    launch_excel_process,
    launch_or_focus_vscode,
    launch_or_focus_excel,
)

class TestLaunchMechanics(unittest.TestCase):
    def test_vscode_window_discriminator(self):
        """Ensures is_vscode_window only accepts genuine VS Code windows and rejects browsers/consoles."""
        # Genuine VS Code titles
        self.assertTrue(is_vscode_window("Visual Studio Code", "Chrome_WidgetWin_1"))
        self.assertTrue(is_vscode_window("main.py - my_project - Visual Studio Code", "Chrome_WidgetWin_1"))
        self.assertTrue(is_vscode_window("settings.py - Code", "Chrome_WidgetWin_1"))

        # False positives that previously broke the bot
        self.assertFalse(is_vscode_window("petero-codes/automation- - Google Chrome", "Chrome_WidgetWin_1"))
        self.assertFalse(is_vscode_window("C:\\Windows\\System32\\cmd.exe - python code.py", "ConsoleWindowClass"))
        self.assertFalse(is_vscode_window("D:\\projects\\loggy\\code - File Explorer", "CabinetWClass"))
        self.assertFalse(is_vscode_window("Save As", "#32770"))

    def test_excel_window_discriminator(self):
        """Ensures is_excel_window only accepts genuine Excel windows and rejects explorer/browser false matches."""
        # Genuine Excel windows
        self.assertTrue(is_excel_window("Book1 - Excel", "XLMAIN"))
        self.assertTrue(is_excel_window("Corporate_PnL.xlsx - Excel", "XLMAIN"))
        self.assertTrue(is_excel_window("Excel", "XLMAIN"))

        # False positives that previously broke the bot
        self.assertFalse(is_excel_window("D:\\projects\\loggy\\excel.ico - File Explorer", "CabinetWClass"))
        self.assertFalse(is_excel_window("excel tutorial - Brave", "Chrome_WidgetWin_1"))

    def test_executable_detection(self):
        """Verifies that VS Code and Excel executables are located on the host machine."""
        code_exe = get_vscode_executable()
        self.assertIsNotNone(code_exe, "VS Code executable must be found on this machine.")
        self.assertTrue(os.path.isfile(code_exe), f"VS Code file must exist: {code_exe}")

        excel_exe = get_excel_executable()
        self.assertIsNotNone(excel_exe, "Excel executable must be found on this machine.")
        self.assertTrue(os.path.isfile(excel_exe), f"Excel file must exist: {excel_exe}")

    @patch("tasks.shared.launch_code_process")
    @patch("tasks.shared.focus_window_by_title")
    @patch("tasks.shared.wait_for_window")
    @patch("tasks.shared.maximize_active_window")
    def test_launch_or_focus_vscode_flow(self, mock_max, mock_wait, mock_focus, mock_launch):
        """Verifies that launch_or_focus_vscode spawns process directly when window is not present."""
        mock_focus.return_value = False
        mock_wait.return_value = True

        res = launch_or_focus_vscode("C:\\TestWorkspace", file_path=None)
        self.assertTrue(res)
        self.assertTrue(mock_launch.called, "Must invoke launch_code_process directly, zero Start menu typing.")

    @patch("tasks.shared.launch_excel_process")
    @patch("tasks.shared.focus_window_by_title")
    @patch("tasks.shared.wait_for_window")
    @patch("tasks.shared.maximize_active_window")
    def test_launch_or_focus_excel_flow(self, mock_max, mock_wait, mock_focus, mock_launch):
        """Verifies that launch_or_focus_excel launches without start menu typing."""
        mock_focus.return_value = False
        mock_wait.return_value = True

        res = launch_or_focus_excel(workbook_path=None)
        self.assertTrue(res)
        mock_max.assert_called()

    @patch("core.window_manager.restore_console_window")
    def test_console_window_does_not_pop_up_on_pause(self, mock_restore):
        """Ensures console window is NOT restored or brought forward when human control is yielded."""
        from core.session_manager import session_mgr
        session_mgr.mark_paused("Hardware Mouse Displacement (65px > 60px)")
        self.assertTrue(session_mgr.is_paused())
        mock_restore.assert_not_called()

    def test_persona_matrix_and_checkpoint_preservation(self):
        """Ensures developer personas match Nimrod specs and preserve across checkpoints."""
        from tasks.engineering_workload import DEVELOPER_PERSONAS, get_session_developer_persona, save_vscode_checkpoint
        from core.checkpoint_manager import checkpoint_mgr
        from core.procedural_coder import CodingTask

        # Assert persona matrix
        persona_names = {p["name"] for p in DEVELOPER_PERSONAS}
        self.assertIn("Burst Engineer", persona_names)
        self.assertIn("Methodical Architect", persona_names)
        self.assertIn("Pragmatic Developer", persona_names)

        persona = get_session_developer_persona()
        self.assertIn(persona["name"], persona_names)

        # Test checkpoint preservation
        task = CodingTask(project_name="test_proj", language="python", files={"main.py": "print('hi')\n"}, git_commits=["init"])
        save_vscode_checkpoint(task, "C:\\test", "main.py", 0, ["print('hi')\n"], col_idx=5, persona=persona)
        cp = checkpoint_mgr.load_checkpoint()
        self.assertIsNotNone(cp)
        payload = cp.get("payload", {})
        self.assertEqual(payload.get("persona", {}).get("name"), persona["name"])
        checkpoint_mgr.clear_checkpoint()

    def test_idle_timeout_is_two_minutes(self):
        """Ensures idle timeout is strictly configured to 120 seconds (2 minutes)."""
        from config.settings import IDLE_TIMEOUT
        self.assertEqual(IDLE_TIMEOUT, 120, "IDLE_TIMEOUT must be strictly 120s (2 minutes).")

if __name__ == "__main__":
    unittest.main()
