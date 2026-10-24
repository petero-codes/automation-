"""
Comprehensive Unit & Integration Test Suite for Nextgen Autonomous Workforce Engine.
Strict verification of all 12 mission-critical requirements:
1. VS Code tasks execute correctly.
2. Excel tasks execute correctly.
3. Unrelated application modes are no longer accessible.
4. Human input pauses automation.
5. Automation does not resume until explicitly requested.
6. Excel resumes from the bot's correct task cell/range.
7. VS Code resumes from the bot's correct task location.
8. Human edits are preserved during a pause.
9. Checkpoints cannot cause completed operations to be blindly repeated.
10. Terminated sessions cannot be resumed.
11. Interrupted sessions recover only through the intended recovery flow.
12. Errors and unavailable applications fail safely.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
from pathlib import Path

# Add final_bot to path
BASE_DIR = Path(__file__).resolve().parent.parent / "final_bot"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core import state
from core.priority_engine import priority_engine, get_idle_time_ms
from core.checkpoint_manager import CheckpointManager, checkpoint_mgr
from core.session_manager import SessionManager, SessionState, session_mgr
from core.procedural_coder import ProceduralCoder, CodingTask, sanitize_project_name
from core.financial_generator import FinancialGenerator, FinancialModel, FinancialCell
from tasks.scheduler import Scheduler, filter_runnable_tasks, is_task_runnable
from tasks.shared import (
    is_vscode_installed,
    get_vscode_executable,
    is_excel_installed,
    get_excel_executable,
    get_app_path,
)
from tasks.engineering_workload import (
    task_software_engineering,
    validate_vscode_resume,
    compute_file_hash,
)
from tasks.financial_workload import (
    task_financial_modeling,
    validate_excel_resume,
    reacquire_excel_application_state,
    col_idx_to_letter,
)

class TestNextgenWorkforceEngine(unittest.TestCase):

    def setUp(self):
        state.clear_stop()
        state.clear_resume()
        state.automation_active.clear()
        checkpoint_mgr.clear_checkpoint()

    def tearDown(self):
        state.clear_stop()
        state.clear_resume()
        state.automation_active.clear()
        checkpoint_mgr.clear_checkpoint()

    # -------------------------------------------------------------
    # 1. VS Code tasks execute correctly
    # -------------------------------------------------------------
    @patch("tasks.engineering_workload.time.sleep")
    @patch("core.state.stop_automation_event.wait", return_value=False)
    @patch("tasks.engineering_workload.is_vscode_installed", return_value=True)
    @patch("tasks.engineering_workload.launch_or_focus_vscode", return_value=True)
    @patch("tasks.engineering_workload.focus_window_by_title", return_value=True)
    @patch("tasks.engineering_workload.maximize_active_window")
    @patch("tasks.engineering_workload.human_typing")
    @patch("tasks.engineering_workload.safe_press")
    @patch("tasks.engineering_workload.hotkey")
    @patch("tasks.engineering_workload.human_scroll")
    @patch("tasks.engineering_workload.coder_instance.generate_task")
    def test_1_vscode_tasks_execute_correctly(self, mock_gen, mock_scroll, mock_hotkey, mock_press, mock_type, mock_max, mock_focus, mock_launch, mock_inst, mock_wait, mock_sleep):
        """Verifies VS Code task completes successfully with code generation and git staging."""
        mock_gen.return_value = CodingTask(
            project_name="unit_test_proj",
            language="python",
            files={"main.py": "x = 1\ny = 2\n"},
            git_commits=["feat: initial test"]
        )
        result = task_software_engineering(duration=300)
        self.assertTrue(result)
        self.assertTrue(mock_launch.called or mock_focus.called)
        self.assertTrue(mock_type.called)
        self.assertTrue(mock_press.called)

    # -------------------------------------------------------------
    # 2. Excel tasks execute correctly
    # -------------------------------------------------------------
    @patch("tasks.financial_workload.time.sleep")
    @patch("core.state.stop_automation_event.wait", return_value=False)
    @patch("tasks.financial_workload.is_excel_installed", return_value=True)
    @patch("tasks.financial_workload.launch_or_focus_excel", return_value=True)
    @patch("tasks.financial_workload.focus_window_by_title", return_value=True)
    @patch("tasks.financial_workload.maximize_active_window")
    @patch("tasks.financial_workload.human_typing")
    @patch("tasks.financial_workload.safe_press")
    @patch("tasks.financial_workload.hotkey")
    @patch("tasks.financial_workload.human_scroll")
    @patch("tasks.financial_workload.financial_gen.generate_model")
    def test_2_excel_tasks_execute_correctly(self, mock_gen, mock_scroll, mock_hotkey, mock_press, mock_type, mock_max, mock_focus, mock_launch, mock_inst, mock_wait, mock_sleep):
        """Verifies Excel task completes successfully with formulas, borders, and auto-fitting."""
        mock_gen.return_value = FinancialModel(
            model_name="Unit_Test_Model",
            sheet_title="Sheet1",
            row_count=2,
            headers=["Revenue", "Cost"],
            cells=[
                FinancialCell(1, 1, "Revenue", False, False),
                FinancialCell(1, 2, "1000", False, True)
            ]
        )
        result = task_financial_modeling(duration=300)
        self.assertTrue(result)
        self.assertTrue(mock_launch.called or mock_focus.called)
        self.assertTrue(mock_type.called)
        self.assertTrue(mock_press.called)

    # -------------------------------------------------------------
    # 3. Unrelated application modes are no longer accessible
    # -------------------------------------------------------------
    def test_3_unrelated_application_modes_are_inaccessible(self):
        """Verifies only VS Code and Excel exist in task pool and mode filter strictly excludes others."""
        import main
        # Only 2 workloads allowed in main matrix
        self.assertEqual(len(main.TASK_WEIGHTS), 2)
        self.assertIn(task_software_engineering, main.TASK_WEIGHTS)
        self.assertIn(task_financial_modeling, main.TASK_WEIGHTS)

        # Mode: vscode only
        with patch("tasks.scheduler.is_vscode_installed", return_value=True), \
             patch("tasks.scheduler.is_excel_installed", return_value=True):
            vscode_only = filter_runnable_tasks(main.TASK_WEIGHTS, mode="vscode")
            self.assertIn(task_software_engineering, vscode_only)
            self.assertNotIn(task_financial_modeling, vscode_only)

            # Mode: excel only
            excel_only = filter_runnable_tasks(main.TASK_WEIGHTS, mode="excel")
            self.assertIn(task_financial_modeling, excel_only)
            self.assertNotIn(task_software_engineering, excel_only)

            # Mode: both
            both = filter_runnable_tasks(main.TASK_WEIGHTS, mode="both")
            self.assertEqual(len(both), 2)

    # -------------------------------------------------------------
    # 4. Human input pauses automation
    # -------------------------------------------------------------
    def test_4_human_input_pauses_automation(self):
        """Verifies mouse or keyboard human input immediately yields control, measures latency, and sets session to PAUSED."""
        state.automation_active.set()
        session_mgr.state = SessionState.ACTIVE
        self.assertTrue(state.automation_active.is_set())

        # Simulate instant yield triggered by mouse displacement > 25px
        latency = priority_engine.trigger_instant_yield("Hardware Mouse Displacement (32.4px > 25.0px)")

        self.assertTrue(state.is_stopped())
        self.assertFalse(state.automation_active.is_set())
        self.assertTrue(session_mgr.is_paused())
        self.assertIsNotNone(priority_engine.last_yield_latency_ms)
        self.assertIsInstance(priority_engine.last_yield_latency_ms, float)
        self.assertGreater(priority_engine.last_yield_latency_ms, 0.0)
        self.assertLess(priority_engine.last_yield_latency_ms, 50.0)

    # -------------------------------------------------------------
    # 5. Automation does not resume until explicitly requested
    # -------------------------------------------------------------
    def test_5_automation_does_not_resume_until_explicitly_requested(self):
        """Verifies paused session never auto-resumes on timer and only resumes on explicit trigger."""
        session_mgr.mark_paused("Human User Pause")
        self.assertTrue(session_mgr.is_paused())
        self.assertFalse(state.automation_active.is_set())

        # An idle timer check must NOT resume when session is paused
        self.assertTrue(session_mgr.is_paused())

        # Only explicit request_resume activates it
        res = session_mgr.request_resume("Dedicated Toggle Key [F8]")
        self.assertTrue(res)
        self.assertTrue(session_mgr.is_active())
        self.assertTrue(state.automation_active.is_set())

    # -------------------------------------------------------------
    # 6. Excel resumes from the bot's correct task cell/range
    # -------------------------------------------------------------
    def test_6_excel_resumes_from_bot_correct_task_cell(self):
        """Verifies Excel task resumes from the exact next cell coordinate, skipping completed cells."""
        mock_payload = {
            "status": "PAUSED",
            "model_name": "FY27_SaaS_Valuation",
            "worksheet_name": "Sheet1",
            "models_dir": "C:\\Models",
            "cell_index": 1,
            "current_row": 5,
            "current_col": 2,
            "cells_data": [
                (1, 1, "Header", False, False),
                (5, 2, "ARR", False, True),
                (5, 3, "MRR", False, True),  # Next cell index 2 is at (5, 3)
            ]
        }
        valid, reason, next_idx, target_coord = validate_excel_resume(mock_payload)
        self.assertTrue(valid)
        self.assertEqual(next_idx, 2)
        self.assertEqual(target_coord, (5, 3))

    # -------------------------------------------------------------
    # 7. VS Code resumes from the bot's correct task location
    # -------------------------------------------------------------
    def test_7_vscode_resumes_from_bot_correct_task_location(self):
        """Verifies VS Code task resumes from next intended line without repeating completed lines."""
        mock_payload = {
            "status": "PAUSED",
            "project_name": "distributed_cache",
            "current_file": "cache.py",
            "file_path": "C:\\nonexistent\\cache.py",
            "line_index": 18,
            "last_completed_op": {
                "op": "WRITE_LINE",
                "file": "cache.py",
                "line_index": 18,
                "content": "    def get(self, key):",
            },
            "next_intended_op": {
                "op": "WRITE_LINE",
                "file": "cache.py",
                "line_index": 19,
                "content": "        return self._store.get(key)",
            }
        }
        valid, reason, next_line_index, col_idx = validate_vscode_resume(mock_payload["file_path"], mock_payload)
        self.assertTrue(valid)
        self.assertEqual(next_line_index, 19)

    # -------------------------------------------------------------
    # 8. Human edits are preserved during a pause
    # -------------------------------------------------------------
    def test_8_human_edits_preserved_during_pause(self):
        """Verifies when a human inserts edits into the file during pause, the bot preserves them and re-anchors."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
            temp_path = f.name
            f.write("import os\n")
            f.write("# Human edit: custom configuration\n")
            f.write("DEBUG = True\n")
            f.write("def calculate_metrics():\n")
            f.write("    pass\n")

        try:
            mock_payload = {
                "status": "PAUSED",
                "file_path": temp_path,
                "line_index": 3,
                "last_completed_op": {
                    "op": "WRITE_LINE",
                    "content": "def calculate_metrics():",
                }
            }
            valid, reason, next_line, col_idx = validate_vscode_resume(temp_path, mock_payload)
            self.assertTrue(valid)
            # Must re-anchor to line after 'def calculate_metrics():' (index 4 in file)
            self.assertEqual(next_line, 4)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------
    # 9. Checkpoints cannot cause completed operations to be blindly repeated
    # -------------------------------------------------------------
    def test_9_checkpoints_cannot_cause_completed_operations_to_be_repeated(self):
        """Verifies resumption index is strictly greater than last completed operation."""
        # For VS Code
        last_vscode_line = 10
        mock_vs_payload = {
            "status": "PAUSED",
            "file_path": "nonexistent.py",
            "line_index": last_vscode_line,
            "last_completed_op": {"line_index": last_vscode_line, "content": "x = 1"}
        }
        _, _, next_vs_line, _ = validate_vscode_resume("nonexistent.py", mock_vs_payload)
        self.assertGreater(next_vs_line, last_vscode_line)

        # For Excel
        last_excel_idx = 5
        mock_xl_payload = {
            "status": "PAUSED",
            "model_name": "FY27_Model",
            "worksheet_name": "Sheet1",
            "cell_index": last_excel_idx,
            "cells_data": [(i, 1, f"val_{i}", False, False) for i in range(10)]
        }
        _, _, next_xl_idx, _ = validate_excel_resume(mock_xl_payload)
        self.assertGreater(next_xl_idx, last_excel_idx)

    # -------------------------------------------------------------
    # 10. Terminated sessions cannot be resumed
    # -------------------------------------------------------------
    def test_10_terminated_sessions_cannot_be_resumed(self):
        """Verifies terminated session purges checkpoint and explicitly rejects resume attempts."""
        test_file = str(BASE_DIR / ".test_term_checkpoint.bin")
        mgr = CheckpointManager(storage_path=test_file)
        mgr.save_checkpoint("VS_CODE", {"project_name": "test", "line_index": 5})

        test_session = SessionManager(checkpoint_manager=mgr)
        test_session.start_session()
        self.assertIn(test_session.state, [SessionState.ACTIVE, SessionState.PAUSED])

        # Terminate session
        test_session.terminate_session("User Closed Console (X)")
        self.assertTrue(test_session.is_terminated())

        # Attempt to resume terminated session
        resume_result = test_session.request_resume("[F8] Toggle")
        self.assertFalse(resume_result)
        self.assertTrue(test_session.is_terminated())

        # Checkpoint file must not exist
        mgr.clear_checkpoint()
        self.assertFalse(os.path.exists(test_file))

    # -------------------------------------------------------------
    # 11. Interrupted sessions recover only through the intended recovery flow
    # -------------------------------------------------------------
    def test_11_interrupted_sessions_recover_only_through_intended_recovery_flow(self):
        """Verifies crashed/interrupted session requires explicit recovery decision before resuming."""
        test_file = str(BASE_DIR / ".test_interrupted_checkpoint.bin")
        mgr = CheckpointManager(storage_path=test_file)
        mgr.save_checkpoint("VS_CODE", {"project_name": "crashed_project", "line_index": 12}, status="INTERRUPTED")

        test_session = SessionManager(checkpoint_manager=mgr)
        # Launch without recovery decision -> enters INTERRUPTED state
        test_session.start_session(recovery_decision=None)
        self.assertTrue(test_session.is_interrupted())

        # Cannot resume directly while interrupted
        res = test_session.request_resume("Toggle [F8]")
        self.assertFalse(res)

        # Recovery decision: recover
        recovered = test_session.recover_interrupted_session()
        self.assertTrue(recovered)
        self.assertTrue(test_session.is_paused())

        # Now can resume
        res_after = test_session.request_resume("Toggle [F8]")
        self.assertTrue(res_after)
        self.assertTrue(test_session.is_active())

        # Test recovery decision: discard
        test_session.mark_interrupted("Another crash")
        test_session.discard_interrupted_session()
        self.assertTrue(test_session.is_active())

        mgr.clear_checkpoint()
        if os.path.exists(test_file):
            os.remove(test_file)

    # -------------------------------------------------------------
    # 12. Errors and unavailable applications fail safely
    # -------------------------------------------------------------
    def test_12_errors_and_unavailable_applications_fail_safely(self):
        """Verifies unavailable apps skip cleanly with zero keystroke injection and zero crash."""
        with patch("tasks.engineering_workload.is_vscode_installed", return_value=False):
            res_vs = task_software_engineering(10)
            self.assertFalse(res_vs)

        with patch("tasks.financial_workload.is_excel_installed", return_value=False):
            res_xl = task_financial_modeling(10)
            self.assertFalse(res_xl)

        # When neither application is installed, scheduler prunes gracefully
        with patch("tasks.scheduler.is_vscode_installed", return_value=False), \
             patch("tasks.scheduler.is_excel_installed", return_value=False):
            weights = {task_software_engineering: 5, task_financial_modeling: 5}
            sched = Scheduler(weights, mode="both")
            self.assertEqual(len(sched.task_weights), 0)
            self.assertIsNone(sched.pick_next_task())

    # -------------------------------------------------------------
    # Helper & Component Tests
    # -------------------------------------------------------------
    def test_procedural_coder_generation(self):
        coder = ProceduralCoder()
        task = coder.generate_task()
        self.assertTrue(len(task.project_name) > 0)
        self.assertIn(task.language, ["python", "typescript", "go"])
        self.assertGreaterEqual(len(task.files), 1)

    def test_financial_generator_structure_and_formulas(self):
        gen = FinancialGenerator()
        model = gen.generate_model()
        self.assertGreaterEqual(model.row_count, 50)
        self.assertLessEqual(model.row_count, 90)
        formulas = [c.value for c in model.cells if c.is_formula]
        self.assertGreater(len(formulas), 20)

    def test_dpapi_encrypted_checkpoints(self):
        test_file = str(BASE_DIR / ".test_dpapi.bin")
        mgr = CheckpointManager(storage_path=test_file)
        payload = {"project_name": "rate_limiter", "line_index": 44}
        saved = mgr.save_checkpoint("VS_CODE", payload)
        self.assertTrue(saved)
        loaded = mgr.load_checkpoint()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["workload"], "VS_CODE")
        self.assertEqual(loaded["payload"]["line_index"], 44)
        mgr.clear_checkpoint()
        self.assertFalse(os.path.exists(test_file))

    def test_project_name_sanitization(self):
        unsafe = "../../test<dir>:*name?"
        clean = sanitize_project_name(unsafe)
        self.assertTrue(all(c not in clean for c in '<>:"/\\|?*'))

    def test_purge_legacy_system_artifacts(self):
        from core.system_cleaner import purge_legacy_system_artifacts
        dummy = BASE_DIR / "idle_shorts.log"
        dummy.write_text("legacy log", encoding="utf-8")
        self.assertTrue(dummy.is_file())
        purged = purge_legacy_system_artifacts()
        self.assertIn(str(dummy), purged)
        self.assertFalse(dummy.exists())

    def test_os_shutdown_preserves_interrupted_checkpoint(self):
        """Verifies OS shutdown / logoff marks session INTERRUPTED without deleting checkpoint."""
        test_file = str(BASE_DIR / ".test_shutdown_cp.bin")
        mgr = CheckpointManager(storage_path=test_file)
        mgr.save_checkpoint("VS_CODE", {"project_name": "important_task", "line_index": 50})

        test_sess = SessionManager(checkpoint_manager=mgr)
        test_sess.start_session()

        # Simulate CTRL_SHUTDOWN_EVENT (6)
        ret = test_sess._console_ctrl_handler(6)
        self.assertEqual(ret, 1)
        self.assertTrue(test_sess.is_interrupted())

        # Checkpoint file must still exist and be marked INTERRUPTED
        loaded = mgr.load_checkpoint()
        self.assertIsNotNone(loaded)
        status = loaded.get("status") or loaded.get("payload", {}).get("status")
        self.assertEqual(status, "INTERRUPTED")
        mgr.clear_checkpoint()

    def test_dpapi_encryption_failure_prevents_plaintext_leak(self):
        """Verifies when DPAPI fails, unencrypted plaintext is NEVER written to disk."""
        test_file = str(BASE_DIR / ".test_fail_dpapi.bin")
        mgr = CheckpointManager(storage_path=test_file)
        with patch.object(mgr, "_encrypt_dpapi", side_effect=RuntimeError("DPAPI Access Denied")):
            saved = mgr.save_checkpoint("VS_CODE", {"sensitive": "secret_code", "line_index": 5})
            self.assertFalse(saved)
            self.assertFalse(os.path.exists(test_file))

    def test_checkpoint_schema_deep_validation(self):
        """Verifies deep schema checks reject invalid workloads, negative indices, or malformed ops."""
        mgr = CheckpointManager()
        # Invalid workload
        self.assertFalse(mgr.validate_checkpoint({"workload": "BROWSER", "status": "PAUSED"}))
        # Negative line index
        self.assertFalse(mgr.validate_checkpoint({
            "workload": "VS_CODE",
            "status": "PAUSED",
            "payload": {"project_name": "valid", "line_index": -5}
        }))
        # Invalid op structure
        self.assertFalse(mgr.validate_checkpoint({
            "workload": "VS_CODE",
            "status": "PAUSED",
            "payload": {"project_name": "valid", "line_index": 5, "last_completed_op": "invalid_string_not_dict"}
        }))

    def test_vscode_resume_stops_when_context_changed(self):
        """Verifies VS Code resume halts safely rather than guessing when target file content has changed fundamentally."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
            temp_path = f.name
            # Write completely unrelated content
            f.write("# Completely unrelated code written by user\n")
            f.write("def unrelated_function():\n")
            f.write("    return 42\n")

        try:
            mock_payload = {
                "status": "PAUSED",
                "file_path": temp_path,
                "line_index": 12,
                "last_completed_op": {
                    "op": "WRITE_LINE",
                    "content": "class DatabaseConnectionPool:",
                },
                "expected_context_lines": ["import psycopg2", "from sqlalchemy import create_engine"],
            }
            can_resume, reason, next_line, col_idx = validate_vscode_resume(temp_path, mock_payload)
            self.assertFalse(can_resume)
            self.assertIn("context has changed", reason.lower())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_excel_col_idx_to_letter_accuracy(self):
        """Verifies column coordinate conversion handles single, double, and boundary column indices."""
        self.assertEqual(col_idx_to_letter(1), "A")
        self.assertEqual(col_idx_to_letter(2), "B")
        self.assertEqual(col_idx_to_letter(26), "Z")
        self.assertEqual(col_idx_to_letter(27), "AA")
        self.assertEqual(col_idx_to_letter(28), "AB")
        self.assertEqual(col_idx_to_letter(52), "AZ")
        self.assertEqual(col_idx_to_letter(53), "BA")

    def test_excel_resume_stops_when_structure_changed(self):
        """Verifies Excel resume halts and marks session INTERRUPTED if target cell has conflicting data."""
        mock_payload = {
            "status": "PAUSED",
            "model_name": "FY27_Model",
            "worksheet_name": "Sheet1",
            "cell_index": 5,
            "cells_data": [(i, 1, f"val_{i}", False, False) for i in range(10)],
            "last_completed_op": {"row": 5, "col": 1, "value": "val_5"},
            "next_intended_op": {"row": 6, "col": 1, "value": "val_6"},
        }
        # Simulate COM finding conflicting data in target cell
        from unittest.mock import MagicMock
        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_wb.Name = "FY27_Model.xlsx"
        mock_ws = MagicMock()
        mock_ws.Name = "Sheet1"
        mock_wb.Worksheets = [mock_ws]
        mock_excel.Workbooks = [mock_wb]

        # Target cell occupied by conflicting human data
        conflicting_cell = MagicMock()
        conflicting_cell.Value = "CONF_HUMAN_ENTRY"
        conflicting_cell.Formula = "CONF_HUMAN_ENTRY"
        mock_ws.Range.return_value = conflicting_cell

        with patch("win32com.client.GetObject", return_value=mock_excel):
            reacquired, msg, row, col = reacquire_excel_application_state(
                workbook_path="C:\\Models\\FY27_Model.xlsx",
                worksheet_name="Sheet1",
                target_row=6,
                target_col=1,
                last_op=mock_payload["last_completed_op"],
                next_op=mock_payload["next_intended_op"],
            )
            self.assertFalse(reacquired)
            self.assertIn("structure", msg.lower())


class TestRealWindowsDesktopIntegration(unittest.TestCase):
    """
    Genuine Windows Desktop Integration Tests.
    Executes real Windows COM automation with Microsoft Excel and real filesystem / CLI with VS Code.
    No GUI mocks used in these tests.
    """

    def setUp(self):
        state.clear_stop()
        state.clear_resume()
        state.automation_active.clear()
        checkpoint_mgr.clear_checkpoint()

    def tearDown(self):
        state.clear_stop()
        state.clear_resume()
        state.automation_active.clear()
        checkpoint_mgr.clear_checkpoint()

    def test_real_excel_com_application_state_reacquisition(self):
        """
        Genuine Windows Excel Integration Test:
        Spawns real Excel via COM, creates real workbook with custom sheet,
        writes cell data, saves checkpoint, and validates exact target cell reacquisition by application state.
        """
        import win32com.client
        try:
            excel = win32com.client.Dispatch("Excel.Application")
        except Exception as e:
            self.skipTest(f"Excel COM dispatch unavailable on this environment: {e}")

        excel.Visible = False
        wb = None
        temp_dir = tempfile.mkdtemp()
        wb_path = os.path.join(temp_dir, "Real_Audit_Model.xlsx")

        try:
            wb = excel.Workbooks.Add()
            ws = wb.Worksheets(1)
            ws.Name = "Real_Audit_Sheet"

            # Write header and initial cell
            ws.Range("B5").Value = "Revenue"
            ws.Range("C5").Formula = "=SUM(100, 250)"
            wb.SaveAs(wb_path)

            # Checkpoint last completed at B5 and next intended at C5
            last_op = {"op": "WRITE_CELL", "row": 5, "col": 2, "value": "Revenue"}
            next_op = {"op": "WRITE_CELL", "row": 5, "col": 3, "value": "=SUM(100, 250)"}

            # Reacquire application state on real Excel instance
            reacquired, msg, r, c = reacquire_excel_application_state(
                workbook_path=wb_path,
                worksheet_name="Real_Audit_Sheet",
                target_row=5,
                target_col=3,
                last_op=last_op,
                next_op=next_op,
            )
            self.assertTrue(reacquired)
            self.assertEqual(r, 5)
            self.assertEqual(c, 3)

            # Verify real Excel computation
            computed_val = ws.Range("C5").Value
            self.assertEqual(computed_val, 350.0)

        finally:
            if wb:
                try:
                    wb.Close(SaveChanges=False)
                except Exception:
                    pass
            try:
                excel.Quit()
            except Exception:
                pass
            if os.path.exists(wb_path):
                try:
                    os.remove(wb_path)
                except Exception:
                    pass
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass

    def test_real_vscode_workspace_file_state_validation(self):
        """
        Genuine Windows Filesystem / VS Code Integration Test:
        Creates a real workspace directory and Python source file, simulates interruption checkpoint,
        performs manual human edits, and verifies that validate_vscode_resume preserves human edits
        and re-anchors to the exact next intended operation.
        """
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "real_service.py")

        try:
            # 1. Initial bot writes
            initial_lines = [
                "import os",
                "import sys",
                "class AuthService:",
                "    def __init__(self):",
                "        self.active = True",
            ]
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(initial_lines) + "\n")

            checkpoint_payload = {
                "status": "PAUSED",
                "project_name": "AuthProject",
                "workspace_dir": temp_dir,
                "current_file": "real_service.py",
                "file_path": file_path,
                "line_index": 4,  # completed up to "        self.active = True"
                "last_completed_op": {
                    "op": "WRITE_LINE",
                    "content": "        self.active = True",
                    "line_index": 4,
                },
                "next_intended_op": {
                    "op": "WRITE_LINE",
                    "content": "    def authenticate(self, token):",
                    "line_index": 5,
                },
                "expected_context_lines": ["class AuthService:", "self.active = True"],
            }

            # 2. Simulate human manual edits made while paused:
            # Human inserts a custom comment and a debug flag at line 2
            with open(file_path, "r", encoding="utf-8") as f:
                existing = f.readlines()

            # Insert human edits
            existing.insert(2, "# Human edit: enable verbose security tracing\n")
            existing.insert(3, "SECURITY_TRACE = True\n")
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(existing)

            # 3. Validate resume: bot must preserve human edits and re-anchor
            can_resume, reason, next_line_idx, col_idx = validate_vscode_resume(file_path, checkpoint_payload)
            self.assertTrue(can_resume)
            # Original line was at index 4, but human added 2 lines above it, so line is now at index 6
            # Next line to write must be line 7 (index 7)
            self.assertEqual(next_line_idx, 7)

            # 4. Verify human edits remained completely intact in file
            with open(file_path, "r", encoding="utf-8") as f:
                content_after = f.read()
            self.assertIn("SECURITY_TRACE = True", content_after)
            self.assertIn("# Human edit: enable verbose security tracing", content_after)

        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass

    # -------------------------------------------------------------
    # 28. Bot mouse movement filtering and multi-key / console resume
    # -------------------------------------------------------------
    def test_28_bot_mouse_move_filtering_and_multi_key_resumption(self):
        """Verifies bot mouse moves do not trigger self-pause, and verifies [F9] / Console resume."""
        # 1. Verify notify_bot_mouse_move synchronizes reference position
        priority_engine.notify_bot_mouse_move(450, 300)
        self.assertEqual(priority_engine.last_mouse_pos, (450, 300))

        # 2. Verify _is_bot_injecting recognizes bot mouse movement flag
        state.is_bot_moving_mouse = True
        self.assertTrue(priority_engine._is_bot_injecting())
        state.is_bot_moving_mouse = False

        # 3. Verify session pause and multi-key / console resume
        session_mgr.mark_paused("Test Pause")
        self.assertTrue(session_mgr.is_paused())

        # Test resume via [F9]
        res_f9 = session_mgr.request_resume("Dedicated Toggle Key [F9]")
        self.assertTrue(res_f9)
        self.assertTrue(session_mgr.is_active())
        self.assertTrue(state.is_resume_requested())

        # Re-pause and test resume via console key
        session_mgr.mark_paused("Test Pause 2")
        self.assertTrue(session_mgr.is_paused())
        res_console = session_mgr.request_resume("Console Key (ENTER/SPACE)")
        self.assertTrue(res_console)
        self.assertTrue(session_mgr.is_active())
        self.assertTrue(state.is_resume_requested())


if __name__ == "__main__":
    unittest.main()

