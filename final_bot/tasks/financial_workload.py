import os
import time
import random
from typing import Tuple, Dict, Any, Optional

from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import human_typing, human_scroll, active_wait
from core.window_manager import (
    focus_window_by_title,
    maximize_active_window,
    close_app_safely,
    wait_for_window,
    bind_thread_to_interactive_desktop,
)
from tasks.shared import is_excel_installed, get_excel_executable, open_app_via_run
from core.financial_generator import FinancialGenerator, FinancialModel, FinancialCell
from core.checkpoint_manager import checkpoint_mgr
from core.session_manager import session_mgr

financial_gen = FinancialGenerator()

def col_idx_to_letter(col_idx: int) -> str:
    """Converts 1-based column index (1, 2, 27) to Excel column letters ('A', 'B', 'AA')."""
    result = []
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))

def launch_or_focus_excel(workbook_path: Optional[str] = None) -> bool:
    """
    Directly and reliably launches Microsoft Excel or brings an existing instance forward,
    opening the target workbook if provided.
    """
    bind_thread_to_interactive_desktop()
    target_titles = ["Excel", "Microsoft Excel"]

    # 1. If Excel is already open, bring to front
    if focus_window_by_title(target_titles):
        log("[Financial Modeling] Microsoft Excel is already running; brought to front.")
        return True

    # 2. Try launching via Start menu
    log("[Financial Modeling] Launching Microsoft Excel via Start Menu...")
    open_app_via_run("excel")
    time.sleep(2.0)

    # 3. Direct process spawn fallback with workbook path
    if not wait_for_window(target_titles, timeout=10.0):
        excel_exe = get_excel_executable()
        args = [excel_exe] if (excel_exe and os.path.isfile(excel_exe)) else ["cmd.exe", "/c", "start", "excel"]
        if workbook_path and os.path.isfile(workbook_path):
            args.append(workbook_path)
        try:
            import subprocess
            subprocess.Popen(args)
        except Exception as e:
            log(f"[Financial Modeling] Launch error: {e}")

    # 4. Wait for window to appear, focus, and verify
    return wait_for_window(target_titles, timeout=15.0)

def _navigate_cell(curr: Tuple[int, int], target: Tuple[int, int]):
    """Navigates from current grid coordinate to target using arrow keys."""
    curr_r, curr_c = curr
    target_r, target_c = target

    # Row navigation
    d_r = target_r - curr_r
    if d_r > 0:
        for _ in range(d_r):
            if state.is_stopped(): break
            safe_press('down')
            time.sleep(0.04)
    elif d_r < 0:
        for _ in range(-d_r):
            if state.is_stopped(): break
            safe_press('up')
            time.sleep(0.04)

    # Column navigation
    d_c = target_c - curr_c
    if d_c > 0:
        for _ in range(d_c):
            if state.is_stopped(): break
            safe_press('right')
            time.sleep(0.04)
    elif d_c < 0:
        for _ in range(-d_c):
            if state.is_stopped(): break
            safe_press('left')
            time.sleep(0.04)

def save_excel_checkpoint(
    model: FinancialModel,
    models_dir: str,
    cell_idx: int,
    cell: FinancialCell,
    all_cells: list,
) -> None:
    """Persists granular Excel checkpoint with last completed and next intended cell operations."""
    workbook_path = os.path.join(models_dir, f"{model.model_name}.xlsx")
    next_idx = cell_idx + 1
    next_cell = all_cells[next_idx] if next_idx < len(all_cells) else None

    last_op = {
        "op": "WRITE_CELL",
        "cell_index": cell_idx,
        "row": cell.row,
        "col": cell.col,
        "value": cell.value,
        "is_formula": cell.is_formula,
        "cell_ref": f"{col_idx_to_letter(cell.col)}{cell.row}",
    }
    next_op = {
        "op": "WRITE_CELL",
        "cell_index": next_idx,
        "row": next_cell.row if next_cell else None,
        "col": next_cell.col if next_cell else None,
        "value": next_cell.value if next_cell else None,
        "is_formula": next_cell.is_formula if next_cell else None,
        "cell_ref": f"{col_idx_to_letter(next_cell.col)}{next_cell.row}" if next_cell else None,
    } if next_cell else None

    checkpoint_payload = {
        "status": "PAUSED",
        "model_name": model.model_name,
        "models_dir": models_dir,
        "workbook_path": workbook_path,
        "worksheet_name": "Sheet1",
        "cell_index": cell_idx,
        "current_row": cell.row,
        "current_col": cell.col,
        "target_cell": f"R{cell.row}C{cell.col}",
        "last_completed_op": last_op,
        "next_intended_op": next_op,
        "cells_data": [(c.row, c.col, c.value, c.is_formula, c.format_currency) for c in model.cells],
        "interrupted_at": time.time(),
    }
    checkpoint_mgr.save_checkpoint("FINANCIAL_MODELING", checkpoint_payload)
    target_str = next_op.get("cell_ref", "Complete") if next_op else "Complete"
    log(f"[Resume Controller] Checkpointed exact Excel position: {model.model_name} at cell ({cell.row}, {cell.col}) [Next: {target_str}]")

def reacquire_excel_application_state(
    workbook_path: str,
    worksheet_name: str,
    target_row: int,
    target_col: int,
    last_op: Optional[Dict[str, Any]] = None,
    next_op: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, int, int]:
    """
    Reacquires exact workbook, worksheet, and target cell by Excel application state.
    Validates workbook structure and prevents duplicate writes/formula execution.
    If structure has changed and target cannot be safely identified, returns False to request recovery decision.
    """
    target_ref = f"{col_idx_to_letter(target_col)}{target_row}"

    # 1. Attempt programmatic Application State reacquisition via COM (Windows pywin32)
    try:
        import win32com.client
        excel = win32com.client.GetObject(Class="Excel.Application")
        if excel:
            # A. Validate Workbook Identity
            target_wb = None
            wb_basename = os.path.basename(workbook_path).lower()
            for wb in excel.Workbooks:
                if wb.Name.lower() == wb_basename or (workbook_path and wb.FullName.lower() == workbook_path.lower()):
                    target_wb = wb
                    break

            if not target_wb and os.path.isfile(workbook_path):
                target_wb = excel.Workbooks.Open(workbook_path)

            if not target_wb:
                log(f"[Resume Controller] Workbook '{wb_basename}' is not open and cannot be found.")
                return False, f"Workbook '{wb_basename}' not open", -1, -1

            target_wb.Activate()

            # B. Validate Worksheet Identity
            target_ws = None
            for ws in target_wb.Worksheets:
                if ws.Name.lower() == worksheet_name.lower():
                    target_ws = ws
                    break

            if not target_ws:
                log(f"[Resume Controller] Safety Halt: Worksheet '{worksheet_name}' not found in workbook. Structure has changed.")
                return False, f"Worksheet '{worksheet_name}' missing", -1, -1

            target_ws.Activate()

            # C. Validate Target Cell State and Prevent Duplicate Writes
            if next_op:
                next_cell_obj = target_ws.Range(f"{col_idx_to_letter(next_op['col'])}{next_op['row']}")
                curr_val = str(next_cell_obj.Value or '').strip()
                curr_formula = str(next_cell_obj.Formula or '').strip()
                expected_next = str(next_op.get("value", "")).strip()

                # If the target cell already contains the expected value/formula, operation was already committed!
                if curr_val == expected_next or curr_formula == expected_next:
                    log(f"[Resume Controller] Operation at {target_ref} already completed in workbook. Advancing to prevent duplicate write.")
                elif curr_val != "" and curr_val != expected_next:
                    # Cell contains unexpected conflicting data -> workbook structure was modified
                    log(f"[Resume Controller] Safety Halt: Target cell {target_ref} contains conflicting data ('{curr_val}'). Workbook structure modified.")
                    return False, "Target cell contains conflicting data; workbook structure changed", -1, -1

            # D. Select target cell directly by application reference
            target_ws.Range(target_ref).Select()
            log(f"[Resume Controller] Reacquired Excel application state: Workbook '{target_wb.Name}', Sheet '{target_ws.Name}', Cell '{target_ref}'.")
            return True, "Reacquired via Excel COM", target_row, target_col
    except Exception as e:
        log(f"[Resume Controller] COM application state query note ({e}); using direct reference Go To dialog.")

    # 2. UI-Level Direct Reference Reacquisition (Go To dialog: 'Sheet1'!B15)
    # Does NOT rely on Ctrl+Home followed by relative arrow navigation!
    try:
        # F5 opens Excel Go To dialog
        safe_press('f5')
        time.sleep(0.4)
        full_ref = f"'{worksheet_name}'!{target_ref}"
        human_typing(full_ref, wpm=140, typos=False)
        time.sleep(0.2)
        safe_press('enter')
        time.sleep(0.4)
        log(f"[Resume Controller] Directly reacquired target cell via Excel Go To: {full_ref}")
        return True, "Reacquired via Excel Go To", target_row, target_col
    except Exception as e:
        log(f"[Resume Controller] Error during direct cell reacquisition: {e}")
        return False, str(e), -1, -1

def validate_excel_resume(checkpoint_payload: Dict[str, Any]) -> Tuple[bool, str, int, Tuple[int, int]]:
    """
    Validates Excel checkpoint structure, workbook identity, worksheet identity,
    and ensures operations are not blindly repeated.
    Returns (valid: bool, reason: str, next_cell_idx: int, target_coord: (row, col)).
    """
    last_idx = checkpoint_payload.get("cell_index", -1)
    cells_data = checkpoint_payload.get("cells_data", [])
    next_idx = last_idx + 1

    if not checkpoint_payload.get("model_name"):
        return False, "Checkpoint missing model_name", -1, (1, 1)

    if not checkpoint_payload.get("worksheet_name"):
        return False, "Checkpoint missing worksheet_name", -1, (1, 1)

    if next_idx >= len(cells_data):
        log("[Resume Controller] Checkpoint indicates model was already completed.")
        return False, "Model already completed end-to-end", -1, (1, 1)

    next_cell_tuple = cells_data[next_idx]
    target_coord = (next_cell_tuple[0], next_cell_tuple[1])
    return True, "Checkpoint validated", next_idx, target_coord

def task_financial_modeling(duration: int) -> bool:
    r"""
    Autonomous Financial Modeling & Analysis Workload in Microsoft Excel:
      - Restores the correct workbook and worksheet by application state.
      - Reacquires exact target cell by application reference (does not rely on Ctrl+Home relative navigation).
      - Validates workbook identity, worksheet identity, target cell, and operation state.
      - Prevents duplicate writes, formula execution, or destructive operations.
      - Stops and requests a recovery decision if workbook structure has changed.
      - Applies professional accounting borders and currency formatting.
    """
    if not is_excel_installed():
        log("[Financial Modeling] Microsoft Excel is not installed on this system. Skipping workload cleanly.")
        return False

    # Check for an interrupted paused session checkpoint
    cp = checkpoint_mgr.load_checkpoint()
    is_resuming = (
        cp is not None
        and cp.get("workload") in ("FINANCIAL_MODELING", "EXCEL")
        and (cp.get("status") == "PAUSED" or cp.get("payload", {}).get("status") == "PAUSED")
    )

    if is_resuming:
        payload = cp.get("payload", cp)
        model_name = payload.get("model_name", "Resumed_Model")
        models_dir = payload.get("models_dir", "")
        worksheet_name = payload.get("worksheet_name", "Sheet1")
        workbook_path = payload.get("workbook_path", os.path.join(models_dir, f"{model_name}.xlsx"))
        cells_data = payload.get("cells_data", [])
        last_op = payload.get("last_completed_op")
        next_op = payload.get("next_intended_op")

        valid, reason, next_cell_idx, target_coord = validate_excel_resume(payload)
        if not valid:
            log(f"[Financial Modeling] Invalid Excel checkpoint: {reason}. Aborting task safely.")
            checkpoint_mgr.clear_checkpoint()
            return False

        reconstructed_cells = [
            FinancialCell(r, c, v, is_f, fmt_c)
            for (r, c, v, is_f, fmt_c) in cells_data
        ]
        model = FinancialModel(
            model_name=model_name,
            sheet_title=worksheet_name,
            row_count=len(reconstructed_cells),
            headers=[],
            cells=reconstructed_cells
        )
        current_r, current_c = target_coord
        start_cell_idx = next_cell_idx
        log(f"[Resume Controller] Restoring interrupted Excel model: {model_name} skipping completed cells and resuming at cell ({current_r}, {current_c}) [Index {start_cell_idx + 1}]")
    else:
        log("[Financial Modeling] Generating dynamic financial model...")
        model = financial_gen.generate_model()
        start_cell_idx = 0
        current_r = 1
        current_c = 1
        worksheet_name = "Sheet1"
        workbook_path = ""
        last_op = None
        next_op = None
        log(f"[Financial Modeling] Active Model: {model.model_name} ({model.row_count} rows, {len(model.cells)} cells)")

        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
        models_dir = os.path.join(user_profile, "Desktop", "Financial_Models")
        try:
            os.makedirs(models_dir, exist_ok=True)
        except Exception as e:
            log(f"[Financial Modeling] Directory note: {e}")

    start_time = time.time()
    target_titles = ["Excel", "Microsoft Excel"]

    # Step 1: Launch or Bring Forward Excel
    if not is_resuming or not focus_window_by_title(target_titles):
        if not launch_or_focus_excel(workbook_path=workbook_path):
            log("[Financial Modeling] Verification Failed: Excel window did not appear. Aborting safely.")
            return False
        if state.is_stopped(): return False

    # Step 2: Focus & Maximize Excel Window with strict verification
    if not focus_window_by_title(target_titles):
        log("[Financial Modeling] Verification Failed: Could not focus Excel window. Aborting safely.")
        return False

    time.sleep(0.6)
    maximize_active_window()
    time.sleep(random.uniform(0.8, 1.5))

    if not is_resuming:
        # If opening a fresh Excel instance, select blank workbook
        safe_press('enter')
        time.sleep(random.uniform(0.8, 1.4))
    else:
        # Reacquire exact workbook, worksheet, and target cell by application state
        reacquired, reacq_msg, current_r, current_c = reacquire_excel_application_state(
            workbook_path=workbook_path,
            worksheet_name=worksheet_name,
            target_row=current_r,
            target_col=current_c,
            last_op=last_op,
            next_op=next_op,
        )
        if not reacquired:
            log(f"[Financial Modeling] Application state reacquisition failed: {reacq_msg}. Stopping to request recovery decision.")
            session_mgr.mark_interrupted(f"Excel recovery required: {reacq_msg}")
            return False

    # Step 3: Populate Spreadsheet Grid with Human Cadence & Fine-Grained Resumability
    current_pos = (current_r, current_c)

    for cell_idx in range(start_cell_idx, len(model.cells)):
        cell = model.cells[cell_idx]
        if state.is_stopped() or time.time() - start_time >= duration:
            # Interrupted: Checkpoint exact model, cell index, and (row, col) coordinate!
            prev_cell_idx = cell_idx - 1 if cell_idx > 0 else 0
            prev_cell = model.cells[prev_cell_idx]
            save_excel_checkpoint(model, models_dir, prev_cell_idx, prev_cell, model.cells)
            return False

        # Verify Excel is still in foreground before injecting inputs
        if not focus_window_by_title(target_titles):
            log("[Financial Modeling] Excel window lost focus. Halting grid entry.")
            return False

        # Move to target cell if not already on it
        if current_pos != (cell.row, cell.col):
            _navigate_cell(current_pos, (cell.row, cell.col))
            current_pos = (cell.row, cell.col)

        # Type cell value / live formula
        human_typing(cell.value, wpm=random.randint(65, 95), typos=False)
        if state.is_stopped():
            save_excel_checkpoint(model, models_dir, cell_idx, cell, model.cells)
            return False

        # Submit cell entry (Enter moves down by 1 in Excel default settings)
        safe_press('enter')
        current_pos = (cell.row + 1, cell.col)
        time.sleep(random.uniform(0.06, 0.18))

        # Format Currency if needed
        if cell.format_currency and random.random() < 0.25:
            safe_press('up')
            time.sleep(0.04)
            hotkey('ctrl', 'shift', '$')
            safe_press('down')
            time.sleep(0.04)

        # Natural cognitive review pause every 10-18 cells
        if cell.row % random.randint(10, 18) == 0 and cell.col == 1:
            if state.stop_automation_event.wait(random.uniform(1.0, 2.5)):
                save_excel_checkpoint(model, models_dir, cell_idx, cell, model.cells)
                return False

    # Step 4: Apply Professional Formatting & Accounting Borders
    if not state.is_stopped() and time.time() - start_time < duration:
        if not focus_window_by_title(target_titles):
            log("[Financial Modeling] Excel not focused for formatting. Aborting.")
            return False

        log("[Financial Modeling] Applying accounting borders and column formatting...")

        # Select All
        hotkey('ctrl', 'a')
        time.sleep(0.4)

        # Apply All Borders: Alt -> H -> B -> A
        for key in ('alt', 'h', 'b', 'a'):
            if state.is_stopped(): break
            safe_press(key)
            time.sleep(0.10)
        time.sleep(0.3)

        # Auto-fit Column Widths: Alt -> H -> O -> I
        for key in ('alt', 'h', 'o', 'i'):
            if state.is_stopped(): break
            safe_press(key)
            time.sleep(0.10)
        time.sleep(0.4)

        # Deselect and return to top-left
        hotkey('ctrl', 'home')
        time.sleep(0.5)

        # Save Workbook: Ctrl + S
        hotkey('ctrl', 's')
        time.sleep(0.6)

    # Step 5: Natural Review Scroll Session
    remaining = duration - (time.time() - start_time)
    if remaining > 10 and not state.is_stopped():
        log("[Financial Modeling] Reviewing financial worksheet...")
        for _ in range(random.randint(3, 7)):
            if state.is_stopped(): break
            human_scroll('down', random.randint(2, 4))
            time.sleep(random.uniform(1.0, 2.0))
        for _ in range(random.randint(1, 4)):
            if state.is_stopped(): break
            human_scroll('up', random.randint(2, 3))
            time.sleep(random.uniform(0.8, 1.8))

    if not state.is_stopped():
        # Task completed end-to-end: clear checkpoint
        checkpoint_mgr.clear_checkpoint()
        log("[Financial Modeling] Workload cycle complete. Checkpoint cleared.")
        return True
    return False
