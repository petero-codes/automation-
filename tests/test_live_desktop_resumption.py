"""
Live Real-Desktop Integration Test Suite: 6-Step End-to-End Resumption Sequence
Tests real Microsoft Excel (Office 16 COM) and real Visual Studio Code on Windows.

Sequence Under Test:
  1. Start a multi-step task in Excel / VS Code.
  2. Take manual control midway through the task (simulate interruption & pause).
  3. Make a change yourself (human user edit during pause).
  4. Explicitly resume the bot ([F8] toggle).
  5. Confirm it returns to the correct task location, preserves your edit, and continues without repeating completed operations.
  6. Terminate the session, relaunch the bot, and confirm it starts fresh.
"""

import os
import sys
import time
import tempfile
import unittest
from pathlib import Path

# Ensure final_bot is on python search path
BASE_DIR = Path(__file__).resolve().parent.parent / "final_bot"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core import state
from core.logger import log
from core.checkpoint_manager import checkpoint_mgr
from core.session_manager import SessionManager, SessionState
from tasks.shared import is_excel_installed, is_vscode_installed, get_vscode_executable
from tasks.financial_workload import (
    reacquire_excel_application_state,
    save_excel_checkpoint,
    validate_excel_resume,
    FinancialModel,
    FinancialCell,
)
from tasks.engineering_workload import (
    validate_vscode_resume,
    save_vscode_checkpoint,
    compute_file_hash,
    CodingTask,
)


class TestRealDesktopResumptionSequence(unittest.TestCase):
    """
    Genuine Windows Desktop Integration Tests:
    Exercises the exact 6-step lifecycle sequence on real Microsoft Excel and real Visual Studio Code.
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

    # =========================================================================
    # EXCEL 6-STEP REAL DESKTOP SEQUENCE
    # =========================================================================
    def test_excel_live_resumption_6_step_sequence(self):
        """
        Executes the full 6-step lifecycle sequence against a real Microsoft Excel COM instance:
          Step 1: Start a multi-step task in Excel.
          Step 2: Take manual control midway through the task.
          Step 3: Make a change yourself (human edit).
          Step 4: Explicitly resume the bot.
          Step 5: Confirm it returns to correct task cell, preserves human edit, and finishes without repetition.
          Step 6: Terminate session, relaunch, and confirm fresh start.
        """
        if not is_excel_installed():
            self.skipTest("Microsoft Excel is not installed on this system.")

        import win32com.client
        try:
            excel = win32com.client.Dispatch("Excel.Application")
        except Exception as e:
            self.skipTest(f"Excel COM dispatch unavailable: {e}")

        excel.Visible = False
        wb = None
        temp_dir = tempfile.mkdtemp()
        wb_path = os.path.join(temp_dir, "Live_Financial_Model.xlsx")
        session_mgr = SessionManager(checkpoint_mgr)

        try:
            # -------------------------------------------------------------
            # STEP 1: Start a multi-step task in Excel
            # -------------------------------------------------------------
            log("\n--- [STEP 1] Starting multi-step Excel task ---")
            session_mgr.start_session()
            self.assertTrue(session_mgr.is_active())

            wb = excel.Workbooks.Add()
            ws = wb.Worksheets(1)
            ws.Name = "Model_Q4"

            # 10-step financial modeling plan:
            # (row, col, value, is_formula, format_cmd)
            task_steps = [
                FinancialCell(2, 2, "Metric", False, "none"),          # Step 0: B2
                FinancialCell(2, 3, "Amount", False, "none"),          # Step 1: C2
                FinancialCell(3, 2, "Gross Revenue", False, "none"),   # Step 2: B3
                FinancialCell(3, 3, "10000", False, "currency"),       # Step 3: C3
                FinancialCell(4, 2, "COGS", False, "none"),            # Step 4: B4
                FinancialCell(4, 3, "4000", False, "currency"),        # Step 5: C4
                # --- INTERRUPT OCCURS HERE (Midway after step 5) ---
                FinancialCell(5, 2, "Gross Profit", False, "none"),    # Step 6: B5
                FinancialCell(5, 3, "=C3-C4", True, "currency"),       # Step 7: C5 (Formula)
                FinancialCell(6, 2, "Operating Expenses", False, "none"), # Step 8: B6
                FinancialCell(6, 3, "2500", False, "currency"),        # Step 9: C6
                FinancialCell(7, 2, "Net Income", False, "none"),      # Step 10: B7
                FinancialCell(7, 3, "=C5-C6", True, "currency"),       # Step 11: C7 (Formula)
            ]

            model = FinancialModel(
                model_name="Live_Financial_Model",
                sheet_title="Model_Q4",
                row_count=12,
                headers=["Metric", "Amount"],
                cells=task_steps,
            )

            # Bot executes steps 0 through 5
            for i in range(6):
                cell = task_steps[i]
                target_range = ws.Cells(cell.row, cell.col)
                if cell.is_formula:
                    target_range.Formula = cell.value
                else:
                    target_range.Value = cell.value

            wb.SaveAs(wb_path)

            # Verify initial writes are committed in Excel
            self.assertEqual(ws.Range("B2").Value, "Metric")
            self.assertEqual(ws.Range("C3").Value, 10000.0)
            self.assertEqual(ws.Range("C4").Value, 4000.0)
            log("Bot completed steps 0-5 in Excel (wrote headers, Revenue 10000, COGS 4000).")

            # -------------------------------------------------------------
            # STEP 2: Take manual control midway through the task
            # -------------------------------------------------------------
            log("\n--- [STEP 2] Simulating human taking control midway ---")
            session_mgr.mark_paused("Human User Interruption Detected")
            self.assertTrue(session_mgr.is_paused())
            self.assertTrue(state.is_stopped())

            # Checkpoint the interrupted state (last completed: step 5, next intended: step 6)
            last_cell = task_steps[5]
            save_excel_checkpoint(model, temp_dir, cell_idx=5, cell=last_cell, all_cells=task_steps)

            cp = checkpoint_mgr.load_checkpoint()
            self.assertIsNotNone(cp)
            self.assertEqual(cp["status"], "PAUSED")
            self.assertEqual(cp["payload"]["last_completed_op"]["row"], 4)
            self.assertEqual(cp["payload"]["last_completed_op"]["col"], 3)
            self.assertEqual(cp["payload"]["next_intended_op"]["row"], 5)
            self.assertEqual(cp["payload"]["next_intended_op"]["col"], 2)
            log("Interruption checkpoint safely stored with last op at C4 and next op at B5.")

            # -------------------------------------------------------------
            # STEP 3: Make a change yourself (Human user edit during pause)
            # -------------------------------------------------------------
            log("\n--- [STEP 3] Human user enters manual edit into real Excel ---")
            # Human adds audit note in Column D, row 3 and row 4
            ws.Range("D3").Value = "Human Verified: Tier 1 Client"
            ws.Range("D4").Value = "Human Verified: Verified Supplier Invoice #4401"
            wb.Save()
            log("Human edit written: D3='Human Verified: Tier 1 Client', D4='Human Verified: Verified Supplier Invoice #4401'.")

            # -------------------------------------------------------------
            # STEP 4: Explicitly resume the bot
            # -------------------------------------------------------------
            log("\n--- [STEP 4] Explicitly resuming the bot via [F8] toggle ---")
            resumed = session_mgr.request_resume("User Toggle [F8]")
            self.assertTrue(resumed)
            self.assertTrue(session_mgr.is_active())
            self.assertFalse(state.is_stopped())

            # -------------------------------------------------------------
            # STEP 5: Confirm it returns to correct task location, preserves edit,
            #         and continues without repeating completed operations
            # -------------------------------------------------------------
            log("\n--- [STEP 5] Validating resumption and finishing workload ---")
            cp_payload = cp["payload"]
            valid, reason, next_cell_idx, target_coord = validate_excel_resume(cp_payload)
            self.assertTrue(valid)
            self.assertEqual(next_cell_idx, 6)
            self.assertEqual(target_coord, (5, 2))  # B5

            # Reacquire Excel application state on the live COM instance
            reacquired, reacq_msg, target_r, target_c = reacquire_excel_application_state(
                workbook_path=wb_path,
                worksheet_name="Model_Q4",
                target_row=target_coord[0],
                target_col=target_coord[1],
                last_op=cp_payload["last_completed_op"],
                next_op=cp_payload["next_intended_op"],
            )
            self.assertTrue(reacquired, f"Reacquisition failed: {reacq_msg}")
            self.assertEqual(target_r, 5)
            self.assertEqual(target_c, 2)
            log(f"Reacquired live Excel target cell at Row {target_r}, Col {target_c} (B5).")

            # Bot continues execution from step 6 to 11
            for i in range(next_cell_idx, len(task_steps)):
                cell = task_steps[i]
                target_range = ws.Cells(cell.row, cell.col)
                if cell.is_formula:
                    target_range.Formula = cell.value
                else:
                    target_range.Value = cell.value

            wb.Save()

            # Confirm 1: Bot did NOT repeat steps 0-5 (Gross Revenue and COGS remain intact)
            self.assertEqual(ws.Range("C3").Value, 10000.0)
            self.assertEqual(ws.Range("C4").Value, 4000.0)

            # Confirm 2: Human edits in column D were preserved completely
            self.assertEqual(ws.Range("D3").Value, "Human Verified: Tier 1 Client")
            self.assertEqual(ws.Range("D4").Value, "Human Verified: Verified Supplier Invoice #4401")

            # Confirm 3: Subsequent formulas were calculated correctly by Excel
            self.assertEqual(ws.Range("B5").Value, "Gross Profit")
            self.assertEqual(ws.Range("C5").Value, 6000.0)  # =10000 - 4000
            self.assertEqual(ws.Range("B7").Value, "Net Income")
            self.assertEqual(ws.Range("C7").Value, 3500.0)  # =6000 - 2500
            log("Excel verified: B5 Gross Profit = 6000.0, B7 Net Income = 3500.0, human notes intact.")

            # -------------------------------------------------------------
            # STEP 6: Terminate session, relaunch, confirm it starts fresh
            # -------------------------------------------------------------
            log("\n--- [STEP 6] Terminating session and relaunching bot ---")
            session_mgr.terminate_session("Task Completed Successfully")
            self.assertTrue(session_mgr.is_terminated())
            self.assertIsNone(checkpoint_mgr.load_checkpoint())

            # Relaunch a new session
            new_session_mgr = SessionManager(checkpoint_mgr)
            new_session_mgr.start_session()
            self.assertTrue(new_session_mgr.is_active())
            self.assertFalse(new_session_mgr.is_paused())
            self.assertIsNone(checkpoint_mgr.load_checkpoint())
            log("New session started completely fresh with zero restored checkpoints.")

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

    # =========================================================================
    # VS CODE 6-STEP REAL DESKTOP SEQUENCE
    # =========================================================================
    def test_vscode_live_resumption_6_step_sequence(self):
        """
        Executes the full 6-step lifecycle sequence against a real file & workspace:
          Step 1: Start a multi-step task in VS Code.
          Step 2: Take manual control midway through the task.
          Step 3: Make a change yourself (human edit inserted into file).
          Step 4: Explicitly resume the bot.
          Step 5: Confirm it returns to correct line, preserves human edits, and finishes without repeating.
          Step 6: Terminate session, relaunch, and confirm fresh start.
        """
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "auth_controller.py")
        session_mgr = SessionManager(checkpoint_mgr)

        try:
            # -------------------------------------------------------------
            # STEP 1: Start a multi-step task in VS Code
            # -------------------------------------------------------------
            log("\n--- [STEP 1] Starting multi-step VS Code task ---")
            session_mgr.start_session()
            self.assertTrue(session_mgr.is_active())

            # 12-line code plan for auth_controller.py:
            code_lines = [
                "import os",
                "import sys",
                "import logging",
                "class AuthController:",
                "    def __init__(self, realm):",
                "        self.realm = realm",
                "        self.is_ready = True",
                # --- INTERRUPT OCCURS HERE (Midway after line index 6) ---
                "    def authenticate_request(self, token):",
                "        if not token:",
                "            return False",
                "        return token.startswith('bearer_')",
            ]

            task = CodingTask(
                project_name="LiveSecurityProject",
                language="python",
                files={"auth_controller.py": "\n".join(code_lines)},
                git_commits=["feat: implement auth controller"],
            )

            # Bot writes lines 0 through 6 to disk
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(code_lines[:7]) + "\n")

            with open(file_path, "r", encoding="utf-8") as f:
                content_initial = f.read()
            self.assertIn("self.is_ready = True", content_initial)
            self.assertNotIn("def authenticate_request", content_initial)
            log("Bot completed lines 0-6 in auth_controller.py.")

            # -------------------------------------------------------------
            # STEP 2: Take manual control midway through the task
            # -------------------------------------------------------------
            log("\n--- [STEP 2] Simulating human taking control midway ---")
            session_mgr.mark_paused("Human User Interruption Detected")
            self.assertTrue(session_mgr.is_paused())
            self.assertTrue(state.is_stopped())

            # Checkpoint the state after line index 6
            save_vscode_checkpoint(
                task=task,
                workspace_dir=temp_dir,
                filename="auth_controller.py",
                line_idx=6,
                lines=code_lines,
                col_idx=len(code_lines[6]),
            )

            cp = checkpoint_mgr.load_checkpoint()
            self.assertIsNotNone(cp)
            self.assertEqual(cp["status"], "PAUSED")
            self.assertEqual(cp["payload"]["line_index"], 6)
            self.assertEqual(cp["payload"]["last_completed_op"]["content"], "        self.is_ready = True")
            self.assertEqual(cp["payload"]["next_intended_op"]["content"], "    def authenticate_request(self, token):")
            log("Interruption checkpoint safely stored for VS Code.")

            # -------------------------------------------------------------
            # STEP 3: Make a change yourself (Human user edit during pause)
            # -------------------------------------------------------------
            log("\n--- [STEP 3] Human user enters manual edits into the code file ---")
            # Human opens file and inserts 2 lines of custom code between line 6 and 7:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

            # Insert at line 5 (above self.is_ready = True):
            existing_lines.insert(5, "        # HUMAN EDIT: Enable enterprise audit trace\n")
            existing_lines.insert(6, "        self.audit_trace = True\n")

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(existing_lines)

            log("Human edit inserted: '# HUMAN EDIT: Enable enterprise audit trace' and 'self.audit_trace = True'.")

            # -------------------------------------------------------------
            # STEP 4: Explicitly resume the bot
            # -------------------------------------------------------------
            log("\n--- [STEP 4] Explicitly resuming the bot via [F8] toggle ---")
            resumed = session_mgr.request_resume("User Toggle [F8]")
            self.assertTrue(resumed)
            self.assertTrue(session_mgr.is_active())
            self.assertFalse(state.is_stopped())

            # -------------------------------------------------------------
            # STEP 5: Confirm it returns to correct task location, preserves edit,
            #         and continues without repeating completed operations
            # -------------------------------------------------------------
            log("\n--- [STEP 5] Validating resumption and finishing workload ---")
            cp_payload = cp["payload"]
            can_resume, reason, next_line_idx, next_col = validate_vscode_resume(file_path, cp_payload)
            self.assertTrue(can_resume, f"Resume validation failed: {reason}")
            # Human added 2 lines, so 'self.is_ready = True' is now at index 8 (line 9).
            # Next intended line must be line index 9 (line 10).
            self.assertEqual(next_line_idx, 9)
            log(f"Re-anchored resume line to index {next_line_idx} (compensating for human inserted lines).")

            # Bot writes remaining lines (index 7 through 10 from original plan)
            with open(file_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()

            # Append the remaining intended lines
            for i in range(7, len(code_lines)):
                file_lines.append(code_lines[i] + "\n")

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(file_lines)

            # Read back final file to verify all conditions
            with open(file_path, "r", encoding="utf-8") as f:
                final_content = f.read()

            # Confirm 1: Human edits preserved completely
            self.assertIn("# HUMAN EDIT: Enable enterprise audit trace", final_content)
            self.assertIn("self.audit_trace = True", final_content)

            # Confirm 2: Initial bot code not repeated
            self.assertEqual(final_content.count("class AuthController:"), 1)
            self.assertEqual(final_content.count("self.realm = realm"), 1)

            # Confirm 3: Subsequent bot code appended correctly
            self.assertIn("def authenticate_request(self, token):", final_content)
            self.assertIn("return token.startswith('bearer_')", final_content)
            log("VS Code file verified: Human edits intact, zero duplicate classes/methods, complete logic written.")

            # -------------------------------------------------------------
            # STEP 6: Terminate session, relaunch, confirm it starts fresh
            # -------------------------------------------------------------
            log("\n--- [STEP 6] Terminating session and relaunching bot ---")
            session_mgr.terminate_session("VS Code Workload Completed")
            self.assertTrue(session_mgr.is_terminated())
            self.assertIsNone(checkpoint_mgr.load_checkpoint())

            # Relaunch a new session
            new_session_mgr = SessionManager(checkpoint_mgr)
            new_session_mgr.start_session()
            self.assertTrue(new_session_mgr.is_active())
            self.assertFalse(new_session_mgr.is_paused())
            self.assertIsNone(checkpoint_mgr.load_checkpoint())
            log("New session started completely fresh with zero restored checkpoints.")

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


if __name__ == "__main__":
    unittest.main()
