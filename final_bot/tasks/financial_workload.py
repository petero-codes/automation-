import os
import time
import random
from typing import Tuple

from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import human_typing, human_scroll, active_wait
from core.window_manager import focus_window_by_title, maximize_active_window, close_app_safely, wait_for_window
from tasks.engineering_workload import navigate_explorer_address_bar
from tasks.shared import is_excel_installed, get_excel_executable
from core.financial_generator import FinancialGenerator, FinancialModel, FinancialCell
from core.checkpoint_manager import checkpoint_mgr

financial_gen = FinancialGenerator()

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

def task_financial_modeling(duration: int) -> bool:
    r"""
    Autonomous Financial Modeling & Analysis Workload in Microsoft Excel:
      - Resumes from exact workbook and cell coordinate if previously paused by human.
      - Checks installation; cleanly skips if Excel is missing.
      - Generates 50-90 dynamic rows across financial domains.
      - Procedural File Explorer address-bar launch into Desktop\Financial_Models.
      - Strict foreground window focus verification (zero blind typing).
      - Enters data and live accounting formulas (=SUM, =AVERAGE, =IF, =VLOOKUP).
      - Applies professional accounting borders and currency formatting.
    """
    if not is_excel_installed():
        log("[Financial Modeling] Microsoft Excel is not installed on this system. Skipping workload cleanly.")
        return False

    # Check for an interrupted paused session checkpoint
    cp = checkpoint_mgr.load_checkpoint()
    is_resuming = (
        cp is not None
        and cp.get("workload") == "FINANCIAL_MODELING"
        and cp.get("payload", {}).get("status") == "PAUSED"
    )

    if is_resuming:
        payload = cp["payload"]
        model_name = payload["model_name"]
        models_dir = payload["models_dir"]
        resume_cell_idx = payload.get("cell_index", -1)
        current_r = payload.get("current_row", 1)
        current_c = payload.get("current_col", 1)
        cells_data = payload.get("cells_data", [])
        reconstructed_cells = [
            FinancialCell(r, c, v, is_f, fmt_c)
            for (r, c, v, is_f, fmt_c) in cells_data
        ]
        model = FinancialModel(
            model_name=model_name,
            domain="Financial Modeling",
            row_count=len(reconstructed_cells),
            cells=reconstructed_cells
        )
        log(f"[Resume Controller] Restoring interrupted Excel model: {model_name} at cell ({current_r}, {current_c}) [Index {resume_cell_idx + 1}]")
    else:
        log("[Financial Modeling] Generating dynamic financial model...")
        model = financial_gen.generate_model()
        resume_cell_idx = -1
        current_r = 1
        current_c = 1
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
    excel_exe = get_excel_executable()
    model_file = os.path.join(models_dir, f"{model.model_name}.xlsx")
    import shutil
    if shutil.which("excel"):
        excel_cmd = f'excel "{model.model_name}.xlsx"'
    elif excel_exe:
        excel_cmd = f'"{excel_exe}" "{model_file}"'
    else:
        excel_cmd = f'excel "{model.model_name}.xlsx"'

    if not is_resuming or not focus_window_by_title(target_titles):
        if not navigate_explorer_address_bar(models_dir, excel_cmd):
            log("[Financial Modeling] Explorer navigation aborted or interrupted.")
            return False
        if state.is_stopped(): return False

    # Step 2: Focus & Maximize Excel Window with strict verification
    if not wait_for_window(target_titles, timeout=18):
        log("[Financial Modeling] Verification Failed: Excel window did not appear. Aborting safely.")
        close_app_safely()
        return False

    if not focus_window_by_title(target_titles):
        log("[Financial Modeling] Verification Failed: Could not focus Excel window. Aborting safely.")
        return False

    time.sleep(0.6)
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.0))

    if not is_resuming:
        # If opening a fresh Excel instance, select blank workbook
        safe_press('enter')
        time.sleep(random.uniform(0.8, 1.4))

    # Step 3: Populate Spreadsheet Grid with Human Cadence & Fine-Grained Resumability
    current_pos = (current_r, current_c)
    start_cell_idx = resume_cell_idx + 1 if is_resuming else 0

    for cell_idx in range(start_cell_idx, len(model.cells)):
        cell = model.cells[cell_idx]
        if state.is_stopped() or time.time() - start_time >= duration:
            # Interrupted: Checkpoint exact model, cell index, and (row, col) coordinate!
            checkpoint_mgr.save_checkpoint("FINANCIAL_MODELING", {
                "status": "PAUSED",
                "model_name": model.model_name,
                "models_dir": models_dir,
                "cell_index": cell_idx,
                "current_row": cell.row,
                "current_col": cell.col,
                "cells_data": [(c.row, c.col, c.value, c.is_formula, c.format_currency) for c in model.cells],
                "interrupted_at": time.time(),
            })
            log(f"[Resume Controller] Checkpointed exact Excel position: {model.model_name} at cell ({cell.row}, {cell.col}) [Index {cell_idx + 1}]")
            return False

        # Verify Excel is still in foreground before injecting inputs
        if not focus_window_by_title(target_titles):
            log("[Financial Modeling] Excel window lost focus. Halting grid entry.")
            return False

        # Move to target cell
        _navigate_cell(current_pos, (cell.row, cell.col))
        current_pos = (cell.row, cell.col)

        # Type cell value / live formula
        human_typing(cell.value, wpm=random.randint(65, 95), typos=False)
        if state.is_stopped():
            checkpoint_mgr.save_checkpoint("FINANCIAL_MODELING", {
                "status": "PAUSED",
                "model_name": model.model_name,
                "models_dir": models_dir,
                "cell_index": cell_idx,
                "current_row": cell.row,
                "current_col": cell.col,
                "cells_data": [(c.row, c.col, c.value, c.is_formula, c.format_currency) for c in model.cells],
                "interrupted_at": time.time(),
            })
            return False

        # Submit cell entry (Enter moves down by 1 in Excel default settings)
        safe_press('enter')
        current_pos = (cell.row + 1, cell.col)
        time.sleep(random.uniform(0.06, 0.20))

        # Format Currency if needed
        if cell.format_currency and random.random() < 0.25:
            safe_press('up')
            time.sleep(0.05)
            hotkey('ctrl', 'shift', '$')
            safe_press('down')
            time.sleep(0.05)

        # Natural cognitive review pause every 10-18 cells
        if cell.row % random.randint(10, 18) == 0 and cell.col == 1:
            if state.stop_automation_event.wait(random.uniform(1.2, 3.0)):
                checkpoint_mgr.save_checkpoint("FINANCIAL_MODELING", {
                    "status": "PAUSED",
                    "model_name": model.model_name,
                    "models_dir": models_dir,
                    "cell_index": cell_idx,
                    "current_row": cell.row,
                    "current_col": cell.col,
                    "cells_data": [(c.row, c.col, c.value, c.is_formula, c.format_currency) for c in model.cells],
                    "interrupted_at": time.time(),
                })
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
            time.sleep(0.12)
        time.sleep(0.4)

        # Auto-fit Column Widths: Alt -> H -> O -> I
        for key in ('alt', 'h', 'o', 'i'):
            if state.is_stopped(): break
            safe_press(key)
            time.sleep(0.12)
        time.sleep(0.5)

        # Deselect and return to top-left
        hotkey('ctrl', 'home')
        time.sleep(0.6)

        # Save Workbook: Ctrl + S
        hotkey('ctrl', 's')
        time.sleep(0.8)

    # Step 5: Natural Review Scroll Session
    remaining = duration - (time.time() - start_time)
    if remaining > 10 and not state.is_stopped():
        log("[Financial Modeling] Reviewing financial worksheet...")
        for _ in range(random.randint(4, 10)):
            if state.is_stopped(): break
            human_scroll('down', random.randint(2, 5))
            time.sleep(random.uniform(1.2, 2.5))
        for _ in range(random.randint(2, 5)):
            if state.is_stopped(): break
            human_scroll('up', random.randint(2, 4))
            time.sleep(random.uniform(1.0, 2.0))

    if not state.is_stopped():
        # Task completed end-to-end: clear checkpoint
        checkpoint_mgr.clear_checkpoint()
        log("[Financial Modeling] Workload cycle complete. Checkpoint cleared.")
        return True
    return False
